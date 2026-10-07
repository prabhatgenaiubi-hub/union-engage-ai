"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {Image} from "lucide-react";
import {api} from "@/lib/api";

const nav=[["users","Users"],["knowledge","Knowledge Base"],["products","Products"],["routing-rules","Routing Rules"],["audit","Audit Logs"],["ai-settings","AI Configuration"]];
const endpoints:any={users:"/admin/users",knowledge:"/knowledge","routing-rules":"/admin/routing-rules",audit:"/admin/audit-logs","ai-settings":"/admin/ai-settings"};

export function AdminPage({kind}:{kind:string}){
 const [data,setData]=useState<any>();
 useEffect(()=>{if(endpoints[kind])api(endpoints[kind]).then(setData).catch(()=>{})},[kind]);
 return <><h1 className="text-3xl font-bold text-navy">Administration</h1><div className="mt-5 flex flex-wrap gap-2">{nav.map(([href,label])=><Link key={href} className={`btn-secondary ${kind==href?"border-navy bg-navy text-white":""}`} href={`/bank/admin/${href}`}>{label}</Link>)}</div><div className="card mt-6 p-6"><h2 className="text-xl font-bold capitalize">{kind.replaceAll("-"," ")}</h2>{kind==="products"?<p className="mt-5 text-slate-500">Savings Account, Debit Card, Credit Card, Home Loan, Fixed Deposit</p>:kind==="ai-settings"?<AISettings data={data} onChange={setData}/>:data?<pre className="mt-5 max-h-[540px] overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-5 text-xs text-slate-200">{JSON.stringify(data,null,2)}</pre>:<p className="mt-5">Loading...</p>}</div></>;
}

function AISettings({data,onChange}:{data:any;onChange:(value:any)=>void}){
 const [selected,setSelected]=useState(""),[saving,setSaving]=useState(false),[error,setError]=useState(""),[saved,setSaved]=useState(false);
 useEffect(()=>{setSelected(data?.selected_provider||"")},[data?.selected_provider]);
 if(!data)return <p className="mt-5">Loading...</p>;
 async function save(){if(!selected||selected===data.selected_provider)return;setSaving(true);setError("");setSaved(false);try{const updated=await api<any>("/admin/ai-settings/chat-reply-model",{method:"PATCH",body:JSON.stringify({provider:selected})});onChange({...data,...updated});setSaved(true)}catch(e:any){setError(e.message)}finally{setSaving(false)}}
 return <div className="mt-5 max-w-2xl space-y-8"><section><p className="text-sm text-slate-500">Select the model used only for chat replies. Other AI services remain unchanged.</p><div className="mt-4 flex flex-wrap items-end gap-3"><label className="min-w-72 flex-1 text-sm font-medium text-slate-700">Chat reply model<select className="input mt-1" value={selected} disabled={saving} onChange={event=>{setSelected(event.target.value);setSaved(false)}}>{data.options.map((option:any)=><option key={option.id} value={option.id}>{option.label}</option>)}</select></label><button className="btn-primary" disabled={saving||selected===data.selected_provider} onClick={save}>{saving?"Saving...":"Save chat model"}</button></div><p className="mt-2 text-xs text-slate-500">Active: {data.active.label} - {data.active.model}</p>{saved&&<p className="mt-3 text-sm text-emerald-700">Saved. New chat replies will use this model.</p>}{error&&<p className="mt-3 text-sm text-red-600">{error}</p>}</section><ImageGenerationToggle data={data.image_generation} onChange={value=>onChange({...data,image_generation:value})}/></div>;
}

function ImageGenerationToggle({data,onChange}:{data:any;onChange:(value:any)=>void}){
 const [saving,setSaving]=useState(false),[error,setError]=useState("");
 if(!data)return null;
 async function toggle(){setSaving(true);setError("");try{onChange(await api("/admin/ai-settings/image-generation",{method:"PATCH",body:JSON.stringify({enabled:!data.enabled})}))}catch(e:any){setError(e.message)}finally{setSaving(false)}}
 return <section className="border-t border-slate-200 pt-6"><div className="flex items-start justify-between gap-5"><div><h3 className="flex items-center gap-2 font-bold text-navy"><Image size={18}/>Campaign email images</h3><p className="mt-1 text-sm text-slate-500">Generate a local FLUX visual for retention and next-best-opportunity emails. When off, emails contain text only.</p><p className="mt-2 text-xs text-slate-500">{data.provider} - {data.model}</p></div><button type="button" role="switch" aria-checked={data.enabled} aria-label="Generate campaign email images" disabled={saving} onClick={toggle} className={`relative h-7 w-12 shrink-0 rounded-full transition ${data.enabled?"bg-emerald-600":"bg-slate-300"}`}><span className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition ${data.enabled?"left-6":"left-1"}`}/></button></div><p className={`mt-3 text-sm ${data.enabled?"text-emerald-700":"text-slate-500"}`}>{saving?"Saving...":data.enabled?"Enabled - approved campaign emails will include a generated image.":"Disabled - campaign emails are text only."}</p>{error&&<p className="mt-2 text-sm text-red-600">{error}</p>}</section>;
}
