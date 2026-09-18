import {chromium} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
const out='../../docs/verification';await mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});
const results=[];
for(const width of [1222,1440,1280,1024,768,390]){
 const page=await browser.newPage({viewport:{width,height:width===390?844:1287},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.PLAYWRIGHT_BASE_URL||'http://127.0.0.1:3000',{waitUntil:'networkidle',timeout:120000});
 await page.waitForFunction(()=>{const input=document.querySelector('input[aria-label="Product image"]');return input&&!input.disabled;},{},{timeout:60000});
 await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:`${out}/create-${width}.png`,fullPage:true});
 results.push({width,errors,overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),workspace:await page.locator('.workspace').boundingBox(),preview:await page.locator('.preview-frame, .showcase-horizontal-window').first().boundingBox()});
 await page.close();
}
await browser.close();await writeFile(`${out}/visual-measurements.json`,JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
