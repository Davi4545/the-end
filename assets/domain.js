// Pure, dependency-free business functions. All currency is stored in integer cents.
export const money = cents => (cents / 100).toLocaleString('pt-BR', {style:'currency',currency:'BRL'});
export const parseMoney = value => {
  if (typeof value === 'number') return Math.round(value * 100);
  const normalized = String(value ?? '').trim().replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.');
  const n = Number(normalized);
  return Number.isFinite(n) ? Math.round(n * 100) : NaN;
};
export const uid = prefix => prefix + '-' + (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`);
export const today = () => new Date().toISOString().slice(0,10);
export const localDate = iso => new Date(iso).toLocaleDateString('pt-BR');
export const isoNow = () => new Date().toISOString();
export function createSale(db, input) {
  const entries = (input.items || []).map(row => {
    const product = db.products.find(p => p.id === row.productId);
    if (!product) throw Error('Produto não encontrado.');
    const quantity = Number(row.quantity);
    if (!Number.isSafeInteger(quantity) || quantity < 1) throw Error('Quantidade inválida.');
    return { product, quantity };
  });
  if (!entries.length) throw Error('Adicione pelo menos um item.');
  const counts = new Map();
  for (const row of entries) counts.set(row.product.id, (counts.get(row.product.id) || 0) + row.quantity);
  for (const [id, qty] of counts) {
    const product = db.products.find(p => p.id === id);
    if (qty > product.stock) throw Error(`Estoque insuficiente: ${product.name} (disponível: ${product.stock}).`);
  }
  const subtotal = entries.reduce((sum, { product, quantity }) => sum + product.price * quantity, 0);
  const discount = Number(input.discount || 0);
  if (!Number.isSafeInteger(discount) || discount < 0 || discount > subtotal) throw Error('Desconto inválido.');
  const customer = db.customers.find(c => c.id === input.customerId) ?? null;
  const redeem = Number(input.redeem || 0);
  if (!Number.isSafeInteger(redeem) || redeem < 0) throw Error('Resgate inválido.');
  if (redeem && !customer) throw Error('Selecione um cliente para usar cashback.');
  if (redeem > (customer?.cashback || 0)) throw Error('Saldo de cashback insuficiente.');
  if (redeem > subtotal - discount) throw Error('Resgate maior que o total.');
  const total = subtotal - discount - redeem;
  const cashbackEarned = customer ? Math.floor(total * Math.max(0, db.settings.cashbackPercent) / 100) : 0;
  const sale = {
    id: uid('V'), number: db.nextSale++, at: isoNow(), customerId: customer?.id || null,
    items: entries.map(({ product, quantity }) => ({productId: product.id, sku:product.sku,name:product.name,price:product.price,cost:product.cost,quantity})),
    subtotal, discount, redeem, total, cashbackEarned, method:input.method, status:'concluída', fiscalStatus:'não emitido'
  };
  for (const [id, qty] of counts) {
    const product = db.products.find(p => p.id === id);
    product.stock -= qty;
    db.movements.unshift({id:uid('M'),at:sale.at,productId:id,delta:-qty,reason:`Venda #${sale.number}`});
  }
  if (customer) {
    customer.cashback = (customer.cashback || 0) - redeem + cashbackEarned;
    customer.lastPurchase = sale.at;
    if(redeem) db.wallet.unshift({id:uid('W'),at:sale.at,customerId:customer.id,saleId:sale.id,amount:-redeem,reason:'Resgate em venda'});
    if(cashbackEarned) db.wallet.unshift({id:uid('W'),at:sale.at,customerId:customer.id,saleId:sale.id,amount:cashbackEarned,reason:'Crédito por compra'});
  }
  db.sales.unshift(sale);
  return sale;
}
export function applyStock(db, productId, delta, reason) {
  const product = db.products.find(p => p.id === productId);
  if(!product) throw Error('Produto não encontrado.');
  if(!Number.isSafeInteger(delta) || delta === 0) throw Error('Informe uma quantidade inteira diferente de zero.');
  if(product.stock + delta < 0) throw Error('Movimentação resultaria em estoque negativo.');
  product.stock += delta;
  db.movements.unshift({id:uid('M'),at:isoNow(),productId,delta,reason:reason || 'Ajuste manual'});
}
export function kpis(db) {
  const count = db.sales.length;
  const revenue = db.sales.reduce((s,v)=>s+v.total,0);
  const redeemed = db.sales.reduce((s,v)=>s+v.redeem,0);
  const cost = db.sales.reduce((s,v)=>s+v.items.reduce((a,i)=>a+i.cost*i.quantity,0),0);
  return { count, revenue, ticket: count ? Math.round(revenue/count) : 0, cost, grossProfit:revenue+redeemed-cost, customers:db.customers.length, lowStock:db.products.filter(p=>p.stock<=p.minStock).length };
}
export const escapeHtml = text => String(text ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
