import fs from 'node:fs';
import crypto from 'node:crypto';
import ts from 'typescript';
import type {TemplateDefinition} from '../../packages/video-templates/src/types';
export const sha256=(value:string|Buffer)=>crypto.createHash('sha256').update(value).digest('hex');
export const sharedFiles=['packages/video-templates/src/root.tsx','packages/video-templates/src/style.css','scripts/templates/runtime.ts','scripts/templates/schema.ts'];
export function semanticSource(source:string,file:string){return file.endsWith('.css')?source:ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,removeComments:true}}).outputText;}
export function sharedFingerprint(){return sha256(JSON.stringify(sharedFiles.map(file=>semanticSource(fs.readFileSync(file,'utf8'),file))));}
export function templateFingerprint(template:TemplateDefinition,shared=sharedFingerprint()){
 return sha256(JSON.stringify({shared,source:template.source.adaptedSha256,schema:template.inputSchema,remotion:template.remotion,aspects:template.supportedAspectRatios,durations:template.supportedDurations}));
}
