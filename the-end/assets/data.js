import {today,uid,isoNow} from './domain.js';
export const STORAGE_KEY = 'the-end-demo-v1';
const exampleData = () => ({
 version:1, nextSale:1001, settings:{storeName:'Loja demonstração',cashbackPercent:5,monthlyGoal:3500000},
 products:[
  {id:'p1',sku:'CAM-001',name:'Camiseta Essential',category:'Vestuário',price:8990,cost:3600,stock:38,minStock:10},
  {id:'p2',sku:'CAL-002',name:'Calça Jeans Slim',category:'Vestuário',price:18990,cost:8500,stock:19,minStock:6},
  {id:'p3',sku:'BON-003',name:'Boné Classic',category:'Acessórios',price:6990,cost:2800,stock:5,minStock:8},
  {id:'p4',sku:'MOC-004',name:'Mochila Urban',category:'Acessórios',price:24990,cost:11200,stock:12,minStock:4},
  {id:'p5',sku:'TEN-005',name:'Tênis Street',category:'Calçados',price:32990,cost:15000,stock:7,minStock:5}
 ],
 customers:[
  {id:'c1',name:'Marina Oliveira',phone:'(62) 99999-1234',email:'marina@exemplo.com',cashback:2450,notes:'Prefere lançamentos',lastPurchase:null},
  {id:'c2',name:'Rafael Santos',phone:'(62) 98888-4567',email:'rafael@exemplo.com',cashback:0,notes:'Cliente recorrente',lastPurchase:null},
  {id:'c3',name:'Ana Costa',phone:'(62) 97777-8910',email:'ana@exemplo.com',cashback:950,notes:'Interessada em acessórios',lastPurchase:null}
 ], sales:[],wallet:[],movements:[],activities:[]
});
export function loadDb() {
 try {const raw=localStorage.getItem(STORAGE_KEY); if(raw){const parsed=JSON.parse(raw);if(parsed.version===1 && Array.isArray(parsed.products) && Array.isArray(parsed.sales)) return parsed;}}catch{}
 return exampleData();
}
export function saveDb(db){localStorage.setItem(STORAGE_KEY,JSON.stringify(db));}
export function resetDb(){const db=exampleData(); saveDb(db); return db;}
export function importDb(raw){
 const obj=JSON.parse(raw);
 if(obj?.version!==1 || !Array.isArray(obj.products)||!Array.isArray(obj.customers)||!Array.isArray(obj.sales)||!Array.isArray(obj.movements)||!Array.isArray(obj.wallet)||!obj.settings) throw Error('Arquivo de backup incompatível.');
 return obj;
}
