// Observe native CLI traffic without answering or rewriting requests.
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const readline = require('node:readline');
const {spawn} = require('node:child_process');
const {pathToFileURL} = require('node:url');
let child, listener, sockets=[], secret='', directory, stream, methods=new Map(), requests=new Set();
const scrub = value => secret ? String(value).split(secret).join('[REDACTED]') : String(value);
const delay = ms => new Promise(resolve=>setTimeout(resolve,ms));
async function freePort() {
  const socket=net.createServer();await new Promise(resolve=>socket.listen(0,'127.0.0.1',resolve));
  const port=socket.address().port;await new Promise(resolve=>socket.close(resolve));return port;
}
function observe(direction, data) {
  let message;try {message=JSON.parse(data.toString());} catch {return;}
  const method=message.method,id=String(message.id);
  if(direction==='client' && method) methods.set(id,method);
  if(direction==='server' && method?.includes('requestApproval')) requests.add(id);
  const conversation=method && /^(thread\/(started|start|resume)|turn\/|item\/|error|codex\/event)/.test(method);
  const response=!method && (['thread/start','thread/resume','turn/start'].includes(methods.get(id)) || requests.has(id));
  if(conversation || response) fs.appendFileSync(directory+'/codex-native-wire.jsonl',scrub(JSON.stringify({direction,atUnixMs:Date.now(),message}))+'\n');
}
async function start(config) {
  directory=config.directory;
  const module=await import(pathToFileURL(config.launchModule).href);
  const setup=JSON.parse(fs.readFileSync(config.launchConfig,'utf8'));
  secret=await module.resolveKey(setup);
  const native=module.makeLaunch('codex',[],process.env,setup,secret);
  const port=await freePort();
  const args=['app-server','--listen',`ws://127.0.0.1:${port}`];
  for(const value of config.modelArguments)args.push('-c',value);
  child=spawn(native.executable,args,{env:native.env,cwd:config.workspace,windowsHide:true,stdio:['ignore','pipe','pipe']});
  stream=fs.createWriteStream(directory+'/codex-startup.log');
  child.stdout.on('data',d=>stream.write(scrub(d)));child.stderr.on('data',d=>stream.write(scrub(d)));
  child.on('error',e=>stream.write('Native server launch failed: '+e.code+'\n'));
  const deadline=Date.now()+90000;
  while(true) {
    if(child.exitCode!==null)throw Error('Owned Codex server exited; inspect codex-startup.log');
    try {if((await fetch(`http://127.0.0.1:${port}/readyz`,{signal:AbortSignal.timeout(1000)})).ok)break;}catch {}
    if(Date.now()>deadline)throw Error('Owned Codex server did not become ready');await delay(150);
  }
  const {WebSocket,WebSocketServer}=require(config.wsModule);
  listener=http.createServer((req,res)=>{res.writeHead(404);res.end();});
  const wss=new WebSocketServer({noServer:true});
  listener.on('upgrade',(req,socket,head)=>{
    if(req.headers.origin || req.url!=='/')return socket.destroy();
    wss.handleUpgrade(req,socket,head,peer=>wss.emit('connection',peer));
  });
  wss.on('connection',peer=>{
    const upstream=new WebSocket(`ws://127.0.0.1:${port}`);sockets.push(peer,upstream);let queue=[];
    peer.on('message',(data,binary)=>{observe('client',data);if(upstream.readyState===1)upstream.send(data,{binary});else queue.push([data,binary]);});
    upstream.on('open',()=>{for(const [data,binary] of queue)upstream.send(data,{binary});queue=[];});
    upstream.on('message',(data,binary)=>{observe('server',data);if(peer.readyState===1)peer.send(data,{binary});});
    peer.on('close',()=>upstream.close());upstream.on('close',()=>peer.close());
    peer.on('error',()=>upstream.close());upstream.on('error',()=>peer.close());
  });
  await new Promise(resolve=>listener.listen(0,'127.0.0.1',resolve));
  return {url:`ws://127.0.0.1:${listener.address().port}`,serverPid:child.pid};
}
async function close() {
  for(const socket of sockets)socket.terminate();
  listener?.close();
  if(child && child.exitCode===null)child.kill();
  stream?.end();
  setTimeout(()=>process.exit(0),250);
  return true;
}
let chain=Promise.resolve();
readline.createInterface({input:process.stdin}).on('line',line=>{
  chain=chain.then(async()=>{
    try {const request=JSON.parse(line);const value=request.action==='start'?await start(request):await close();process.stdout.write(JSON.stringify({ok:true,value})+'\n');}
    catch(error){process.stdout.write(JSON.stringify({ok:false,error:scrub(error.message)})+'\n');}
  });
}).on('close',close);
