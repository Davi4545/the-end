"""Módulos adicionais locais. Não confirma pagamentos, créditos ou documentos fiscais reais."""
import json
from datetime import date

SCHEMA = '''
CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,store_id TEXT NOT NULL,customer_id TEXT,actor_id TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',total_cents INTEGER NOT NULL,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quote_items(id TEXT PRIMARY KEY,quote_id TEXT NOT NULL REFERENCES quotes(id),product_id TEXT NOT NULL,quantity INTEGER NOT NULL,price_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS crm_opportunities(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,customer_id TEXT NOT NULL,title TEXT NOT NULL,stage TEXT NOT NULL,value_cents INTEGER NOT NULL,actor_id TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS crm_tasks(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,customer_id TEXT,title TEXT NOT NULL,due_date TEXT,status TEXT NOT NULL,actor_id TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS finance_entries(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,store_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,category TEXT NOT NULL,description TEXT NOT NULL,amount_cents INTEGER NOT NULL,due_date TEXT NOT NULL,source_id TEXT,actor_id TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stock_transfers(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,source_store_id TEXT NOT NULL,destination_store_id TEXT NOT NULL,product_id TEXT NOT NULL,quantity INTEGER NOT NULL,actor_id TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sale_returns(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,sale_id TEXT NOT NULL,product_id TEXT NOT NULL,store_id TEXT NOT NULL,quantity INTEGER NOT NULL,refund_estimate_cents INTEGER NOT NULL,cashback_reversal_cents INTEGER NOT NULL,refund_status TEXT NOT NULL DEFAULT 'not_processed',actor_id TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS loyalty_policies(organization_id TEXT PRIMARY KEY,percent_basis_points INTEGER NOT NULL DEFAULT 500,enabled INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fiscal_documents(id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,sale_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,provider TEXT,external_id TEXT,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_quotes_org ON quotes(organization_id,created_at);
CREATE INDEX IF NOT EXISTS idx_finance_org ON finance_entries(organization_id,due_date);
CREATE INDEX IF NOT EXISTS idx_returns_sale ON sale_returns(sale_id,product_id);
CREATE INDEX IF NOT EXISTS idx_tasks_org ON crm_tasks(organization_id,status);
'''

def init(db):
    db.executescript(SCHEMA)

def helpers():
    from server import app as a
    return a

def check_date(value, name):
    a=helpers()
    if not isinstance(value,str):raise a.APIError(422,f'{name} inválida.')
    try:date.fromisoformat(value)
    except ValueError:raise a.APIError(422,f'{name} inválida. Use AAAA-MM-DD.')
    return value

