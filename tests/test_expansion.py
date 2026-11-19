import tempfile
import unittest
from pathlib import Path
from server import app

class ExtendedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=app.DB_PATH
        app.DB_PATH=Path(self.tmp.name)/'test.db';app.initialize()
        app.bootstrap('Admin','test@example.test','SenhaComprida123!','Empresa A','Origem')
        with app.connect() as db:
            self.admin=dict(db.execute('SELECT id,name,email,role,organization_id FROM users').fetchone())
            self.src=db.execute('SELECT id FROM stores').fetchone()[0]
        self.dst=self.write('stores',{'name':'Destino'})['id']
        self.pid=self.write('products',{'sku':'C01','name':'Produto A','price_cents':10000,'cost_cents':4500})['id']
        self.cid=self.write('customers',{'name':'Comprador'})['id']
        self.write('stock-adjustments',{'store_id':self.src,'product_id':self.pid,'delta':20,'reason':'Abertura'})

    def tearDown(self):
        app.DB_PATH=self.old;self.tmp.cleanup()

    def write(self,endpoint,data,user=None):
        with app.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                r=app.create(db,user or self.admin,'/api/'+endpoint,data)
                db.commit();return r
            except Exception:
                db.rollback();raise

    def read(self,endpoint,user=None):
        with app.connect() as db:return app.list_endpoint(db,user or self.admin,'/api/'+endpoint)

    def test_quote_does_not_decrease_stock(self):
        r=self.write('quotes',{'store_id':self.src,'customer_id':self.cid,'items':[{'product_id':self.pid,'quantity':3}]})
        self.assertEqual(r['total_cents'],30000)
        self.assertEqual(self.read('stock')['items'][0]['quantity'],20)

    def test_transfer_atomic_and_isolated(self):
        self.write('transfers',{'source_store_id':self.src,'destination_store_id':self.dst,'product_id':self.pid,'quantity':6})
        stocks={r['store_id']:r['quantity'] for r in self.read('stock')['items']}
        self.assertEqual(stocks[self.src],14);self.assertEqual(stocks[self.dst],6)
        with self.assertRaises(app.APIError):self.write('transfers',{'source_store_id':self.src,'destination_store_id':self.dst,'product_id':self.pid,'quantity':100})
        self.assertEqual({r['store_id']:r['quantity'] for r in self.read('stock')['items']},stocks)

    def test_finance_policy_and_crm(self):
        f=self.write('finance',{'store_id':self.src,'kind':'payable','description':'Energia','category':'Operacional','amount_cents':7500,'due_date':'2026-12-10'})
        self.write('finance-settle',{'id':f['id']})
        self.assertEqual(self.read('finance')['items'][0]['status'],'settled')
        self.write('loyalty-policy',{'percent_basis_points':800,'enabled':1})
        self.assertEqual(self.read('loyalty-policy')['policy']['percent_basis_points'],800)
        self.write('opportunities',{'customer_id':self.cid,'title':'Nova compra','stage':'proposal','value_cents':13000})
        task=self.write('tasks',{'customer_id':self.cid,'title':'Ligar cliente','due_date':'2026-12-10'})
        self.write('tasks-complete',{'id':task['id']})
        self.assertEqual(self.read('tasks')['items'][0]['status'],'done')
        self.assertEqual(len(self.read('opportunities')['items']),1)

    def test_return_prevents_double_return(self):
        sale=self.write('sales',{'store_id':self.src,'customer_id':self.cid,'items':[{'product_id':self.pid,'quantity':3}],'payment_method':'pix','idempotency_key':'sale-test'})
        r=self.write('returns',{'sale_id':sale['id'],'product_id':self.pid,'quantity':2})
        self.assertEqual(r['refund_status'],'not_processed')
        with self.assertRaises(app.APIError):self.write('returns',{'sale_id':sale['id'],'product_id':self.pid,'quantity':2})
        self.assertEqual(self.read('stock')['items'][0]['quantity'],19)

    def test_org_isolation_extra(self):
        with app.connect() as db:
            db.execute('INSERT INTO organizations VALUES(?,?,?)',('another','Empresa B',app.now()))
        other=dict(self.admin,organization_id='another')
        self.write('finance',{'store_id':self.src,'kind':'payable','description':'Aluguel','category':'Fixo','amount_cents':800,'due_date':'2026-12-10'})
        self.assertEqual(self.read('finance',other)['items'],[])
        with self.assertRaises(app.APIError):self.write('quotes',{'store_id':self.src,'items':[{'product_id':self.pid,'quantity':1}]},other)

if __name__=='__main__':unittest.main()
