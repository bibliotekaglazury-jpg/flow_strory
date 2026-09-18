import React from 'react';
import {AbsoluteFill,Composition,registerRoot,useVideoConfig} from 'remotion';
import {registry} from './registry.generated';
import manifest from '../manifest.json';
import type {NormalizedTemplateInput} from './types';
import './style.css';
import {SubtitleComposition} from './subtitles/subtitle-composition';
import {SUBTITLE_COMPOSITION_ID,SUBTITLE_FPS,subtitleDimensions} from './subtitles/types';
type Props={templateId:string;inputs:NormalizedTemplateInput};
export function TemplateScene({templateId,inputs}:Props){
 const entry=registry[templateId as keyof typeof registry];
 if(!entry)throw Error('Unknown template');
 const {width,height}=useVideoConfig();
 const Component=entry.component as React.ComponentType<Record<string,unknown>>;
 const scale=Math.min(width/1280,height/720);
 return <AbsoluteFill style={{backgroundColor:'#111827',fontFamily:'Inter, Arial, sans-serif',overflow:'hidden'}}>
  <div style={{position:'absolute',width:1280,height:720,left:(width-1280*scale)/2,top:(height-720*scale)/2,transform:`scale(${scale})`,transformOrigin:'top left'}}>
   <Component {...(entry.media?{imageUrl:inputs.productImage}:inputs)}/>
  </div>
 </AbsoluteFill>;
}
function Root(){return <>{manifest.map(template=><Composition key={template.id} id={template.remotion.compositionId} component={TemplateScene} durationInFrames={450} fps={30} width={1280} height={720} defaultProps={{templateId:template.id,inputs:template.remotion.defaultProps}}/>)}
  {/* Subtitle Studio export: the renderer overrides size and duration per job. */}
  <Composition id={SUBTITLE_COMPOSITION_ID} component={SubtitleComposition} durationInFrames={300} fps={SUBTITLE_FPS} {...subtitleDimensions['9:16']} defaultProps={{sourceUrl:'',cues:[],preset:'modern',position:'bottom',size:'medium',safeArea:true,textColor:'#FFFFFF',highlightColor:'#C9FF27'}}/>
 </>}
registerRoot(Root);
