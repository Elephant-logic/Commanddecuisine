import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const code=fs.readFileSync('full_stock_html_export.js','utf8');
const hook='window.CDCDownloadFullStockHTML=exportHtml;';
assert.ok(code.includes(hook),'Exporter test hook marker missing');
const state={
  stock:[
    {id:'a',item:'Tomato puree',cat:'Veg',unit:'g',qty:0,qtyKnown:false,supplier:''},
    {id:'b',item:'Tomato purée',cat:'Veg',unit:'g',qty:0,qtyKnown:false,supplier:''},
    {id:'c',item:'New potatoes',cat:'Veg',unit:'g',qty:0,qtyKnown:false},
    {id:'d',item:'Potatoes',cat:'Veg',unit:'g',qty:0,qtyKnown:false},
    {id:'e',item:'Parmesan cheese',cat:'Dairy',unit:'g'},
    {id:'f',item:'Parmesan',cat:'Dairy',unit:'g'},
    {id:'g',item:'Salt and black pepper, to taste',cat:'Ambient',unit:'each'},
    {id:'h',item:'Salt',cat:'Ambient',unit:'g'},
    {id:'i',item:'Black pepper',cat:'Ambient',unit:'g'},
    {id:'j',item:'Canned chopped tomatoes',cat:'Veg',unit:'g'}
  ],
  recipes:[
    {id:'recipe1',name:'Lasagne',needsReview:true,ingredients:[
      {name:'Tomato purée',stockId:'b',qty:10,unit:'g'},
      {name:'Parmesan cheese',stockId:'e',qty:90,unit:'g'},
      {name:'Salt and black pepper, to taste',stockId:'g',qty:1,unit:'each'},
      {name:'Ricotta',qty:400,unit:'g'}
    ]}
  ],
  menus:[{id:'menu1',name:'Test menu',dishIds:['recipe1']}]
};
const listeners={};
const doc={querySelectorAll(){return []}};
const win={addEventListener(event,fn){listeners[event]=fn}};
const context={window:win,document:doc,STATE:state,setInterval(){},console,Map,Set};
const modified=code.replace(hook,'window.__testFullList=fullList;'+hook);
vm.runInNewContext(modified,context);
let list=win.__testFullList();
assert.equal(list.length,8,'Clear duplicates and recipe instructions should be consolidated');
assert.equal(list.filter(x=>x.name==='Tomato purée').length,1);
assert.equal(list.filter(x=>x.name==='Parmesan').length,1);
assert.equal(list.filter(x=>x.name==='Ricotta').length,1,'Unlinked recipe ingredient must appear');
assert.ok(list.some(x=>x.name==='New potatoes'));
assert.ok(list.some(x=>x.name==='Potatoes'));
assert.ok(list.some(x=>x.name==='Canned chopped tomatoes'));
assert.ok(!list.some(x=>x.name.startsWith('Salt and black pepper')));
assert.ok(list.every(x=>x.quantity===''),'Stock levels must never set ordering quantities');
assert.ok(list.some(x=>x.name==='Tomato purée'&&x.needsReview));
assert.ok(list.some(x=>x.name==='Ricotta'&&x.usedIn.includes('Lasagne')));
assert.ok(typeof listeners['cdc:menu-saved']==='function','Missing menu success listener');
listeners['cdc:menu-saved']({detail:{name:'Test menu'}});
const blankState={stock:[],recipes:[{name:'Soup',ingredients:[{name:'Carrots',qty:200,unit:'g'}]}]};
context.STATE=blankState;
list=win.__testFullList();
assert.equal(list.length,1,'Immediately after menu import, recipe-only ingredient must export');
assert.equal(list[0].name,'Carrots');
console.log('PASS: All-stock inclusion, aliases, no false quantities, recipe fallback and menu-save signal');
