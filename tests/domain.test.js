import test from 'node:test';
import assert from 'node:assert/strict';
import {createSale,applyStock,kpis,parseMoney} from '../assets/domain.js';
const makeDb=()=>({nextSale:1001,settings:{cashbackPercent:5},products:[{id:'p1',sku:'A',name:'Produto A',stock:5,price:10000,cost:4000,minStock:2}],customers:[{id:'c1',name:'Cliente',cashback:1000}],sales:[],movements:[],wallet:[]});
test('converts BRL strings to integer cents',()=>{assert.equal(parseMoney('1.234,56'),123456);assert.equal(parseMoney('20,00'),2000);});
test('sale decreases stock, grants cashback and records ledger',()=>{const db=makeDb();const sale=createSale(db,{customerId:'c1',items:[{productId:'p1',quantity:2}],discount:1000,redeem:500,method:'pix'});assert.equal(sale.total,18500);assert.equal(sale.cashbackEarned,925);assert.equal(db.products[0].stock,3);assert.equal(db.customers[0].cashback,1425);assert.equal(db.movements[0].delta,-2);assert.equal(db.wallet.length,2);assert.equal(kpis(db).revenue,18500);});
test('rejects over-selling, including duplicate cart entries',()=>{const db=makeDb();assert.throws(()=>createSale(db,{items:[{productId:'p1',quantity:3},{productId:'p1',quantity:3}],method:'pix'}),/Estoque insuficiente/);assert.equal(db.products[0].stock,5);});
test('rejects cashback overspending without mutating data',()=>{const db=makeDb();assert.throws(()=>createSale(db,{customerId:'c1',items:[{productId:'p1',quantity:1}],redeem:1500,method:'pix'}),/Saldo/);assert.equal(db.sales.length,0);assert.equal(db.customers[0].cashback,1000);});
test('stock movements never go negative',()=>{const db=makeDb();assert.throws(()=>applyStock(db,'p1',-6,'Ajuste'),/negativo/);applyStock(db,'p1',-2,'Ajuste');assert.equal(db.products[0].stock,3);assert.equal(db.movements.length,1);});
