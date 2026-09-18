export type Schema={type:string;properties?:Record<string,Schema>;required?:string[];additionalProperties?:boolean;maxLength?:number;minLength?:number;format?:string;enum?:unknown[];default?:unknown};
export function validateInputs(schema:Schema,value:unknown):asserts value is Record<string,string>{
 if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Inputs must be an object');
 const input=value as Record<string,unknown>;
 for(const key of Object.keys(input)){
  const rule=schema.properties?.[key];
  if(!rule)throw Error(`Unknown input: ${key}`);
  const v=input[key];if(typeof v!==rule.type)throw Error(`Invalid type: ${key}`);
  if(typeof v==='string'&&((rule.maxLength!==undefined&&v.length>rule.maxLength)||(rule.minLength!==undefined&&v.length<rule.minLength)))throw Error(`Invalid length: ${key}`);
  if(rule.enum&&!rule.enum.includes(v))throw Error(`Invalid option: ${key}`);
 }
 for(const key of schema.required??[])if(!(key in input))throw Error(`Missing input: ${key}`);
}
