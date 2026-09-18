import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';
import {packageRoot,readManifest} from './runtime';
async function main(){
 const records=readManifest().filter((r:any)=>r.validation.status==='passed');
 const fingerprints:Record<string,number[]>={},pixelsById:Record<string,Buffer>={};
 for(const record of records){
  const pixels=await sharp(path.join(packageRoot,'public/template-media',record.id+'.webp')).resize(9,8,{fit:'fill'}).grayscale().raw().toBuffer();
  pixelsById[record.id]=await sharp(path.join(packageRoot,'public/template-media',record.id+'.webp')).resize(128,72,{fit:'fill'}).removeAlpha().raw().toBuffer();
  fingerprints[record.id]=Array.from({length:64},(_,i)=>Number(pixels[Math.floor(i/8)*9+i%8]>pixels[Math.floor(i/8)*9+i%8+1]));
 }
 const decisions=JSON.parse(fs.readFileSync(path.join(packageRoot,'similarity-decisions.json'),'utf8')).decisions as {a:string;b:string;aSourceSha256:string;bSourceSha256:string;decision:string;reason:string}[];
 const candidates:unknown[]=[];
 for(let i=0;i<records.length;i++)for(let j=i+1;j<records.length;j++){
  const a=records[i].id,b=records[j].id,distance=fingerprints[a].reduce((n,bit,k)=>n+Number(bit!==fingerprints[b][k]),0);
  if(distance<=4){
   const difference=pixelsById[a].reduce((total,value,k)=>total+Math.abs(value-pixelsById[b][k]),0)/pixelsById[a].length;
   const reviewed=decisions.find(d=>d.a===a&&d.b===b&&d.aSourceSha256===records[i].source.adaptedSha256&&d.bSourceSha256===records[j].source.adaptedSha256);
   candidates.push({a,b,distance,meanAbsoluteColorDifference:difference,status:difference>0.5?'distinct-pixel-content':reviewed?.decision??'review-required',note:reviewed?.reason??'Hash candidates are compared at128x72 RGB; source motion determines whether a shared end layout is redundant.'});
  }
 }
 fs.writeFileSync(path.join(packageRoot,'near-duplicates.json'),JSON.stringify({method:'64-bit difference hash, Hamming <=4; then mean RGB difference <=0.5 on128x72 pixels',candidates},null,2)+'\n');
 const tiles=await Promise.all(records.map(async(r:any,i:number)=>({input:await sharp(path.join(packageRoot,'public/template-media',r.id+'.webp')).resize(256,144).extend({bottom:28,background:'#ffffff'}).composite([{input:Buffer.from(`<svg width="256" height="28"><text x="5" y="19" font-family="sans-serif" font-size="12">${r.slug}</text></svg>`),top:144,left:0}]).png().toBuffer(),left:(i%5)*256,top:Math.floor(i/5)*172})));
 if(tiles.length)await sharp({create:{width:1280,height:Math.ceil(tiles.length/5)*172,channels:3,background:'#fff'}}).composite(tiles).png().toFile(path.join(packageRoot,'validation/contact-sheet.png'));
 console.log(JSON.stringify({reviewCandidates:candidates.length}));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
