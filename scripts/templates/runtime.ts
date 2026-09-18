import fs from 'node:fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {getCompositions,renderMedia,renderStill,openBrowser} from '@remotion/renderer';
import sharp from 'sharp';
import {validateInputs} from './schema';
import type {TemplateDefinition,NormalizedTemplateInput} from '../../packages/video-templates/src/types';
import {parseManifest} from './manifest';
export const packageRoot=path.resolve('packages/video-templates');
export const readManifest=()=>parseManifest(JSON.parse(fs.readFileSync(path.join(packageRoot,'manifest.json'),'utf8')));
export const dimensions=(aspect:string)=>aspect==='9:16'?{width:720,height:1280}:aspect==='1:1'?{width:720,height:720}:{width:1280,height:720};
export async function prepareInput(template:TemplateDefinition,input:unknown){
 validateInputs(template.inputSchema,input);
 const prepared={...template.remotion.defaultProps,...input};
 if(prepared.productImage){
  // Only the trusted local worker supplies filesystem paths. Public API resolves owned assets first.
  const local=prepared.productImage;
  if(typeof local!=='string'||!path.isAbsolute(local)||!fs.statSync(local).isFile())throw Error('Product image must be a local regular file');
  const bytes=fs.readFileSync(local);if(bytes.length>10*1024*1024)throw Error('Image too large');
  const metadata=await sharp(bytes,{limitInputPixels:40_000_000}).metadata();
  if(!['png','jpeg','webp'].includes(metadata.format??''))throw Error('Unsupported image content');
  prepared.productImage=`data:image/${metadata.format};base64,${bytes.toString('base64')}`;
 }
 return prepared;
}
export async function createRuntime(){
 const serveUrl=await bundle({entryPoint:path.join(packageRoot,'src/root.tsx'),publicDir:path.join(packageRoot,'public')});
 console.log('Bundle compiled');
 const browser=await openBrowser('chrome',{browserExecutable:process.env.REMOTION_BROWSER_EXECUTABLE||undefined});
 const compositions=await getCompositions(serveUrl,{puppeteerInstance:browser});
 return {serveUrl,browser,compositions};
}
export async function renderTemplate(runtime:Awaited<ReturnType<typeof createRuntime>>,template:TemplateDefinition,inputs:NormalizedTemplateInput,output:string,duration:number,aspect:string,video=true,previewFrameRange?:[number,number]){
 const registered=runtime.compositions.find(c=>c.id===template.remotion.compositionId);
 if(!registered)throw Error('Composition not registered');
 const composition={...registered,props:{templateId:template.id,inputs},...dimensions(aspect),durationInFrames:duration*30};
 const errors:string[]=[];
 const common={serveUrl:runtime.serveUrl,composition,inputProps:{templateId:template.id,inputs},puppeteerInstance:runtime.browser,onBrowserLog:(log:any)=>{if(log.type==='error')errors.push(log.text)},timeoutInMilliseconds:120_000};
 fs.mkdirSync(path.dirname(output),{recursive:true});
 // Thumbnail is a genuine frame from this registered composition.
 console.log(`Rendering thumbnail: ${template.id}`);
 const still=await renderStill({...common,frame:Math.min(60,composition.durationInFrames-1),imageFormat:'png'});
 const thumbnail=output.replace(/\.[^.]+$/,'.webp');
 await sharp(still.buffer).webp({quality:88}).toFile(thumbnail);
 if(video){
  console.log(`Rendering MP4: ${template.id}; ${composition.durationInFrames} frames`);
  let lastProgress=-1;
  await renderMedia({...common,codec:'h264',outputLocation:output,concurrency:2,crf:24,frameRange:previewFrameRange,onProgress:progress=>{const step=Math.floor(progress.renderedFrames/30);if(step!==lastProgress){lastProgress=step;console.log(`Rendered frames: ${progress.renderedFrames}/${composition.durationInFrames}`);}}});
  console.log(`MP4 complete: ${template.id}`);
 }
 if(errors.length)throw Error(`Browser errors: ${errors.join('; ')}`);
 return {thumbnail,composition,errors};
}
