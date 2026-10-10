// Компиляция без исполнения: исходники инструментов и скрипты свежего HTML.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(process.argv[2]||path.join(__dirname,'..'));
let checked=0;
function parse(source,file){new vm.Script(source,{filename:file});checked++}
function visit(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
 const file=path.join(dir,entry.name);
 if(entry.isDirectory()&&!['node_modules','__pycache__'].includes(entry.name))visit(file);
 else if(entry.isFile()&&/\.(cjs|js)$/.test(file))parse(fs.readFileSync(file,'utf8'),file);
}}
visit(path.join(root,'scripts'));
for(const filename of ['Помощник варки.html','Пульт мастера.html']){
 const html=fs.readFileSync(path.join(root,filename),'utf8');
 if(/__RULE_[A-Z0-9_]+__/.test(html))throw Error(filename+': остались маркеры правил');
 let index=0;for(const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)){
  if(/\bsrc\s*=/.test(match[1])||/type\s*=\s*["']application\//i.test(match[1]))continue;
  parse(match[2],filename+':script-'+(++index));
 }
}
console.log(`PASS: syntax compiled for ${checked} JavaScript sources; no template markers`);