def list_extra(db,user,path):
    a=helpers();o=user['organization_id']
    tables={
      '/api/quotes':('quotes','created_at'),'/api/opportunities':('crm_opportunities','created_at'),
      '/api/tasks':('crm_tasks','created_at'),'/api/finance':('finance_entries','created_at'),
      '/api/transfers':('stock_transfers','created_at'),'/api/returns':('sale_returns','created_at'),
      '/api/fiscal-documents':('fiscal_documents','created_at')}
    if path in tables:
        if path in ('/api/finance','/api/fiscal-documents'):a.authorize(user,'manager')
        table,sort=tables[path]
        return {'items':[dict(r) for r in db.execute(f'SELECT * FROM {table} WHERE organization_id=? ORDER BY {sort} DESC LIMIT 300',(o,))]}
    if path=='/api/loyalty-policy':
        row=db.execute('SELECT * FROM loyalty_policies WHERE organization_id=?',(o,)).fetchone()
        return {'policy':dict(row) if row else {'percent_basis_points':500,'enabled':1}}
    if path=='/api/intelligence':
        low=[dict(r) for r in db.execute('''SELECT p.name,t.name AS store_name,s.quantity FROM stock s JOIN products p ON p.id=s.product_id JOIN stores t ON t.id=s.store_id WHERE s.organization_id=? AND s.quantity<=5 ORDER BY s.quantity LIMIT 20''',(o,))]
        inactive=[dict(r) for r in db.execute('''SELECT c.id,c.name,MAX(s.created_at) last_purchase FROM customers c LEFT JOIN sales s ON s.customer_id=c.id AND s.organization_id=c.organization_id WHERE c.organization_id=? GROUP BY c.id HAVING MAX(s.created_at) IS NULL OR MAX(s.created_at)<datetime('now','-60 days') ORDER BY last_purchase LIMIT 20''',(o,))]
        outstanding=db.execute("SELECT COALESCE(SUM(CASE WHEN kind='receivable' THEN amount_cents ELSE -amount_cents END),0) FROM finance_entries WHERE organization_id=? AND status='open'",(o,)).fetchone()[0]
        return {'low_stock':low,'inactive_customers':inactive,'open_finance_net_cents':outstanding}
    if path=='/api/reports':
        daily=[dict(r) for r in db.execute("SELECT substr(created_at,1,10) AS day,COUNT(*) sales,COALESCE(SUM(total_cents),0) total_cents FROM sales WHERE organization_id=? GROUP BY day ORDER BY day DESC LIMIT 31",(o,))]
        ranking=[dict(r) for r in db.execute('''SELECT p.name,SUM(si.quantity) quantity,SUM(si.price_cents*si.quantity) gross_cents FROM sale_items si JOIN sales s ON s.id=si.sale_id JOIN products p ON p.id=si.product_id WHERE s.organization_id=? GROUP BY p.id ORDER BY gross_cents DESC LIMIT 20''',(o,))]
        finance=[dict(r) for r in db.execute("SELECT kind,status,COALESCE(SUM(amount_cents),0) amount_cents FROM finance_entries WHERE organization_id=? GROUP BY kind,status",(o,))]
        return {'daily_sales':daily,'top_products':ranking,'finance':finance,'notice':'Pagamentos não confirmados; receitas registradas não equivalem a caixa recebido.'}
    return None

