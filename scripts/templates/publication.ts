import fs from 'node:fs';
import crypto from 'node:crypto';
import type {TemplateDefinition} from '../../packages/video-templates/src/types';
export async function withGatePublication(records:TemplateDefinition[],ids:Set<string>,save:()=>void,work:()=>Promise<void>):Promise<void>{
 for(const record of records)if(ids.has(record.id)){record.enabled=false;record.validation={...record.validation,status:'pending'};}
 save();
 try{
  await work();
  for(const record of records)if(ids.has(record.id))record.enabled=record.validation.status==='passed'&&!record.curation;
  save();
 }catch(error){
  // Compile, startup and shared-wrapper failures affect the common bundle.
  for(const record of records)record.enabled=false;
  save();throw error;
 }
}
export function canResume(record:TemplateDefinition,fingerprint:string,thumbnail:string):boolean{
 if(record.validation.status!=='passed'||record.validation.rendererFingerprint!==fingerprint)return false;
 try{return crypto.createHash('sha256').update(fs.readFileSync(thumbnail)).digest('hex')===record.validation.thumbnailSha256;}catch{return false;}
}
