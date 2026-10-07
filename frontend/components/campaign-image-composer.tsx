"use client";
import {useEffect,useState} from "react";
import type {ReactNode} from "react";
import {Image as ImageIcon,RefreshCw,Sparkles,Trash2} from "lucide-react";
import {api} from "@/lib/api";

type Position="top"|"after_greeting"|"bottom"|"custom";
type Alignment="left"|"center"|"right";
type Props={campaignType:"opportunity"|"retention";prompt:string;imageBase64?:string;imageFilename?:string;imagePosition?:Position;imageWidthPercent?:number;imageHeightPx?:number;imageAlignment?:Alignment;message?:string;onChange:(values:{imagePrompt?:string;imageBase64?:string;imageFilename?:string;imagePosition?:Position;imageWidthPercent?:number;imageHeightPx?:number;imageAlignment?:Alignment;message?:string})=>void};

export function CampaignImageComposer({campaignType,prompt,imageBase64,imageFilename,imagePosition,imageWidthPercent,imageHeightPx,imageAlignment,message,onChange}:Props){
 const [enabled,setEnabled]=useState(false),[loaded,setLoaded]=useState(false),[generating,setGenerating]=useState(false),[error,setError]=useState("");
 const [localPosition,setLocalPosition]=useState<Position>(imagePosition||"top"),[localWidth,setLocalWidth]=useState(imageWidthPercent||100),[localHeight,setLocalHeight]=useState(imageHeightPx||300),[localAlignment,setLocalAlignment]=useState<Alignment>(imageAlignment||"center");
 const effectivePosition=imagePosition??localPosition,effectiveWidth=imageWidthPercent??localWidth,effectiveHeight=imageHeightPx??localHeight,effectiveAlignment=imageAlignment??localAlignment;
 useEffect(()=>{api<any>("/campaign-images/settings").then(value=>setEnabled(value.enabled)).catch(()=>setEnabled(false)).finally(()=>setLoaded(true))},[]);
 if(!loaded||!enabled)return null;
 async function generate(){setGenerating(true);setError("");try{const result=await api<any>("/campaign-images/generate",{method:"POST",body:JSON.stringify({campaign_type:campaignType,prompt:prompt.trim()})});onChange({imageBase64:result.image_base64,imageFilename:result.filename})}catch(e:any){setError(e.message)}finally{setGenerating(false)}}
 function messageBox(){return document.querySelector('[role="dialog"] textarea') as HTMLTextAreaElement|null}
 function previewMessage(){return message??messageBox()?.value??""}
 function setPosition(position:Position){
  setLocalPosition(position);
  const current=message??messageBox()?.value;
  if(current===undefined)onChange({imagePosition:position});
  else if(position==="custom"&&!current.includes("[CAMPAIGN_IMAGE]"))onChange({imagePosition:position,message:`${current.trimEnd()}\n\n[CAMPAIGN_IMAGE]`});
  else onChange({imagePosition:position,message:position==="custom"?current:current.replaceAll("[CAMPAIGN_IMAGE]","").replace(/\n{3,}/g,"\n\n")});
  if(position==="custom")window.setTimeout(()=>{const box=messageBox();box?.focus();box?.scrollIntoView({behavior:"smooth",block:"center"})},0);
 }
 function composedPreview(){
  const image=<img key="campaign-image" src={`data:image/png;base64,${imageBase64}`} alt="Generated campaign preview" style={{display:"block",width:`${effectiveWidth}%`,height:`${effectiveHeight}px`,objectFit:"cover",marginLeft:effectiveAlignment==="left"?0:"auto",marginRight:effectiveAlignment==="right"?0:"auto"}}/>;
  const paragraphs=previewMessage().split(/\n+/).filter(Boolean);
  const content:ReactNode[]=[];
  paragraphs.forEach((part,index)=>{
   if(part.includes("[CAMPAIGN_IMAGE]")){
    const [before,after]=part.split("[CAMPAIGN_IMAGE]",2);if(before.trim())content.push(<p key={`before-${index}`}>{before}</p>);content.push(image);if(after.trim())content.push(<p key={`after-${index}`}>{after}</p>);
   }else content.push(<p key={`text-${index}`}>{part}</p>);
  });
  if(!previewMessage().includes("[CAMPAIGN_IMAGE]")){const index=effectivePosition==="after_greeting"?Math.min(1,content.length):effectivePosition==="bottom"?content.length:0;content.splice(index,0,image)}
  return content;
 }
 return <section className="rounded-xl border border-blue-200 bg-blue-50 p-4">
  <div className="flex items-center gap-2 font-semibold text-navy"><ImageIcon size={17}/>Optional campaign image</div>
  <p className="mt-1 text-xs leading-5 text-slate-600">Describe the visual you want. Do not include customer names, account details, rates, or email copy.</p>
  <label className="mt-3 block text-sm font-semibold text-slate-700">Image prompt<textarea className="input mt-2 min-h-24 bg-white leading-6" maxLength={1000} placeholder="Example: A confident Indian small-business owner in a modern shop, warm natural light, subject on the left, clean space on the right, no text or logos" value={prompt} onChange={e=>onChange({imagePrompt:e.target.value,imageBase64:undefined,imageFilename:undefined})}/></label>
  <div className="mt-3 flex flex-wrap gap-2"><button type="button" className="btn-secondary" disabled={generating||prompt.trim().length<10} onClick={generate}>{generating?<RefreshCw className="animate-spin" size={15}/>:<Sparkles size={15}/>} {generating?"Generating image...":imageBase64?"Regenerate image":"Generate image"}</button>{imageBase64&&<button type="button" className="btn-secondary text-red-600" disabled={generating} onClick={()=>onChange({imageBase64:undefined,imageFilename:undefined})}><Trash2 size={15}/>Remove image</button>}</div>
  {error&&<p className="mt-3 text-sm text-red-700">{error}</p>}
  {imageBase64&&<><div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="block text-sm font-semibold text-slate-700">Place image<select className="input mt-2 bg-white" value={effectivePosition} onChange={e=>setPosition(e.target.value as Position)}><option value="top">Above the message</option><option value="after_greeting">After the greeting</option><option value="bottom">Below the message</option><option value="custom">Custom position inside message</option></select></label><label className="block text-sm font-semibold text-slate-700">Horizontal alignment<select className="input mt-2 bg-white" value={effectiveAlignment} onChange={e=>{const alignment=e.target.value as Alignment;setLocalAlignment(alignment);onChange({imageAlignment:alignment})}}><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select></label><label className="block text-sm font-semibold text-slate-700">Image width: {effectiveWidth}%<input className="mt-4 w-full accent-blue-700" type="range" min="25" max="100" step="5" value={effectiveWidth} onChange={e=>{const width=Number(e.target.value);setLocalWidth(width);onChange({imageWidthPercent:width})}}/></label><label className="block text-sm font-semibold text-slate-700">Image height: {effectiveHeight}px<input className="mt-4 w-full accent-blue-700" type="range" min="100" max="600" step="20" value={effectiveHeight} onChange={e=>{const height=Number(e.target.value);setLocalHeight(height);onChange({imageHeightPx:height})}}/></label></div>{effectivePosition==="custom"&&<div className="mt-2 rounded-lg bg-white p-3 text-xs leading-5 text-slate-600"><p>The <b>[CAMPAIGN_IMAGE]</b> marker is now inside the message box. Move it wherever the image should appear.</p><button type="button" className="mt-2 font-semibold text-blue-700 underline" onClick={()=>{messageBox()?.focus();messageBox()?.scrollIntoView({behavior:"smooth",block:"center"})}}>Go to message box</button></div>}<div className="mt-4 overflow-hidden rounded-xl border border-slate-200 bg-white"><div className="border-b bg-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Email preview</div><div className="space-y-3 p-5 text-sm leading-6 text-slate-700">{composedPreview()}</div><p className="border-t p-2 text-xs text-slate-500">The delivered email will use this placement, size, and alignment for {imageFilename||"campaign.png"}.</p></div></>}
 </section>;
}
