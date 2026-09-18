import fs from 'node:fs';
import {parseArgs} from 'node:util';
import {createRuntime,prepareInput,readManifest,renderTemplate} from './runtime';
async function main(){
 const {values}=parseArgs({options:{template:{type:'string'},input:{type:'string'},output:{type:'string'},duration:{type:'string'},'aspect-ratio':{type:'string'}}});
 const template=readManifest().find((r:any)=>r.id===values.template&&r.enabled);
 if(!template)throw Error('Template unavailable');
 const duration=Number(values.duration),aspect=values['aspect-ratio']||'';
 if(!template.supportedDurations.includes(duration)||!template.supportedAspectRatios.some(value=>value===aspect))throw Error('Unsupported render settings');
 if(!values.input||!values.output||!values.output.endsWith('.mp4'))throw Error('Input JSON and output MP4 paths required');
 const inputs=await prepareInput(template,JSON.parse(fs.readFileSync(values.input,'utf8')));
 const runtime=await createRuntime();
 try{const result=await renderTemplate(runtime,template,inputs,values.output,duration,aspect);console.log(JSON.stringify({output:values.output,thumbnail:result.thumbnail}));}finally{await runtime.browser.close({silent:true});}
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
