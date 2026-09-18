/** One-time, evidence-preserving migration from the initial global fingerprint. */
import fs from 'node:fs';
import path from 'node:path';
import {readManifest,packageRoot} from './runtime';
import {sharedFiles,semanticSource,sharedFingerprint,templateFingerprint,sha256} from './fingerprint';
const reviewed=process.argv[2];if(!reviewed)throw Error('Reviewed import directory required');
const records=readManifest();
const fresh=JSON.parse(fs.readFileSync(path.join(reviewed,'manifest.json'),'utf8')) as typeof records;
const files=sharedFiles.map(file=>fs.readFileSync(file,'utf8'));
// The only shared-file change since the completed run was this erased TypeScript annotation.
const previousRuntime=files[2].replace('TemplateDefinition,NormalizedTemplateInput','TemplateDefinition').replace('inputs:NormalizedTemplateInput,output:string','inputs:Record<string,unknown>,output:string');
const candidates=[files,files.map((content,index)=>index===2?previousRuntime:content)];
const captured=candidates.find(contents=>{
 const checkpoint=sha256(JSON.stringify({templates:records.map(r=>({source:r.source.adaptedSha256,schema:r.inputSchema,remotion:r.remotion})),files:contents}));
 return records.every(r=>r.validation.status==='passed'&&r.validation.rendererFingerprint===checkpoint);
});
if(!captured)throw Error('Cannot prove the completed global renderer checkpoint; migration refused');
if(captured.some((content,index)=>semanticSource(content,sharedFiles[index])!==semanticSource(files[index],sharedFiles[index])))throw Error('Shared executable renderer changed; migration refused');
const globalFingerprint=String(records[0].validation.rendererFingerprint),shared=sharedFingerprint();
const repaired:string[]=[],retained:string[]=[];
const evidence={globalFingerprint,sharedExecutableFingerprint:shared,sharedFiles:sharedFiles.map((file,index)=>({file,checkpointSha256:sha256(captured[index]),currentSha256:sha256(files[index]),sameExecutableSource:true})),templates:records.map(record=>({id:record.id,source:record.source.adaptedSha256,inputSchema:record.inputSchema,remotion:record.remotion,validation:record.validation}))};
fs.writeFileSync(path.join(packageRoot,'validation/pre-review-checkpoint.json'),JSON.stringify(evidence,null,2)+'\n');
const repairIds=new Set(['rve_glitch_text','rve_logo_glitch_reveal','rve_sound_wave','rve_pixel_transition','rve_progress_steps']);
const save=(file:string,data:unknown)=>{fs.writeFileSync(file+'.tmp',JSON.stringify(data,null,2)+'\n');fs.renameSync(file+'.tmp',file);};
// Verify every artifact before any mutation, then disable affected records before replacing code.
for(const record of records){
 const next=fresh.find(r=>r.id===record.id);if(!next)throw Error('Missing reviewed record');
 if(sha256(fs.readFileSync(path.join(packageRoot,record.remotion.componentPath)))!==record.source.adaptedSha256)throw Error('Source verification failed');
 if(sha256(fs.readFileSync(path.join(packageRoot,'public/template-media',record.id+'.webp')))!==record.validation.thumbnailSha256)throw Error('Thumbnail verification failed');
 if(record.source.adaptedSha256!==next.source.adaptedSha256&&!repairIds.has(record.id))throw Error('Unexpected source repair');
}
const disabled=records.map(record=>repairIds.has(record.id)?{...record,enabled:false,validation:{status:'pending',reason:'Source repair in progress'}}:record);
save(path.join(packageRoot,'manifest.json'),disabled);
save(path.join(packageRoot,'public-manifest.json'),disabled.map(({source,remotion,validation,curation,...r})=>({...r,thumbnailUrl:r.thumbnail,available:r.enabled})));
for(const record of records){
 const next=fresh.find(r=>r.id===record.id);if(!next)throw Error('Missing reviewed record');
 const currentSource=fs.readFileSync(path.join(packageRoot,record.remotion.componentPath));
 if(sha256(currentSource)!==record.source.adaptedSha256)throw Error(`Current source changed: ${record.id}`);
 const thumbnail=path.join(packageRoot,'public/template-media',record.id+'.webp');
 if(sha256(fs.readFileSync(thumbnail))!==record.validation.thumbnailSha256)throw Error(`Thumbnail changed: ${record.id}`);
 const unchanged=record.source.adaptedSha256===next.source.adaptedSha256&&JSON.stringify(record.inputSchema)===JSON.stringify(next.inputSchema)&&JSON.stringify(record.remotion)===JSON.stringify(next.remotion);
 record.category=next.category;record.description=next.description;record.curation=next.curation;
 if(unchanged){
  record.validation.migratedFromGlobalFingerprint=globalFingerprint;record.validation.rendererFingerprint=templateFingerprint(record,shared);retained.push(record.id);
  record.enabled=!record.curation;
 }else{
  if(!['rve_glitch_text','rve_logo_glitch_reveal','rve_sound_wave','rve_pixel_transition','rve_progress_steps'].includes(record.id))throw Error(`Unexpected source/config change ${record.id}`);
  fs.copyFileSync(path.join(reviewed,next.remotion.componentPath),path.join(packageRoot,next.remotion.componentPath));
  record.source=next.source;record.inputSchema=next.inputSchema;record.remotion=next.remotion;
  record.enabled=false;record.validation={status:'pending',reason:'Bounded source repair requires new render evidence'};repaired.push(record.id);
 }
}
fs.copyFileSync(path.join(reviewed,'mapping-audit.json'),path.join(packageRoot,'mapping-audit.json'));

save(path.join(packageRoot,'manifest.json'),records);
save(path.join(packageRoot,'public-manifest.json'),records.map(({source,remotion,validation,curation,...r})=>({...r,thumbnailUrl:r.thumbnail,available:r.enabled})));
save(path.join(packageRoot,'validation/review-migration.json'),{globalFingerprint,sharedExecutableFingerprint:shared,retained,repaired,proof:'Original global fingerprint reproduced; shared executable source identical; each retained source/config and thumbnail hash verified.'});
console.log(JSON.stringify({retained:retained.length,repaired}));
