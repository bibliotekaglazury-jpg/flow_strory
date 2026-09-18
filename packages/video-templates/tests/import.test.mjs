import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const file = new URL('../manifest.json',import.meta.url);
test('all audited components have unique catalog records',()=>{
 assert.ok(fs.existsSync(file),'manifest must be generated');
 const records=JSON.parse(fs.readFileSync(file));
 assert.equal(records.length,81);assert.equal(new Set(records.map(r=>r.id)).size,81);
 for(const r of records){assert.match(r.id,/^rve_[a-z0-9_]+$/);assert.equal(r.source.commit,'6209b724798e48ff395f8df1a6fa2d26082372b5');assert.equal(r.inputSchema.additionalProperties,false);assert.ok(r.remotion.compositionId);}
});
