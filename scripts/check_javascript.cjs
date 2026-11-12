// Один обход исходников и страниц: компиляция; с --lint также ESLint.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const args=process.argv.slice(2),lint=args.includes('--lint');
if(args.some(arg=>arg.startsWith('--')&&arg!=='--lint'))throw Error('Неизвестный параметр');
const root=path.resolve(args.find(arg=>arg!=='--lint')||path.join(__dirname,'..'));

function* sources(directory){
  for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
    const file=path.join(directory,entry.name);
    if(entry.isDirectory()){
      if(!['.git','node_modules','__pycache__','.ruff_cache'].includes(entry.name))yield* sources(file);
    }else if(entry.isFile()){
      if(/\.(cjs|js)$/.test(file)&&path.relative(root,file).split(path.sep)[0]==='scripts'){
        yield {name:file,text:fs.readFileSync(file,'utf8'),page:false};
      }else if(entry.name.endsWith('.html')&&!entry.name.endsWith('_tpl.html')){
        const html=fs.readFileSync(file,'utf8');
        if(/__RULE_[A-Z0-9_]+__/.test(html))throw Error(file+': остались маркеры правил');
        const scripts=[...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)]
          .filter(match=>!/\bsrc\s*=|type\s*=\s*["']application\//i.test(match[1])).map(match=>match[2]);
        if(scripts.length)yield {name:file,text:scripts.join('\n'),page:true};
      }
    }
  }
}

async function main(){
  let engines;
  if(lint){
    const {ESLint}=require('eslint'),globals=require('globals');
    const structural={'no-unreachable':'error','no-dupe-args':'error','no-dupe-keys':'error',
      'no-func-assign':'error','no-const-assign':'error'};
    const engine=page=>new ESLint({overrideConfigFile:true,overrideConfig:[{files:['**/*.js'],
      languageOptions:{ecmaVersion:2022,sourceType:'script',globals:page?globals.browser:{...globals.node,...globals.browser}},
      rules:{...structural,'no-undef':page?'error':'off'}}]});
    engines={source:engine(false),page:engine(true)};
  }
  let checked=0,failures=0;
  for(const source of sources(root)){
    new vm.Script(source.text,{filename:source.name});
    checked++;
    if(engines){
      const [result]=await engines[source.page?'page':'source'].lintText(source.text,{filePath:'audit.js'});
      for(const message of result.messages){
        failures++;
        console.error(`${source.name}:${message.line}:${message.column}: ${message.ruleId}: ${message.message}`);
      }
    }
  }
  if(failures)process.exitCode=1;
  else console.log(`PASS: compiled ${checked} JavaScript sources/pages; no template markers${lint?'; ESLint passed':''}`);
}
main().catch(error=>{console.error(error);process.exitCode=1});
