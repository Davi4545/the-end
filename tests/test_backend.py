import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server import app

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=app.DB_PATH
        app.DB_PATH=Path(self.tmp.name)/'test.db'
        app.initialize()
        app.bootstrap('Admin','admin@example.test','TesteDeSenhaSegura123!','Org A','Loja A')
        with app.connect() as db:
            self.admin=app.row_dict(db.execute('SELECT id,name,email,role,organization_id FROM users').fetchone())
            self.store=db.execute('SELECT id FROM stores').fetchone()[0]

    def tearDown(self):
        app.DB_PATH=self.old
        self.tmp.cleanup()

    def write(self,path,payload,user=None):
        with app.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                result=app.create(db,user or self.admin,path,payload)
                db.commit()
                return result
            except Exception:
                db.rollback()
                raise

    def test_password_and_login(self):
        with app.connect() as db:
            result=app.login(db,{'email':'admin@example.test','password':'TesteDeSenhaSegura123!'})
            actor=app.current_user(db,'Bearer '+result['token'])
            self.assertEqual(actor['role'],'admin')
            with self.assertRaises(app.APIError):app.login(db,{'email':'admin@example.test','password':'errada'})

    def test_permissions(self):
        seller=dict(self.admin,role='seller')
        with self.assertRaises(app.APIError) as err:self.write('/api/users',{'name':'Test'},seller)
        self.assertEqual(err.exception.status,403)

    def test_sale_ledger_and_idempotency(self):
        p=self.write('/api/products',{'sku':'A01','name':'Camiseta','price_cents':5000,'cost_cents':2000})['id']
        c=self.write('/api/customers',{'name':'Cliente Exemplo'})['id']
        self.write('/api/stock-adjustments',{'product_id':p,'store_id':self.store,'delta':5,'reason':'Contagem inicial'})
        payload={'store_id':self.store,'customer_id':c,'items':[{'product_id':p,'quantity':2}],'discount_cents':1000,'redeem_cents':0,'payment_method':'pix','idempotency_key':'order-0001'}
        first=self.write('/api/sales',payload)
        self.assertEqual(first['total_cents'],9000)
        self.assertEqual(first['cashback_earned_cents'],450)
        second=self.write('/api/sales',payload)
        self.assertTrue(second['duplicate'])
        with app.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM sales').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT quantity FROM stock').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT SUM(amount_cents) FROM cashback_ledger').fetchone()[0],450)
            self.assertEqual(db.execute('SELECT payment_status FROM sales').fetchone()[0],'unverified')
        # Resgate de cashback em nova venda
        payload2=dict(payload,idempotency_key='order-0002',items=[{'product_id':p,'quantity':1}],discount_cents=0,redeem_cents=450)
        second=self.write('/api/sales',payload2)
        self.assertEqual(second['total_cents'],4550)

    def test_stock_failure_rolls_back(self):
        p=self.write('/api/products',{'sku':'B02','name':'Produto','price_cents':2000,'cost_cents':500})['id']
        self.write('/api/stock-adjustments',{'product_id':p,'store_id':self.store,'delta':1,'reason':'Entrada'})
        with self.assertRaises(app.APIError) as err:self.write('/api/sales',{'store_id':self.store,'items':[{'product_id':p,'quantity':2}],'payment_method':'pix','idempotency_key':'failed'})
        self.assertEqual(err.exception.status,409)
        with app.connect() as db:
            self.assertEqual(db.execute('SELECT quantity FROM stock').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM sales').fetchone()[0],0)

    def test_organization_isolation(self):
        p=self.write('/api/products',{'sku':'C03','name':'Org A Produto','price_cents':100,'cost_cents':40})['id']
        with app.connect() as db:
            db.execute('INSERT INTO organizations VALUES(?,?,?)',('org2','Org B',app.now()))
            db.execute('INSERT INTO stores VALUES(?,?,?,?)',('store2','org2','Loja B',app.now()))
        other=dict(self.admin,organization_id='org2')
        with app.connect() as db:
            self.assertEqual(len(app.list_endpoint(db,other,'/api/products')['items']),0)
        with self.assertRaises(app.APIError):self.write('/api/stock-adjustments',{'store_id':'store2','product_id':p,'delta':1,'reason':'Inválido'},other)

if __name__=='__main__':unittest.main()
