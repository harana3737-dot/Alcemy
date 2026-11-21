// Распаковка данных из этой сборки. Импорт игровых сохранений здесь не проходит.
function unpackHtmlPayload([format, size, encoded]) {
  if(format!=='alcemy-deflate')throw new Error('Неизвестный формат встроенных данных');
  const bytes=Uint8Array.from(atob(encoded),character=>character.charCodeAt(0));
  const result=inflateHtmlPayload(bytes,new Uint8Array(size));
  if(result.length!==size)throw new Error('Повреждён встроенный блок данных');
  return new TextDecoder('utf-8',{fatal:true}).decode(result);
}

function readCompressedJson(id) {
  const payload=JSON.parse(document.getElementById(id).textContent);
  return JSON.parse(unpackHtmlPayload(payload));
}
