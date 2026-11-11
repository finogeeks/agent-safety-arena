// One owned native terminal session; never put the credential in its arguments.
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
const spec=JSON.parse(await readFile(process.argv[2],'utf8'));
await writeFile(spec.directory+'/terminal-wrapper-started.json',JSON.stringify({pid:process.pid,at:Date.now()})+'\n');
if (Array.isArray(spec.cliOverrides) && spec.cliOverrides.length) {
  console.error('Claude launch does not accept CLI overrides.');
  process.exit(1);
}
const module=await import(pathToFileURL(spec.launchModule).href);
const config=JSON.parse(await readFile(spec.launchConfig,'utf8'));
const launch=module.makeLaunch('claude',[],process.env,config,await module.resolveKey(config));
launch.env.CLAUDE_CODE_USE_POWERSHELL_TOOL='1';
delete launch.env.CLAUDE_CODE_GIT_BASH_PATH;
let executable=launch.executable;
let args=launch.args;
if (spec.confinement && spec.confinement.executable) {
  executable=spec.confinement.executable;
  args=[...spec.confinement.args, launch.executable, ...launch.args];
}
const child=spawn(executable,args,{env:launch.env,cwd:spec.workspace,stdio:'inherit',windowsHide:false});
await writeFile(spec.directory+'/terminal-processes.json',JSON.stringify({wrapperPid:process.pid,cliPid:child.pid,startedAtMs:Date.now()})+'\n');
child.on('error',()=>{console.error('The owned Claude CLI could not start.');process.exitCode=1;});
child.on('exit',code=>{process.exitCode=code??1;});