def create_extra(db,user,path,data):
    a=helpers();o=user['organization_id'];ts=a.now()
    if path=='/api/quotes':
        a.authorize(user,'seller');store=a.org_lookup(db,'stores',o,data.get('store_id'))
        customer=data.get('customer_id') or None
        if customer:a.org_lookup(db,'customers',o,customer)
        items=data.get('items');total=0;details=[]
        if not isinstance(items,list) or not 1<=len(items)<=100:raise a.APIError(422,'Informe itens do orçamento.')
        for row in items:
            if not isinstance(row,dict):raise a.APIError(422,'Item inválido.')
            p=a.org_lookup(db,'products',o,row.get('product_id'))
            quantity=a.integer(row.get('quantity'),'quantity',1,100000)
            total+=p['price_cents']*quantity
            details.append((p['id'],quantity,p['price_cents']))
        notes=str(data.get('notes') or '')[:500]
        qid=a.new_id('quo');db.execute('INSERT INTO quotes VALUES(?,?,?,?,?,?,?,?,?)',(qid,o,store['id'],customer,user['id'],'open',total,notes,ts))
        for pid,q,price in details:db.execute('INSERT INTO quote_items VALUES(?,?,?,?,?)',(a.new_id('qitem'),qid,pid,q,price))
        a.audit(db,user,'quote.create','quote',qid);return {'id':qid,'total_cents':total}
    if path=='/api/opportunities':
        a.authorize(user,'seller');customer=a.org_lookup(db,'customers',o,data.get('customer_id'))
        title=a.require_text(data,'title');stage=a.require_text(data,'stage',30)
        if stage not in ('new','contact','proposal','won','lost'):raise a.APIError(422,'Etapa inválida.')
        value=a.money(data.get('value_cents',0),'value_cents');oid=a.new_id('opp')
        db.execute('INSERT INTO crm_opportunities VALUES(?,?,?,?,?,?,?,?)',(oid,o,customer['id'],title,stage,value,user['id'],ts))
        a.audit(db,user,'crm.opportunity','opportunity',oid);return {'id':oid}
    if path=='/api/tasks':
        a.authorize(user,'seller');title=a.require_text(data,'title');customer=data.get('customer_id') or None
        if customer:a.org_lookup(db,'customers',o,customer)
        due=data.get('due_date') or None
        if due:due=check_date(due,'Data')
        task=a.new_id('task');db.execute('INSERT INTO crm_tasks VALUES(?,?,?,?,?,?,?,?)',(task,o,customer,title,due,'open',user['id'],ts))
        a.audit(db,user,'crm.task','task',task);return {'id':task}
    if path=='/api/tasks-complete':
        a.authorize(user,'seller');tid=a.require_text(data,'id',100)
        result=db.execute("UPDATE crm_tasks SET status='done' WHERE id=? AND organization_id=? AND status='open'",(tid,o))
        if result.rowcount!=1:raise a.APIError(404,'Tarefa aberta não encontrada.')
        a.audit(db,user,'crm.task.complete','task',tid);return {'id':tid}
    if path=='/api/finance':
        a.authorize(user,'manager');store=a.org_lookup(db,'stores',o,data.get('store_id'))
        kind=a.require_text(data,'kind',15)
        if kind not in ('payable','receivable'):raise a.APIError(422,'Tipo inválido.')
        description=a.require_text(data,'description',200);category=a.require_text(data,'category',60)
        amount=a.money(data.get('amount_cents'),'amount_cents',False);due=check_date(data.get('due_date'),'Vencimento')
        fid=a.new_id('fin');db.execute('INSERT INTO finance_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(fid,o,store['id'],kind,'open',category,description,amount,due,None,user['id'],ts))
        a.audit(db,user,'finance.create','finance',fid);return {'id':fid}
    if path=='/api/finance-settle':
        a.authorize(user,'manager');fid=a.require_text(data,'id',100)
        result=db.execute("UPDATE finance_entries SET status='settled' WHERE id=? AND organization_id=? AND status='open'",(fid,o))
        if result.rowcount!=1:raise a.APIError(404,'Lançamento aberto não encontrado.')
        a.audit(db,user,'finance.settle','finance',fid,{'note':'Baixa manual não corresponde a conciliação bancária.'});return {'id':fid}
    if path=='/api/loyalty-policy':
        a.authorize(user,'manager');percent=a.integer(data.get('percent_basis_points'),'percent_basis_points',0,2000)
        enabled=a.integer(data.get('enabled'),'enabled',0,1)
        db.execute('INSERT INTO loyalty_policies VALUES(?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET percent_basis_points=excluded.percent_basis_points,enabled=excluded.enabled,updated_at=excluded.updated_at',(o,percent,enabled,ts))
        a.audit(db,user,'loyalty.policy','organization',o);return {'ok':True}
    if path=='/api/transfers':
        a.authorize(user,'manager');src=a.org_lookup(db,'stores',o,data.get('source_store_id'));dst=a.org_lookup(db,'stores',o,data.get('destination_store_id'))
        if src['id']==dst['id']:raise a.APIError(422,'Unidades precisam ser diferentes.')
        product=a.org_lookup(db,'products',o,data.get('product_id'))
        quantity=a.integer(data.get('quantity'),'quantity',1,100000);tid=a.new_id('transfer')
        db.execute('INSERT OR IGNORE INTO stock VALUES(?,?,?,0)',(o,src['id'],product['id']))
        db.execute('INSERT OR IGNORE INTO stock VALUES(?,?,?,0)',(o,dst['id'],product['id']))
        updated=db.execute('UPDATE stock SET quantity=quantity-? WHERE organization_id=? AND store_id=? AND product_id=? AND quantity>=?',(quantity,o,src['id'],product['id'],quantity))
        if updated.rowcount!=1:raise a.APIError(409,'Estoque insuficiente na origem.')
        db.execute('UPDATE stock SET quantity=quantity+? WHERE organization_id=? AND store_id=? AND product_id=?',(quantity,o,dst['id'],product['id']))
        db.execute('INSERT INTO stock_transfers VALUES(?,?,?,?,?,?,?,?)',(tid,o,src['id'],dst['id'],product['id'],quantity,user['id'],ts))
        for store_id,delta in ((src['id'],-quantity),(dst['id'],quantity)):
            db.execute('INSERT INTO stock_movements VALUES(?,?,?,?,?,?,?,?,?)',(a.new_id('mov'),o,store_id,product['id'],delta,'Transferência interna',tid,user['id'],ts))
        a.audit(db,user,'stock.transfer','transfer',tid);return {'id':tid}
    if path=='/api/returns':
        a.authorize(user,'manager');sale_id=a.require_text(data,'sale_id',100);product_id=a.require_text(data,'product_id',100)
        sale=db.execute('SELECT * FROM sales WHERE id=? AND organization_id=?',(sale_id,o)).fetchone()
        if not sale:raise a.APIError(404,'Venda não encontrada.')
        line=db.execute('SELECT SUM(quantity) AS qty,MAX(price_cents) AS price FROM sale_items WHERE sale_id=? AND product_id=?',(sale_id,product_id)).fetchone()
        if not line or line['qty'] is None:raise a.APIError(404,'Produto não pertence à venda.')
        count=a.integer(data.get('quantity'),'quantity',1,100000)
        returned=db.execute('SELECT COALESCE(SUM(quantity),0) FROM sale_returns WHERE sale_id=? AND product_id=?',(sale_id,product_id)).fetchone()[0]
        if count>line['qty']-returned:raise a.APIError(409,'Quantidade devolvida excede a vendida.')
        # Crédito fiscal e financeiro NÃO é processado; valor é apenas estimativa proporcional.
        refund=(sale['total_cents']*line['price']*count)//max(sale['subtotal_cents'],1)
        refund=min(refund,sale['total_cents']-db.execute('SELECT COALESCE(SUM(refund_estimate_cents),0) FROM sale_returns WHERE sale_id=?',(sale_id,)).fetchone()[0])
        reversal=0
        if sale['customer_id'] and sale['cashback_earned_cents']:
            previously=db.execute('SELECT COALESCE(SUM(cashback_reversal_cents),0) FROM sale_returns WHERE sale_id=?',(sale_id,)).fetchone()[0]
            reversal=min(sale['cashback_earned_cents']-previously,(sale['cashback_earned_cents']*line['price']*count)//max(sale['subtotal_cents'],1))
            # Não debitar saldo maior do que já está disponível; análise manual se gastou cashback.
            balance=db.execute('SELECT COALESCE(SUM(amount_cents),0) FROM cashback_ledger WHERE organization_id=? AND customer_id=?',(o,sale['customer_id'])).fetchone()[0]
            reversal=max(0,min(reversal,balance))
        rid=a.new_id('ret')
        db.execute('INSERT INTO sale_returns VALUES(?,?,?,?,?,?,?,?,?,?,?)',(rid,o,sale_id,product_id,sale['store_id'],count,refund,reversal,'not_processed',user['id'],ts))
        db.execute('INSERT OR IGNORE INTO stock VALUES(?,?,?,0)',(o,sale['store_id'],product_id))
        db.execute('UPDATE stock SET quantity=quantity+? WHERE organization_id=? AND store_id=? AND product_id=?',(count,o,sale['store_id'],product_id))
        db.execute('INSERT INTO stock_movements VALUES(?,?,?,?,?,?,?,?,?)',(a.new_id('mov'),o,sale['store_id'],product_id,count,'Devolução registrada (sem reembolso)',rid,user['id'],ts))
        if reversal:db.execute('INSERT INTO cashback_ledger VALUES(?,?,?,?,?,?,?)',(a.new_id('cash'),o,sale['customer_id'],sale_id,-reversal,'Estorno por devolução demonstrativa',ts))
        a.audit(db,user,'sale.return','return',rid,{'refund_estimate_cents':refund,'refund_status':'not_processed'})
        return {'id':rid,'refund_estimate_cents':refund,'cashback_reversal_cents':reversal,'refund_status':'not_processed'}
    if path=='/api/fiscal-documents':
        raise a.APIError(501,'Emissão fiscal indisponível: configurar provedor e homologar a operação antes de usar.')
    return None
