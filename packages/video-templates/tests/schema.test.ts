import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {validateInputs} from '../../../scripts/templates/schema';
import {prepareInput,readManifest} from '../../../scripts/templates/runtime';
test('rejects remote media, unknown props and oversized text before rendering',async()=>{
 const templates=readManifest();const text=templates.find(t=>t.id==='rve_animated_text')!;
 assert.throws(()=>validateInputs(text.inputSchema,{untrusted:'x'}),/Unknown input/);
 assert.throws(()=>validateInputs(text.inputSchema,{headline:7}),/Invalid type/);
 assert.throws(()=>validateInputs(text.inputSchema,{headline:'x'.repeat(81)}),/Invalid length/);
 assert.doesNotThrow(()=>validateInputs(text.inputSchema,{headline:'My product'}));
 const image=templates.find(t=>t.id==='rve_ken_burns')!;
 await assert.rejects(prepareInput(image,{productImage:'https://example.com/a.png'}),/local regular file/);
 await assert.rejects(prepareInput(image,{productImage:'/etc/hosts'}));
});
test('each public input is consumed by source and all defaults validate',()=>{
 for(const template of readManifest()){
  validateInputs(template.inputSchema,template.remotion.defaultProps);
  const source=fs.readFileSync(`packages/video-templates/${template.remotion.componentPath}`,'utf8');
  for(const field of Object.keys(template.inputSchema.properties)){
   if(field==='productImage'){assert.match(source,/src=\{imageUrl\}/);continue;}
   assert.ok(source.includes(`inputs.${field}`),`${template.id}.${field} must affect source`);
  }
  assert.doesNotMatch(source,/Math\.random\(|next\/image|animation:\s*`|https:\/\/images\./);
 }
});
test('public manifest contains no source or renderer implementation fields',()=>{
 const records=JSON.parse(fs.readFileSync('packages/video-templates/public-manifest.json','utf8'));
 for(const r of records){assert.equal(r.source,undefined);assert.equal(r.remotion,undefined);assert.equal(r.thumbnail,r.thumbnailUrl);assert.equal(r.enabled,r.available);}
});

test('manifest reader rejects duplicate IDs, missing renderer config and unreviewed source',async()=>{
 const {parseManifest}=await import('../../../scripts/templates/manifest');
 const records=readManifest();
 assert.throws(()=>parseManifest([...records,records[0]]),/duplicate/);
 assert.throws(()=>parseManifest([{...records[0],remotion:undefined}]),/renderer config/);
 assert.throws(()=>parseManifest([{...records[0],source:{...records[0].source,commit:'unreviewed'}}]),/Unreviewed source/);
});
