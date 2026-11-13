// One owned native terminal session; never put the credential in its arguments.
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
const spec=JSON.parse(await readFile(process.argv[2],'utf8'));
await writeFile(spec.directory+'/terminal-wrapper-started.json',JSON.stringify({pid:process.pid,at:Date.now()})+'\n');
const extras=spec.cliOverrides??[];
if (!Array.isArray(extras) || (extras.length &&
    (extras.length!==2 || extras[0]!=='--settings' || typeof extras[1]!=='string'))) {
  throw new Error('Claude launch accepts only a prepared session settings file.');
}
if (extras.length) {
  const bytes=await readFile(extras[1]);
  if (createHash('sha256').update(bytes).digest('hex')!==spec.sessionSettingsSha256) {
    throw new Error('Prepared Claude session settings changed.');
  }
}
const module=await import(pathToFileURL(spec.launchModule).href);
const config=JSON.parse(await readFile(spec.launchConfig,'utf8'));
const launch=module.makeLaunch('claude',extras,process.env,config,await module.resolveKey(config));
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
