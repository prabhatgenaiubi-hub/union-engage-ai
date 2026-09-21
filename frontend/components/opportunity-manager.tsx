"use client";
import {useEffect,useMemo,useState} from "react";
import {Mail,RefreshCw,Search,Sparkles} from "lucide-react";
import {api} from "@/lib/api";

export function OpportunityManager(){
 const [items,setItems]=useState<any[]>([]),[q,setQ]=useState(""),[saving,setSaving]=useState<number>(),[error,setError]=useState("");
 const load=()=>api<any[]>("/opportunities").then(setItems).catch((e:any)=>setError(e.message));
 useEffect(()=>{load()},[]);
 const visible=useMemo(()=>items.filter(item=>JSON.stringify(item).toLowerCase().includes(q.toLowerCase())),[items,q]);
 async function refresh(){setError("");await api("/opportunities/refresh",{method:"POST"});await load()}
 async function review(item:any,status:string){setSaving(item.id);setError("");try{const updated=await api<any>(`/opportunities/${item.id}`,{method:"PATCH",body:JSON.stringify({status,communication_draft:item.communication_draft})});setItems(rows=>rows.map(row=>row.id===item.id?{...row,...updated}:row))}catch(e:any){setError(e.message)}finally{setSaving(undefined)}}
 async function sendEmail(item:any){
  setSaving(item.id);setError("");
  try{
   const result=await api<any>(`/opportunities/${item.id}/send-email`,{method:"POST"});
   setItems(rows=>rows.map(row=>row.id===item.id?{...row,status:result.status}:row));
   alert(`Email accepted by Brevo for ${result.recipient}.`);
  }catch(e:any){setError(e.message)}finally{setSaving(undefined)}
 }
 return <>
  <div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-3xl font-bold text-navy">Next-best-product opportunities</h1><p className="mt-1 text-slate-500">Explainable recommendations with sentiment gating and mandatory employee review.</p></div><div className="flex gap-2"><label className="relative"><Search className="absolute left-3 top-3 text-slate-400" size={17}/><input className="input pl-9" placeholder="Search opportunities" value={q} onChange={e=>setQ(e.target.value)}/></label><button onClick={refresh} className="btn-secondary"><RefreshCw size={16}/>Refresh</button></div></div>
  {error&&<p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
  <div className="mt-6 grid gap-5 xl:grid-cols-2">{visible.map(item=><OpportunityCard key={item.id} item={item} saving={saving===item.id} setItems={setItems} review={review} sendEmail={sendEmail}/>)}{!visible.length&&<div className="card p-12 text-center text-slate-500 xl:col-span-2">No matching opportunities.</div>}</div>
 </>;
}

function OpportunityCard({item,saving,setItems,review,sendEmail}:{item:any;saving:boolean;setItems:React.Dispatch<React.SetStateAction<any[]>>;review:(item:any,status:string)=>void;sendEmail:(item:any)=>void}){
 const locked=item.status==="Approved"||item.status==="Email Sent";
 const emailEnabled=item.engagement?.eligible&&!!item.customer_email&&!!item.communication_draft?.trim()&&item.status==="Approved";
 return <section className="card p-6"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold text-brand">{item.customer_name} • Customer {item.customer_id}</p><h2 className="mt-1 text-xl font-bold text-navy">{item.product}</h2></div><div className="text-right"><span className="text-2xl font-bold text-navy">{item.score}</span><span className="text-xs text-slate-400">/100</span><p className="text-xs text-slate-500">{item.status}</p></div></div><div className="mt-5 space-y-3 text-sm"><Info label="Why this product" value={item.reason}/><Info label="Lifecycle/profile trigger" value={item.trigger}/><Info label="Suggested engagement" value={item.suggested_action}/><Info label="Email recipient" value={item.customer_email||"No email address available"}/></div><div className={`mt-5 rounded-xl p-4 ${item.engagement?.eligible?"bg-emerald-50 text-emerald-800":"bg-red-50 text-red-800"}`}><p className="font-semibold">{item.engagement?.state}</p><p className="mt-1 text-xs leading-5">{item.engagement?.action}</p>{!item.engagement?.eligible&&<p className="mt-2 text-xs font-semibold">Email is disabled until service recovery is complete.</p>}</div><label className="mt-5 block text-sm font-semibold"><span className="flex items-center gap-2"><Sparkles size={16} className="text-brand"/>Personalized communication draft</span><textarea className={`input mt-2 min-h-32 leading-6 ${locked?"bg-slate-100 text-slate-600":""}`} disabled={locked} maxLength={2000} value={item.communication_draft||""} onChange={e=>setItems(rows=>rows.map(row=>row.id===item.id?{...row,communication_draft:e.target.value}:row))}/></label><p className="mt-2 text-xs text-slate-400">{locked?"Content is locked. Choose Edit content to make changes.":"Review the draft and approve it before sending."}</p><div className="mt-4 flex flex-wrap gap-2">{!locked&&<button className="btn-primary" disabled={saving||!item.engagement?.eligible||!item.communication_draft?.trim()} onClick={()=>review(item,"Approved")}>Approve content</button>}{locked&&<button className="btn-secondary" disabled={saving} onClick={()=>review(item,"Pending Review")}>Edit content</button>}<button className="btn-secondary" disabled={saving||!emailEnabled} onClick={()=>sendEmail(item)}><Mail size={16}/>{saving?"Please wait…":item.status==="Email Sent"?"Email sent":"Send email"}</button></div></section>;
}
function Info({label,value}:{label:string;value:string}){return <div><p className="text-xs text-slate-400">{label}</p><p className="mt-1 leading-6">{value}</p></div>}
