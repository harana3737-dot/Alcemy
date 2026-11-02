// Проверка валидатора без браузера: обычный JSON, граница глубины и опасные ключи.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'table_tools.js'),'utf8');
const start=source.indexOf('function validateSnapshot('),end=source.indexOf('\nlet PENDING_SAVE',start);
assert(start>=0&&end>start,'validator source must be found');
const context=vm.createContext({});vm.runInContext(source.slice(start,end),context);
const valid={format:'alcemy-helper',version:1,settings:{},tracks:[],state:{v:1,T:0,
 people:[{id:'p1',name:'Талис',limit:7}],bag:[],ent:[],rests:[],r10:[],lrs:[],trig:[],log:[],
 mat:{gold:1,herbs:[],ess:[],cat:[],other:[]}}};
const validate=data=>{context.data=data;return vm.runInContext('validateSnapshot(data)',context)};
assert.equal(validate(valid),valid);
const crafts={...valid,crafts:{version:1,smith:{rolls:[{d:10,b:7,dc:14}],mods:{str:4},sample:false},scroll:{lvl:'1',when:'rush','c-more':true}}};
assert.equal(validate(crafts),crafts);
assert.doesNotThrow(()=>validate({...valid,crafts:{version:1,smith:null,scroll:null}}));
for(const value of [{version:2,smith:null,scroll:null},{version:1,smith:{rolls:[{d:'<img>'}]},scroll:{}},{version:1,smith:null,scroll:{lvl:{}}}]){
 assert.throws(()=>validate({...valid,crafts:value}),/Неверный/);
}
const nested=depth=>{let value={};for(let i=0;i<depth;i++)value={child:value};return value};
assert.doesNotThrow(()=>validate({...valid,extra:nested(31)})); // root 0, extra 1 → 32
assert.throws(()=>validate({...valid,extra:nested(32)}),/слишком вложенный/);
const deep={...valid,extra:nested(15000)};
assert.throws(()=>validate(deep),/слишком вложенный/);
for(const key of ['__proto__','constructor','prototype']){
 const bad=JSON.parse(JSON.stringify(valid));bad.extra=JSON.parse(`{"${key}":{}}`);
 assert.throws(()=>validate(bad),/Неверный/);
}
assert.equal(validate(valid),valid);
console.log('PASS: valid snapshot, legacy and craft data, invalid crafts, depth boundary, deep input, unsafe keys');
