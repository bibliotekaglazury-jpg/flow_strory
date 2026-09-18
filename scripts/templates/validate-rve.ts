import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import sharp from 'sharp';
import {renderStill,renderFrames} from '@remotion/renderer';
import {createRuntime,readManifest,renderTemplate,prepareInput,packageRoot,dimensions} from './runtime';
import {validateInputs} from './schema';
import {withGatePublication,canResume} from './publication';
import {sharedFingerprint,templateFingerprint} from './fingerprint';
import type {TemplateDefinition} from '../../packages/video-templates/src/types';
const atomicJSON=(file:string,value:unknown)=>{const temporary=file+`.${process.pid}.tmp`;fs.writeFileSync(temporary,JSON.stringify(value,null,2)+'\n');fs.renameSync(temporary,file);};
const hash=(b:Buffer)=>crypto.createHash('sha256').update(b).digest('hex');
const featured=['animated-text','bounce-text','ken-burns','parallax-pan','quote-card','title-split','text-highlight','zoom-pulse'];
const project=(records:TemplateDefinition[])=>records.map(({source,remotion,validation,curation,...r})=>({...r,thumbnailUrl:r.thumbnail,available:r.enabled}));
type FrameEvidence={aspect:string;duration:number;frame:number;sha256:string};
async function main(){
 const manifest=readManifest();
 const selectionIndex=process.argv.indexOf('--only');
 const selected=new Set(selectionIndex<0?manifest.map(r=>r.id):(process.argv[selectionIndex+1]||'').split(','));
 if([...selected].some(id=>!manifest.some(r=>r.id===id)))throw Error('Unknown selected template');
 const cached=new Map(manifest.map(r=>[r.id,structuredClone(r)]));
 // Only advertise source-native geometry for components that use output width/height.
 for(const template of manifest){
  const source=fs.readFileSync(path.join(packageRoot,template.remotion.componentPath),'utf8');
  if(/const \{[^}]*\b(?:width|height)\b[^}]*\} = useVideoConfig\(\)/.test(source))template.supportedAspectRatios=['16:9'];
  if(template.inputSchema.properties.productImage)template.remotion.propSchema={type:'object',properties:{imageUrl:{type:'string',title:'Resolved image',format:'local-media'}},required:[],additionalProperties:false};
 }
 const shared=sharedFingerprint();
 let runtime:Awaited<ReturnType<typeof createRuntime>>;
 const save=()=>{atomicJSON(path.join(packageRoot,'manifest.json'),manifest);atomicJSON(path.join(packageRoot,'public-manifest.json'),project(manifest));};
 const outputDir=path.join(packageRoot,'public/template-media');fs.mkdirSync(outputDir,{recursive:true});
 const evidenceDir=path.join(packageRoot,'validation');fs.mkdirSync(evidenceDir,{recursive:true});
 const sampleImage=path.join(evidenceDir,'custom-product.png');

 const duplicates=new Map<string,string>();
 const wrapperEvidence:Record<string,FrameEvidence[]>={};
 async function frameSet(template:TemplateDefinition,aspect:string,duration:number){
  const registered=runtime.compositions.find(c=>c.id===template.remotion.compositionId);if(!registered)throw Error('Composition missing');
  const frames:FrameEvidence[]=[],errors:string[]=[];
  await renderFrames({serveUrl:runtime.serveUrl,composition:{...registered,...dimensions(aspect),durationInFrames:duration*30},inputProps:{templateId:template.id,inputs:template.remotion.defaultProps},frames:[30,duration*30-1],outputDir:null,timeoutInMilliseconds:120_000,imageFormat:'png',concurrency:1,puppeteerInstance:runtime.browser,onStart:()=>{},onFrameUpdate:()=>{},onFrameBuffer:(buffer,frame)=>{frames.push({aspect,duration,frame,sha256:hash(buffer)});},onBrowserLog:log=>{if(log.type==='error')errors.push(log.text)}});
  if(errors.length)throw Error(errors.join('; '));if(frames.length!==2)throw Error('Incomplete frame pair');return frames;
 }
 try{
  await withGatePublication(manifest,selected,save,async()=>{
   execFileSync('pnpm',['exec','tsc','-p','packages/video-templates/tsconfig.json'],{stdio:'inherit'});
   runtime=await createRuntime();
   await sharp({create:{width:1280,height:720,channels:3,background:'#b04768'}}).png().toFile(sampleImage);
  for(const [index,template] of manifest.entries()){
   if(!selected.has(template.id))continue;
   if(hash(fs.readFileSync(path.join(packageRoot,template.remotion.componentPath)))!==template.source.adaptedSha256)throw Error(`Source hash mismatch: ${template.id}`);
   const rendererFingerprint=templateFingerprint(template,shared);
   const cachedRecord=cached.get(template.id)!;
   if(process.argv.includes('--resume')&&canResume(cachedRecord,rendererFingerprint,path.join(outputDir,template.id+'.webp'))){
    template.validation=structuredClone(cachedRecord.validation);duplicates.set(String(template.validation.thumbnailSha256),template.id);console.log(`${index+1}/${manifest.length} ${template.id}: retained verified result`);continue;
   }
   const started=Date.now();
   try{
    validateInputs(template.inputSchema,template.remotion.defaultProps);
    const registered=runtime.compositions.find(c=>c.id===template.remotion.compositionId);if(!registered)throw Error('Composition missing');
    const frames=await frameSet(template,'16:9',15);
    const editable=Object.keys(template.inputSchema.properties);
    let customInputVerified=editable.length===0;
    if(editable.length){
     const customInputs=await prepareInput(template,Object.fromEntries(editable.map(key=>[key,key==='productImage'?sampleImage:'Zebra launch'.slice(0,template.inputSchema.properties[key].maxLength??80)])));
     const errors:string[]=[];
     // The resolved composition.props must change, not only renderer inputProps.
     for(const frame of [30,120,360]){
      const common={serveUrl:runtime.serveUrl,frame,timeoutInMilliseconds:120_000,imageFormat:'png' as const,puppeteerInstance:runtime.browser,onBrowserLog:(log:{type:string;text:string})=>{if(log.type==='error')errors.push(log.text)}};
      const custom=await renderStill({...common,composition:{...registered,props:{templateId:template.id,inputs:customInputs}},inputProps:{templateId:template.id,inputs:customInputs}});
      const baseline=frame===30?frames.find(f=>f.frame===30)!.sha256:hash((await renderStill({...common,composition:registered,inputProps:{templateId:template.id,inputs:template.remotion.defaultProps}})).buffer!);
      if(hash(custom.buffer!)!==baseline){customInputVerified=true;break;}
     }
     if(errors.length)throw Error(errors.join('; '));
     if(!customInputVerified)throw Error('Mapped input variant did not change rendered frames');
    }
    const individualFieldFrames:Record<string,string>={};
    if(['rve_glitch_text','rve_logo_glitch_reveal'].includes(template.id)){
     const common={serveUrl:runtime.serveUrl,frame:120,timeoutInMilliseconds:120_000,imageFormat:'png' as const,puppeteerInstance:runtime.browser};
     const baseline=hash((await renderStill({...common,composition:registered,inputProps:{templateId:template.id,inputs:template.remotion.defaultProps}})).buffer!);
     for(const field of editable){
      const inputs=await prepareInput(template,{[field]:'Zebra launch'.slice(0,template.inputSchema.properties[field].maxLength??80)});
      const variant=hash((await renderStill({...common,composition:{...registered,props:{templateId:template.id,inputs}},inputProps:{templateId:template.id,inputs}})).buffer!);
      if(variant===baseline)throw Error(`Field ${field} does not affect settled frame120`);individualFieldFrames[field]=variant;
     }
    }
    const result=await renderTemplate(runtime,template,template.remotion.defaultProps,path.join(outputDir,template.id+'.mp4'),15,'16:9',false);
    const thumbHash=hash(fs.readFileSync(result.thumbnail));
    if(duplicates.has(thumbHash))throw Error(`Duplicate thumbnail of ${duplicates.get(thumbHash)}`);
    duplicates.set(thumbHash,template.id);
    template.enabled=false;template.featured=featured.includes(template.slug);template.previewVideo=null;
    template.validation={status:'passed',rendererFingerprint,curation:template.curation,compile:true,schema:true,registered:true,customInputVerified,individualFieldFrames,browserErrors:[],frameCount:frames.length,frames,thumbnailSha256:thumbHash,mp4:false,elapsedMs:Date.now()-started};
   }catch(error){template.enabled=false;template.validation={status:'failed',reason:String(error)};}
   console.log(`${index+1}/${manifest.length} ${template.id}: ${template.validation.status}`);
   atomicJSON(path.join(packageRoot,'manifest.json'),manifest);
  }
  // Shared wrapper checks cover text, image and duration-sensitive motion at every advertised setting.
  for(const id of ['rve_animated_text','rve_ken_burns','rve_camera_shake']){
   const template=manifest.find(r=>r.id===id&&r.validation.status==='passed');if(!template)throw Error(`Wrapper representative missing: ${id}`);
   wrapperEvidence[id]=[];
   for(const aspect of template.supportedAspectRatios)for(const duration of template.supportedDurations)wrapperEvidence[id].push(...await frameSet(template,aspect,duration));
   atomicJSON(path.join(evidenceDir,'wrapper-matrix.json'),wrapperEvidence);
  }
  });
  for(const id of selectionIndex<0?['rve_animated_text','rve_ken_burns','rve_quote_card']:[]){
   const template=manifest.find(r=>r.id===id&&r.enabled);if(!template)continue;
   try{
    await renderTemplate(runtime,template,template.remotion.defaultProps,path.join(outputDir,template.id+'.mp4'),15,'16:9',true,[0,89]);
    template.previewVideo=`/template-media/${template.id}.mp4`;template.validation.mp4=true;template.validation.previewDurationSeconds=3;
   }catch(error){template.validation.previewError=String(error);}
   atomicJSON(path.join(packageRoot,'manifest.json'),manifest);
  }
 }finally{if(runtime!)await runtime.browser.close({silent:true});}
 atomicJSON(path.join(packageRoot,'public-manifest.json'),project(manifest));
 const stats={discovered:manifest.length,imported:manifest.length,validated:manifest.filter(r=>r.validation.status==='passed').length,enabled:manifest.filter(r=>r.enabled).length,disabled:manifest.filter(r=>!r.enabled).length,featured:manifest.filter(r=>r.enabled&&r.featured).length,thumbnails:manifest.filter(r=>r.validation.status==='passed').length,previewVideos:manifest.filter(r=>r.previewVideo).length,categories:Object.fromEntries([...new Set(manifest.map(r=>r.category))].map(c=>[c,manifest.filter(r=>r.category===c).length])),failures:manifest.filter(r=>r.validation.status==='failed').map(r=>({id:r.id,...r.validation})),curatedDisabled:manifest.filter(r=>r.curation).map(r=>({id:r.id,reason:r.curation!.disabledReason}))};
 atomicJSON(path.join(packageRoot,'stats.json'),stats);console.log(JSON.stringify(stats));
 if(stats.failures.length)process.exitCode=1;
}
main().catch(error=>{console.error(error);process.exitCode=1;});
