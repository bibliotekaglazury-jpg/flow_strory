import type {TemplateDefinition} from '../../packages/video-templates/src/types';
const object=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
export function parseManifest(value:unknown):TemplateDefinition[]{
 if(!Array.isArray(value))throw Error('Manifest must be an array');
 const ids=new Set<string>();
 for(const record of value){
  if(!object(record))throw Error('Invalid manifest record');
  for(const key of ['id','slug','version','name','description','category','templateType','thumbnail'])if(typeof record[key]!=='string')throw Error(`Missing manifest field ${key}`);
  if(record.templateType!=='remotion'||typeof record.enabled!=='boolean'||typeof record.featured!=='boolean'||!(record.previewVideo===null||typeof record.previewVideo==='string'))throw Error('Invalid template metadata');
  const id=record.id as string;if(!/^rve_[a-z0-9_]+$/.test(id)||ids.has(id))throw Error('Invalid or duplicate template ID');ids.add(id);
  for(const key of ['tags','supportedAspectRatios','supportedDurations','useCases'])if(!Array.isArray(record[key]))throw Error(`Missing manifest list ${key}`);
  if(!object(record.source)||!['repository','originalTemplateId','commit','path','sha256','adaptedSha256','license','attribution'].every(key=>typeof (record.source as Record<string,unknown>)[key]==='string'))throw Error('Invalid source metadata');
  if(record.source.commit!=='6209b724798e48ff395f8df1a6fa2d26082372b5')throw Error('Unreviewed source commit');
  if(!object(record.inputSchema)||record.inputSchema.type!=='object'||record.inputSchema.additionalProperties!==false||!object(record.inputSchema.properties)||!Array.isArray(record.inputSchema.required))throw Error('Invalid input schema');
  for(const rule of Object.values(record.inputSchema.properties))if(!object(rule)||rule.type!=='string'||typeof rule.title!=='string')throw Error('Unsupported input property');
  if(!object(record.remotion)||!['compositionId','componentPath'].every(key=>typeof (record.remotion as Record<string,unknown>)[key]==='string')||!['fps','width','height','durationInFrames'].every(key=>typeof (record.remotion as Record<string,unknown>)[key]==='number')||!object(record.remotion.defaultProps)||!object(record.remotion.propSchema))throw Error('Invalid renderer config');
 }
 return value as TemplateDefinition[];
}
