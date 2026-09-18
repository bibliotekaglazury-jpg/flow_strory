export interface NormalizedTemplateInput {
 testimonial?: string; author?: string; headline?: string; subheadline?: string;
 body?: string; productImage?: string;
}
export interface InputProperty {
 type: 'string'; title: string; maxLength?: number; minLength?: number;
 format?: 'asset-id'|'local-media'; mediaType?: 'image'; default?: string;
}
export interface InputSchema {
 type: 'object'; properties: Record<string,InputProperty>;
 required: string[]; additionalProperties: false;
}
export type TemplateCategory='UGC'|'Product'|'E-commerce'|'Social Ads'|'Testimonials'|'Hooks'|'Promos'|'Branding'|'Explainers'|'Before / After'|'Lifestyle'|'SaaS'|'Data / Metrics'|'Other';
export interface TemplateDefinition {
 id:string;slug:string;version:string;name:string;description:string;category:TemplateCategory;
 templateType:'remotion';thumbnail:string;previewVideo:string|null;enabled:boolean;featured:boolean;tags:string[];
 source:{repository:string;originalTemplateId:string;commit:string;path:string;sha256:string;adaptedSha256:string;license:'MIT';attribution:string;corrections:string[]};
 supportedAspectRatios:('9:16'|'1:1'|'16:9')[];supportedDurations:number[];
 inputSchema:InputSchema;useCases:('organic-social'|'paid-ads'|'product-showcase'|'ugc'|'branding')[];
 remotion:{compositionId:string;componentPath:string;defaultProps:NormalizedTemplateInput;propSchema:InputSchema;fps:number;width:number;height:number;durationInFrames:number};
 curation:{disabledReason:string}|null;
 validation:{status:'pending'|'passed'|'failed';reason?:string;[evidence:string]:unknown};
}
