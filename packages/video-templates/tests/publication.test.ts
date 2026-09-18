import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {readManifest} from '../../../scripts/templates/runtime';
import {withGatePublication,canResume} from '../../../scripts/templates/publication';
for(const phase of ['compile','browser startup','wrapper matrix'])test(`${phase} failure leaves catalog disabled`,async()=>{
 const records=readManifest().slice(0,1);records[0].enabled=true;
 const snapshots:boolean[][]=[];
 await assert.rejects(withGatePublication(records,new Set([records[0].id]),()=>{snapshots.push(records.map(r=>r.enabled));},async()=>{records[0].validation={status:'passed'};throw Error(phase);}),new RegExp(phase));
 assert.ok(snapshots.every(flags=>flags.every(value=>!value)));
 assert.equal(records[0].enabled,false);
});
test('successful publication waits until shared checks finish',async()=>{
 const records=readManifest().slice(0,1);records[0].enabled=true;records[0].curation=null;
 await withGatePublication(records,new Set([records[0].id]),()=>{},async()=>{assert.equal(records[0].enabled,false);records[0].validation={status:'passed'};});
 assert.equal(records[0].enabled,true);
});
test('resume requires matching fingerprint and actual thumbnail bytes',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'rve-resume-'));
 try{
  const file=path.join(directory,'thumb.webp'),bytes=Buffer.from('verified fixture');fs.writeFileSync(file,bytes);
  const record=readManifest()[0];record.validation={status:'passed',rendererFingerprint:'fingerprint',thumbnailSha256:crypto.createHash('sha256').update(bytes).digest('hex')};
  assert.equal(canResume(record,'fingerprint',file),true);
  assert.equal(canResume(record,'other',file),false);
  fs.writeFileSync(file,'changed');assert.equal(canResume(record,'fingerprint',file),false);
  fs.unlinkSync(file);assert.equal(canResume(record,'fingerprint',file),false);
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
