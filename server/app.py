"""Venqra v1.0 RC: backend local, Python 3.10+ standard library, SQLite.
Não colocar diretamente na internet sem TLS, proteção contra brute-force e revisão de segurança.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
DB_PATH = Path(os.environ.get('THE_END_DB', str(ROOT / 'the_end.db')))
PORT = int(os.environ.get('PORT', '3000'))
MAX_BODY = 256_000
ROLE_LEVEL = {'viewer':0, 'seller':1, 'manager':2, 'admin':3}

class APIError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status

def now():
    return datetime.now(timezone.utc).isoformat()

def hashed(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf8'), salt, 300_000)
    return 'pbkdf2_sha256$300000$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(key).decode()

def verify(password, encoded):
    try:
        algorithm, iterations, salt, key = encoded.split('$')
        if algorithm != 'pbkdf2_sha256': return False
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode(),base64.urlsafe_b64decode(salt),int(iterations))
        return hmac.compare_digest(candidate,base64.urlsafe_b64decode(key))
    except (ValueError, TypeError):
        return False

def require_text(body, field, maxlen=150):
    value = body.get(field)
    if not isinstance(value,str) or not value.strip() or len(value)>maxlen:
        raise APIError(422, f'{field} é obrigatório (máximo {maxlen} caracteres).')
    return value.strip()

def integer(value, field, minimum=None, maximum=None):
    if isinstance(value,bool) or not isinstance(value,int) or (minimum is not None and value<minimum) or (maximum is not None and value>maximum):
        raise APIError(422, f'{field} deve ser um número inteiro válido.')
    return value

def money(value, field, allow_zero=True):
    minimum = 0 if allow_zero else 1
    return integer(value,field,minimum,1_000_000_000_00)

def row_dict(row):
    return dict(row) if row is not None else None

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    con = sqlite3.connect(DB_PATH,timeout=10,isolation_level=None)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=10000')
    con.execute('PRAGMA journal_mode=WAL')
    try: yield con
    finally: con.close()

SCHEMA = '''
CREATE TABLE IF NOT EXISTS organizations(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stores(
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id), name TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(organization_id,id));
CREATE TABLE IF NOT EXISTS users(
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id), name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','manager','seller','viewer')),
 created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products(
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 sku TEXT NOT NULL, name TEXT NOT NULL, price_cents INTEGER NOT NULL CHECK(price_cents>=0),
 cost_cents INTEGER NOT NULL CHECK(cost_cents>=0), created_at TEXT NOT NULL,
 UNIQUE(organization_id,sku));
CREATE TABLE IF NOT EXISTS stock(
 organization_id TEXT NOT NULL REFERENCES organizations(id),store_id TEXT NOT NULL REFERENCES stores(id),
 product_id TEXT NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity>=0),
 PRIMARY KEY(organization_id,store_id,product_id));
CREATE TABLE IF NOT EXISTS customers(
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),
 name TEXT NOT NULL,email TEXT,phone TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sales(
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),store_id TEXT NOT NULL REFERENCES stores(id),
 customer_id TEXT REFERENCES customers(id),seller_id TEXT NOT NULL REFERENCES users(id),
 subtotal_cents INTEGER NOT NULL,discount_cents INTEGER NOT NULL,redeem_cents INTEGER NOT NULL,
 total_cents INTEGER NOT NULL,cashback_earned_cents INTEGER NOT NULL, payment_method TEXT NOT NULL,
 payment_status TEXT NOT NULL DEFAULT 'unverified',fiscal_status TEXT NOT NULL DEFAULT 'not_issued',
 idempotency_key TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(organization_id,idempotency_key));
CREATE TABLE IF NOT EXISTS sale_items(
 id TEXT PRIMARY KEY,sale_id TEXT NOT NULL REFERENCES sales(id),product_id TEXT NOT NULL REFERENCES products(id),
 quantity INTEGER NOT NULL,price_cents INTEGER NOT NULL,cost_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS stock_movements(
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),store_id TEXT NOT NULL REFERENCES stores(id),
 product_id TEXT NOT NULL REFERENCES products(id),delta INTEGER NOT NULL,reason TEXT NOT NULL,
 reference_id TEXT,actor_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cashback_ledger(
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),customer_id TEXT NOT NULL REFERENCES customers(id),
 sale_id TEXT REFERENCES sales(id),amount_cents INTEGER NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS goals(
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),store_id TEXT NOT NULL REFERENCES stores(id),
 month TEXT NOT NULL,target_cents INTEGER NOT NULL CHECK(target_cents>=0),UNIQUE(organization_id,store_id,month));
CREATE TABLE IF NOT EXISTS audit_events(
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id), actor_id TEXT NOT NULL REFERENCES users(id),
 action TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL, payload TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_products_org ON products(organization_id);
CREATE INDEX IF NOT EXISTS idx_customers_org ON customers(organization_id);
CREATE INDEX IF NOT EXISTS idx_sales_store_date ON sales(organization_id,store_id,created_at);
CREATE INDEX IF NOT EXISTS idx_stock_movements_org ON stock_movements(organization_id,created_at);
'''

def initialize():
    with connect() as db:
        db.executescript(SCHEMA)
        from server import expansion
        expansion.init(db)

def new_id(prefix): return prefix+'_'+secrets.token_hex(12)

def audit(db, user,action,entity_type,entity_id,payload=None):
    db.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)',
               (new_id('evt'),user['organization_id'],user['id'],action,entity_type,entity_id,json.dumps(payload or {},ensure_ascii=False),now()))

def bootstrap(name,email,password,org_name,store_name):
    if len(password)<12: raise ValueError('Senha inicial precisa de pelo menos 12 caracteres.')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
            db.rollback(); raise ValueError('A instalação já possui administrador.')
        org=new_id('org');store=new_id('sto');user=new_id('usr');ts=now()
        db.execute('INSERT INTO organizations VALUES(?,?,?)',(org,org_name,ts))
        db.execute('INSERT INTO stores VALUES(?,?,?,?)',(store,org,store_name,ts))
        db.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',(user,org,name,email.lower(),hashed(password),'admin',ts))
        db.commit()
    return {'organization':org,'store':store,'user':user}

def current_user(db, auth):
    if not auth.startswith('Bearer '): raise APIError(401,'Faça login para continuar.')
    token=auth[7:].strip()
    if len(token)!=64: raise APIError(401,'Sessão inválida.')
    digest=hashlib.sha256(token.encode()).hexdigest()
    user=db.execute('''SELECT u.id,u.name,u.email,u.role,u.organization_id
      FROM sessions s JOIN users u ON u.id=s.user_id
      WHERE s.token_hash=? AND s.expires_at>?''',(digest,now())).fetchone()
    if not user: raise APIError(401,'Sessão expirada ou inválida.')
    return row_dict(user)

def authorize(user, role):
    if ROLE_LEVEL[user['role']] < ROLE_LEVEL[role]: raise APIError(403,'Você não tem permissão para esta operação.')

def org_lookup(db, table, org, object_id):
    if table not in ('stores','products','customers'): raise ValueError('Invalid table')
    row=db.execute(f'SELECT * FROM {table} WHERE id=? AND organization_id=?',(object_id,org)).fetchone()
    if not row: raise APIError(404,f'{table}: registro não encontrado.')
    return row_dict(row)

def login(db,data):
    email=require_text(data,'email',254).lower()
    password=data.get('password')
    if not isinstance(password,str): raise APIError(422,'Senha obrigatória.')
    user=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not user or not verify(password,user['password_hash']): raise APIError(401,'Credenciais inválidas.')
    token=secrets.token_hex(32)
    db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],(datetime.now(timezone.utc)+timedelta(hours=12)).isoformat()))
    return {'token':token,'user':{'id':user['id'],'name':user['name'],'role':user['role'],'organization_id':user['organization_id']}}

def list_endpoint(db,user,path):
    org=user['organization_id']
    if path=='/api/me':return {'user':user}
    if path=='/api/stores':return {'items':[row_dict(r) for r in db.execute('SELECT * FROM stores WHERE organization_id=? ORDER BY name',(org,))]}
    if path=='/api/users':
        authorize(user,'manager')
        return {'items':[row_dict(r) for r in db.execute('SELECT id,name,email,role,created_at FROM users WHERE organization_id=? ORDER BY name',(org,))]}
    if path=='/api/products':return {'items':[row_dict(r) for r in db.execute('SELECT * FROM products WHERE organization_id=? ORDER BY name',(org,))]}
    if path=='/api/customers':return {'items':[row_dict(r) for r in db.execute('SELECT * FROM customers WHERE organization_id=? ORDER BY created_at DESC',(org,))]}
    if path=='/api/stock':
        return {'items':[row_dict(r) for r in db.execute('''SELECT s.store_id,s.product_id,s.quantity,p.name,p.sku,t.name AS store_name
          FROM stock s JOIN products p ON p.id=s.product_id AND p.organization_id=s.organization_id
          JOIN stores t ON t.id=s.store_id AND t.organization_id=s.organization_id
          WHERE s.organization_id=? ORDER BY t.name,p.name''',(org,))]}
    if path=='/api/sales':
        return {'items':[row_dict(r) for r in db.execute('''SELECT * FROM sales WHERE organization_id=? ORDER BY created_at DESC LIMIT 200''',(org,))]}
    if path=='/api/cashback':
        authorize(user,'seller')
        return {'items':[row_dict(r) for r in db.execute('SELECT * FROM cashback_ledger WHERE organization_id=? ORDER BY created_at DESC LIMIT 200',(org,))]}
    if path=='/api/goals':return {'items':[row_dict(r) for r in db.execute('SELECT * FROM goals WHERE organization_id=? ORDER BY month DESC',(org,))]}
    if path=='/api/overview':
        sales=db.execute('SELECT COUNT(*) AS count,COALESCE(SUM(total_cents),0) AS total_cents FROM sales WHERE organization_id=?',(org,)).fetchone()
        customers=db.execute('SELECT COUNT(*) FROM customers WHERE organization_id=?',(org,)).fetchone()[0]
        low=db.execute('SELECT COUNT(*) FROM stock WHERE organization_id=? AND quantity<=5',(org,)).fetchone()[0]
        return {'sales_count':sales['count'],'total_cents':sales['total_cents'],'customers_count':customers,'low_stock_count':low}
    if path=='/api/audit':
        authorize(user,'manager')
        return {'items':[row_dict(r) for r in db.execute('SELECT * FROM audit_events WHERE organization_id=? ORDER BY created_at DESC LIMIT 200',(org,))]}
    from server import expansion
    extra=expansion.list_extra(db,user,path)
    if extra is not None:return extra
    raise APIError(404,'Rota não encontrada.')

def create(db,user,path,data):
    org=user['organization_id'];ts=now()
    if path=='/api/stores':
        authorize(user,'admin');name=require_text(data,'name');id=new_id('sto')
        db.execute('INSERT INTO stores VALUES(?,?,?,?)',(id,org,name,ts));audit(db,user,'store.create','store',id)
        return {'id':id}
    if path=='/api/users':
        authorize(user,'admin');name=require_text(data,'name');email=require_text(data,'email',254).lower()
        password=require_text(data,'password',200);role=require_text(data,'role',15)
        if role not in ROLE_LEVEL:raise APIError(422,'Perfil inválido.')
        if len(password)<12:raise APIError(422,'Senha mínima de 12 caracteres.')
        id=new_id('usr')
        db.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',(id,org,name,email,hashed(password),role,ts))
        audit(db,user,'user.create','user',id,{'role':role});return {'id':id}
    if path=='/api/products':
        authorize(user,'manager');name=require_text(data,'name');sku=require_text(data,'sku',70)
        price=money(data.get('price_cents'),'price_cents');cost=money(data.get('cost_cents'),'cost_cents')
        id=new_id('prd')
        db.execute('INSERT INTO products VALUES(?,?,?,?,?,?,?)',(id,org,sku,name,price,cost,ts))
        audit(db,user,'product.create','product',id,{'sku':sku});return {'id':id}
    if path=='/api/customers':
        authorize(user,'seller');name=require_text(data,'name');id=new_id('cus')
        email=data.get('email') or None;phone=data.get('phone') or None
        if email is not None and (not isinstance(email,str) or len(email)>254):raise APIError(422,'E-mail inválido.')
        if phone is not None and (not isinstance(phone,str) or len(phone)>40):raise APIError(422,'Telefone inválido.')
        db.execute('INSERT INTO customers VALUES(?,?,?,?,?,?)',(id,org,name,email,phone,ts))
        audit(db,user,'customer.create','customer',id);return {'id':id}
    if path=='/api/stock-adjustments':
        authorize(user,'manager');store=org_lookup(db,'stores',org,data.get('store_id'))
        product=org_lookup(db,'products',org,data.get('product_id'))
        delta=integer(data.get('delta'),'delta',-1000000,1000000)
        if delta==0:raise APIError(422,'Informe variação diferente de zero.')
        reason=require_text(data,'reason',200)
        db.execute('INSERT OR IGNORE INTO stock VALUES(?,?,?,0)',(org,store['id'],product['id']))
        updated=db.execute('UPDATE stock SET quantity=quantity+? WHERE organization_id=? AND store_id=? AND product_id=? AND quantity+?>=0',
                           (delta,org,store['id'],product['id'],delta))
        if updated.rowcount!=1:raise APIError(409,'Estoque insuficiente.')
        mid=new_id('mov')
        db.execute('INSERT INTO stock_movements VALUES(?,?,?,?,?,?,?,?,?)',
                   (mid,org,store['id'],product['id'],delta,reason,None,user['id'],ts))
        audit(db,user,'stock.adjust','stock_movement',mid,{'delta':delta,'reason':reason})
        return {'id':mid}
    if path=='/api/goals':
        authorize(user,'manager');store=org_lookup(db,'stores',org,data.get('store_id'))
        month=require_text(data,'month',7)
        if len(month)!=7 or month[4]!='-' or not month[:4].isdigit() or not month[5:].isdigit() or not 1<=int(month[5:])<=12:raise APIError(422,'Mês inválido (AAAA-MM).')
        target=money(data.get('target_cents'),'target_cents')
        gid=new_id('goal')
        db.execute('INSERT INTO goals VALUES(?,?,?,?,?) ON CONFLICT(organization_id,store_id,month) DO UPDATE SET target_cents=excluded.target_cents',
                   (gid,org,store['id'],month,target))
        audit(db,user,'goal.upsert','goal',gid,{'month':month,'target_cents':target});return {'id':gid}
    if path=='/api/sales':
        authorize(user,'seller')
        key=require_text(data,'idempotency_key',120)
        existing=db.execute('SELECT id,total_cents FROM sales WHERE organization_id=? AND idempotency_key=?',(org,key)).fetchone()
        if existing:return {'id':existing['id'],'total_cents':existing['total_cents'],'duplicate':True}
        store=org_lookup(db,'stores',org,data.get('store_id'))
        customer_id=data.get('customer_id') or None
        if customer_id:org_lookup(db,'customers',org,customer_id)
        items=data.get('items')
        if not isinstance(items,list) or not 1<=len(items)<=100:raise APIError(422,'Itens da venda inválidos.')
        quantities={}; products={}
        for item in items:
            if not isinstance(item,dict):raise APIError(422,'Item inválido.')
            pid=item.get('product_id');quantity=integer(item.get('quantity'),'quantity',1,100000)
            if pid not in products:products[pid]=org_lookup(db,'products',org,pid)
            quantities[pid]=quantities.get(pid,0)+quantity
        subtotal=sum(products[pid]['price_cents']*q for pid,q in quantities.items())
        discount=money(data.get('discount_cents',0),'discount_cents')
        redeem=money(data.get('redeem_cents',0),'redeem_cents')
        if discount+redeem>subtotal:raise APIError(422,'Desconto/cashback excede subtotal.')
        if redeem and not customer_id:raise APIError(422,'É necessário cliente para resgatar cashback.')
        payment=require_text(data,'payment_method',40)
        if payment not in ('pix','cash','card','other'):raise APIError(422,'Meio de pagamento inválido.')
        if redeem:
            balance=db.execute('SELECT COALESCE(SUM(amount_cents),0) FROM cashback_ledger WHERE organization_id=? AND customer_id=?',(org,customer_id)).fetchone()[0]
            if redeem>balance:raise APIError(409,'Cashback insuficiente.')
        for pid,q in quantities.items():
            db.execute('INSERT OR IGNORE INTO stock VALUES(?,?,?,0)',(org,store['id'],pid))
            updated=db.execute('UPDATE stock SET quantity=quantity-? WHERE organization_id=? AND store_id=? AND product_id=? AND quantity>=?',
                               (q,org,store['id'],pid,q))
            if updated.rowcount!=1:raise APIError(409,f'Estoque insuficiente para {products[pid]["name"]}.')
        total=subtotal-discount-redeem
        # Crédito promocional demonstrativo. Política de cashback configurável virá em etapa posterior.
        policy=db.execute('SELECT percent_basis_points,enabled FROM loyalty_policies WHERE organization_id=?',(org,)).fetchone()
        rate=policy['percent_basis_points'] if policy and policy['enabled'] else (500 if not policy else 0)
        cashback=(total*rate)//10000 if customer_id else 0
        sale=new_id('sale')
        db.execute('INSERT INTO sales VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (sale,org,store['id'],customer_id,user['id'],subtotal,discount,redeem,total,cashback,payment,'unverified','not_issued',key,ts))
        for pid,q in quantities.items():
            product=products[pid]
            db.execute('INSERT INTO sale_items VALUES(?,?,?,?,?,?)',(new_id('item'),sale,pid,q,product['price_cents'],product['cost_cents']))
            mid=new_id('mov')
            db.execute('INSERT INTO stock_movements VALUES(?,?,?,?,?,?,?,?,?)',
                       (mid,org,store['id'],pid,-q,'Venda demonstrativa',sale,user['id'],ts))
        if redeem:
            db.execute('INSERT INTO cashback_ledger VALUES(?,?,?,?,?,?,?)',
                       (new_id('cash'),org,customer_id,sale,-redeem,'Resgate demonstrativo',ts))
        if cashback:
            db.execute('INSERT INTO cashback_ledger VALUES(?,?,?,?,?,?,?)',
                       (new_id('cash'),org,customer_id,sale,cashback,'Crédito demonstrativo',ts))
        audit(db,user,'sale.create','sale',sale,{'total_cents':total,'item_count':len(quantities)})
        return {'id':sale,'total_cents':total,'cashback_earned_cents':cashback,'payment_status':'unverified','fiscal_status':'not_issued'}
    from server import expansion
    extra=expansion.create_extra(db,user,path,data)
    if extra is not None:return extra
    raise APIError(404,'Rota não encontrada.')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt,*args): sys.stderr.write('%s %s\n'%(self.address_string(),fmt%args))
    def send_json(self,status,data):
        body=json.dumps(data,ensure_ascii=False).encode('utf8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'")
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def error_json(self,err):self.send_json(err.status,{'error':str(err)})
    def do_GET(self):
        path=urlsplit(self.path).path
        if not path.startswith('/api/'):
            path = '/index.html' if path=='/' else path
            allowed={'/index.html':'text/html; charset=utf-8','/app.js':'application/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8','/venqra-icon.svg':'image/svg+xml','/favicon.svg':'image/svg+xml'}
            if path not in allowed:self.send_error(404);return
            content=(ROOT/'web'/path.lstrip('/')).read_bytes()
            self.send_response(200);self.send_header('Content-Type',allowed[path]);self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content);return
        try:
            with connect() as db:
                user=current_user(db,self.headers.get('Authorization',''))
                self.send_json(200,list_endpoint(db,user,path))
        except APIError as e:self.error_json(e)
        except Exception:
            self.send_json(500,{'error':'Erro interno.'})
    def do_POST(self):
        path=urlsplit(self.path).path
        try:
            if not path.startswith('/api/'):raise APIError(404,'Rota não encontrada.')
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=MAX_BODY:raise APIError(413,'Requisição inválida ou muito grande.')
            try: data=json.loads(self.rfile.read(size))
            except (ValueError,UnicodeError):raise APIError(400,'JSON inválido.')
            if not isinstance(data,dict):raise APIError(422,'Objeto JSON obrigatório.')
            with connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if path=='/api/login':result=login(db,data)
                else:
                    user=current_user(db,self.headers.get('Authorization',''))
                    if path=='/api/logout':
                        token=self.headers.get('Authorization','')[7:]
                        db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
                        result={'ok':True}
                    else:result=create(db,user,path,data)
                db.commit()
                self.send_json(200 if path in ('/api/login','/api/logout') else 201,result)
        except APIError as e:self.error_json(e)
        except sqlite3.IntegrityError:self.send_json(409,{'error':'Registro duplicado ou referência inválida.'})
        except Exception:
            self.send_json(500,{'error':'Erro interno.'})

def main():
    initialize()
    if len(sys.argv)>1 and sys.argv[1]=='setup':
        import getpass
        name=input('Nome do administrador: ').strip()
        email=input('E-mail: ').strip()
        password=getpass.getpass('Senha (mínimo 12 caracteres): ')
        org=input('Empresa: ').strip() or 'Minha empresa'
        store=input('Loja inicial: ').strip() or 'Loja Matriz'
        print('Instalado:',bootstrap(name,email,password,org,store));return
    print(f'Venqra candidato v1.0 disponível em http://127.0.0.1:{PORT}')
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()

if __name__=='__main__':main()
