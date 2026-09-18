import {createRequire} from 'node:module';
import {writeFile} from 'node:fs/promises';
const require=createRequire(new URL('../../../apps/web/package.json',import.meta.url));
const {chromium}=require('@playwright/test');
const browser=await chromium.launch({channel:'chrome',headless:true});
const evidence=[];
try {
 for(const [name,route,width,height] of [['templates-desktop','/templates',1440,1000],['templates-mobile','/templates',390,844],['create-desktop','/',1222,1287],['create-mobile','/',390,844]]){
  const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:3000${route}`,{waitUntil:'networkidle',timeout:120000});
  if(route==='/templates') await page.waitForFunction(()=>{const s=document.querySelector('[role="status"]');return s&&/^[1-9]\d* templates$/.test(s.textContent??'')&&!document.querySelector('[role="alert"]');},{},{timeout:60000});
  else await page.waitForFunction(()=>document.querySelectorAll('.template-gallery img').length>0,{},{timeout:60000});
  await page.evaluate(async()=>{await document.fonts.ready;await Promise.all(Array.from(document.images).map(i=>i.decode().catch(()=>{})));});
  const images=await page.locator('img[src*="template-media"]').evaluateAll(imgs=>imgs.map(i=>({src:i.getAttribute('src'),loaded:i.complete&&i.naturalWidth>0})));
  if(images.some(i=>!i.loaded))throw Error(`${name}: unloaded imported thumbnails`);
  await page.screenshot({path:new URL(`${name}.png`,import.meta.url).pathname,fullPage:true});
  await page.screenshot({path:new URL(`${name}-viewport.png`,import.meta.url).pathname,fullPage:false});
  let exampleVideo=null;
  if(route==='/') {
   const video=page.getByLabel('Example product video');
   await video.evaluate(async v=>{v.muted=true;await v.play();});
   await page.waitForFunction(()=>{const v=document.querySelector('video[aria-label="Example product video"]');return v&&v.currentTime>0.1;});
   exampleVideo=await video.evaluate(v=>{v.pause();return {width:v.videoWidth,height:v.videoHeight,duration:v.duration,played:v.currentTime>0.1,error:v.error?.message??null};});
  }
  evidence.push({name,route,width,height,errors,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),importedThumbnails:images.length,exampleVideo});
  await page.close();
 }
}finally{await browser.close();}
await writeFile(new URL('visual.json',import.meta.url),JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence));
