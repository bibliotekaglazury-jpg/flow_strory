/** Import only the audited MIT-declared RVE commit. No network access. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import ts from 'typescript';
import {parseArgs} from 'node:util';
import type {TemplateDefinition,InputProperty,InputSchema} from '../../packages/video-templates/src/types';
const {values,positionals}=parseArgs({options:{output:{type:'string'}},allowPositionals:true});
const root=process.cwd(), out=values.output?path.resolve(values.output):path.join(root,'packages/video-templates');
const audit=JSON.parse(fs.readFileSync('docs/audits/rve-source.json','utf8'));
if(audit.repository!=='https://github.com/reactvideoeditor/remotion-templates'||audit.commit!=='6209b724798e48ff395f8df1a6fa2d26082372b5')throw Error('Unreviewed source audit');
const source=positionals[0] || path.join(out,'.cache/rve-source');
if(!positionals[0]&&!fs.existsSync(source)){
 fs.mkdirSync(path.dirname(source),{recursive:true});
 execFileSync('git',['-c','core.hooksPath=/dev/null','clone','--no-checkout',audit.repository,source],{stdio:'inherit'});
 execFileSync('git',['-C',source,'-c','core.hooksPath=/dev/null','checkout','--detach',audit.commit],{stdio:'inherit'});
}
const hash=(s:string)=>crypto.createHash('sha256').update(s).digest('hex');
try{if(execFileSync('git',['-C',source,'rev-parse','HEAD'],{encoding:'utf8'}).trim()!==audit.commit)throw Error('Commit differs');}catch{throw Error('SOURCE_OF_TRUTH_NOT_VERIFIED');}
const files=fs.readdirSync(path.join(source,'templates')).filter(f=>f.endsWith('.tsx')).sort();
if(files.length!==audit.files.length)throw Error('Audited source count changed');
fs.mkdirSync(path.join(out,'src/imported'),{recursive:true});
fs.mkdirSync(path.join(out,'public'),{recursive:true});
const records:TemplateDefinition[]=[],imports:string[]=[],entries:string[]=[],mappings:any[]=[];
const imageSlugs=['ken-burns','parallax-pan','zoom-pulse'];
function category(slug:string){
 if(slug==='image-comparison-slider')return 'Before / After';
 if(imageSlugs.includes(slug)||/photo|polaroid|picture|split-screen|carousel/.test(slug))return 'Product';
 if(/chart|progress|counter|stat-/.test(slug))return 'Data / Metrics';
 if(/transition|wipe|whip|zoom-through|crossfade/.test(slug))return 'Other';
 if(/logo/.test(slug))return 'Branding';
 if(/subtitle|lower-third|caption/.test(slug))return 'Explainers';
 if(/text|title|typewriter/.test(slug))return 'Hooks';
 if(/subscribe|notification|social|like|quote|call-to-action/.test(slug))return slug==='quote-card'?'Testimonials':'Social Ads';
 return 'Other';
}
for(const [index,file] of files.entries()){
 const slug=file.slice(0,-4), original=fs.readFileSync(path.join(source,'templates',file),'utf8');
 const evidence=audit.files.find((f:any)=>f.path===`templates/${file}`);
 if(!evidence||hash(original)!==evidence.sha256)throw Error(`Audit hash mismatch ${file}`);
 const ast=ts.createSourceFile(file,original,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 if(!ast.statements.some(statement=>ts.isExportAssignment(statement)||('modifiers' in statement && (statement.modifiers as ts.NodeArray<ts.Modifier>)?.some(modifier=>modifier.kind===ts.SyntaxKind.DefaultKeyword))))throw Error(`No default component export: ${file}`);
 const edits:{start:number;end:number;text:string}[]=[],props:Record<string,InputProperty>={},defaults:Record<string,string>={},mapped:any[]=[];
 const names=slug==='quote-card'?['testimonial','author','body']:['headline','subheadline','body'];
 let count=0;
 function add(node:ts.Node,value:string,jsx=false){
  const repeated=['glitch-text','logo-glitch-reveal'].includes(slug)?mapped.find(entry=>entry.original===value):undefined;
  if((count>=3&&!repeated)||!/[a-zA-Z]/.test(value))return;
  const name=repeated?.field??names[count++];const safe=value.replace(/Design is not just what it looks like. Design is how it works./g,'A small change can make your everyday routine feel new.').replace(/— Steve Jobs/g,'— Your customer').replace(/ACME STUDIO/g,'YOUR BRAND').replace(/React Video Editor|Hello Remotion|Remotion/g,'Your studio');
  defaults[name]=safe;props[name]={type:'string',title:name==='subheadline'?'Subheadline':name[0].toUpperCase()+name.slice(1),maxLength:slug==='glitch-text'?24:slug==='logo-glitch-reveal'?(name==='headline'?6:name==='subheadline'?40:120):['body','testimonial'].includes(name)?240:80,default:safe};
  edits.push({start:node.getStart(ast),end:node.end,text:jsx?`{inputs.${name} ?? ${JSON.stringify(safe)}}`:`(inputs.${name} ?? ${JSON.stringify(safe)})`});
  mapped.push({field:name,sourceStart:node.getStart(ast),original:value});
 }
 function visit(node:ts.Node){
  if(ts.isVariableDeclaration(node)&&ts.isIdentifier(node.name)&&['text','title','subtitle','words'].includes(node.name.text)&&node.initializer){
   const init=node.initializer;
   if(ts.isStringLiteral(init))add(init,init.text);
   else if(ts.isCallExpression(init)&&ts.isPropertyAccessExpression(init.expression)&&ts.isStringLiteral(init.expression.expression))add(init.expression.expression,init.expression.expression.text);
   else if(ts.isArrayLiteralExpression(init)&&init.elements.every(ts.isStringLiteral)&&node.name.text==='words'&&count<3){
    const name=names[count];add(init,init.elements.map(e=>(e as ts.StringLiteral).text).join(' '));edits[edits.length-1].text+=`.split(/\\s+/)`;
   }
  }
  if(ts.isJsxText(node)){const value=node.text.replace(/\s+/g,' ').trim();if(value&&!value.startsWith('&#'))add(node,value,true);}
  ts.forEachChild(node,visit);
 }
 if(!imageSlugs.includes(slug))visit(ast);
 let adapted=original;
 for(const e of edits.sort((a,b)=>b.start-a.start))adapted=adapted.slice(0,e.start)+e.text+adapted.slice(e.end);
 if(!imageSlugs.includes(slug))adapted=adapted.replace(/export default function (\w+)\(\)/,'export default function $1(inputs: NormalizedTemplateInput = {})');
 adapted='import type { NormalizedTemplateInput } from "../types";\n'+adapted;
 const corrections:string[]=[];
 if(['glitch-text','logo-glitch-reveal'].includes(slug))corrections.push('RGB and clean copies share one field; settled company/tagline text is mapped');
 if(['sound-wave','pixel-transition','progress-steps'].includes(slug)){
  adapted=adapted.replace(/\s+transition: "[^"]+",/g,'');corrections.push('Removed wall-clock CSS transitions; existing frame values control motion');
 }
 if(slug==='floating-bubble-text'){adapted=adapted.replace('animation: `rotate 3s linear infinite`','transform: `rotate(${frame / fps * 120}deg)`');corrections.push('CSS rotation -> frame-driven transform');}
 if(slug==='typewriter-subtitle'){adapted=adapted.replace('Math.random()', 'random(`typewriter-${index}-${frame}`)').replace('import { interpolate,','import { random, interpolate,').replace('transition: "all 0.05s ease-out",','');corrections.push('Seeded frame/index randomness; removed wall-clock transition');}
 if(imageSlugs.includes(slug)){
  props.productImage={type:'string',format:'asset-id',mediaType:'image',title:'Product image'};
  adapted=adapted.replace(/import Image from "next\/image";/,'').replace('import React from "react";','import React from "react";\nimport { Img, useCurrentFrame, useVideoConfig, staticFile } from "remotion";');
  adapted=adapted.replace(/imageUrl = "https:[^"]+"/,'imageUrl = staticFile("neutral-product.svg")').replace(/<Image\b|<img\b/g,'<Img').replace(/\s+unoptimized=\{true\}/,'');
  adapted=adapted.replace(/<style jsx>\{`[\s\S]*?`\}<\/style>/,'');
  adapted=adapted.replace('  return (','  const frame = useCurrentFrame();\n  const { fps } = useVideoConfig();\n  const progress = Math.min(1, frame / (fps * duration));\n  return (');
  if(slug==='ken-burns')adapted=adapted.replace(/animation: `[^`]+`/,'transform: `scale(${1 + (scale - 1) * progress}) translate(${translateX * progress}px, ${translateY * progress}px)`');
  if(slug==='parallax-pan'){
   adapted=adapted.replace(/  const getKeyframes = \(\) => \{[\s\S]*?\n  \};/,'');
   adapted=adapted.replace(/animation: `[^`]+`/,'transform: `scale(${scale}) translate${direction.startsWith("top") || direction.startsWith("bottom") ? "Y" : "X"}(${(direction.startsWith("right") || direction.startsWith("bottom") ? 1-progress : progress) * -12}%)`');
  }
  if(slug==='zoom-pulse')adapted=adapted.replace(/animation: `[^`]+`/,'transform: `scale(${minScale + (maxScale-minScale) * (1-Math.cos(frame / fps / duration * Math.PI * 2))/2})`');
  adapted=adapted.replace('flex: 1,','width: "100%",\n        height: "100%",');
  corrections.push('External photo excluded; original neutral artwork','next/image/CSS keyframes -> Remotion Img/frame transforms');
 }
 fs.writeFileSync(path.join(out,'src/imported',file),adapted);
 const id='rve_'+slug.replaceAll('-','_'), name=slug.split('-').map(x=>x[0].toUpperCase()+x.slice(1)).join(' ');
 const inputSchema:InputSchema={type:'object',properties:props,required:[],additionalProperties:false};
 const record:TemplateDefinition={id,slug,version:'1.0.0',name,description:/image-|photo|gallery|polaroid|picture-in-picture|split-screen|carousel/.test(slug)&&!imageSlugs.includes(slug)?`${name} abstract layout demo. Uploads are not supported.`:Object.keys(props).length===0?`${name} decorative animation with fixed content.`:/chart|counter|stat-|progress/.test(slug)?`${name} animation with illustrative fixed data.`:`${name} animation.`,category:category(slug),templateType:'remotion',thumbnail:`/template-media/${id}.webp`,previewVideo:null,enabled:false,featured:['animated-text','bounce-text','ken-burns','parallax-pan','quote-card','title-split','text-highlight','zoom-pulse'].includes(slug),tags:[...new Set(slug.split('-'))],source:{repository:audit.repository,originalTemplateId:slug,commit:audit.commit,path:`templates/${file}`,sha256:evidence.sha256,adaptedSha256:hash(adapted),license:'MIT',attribution:'React Video Editor team',corrections},supportedAspectRatios:/const \{[^}]*\b(?:width|height)\b[^}]*\} = useVideoConfig\(\)/.test(original)?['16:9']:['9:16','1:1','16:9'],supportedDurations:[15,20,30],inputSchema,useCases:[category(slug)==='Branding'?'branding':category(slug)==='Product'?'product-showcase':category(slug)==='Social Ads'?'paid-ads':'organic-social'],remotion:{compositionId:`rve-${slug}`,componentPath:`src/imported/${file}`,defaultProps:defaults,propSchema:imageSlugs.includes(slug)?{type:'object',properties:{imageUrl:{type:'string',title:'Resolved image',format:'local-media'}},required:[],additionalProperties:false}:inputSchema,fps:30,width:1280,height:720,durationInFrames:450},validation:{status:'pending',reason:'Awaiting actual render gates'},curation: /chart|counter|stat-|progress/.test(slug)?{disabledReason:'Illustrative source metrics are fixed; editable metrics mapping not implemented'}:/image-|photo|gallery|polaroid|picture-in-picture|split-screen|carousel/.test(slug)&&!imageSlugs.includes(slug)?{disabledReason:'Source uses fixed media placeholders; owned image/video layout mapping not implemented'}:null};
 records.push(record);imports.push(`import C${index} from './imported/${slug}';`);entries.push(`${JSON.stringify(id)}: {component: C${index}, media: ${imageSlugs.includes(slug)}}`);mappings.push({id,fields:mapped,corrections});
}
fs.writeFileSync(path.join(out,'src/registry.generated.ts'),`// Generated by scripts/templates/import-rve.ts; do not edit.\n${imports.join('\n')}\nexport const registry = {${entries.join(',\n')}};\n`);
fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(records,null,2)+'\n');
fs.writeFileSync(path.join(out,'public-manifest.json'),JSON.stringify(records.map(({source,remotion,validation,curation,...r})=>({...r,thumbnailUrl:r.thumbnail,available:r.enabled})),null,2)+'\n');
fs.writeFileSync(path.join(out,'mapping-audit.json'),JSON.stringify(mappings,null,2)+'\n');
fs.copyFileSync(path.join(source,'README.md'),path.join(out,'UPSTREAM_README.md'));
for(const weight of [400,700,800,900])fs.copyFileSync(path.join(root,`apps/web/node_modules/@fontsource/inter/files/inter-latin-${weight}-normal.woff2`),path.join(out,`public/inter-${weight}.woff2`));
fs.copyFileSync(path.join(root,'apps/web/node_modules/@fontsource/inter/LICENSE'),path.join(out,'public/INTER-LICENSE.txt'));
console.log(`Imported ${records.length} audited components; all disabled pending render validation.`);
