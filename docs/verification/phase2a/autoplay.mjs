import {createRequire} from 'node:module';
import {writeFile} from 'node:fs/promises';
const require=createRequire(new URL('../../../apps/web/package.json',import.meta.url));
const {chromium}=require('@playwright/test');
const browser=await chromium.launch({channel:'chrome',headless:true});
const evidence=[];
try {
 for(const [name,width,height] of [['desktop',1222,1287],['mobile',390,844]]) {
  const page=await browser.newPage({viewport:{width,height}});
  await page.goto('http://127.0.0.1:3000',{waitUntil:'networkidle'});
  const video=page.getByLabel('Example product video');
  await video.scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>{const v=document.querySelector('video[aria-label="Example product video"]');return v&&v.currentTime>0.1&&!v.paused;});
  const state=await video.evaluate(v=>({autoPlay:v.autoplay,muted:v.muted,loop:v.loop,playsInline:v.playsInline}));
  if(!Object.values(state).every(Boolean))throw Error('Autoplay attributes missing');
  await video.evaluate(v=>{v.currentTime=v.duration-0.2;});
  await page.waitForFunction(()=>{const v=document.querySelector('video[aria-label="Example product video"]');return v&&v.currentTime<2&&!v.paused;});
  await page.screenshot({path:new URL(`autoplay-${name}.png`,import.meta.url).pathname,fullPage:true});
  evidence.push({name,...state,automaticStart:true,restartedAfterEnd:true});
  await page.close();
 }
} finally {await browser.close();}
await writeFile(new URL('autoplay.json',import.meta.url),JSON.stringify(evidence,null,2));
console.log(evidence);
