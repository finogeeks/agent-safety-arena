// One owned native terminal session; never put the credential in its arguments.
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
const spec=JSON.parse(await readFile(process.argv[2],'utf8'));
await writeFile(spec.directory+'/terminal-wrapper-started.json',JSON.stringify({pid:process.pid,at:Date.now()})+'\n');
const module=await import(pathToFileURL(spec.launchModule).href);
const config=JSON.parse(await readFile(spec.launchConfig,'utf8'));
const extras=Array.isArray(spec.cliOverrides)?spec.cliOverrides:[];
const launch=module.makeLaunch('codex',[...extras,'--remote',spec.url,'-C',spec.workspace],process.env,config,await module.resolveKey(config));
const child=spawn(launch.executable,launch.args,{env:launch.env,cwd:spec.workspace,stdio:'inherit',windowsHide:false});
await writeFile(spec.directory+'/terminal-processes.json',JSON.stringify({wrapperPid:process.pid,cliPid:child.pid,startedAtMs:Date.now()})+'\n');
child.on('error',()=>{console.error('The owned Codex CLI could not start.');process.exitCode=1;});
child.on('exit',code=>{process.exitCode=code??1;});
