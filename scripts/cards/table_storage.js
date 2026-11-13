// хранение: аккаунт (db, личный документ) или браузер
let DOC=null,saveT=null;
const setSave=t=>{$('savest').textContent=t};
function save(){
  const local=ls.set('belt',JSON.stringify(ST));
  if(!DOC){if(local)setSave('сохранено в этом браузере');return}
  clearTimeout(saveT);
  saveT=setTimeout(async()=>{try{await DOC.set({s:JSON.stringify(ST),u:ST.u});setSave(local?'сохранено в аккаунте':'Сохранено в аккаунте; в браузере не сохранилось.')}catch(e){setSave(local?'в аккаунт не сохранилось, осталось в этом браузере':'Не сохранено ни в аккаунте, ни в браузере. Не закрывай страницу; скачай сохранение.')}},700);
}
setTimeout(async()=>{
  setSave('сохраняется в этом браузере');
  try{
    if(!window.claude||!window.claude.use)return;
    const db=await window.claude.use('db'), user=await window.claude.use('user');
    if(!db||!user)return;
    const id=await user.id();if(!id)return;
    JDB=db;db.collection('tracks').onSnapshot(sn=>{TR=sn.docs.map(d=>({id:d.id,...d.data()}));jstat('Журнал сохраняется автоматически.');renderJournal();renderBrewingPlan()},()=>jstat('Связь с журналом потеряна — обнови страницу.',true));
    DOC=db.collection('belt').doc('state');
    let snap=await DOC.get();const shared=snap.exists, su=shared?(snap.data().u||0):-1;
    if(!shared){const old=await db.collection('data/users/'+id).doc('belt').get().catch(()=>null);if(old&&old.exists)snap=old}
    if(snap.exists){const d=snap.data();if(d&&d.s&&(d.u||0)>=(ST.u||0)){const x=JSON.parse(d.s);if(x&&x.v===1)ST=x}}
    if(!shared||(ST.u||0)>su)save();
    // подхватывать правки из других вкладок, устройств и от Claude
    DOC.onSnapshot(sn=>{if(!sn.exists||saveT&&sn.metadata&&sn.metadata.hasPendingWrites)return;const d=sn.data();if(!d||!d.s||(d.u||0)<=(ST.u||0))return;try{const x=JSON.parse(d.s);if(x&&x.v===1){ST=x;ls.set('belt',d.s);UNDO=[];renderBelt()}}catch(e){}},()=>{});
    setSave('сохраняется в аккаунте');renderBelt();
  }catch(e){setSave('сохраняется в этом браузере')}
  finally{if(!JDB){JDB=localDB();JDB.collection('tracks').onSnapshot(sn=>{TR=sn.docs.map(d=>({id:d.id,...d.data()}));jstat('Журнал сохраняется только в этом браузере (не на claude.ai).');renderJournal();renderBrewingPlan()})}
    if(matInit()){ST.u=Date.now();save()}migrate();if(ST.seed===undefined)applySeed();else renderBelt()}
},0);
