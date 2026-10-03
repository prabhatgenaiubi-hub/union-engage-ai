"use client";

import {useEffect, useMemo, useState} from "react";
import {CalendarDays, Mail, Phone, RefreshCw, Search, Sparkles, X} from "lucide-react";
import {api} from "@/lib/api";

type EmailDraft = {
  item: any;
  recipient: string;
  subject: string;
  message: string;
};

export function OpportunityManager(){
  const [items,setItems]=useState<any[]>([]);
  const [q,setQ]=useState("");
  const [fromDate,setFromDate]=useState("");
  const [toDate,setToDate]=useState("");
  const [saving,setSaving]=useState<number>();
  const [error,setError]=useState("");
  const [emailDraft,setEmailDraft]=useState<EmailDraft|null>(null);
  const load=()=>api<any[]>("/opportunities").then(setItems).catch((e:any)=>setError(e.message));

  useEffect(()=>{load()},[]);
  const visible=useMemo(()=>items.filter(item=>{const value=new Date(item.created_at).getTime();return JSON.stringify(item).toLowerCase().includes(q.toLowerCase())&&(!fromDate||value>=new Date(`${fromDate}T00:00:00`).getTime())&&(!toDate||value<=new Date(`${toDate}T23:59:59.999`).getTime())}).sort((a,b)=>new Date(b.created_at).getTime()-new Date(a.created_at).getTime()),[items,q,fromDate,toDate]);

  async function refresh(){
    setError("");
    await api("/opportunities/refresh",{method:"POST"});
    await load();
  }

  async function review(item:any,status:string){
    setSaving(item.id);
    setError("");
    try{
      const updated=await api<any>(`/opportunities/${item.id}`,{method:"PATCH",body:JSON.stringify({status,communication_draft:item.communication_draft})});
      setItems(rows=>rows.map(row=>row.id===item.id?{...row,...updated}:row));
    }catch(e:any){setError(e.message)}finally{setSaving(undefined)}
  }

  function openEmailEditor(item:any){
    setError("");
    setEmailDraft({item,recipient:item.customer_email||"",subject:`${item.product} options from Union Bank`,message:item.communication_draft||""});
  }

  async function sendEmail(){
    if(!emailDraft)return;
    const {item,recipient,subject,message}=emailDraft;
    setSaving(item.id);
    setError("");
    try{
      const result=await api<any>(`/opportunities/${item.id}/send-email`,{method:"POST",body:JSON.stringify({recipient:recipient.trim(),subject:subject.trim(),message:message.trim()})});
      setItems(rows=>rows.map(row=>row.id===item.id?{...row,status:result.status}:row));
      setEmailDraft(null);
      alert(`Email submitted to the provider for ${result.recipient}. Final delivery depends on the provider and recipient mailbox.`);
    }catch(e:any){setError(e.message)}finally{setSaving(undefined)}
  }

  return <>
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div><h1 className="text-3xl font-bold text-navy">Next-best-product opportunities</h1><p className="mt-1 text-slate-500">Explainable recommendations with sentiment gating and mandatory employee review.</p></div>
      <div className="flex flex-wrap gap-2"><label className="relative"><Search className="absolute left-3 top-3 text-slate-400" size={17}/><input className="input pl-9" placeholder="Search opportunities" value={q} onChange={e=>setQ(e.target.value)}/></label><label className="relative"><CalendarDays className="absolute left-3 top-3 text-slate-400" size={17}/><input aria-label="Opportunities from date" type="date" className="input pl-9" value={fromDate} onChange={e=>setFromDate(e.target.value)}/></label><label className="relative"><CalendarDays className="absolute left-3 top-3 text-slate-400" size={17}/><input aria-label="Opportunities to date" type="date" className="input pl-9" min={fromDate} value={toDate} onChange={e=>setToDate(e.target.value)}/></label><button onClick={refresh} className="btn-secondary"><RefreshCw size={16}/>Refresh</button></div>
    </div>
    {error&&<p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    <div className="mt-6 grid gap-5 xl:grid-cols-2">{visible.map(item=><OpportunityCard key={item.id} item={item} saving={saving===item.id} setItems={setItems} review={review} openEmailEditor={openEmailEditor}/>)}{!visible.length&&<div className="card p-12 text-center text-slate-500 xl:col-span-2">No matching opportunities.</div>}</div>
    {emailDraft&&<EmailEditor draft={emailDraft} setDraft={setEmailDraft} saving={saving===emailDraft.item.id} error={error} onSend={sendEmail}/>} 
  </>;
}

function OpportunityCard({item,saving,setItems,review,openEmailEditor}:{item:any;saving:boolean;setItems:React.Dispatch<React.SetStateAction<any[]>>;review:(item:any,status:string)=>void;openEmailEditor:(item:any)=>void}){
  const locked=item.status==="Approved"||item.status==="Email Sent";
  const emailEnabled=item.engagement?.eligible&&!!item.communication_draft?.trim()&&item.status==="Approved";
  return <section className="card p-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold text-brand">{item.customer_name} &bull; Customer {item.customer_id}</p><h2 className="mt-1 text-xl font-bold text-navy">{item.product}</h2><p className="mt-1 text-xs text-slate-400">Created {new Date(item.created_at).toLocaleDateString()}</p></div><div className="text-right"><span className="text-2xl font-bold text-navy">{item.score}</span><span className="text-xs text-slate-400">/100</span><p className="text-xs text-slate-500">{item.status}</p></div></div>
    <div className="mt-5 space-y-3 text-sm"><Info label="Why this product" value={item.reason}/><Info label="Lifecycle/profile trigger" value={item.trigger}/><Info label="Suggested engagement" value={item.suggested_action}/><Info label="Phone number" value={item.customer_phone||"No phone number available"} icon={<Phone size={14}/>}/><Info label="Email recipient" value={item.customer_email||"No email address available"}/></div>
    <div className={`mt-5 rounded-xl p-4 ${item.engagement?.eligible?"bg-emerald-50 text-emerald-800":"bg-red-50 text-red-800"}`}><p className="font-semibold">{item.engagement?.state}</p><p className="mt-1 text-xs leading-5">{item.engagement?.action}</p>{!item.engagement?.eligible&&<p className="mt-2 text-xs font-semibold">Email is disabled until service recovery is complete.</p>}</div>
    <label className="mt-5 block text-sm font-semibold"><span className="flex items-center gap-2"><Sparkles size={16} className="text-brand"/>Personalized communication draft</span><textarea className={`input mt-2 min-h-32 leading-6 ${locked?"bg-slate-100 text-slate-600":""}`} disabled={locked} maxLength={2000} value={item.communication_draft||""} onChange={e=>setItems(rows=>rows.map(row=>row.id===item.id?{...row,communication_draft:e.target.value}:row))}/></label>
    <p className="mt-2 text-xs text-slate-400">{locked?"Content is locked. Choose Edit content to make changes.":"Review the draft and approve it before sending."}</p>
    <div className="mt-4 flex flex-wrap gap-2">{!locked&&<button className="btn-primary" disabled={saving||!item.engagement?.eligible||!item.communication_draft?.trim()} onClick={()=>review(item,"Approved")}>Approve content</button>}{locked&&<button className="btn-secondary" disabled={saving} onClick={()=>review(item,"Pending Review")}>Edit content</button>}<button className="btn-secondary" disabled={saving||!emailEnabled} onClick={()=>openEmailEditor(item)}><Mail size={16}/>{saving?"Please wait…":item.status==="Email Sent"?"Email sent":"Review & send email"}</button></div>
  </section>;
}

function EmailEditor({draft,setDraft,saving,error,onSend}:{draft:EmailDraft;setDraft:React.Dispatch<React.SetStateAction<EmailDraft|null>>;saving:boolean;error:string;onSend:()=>void}){
  const canSend=!!draft.recipient.trim()&&!!draft.subject.trim()&&!!draft.message.trim();
  const update=(values:Partial<EmailDraft>)=>setDraft(current=>current?{...current,...values}:current);
  return <div className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-950/55 p-4" role="dialog" aria-modal="true" aria-labelledby="email-editor-title" onMouseDown={e=>{if(e.target===e.currentTarget&&!saving)setDraft(null)}}>
    <div className="w-full max-w-2xl rounded-2xl bg-white shadow-2xl">
      <header className="flex items-start justify-between border-b border-slate-200 px-6 py-5"><div><h2 id="email-editor-title" className="text-xl font-bold text-navy">Review and edit email</h2><p className="mt-1 text-sm text-slate-500">Confirm the recipient and edit the subject or message before sending.</p></div><button className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" aria-label="Close email editor" disabled={saving} onClick={()=>setDraft(null)}><X size={20}/></button></header>
      <div className="space-y-4 px-6 py-5">
        {error&&<p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <label className="block text-sm font-semibold text-slate-700">To<input type="email" className="input mt-2" maxLength={120} value={draft.recipient} onChange={e=>update({recipient:e.target.value})}/></label>
        <label className="block text-sm font-semibold text-slate-700">Subject<input className="input mt-2" maxLength={200} value={draft.subject} onChange={e=>update({subject:e.target.value})}/></label>
        <label className="block text-sm font-semibold text-slate-700">Message<textarea className="input mt-2 min-h-56 leading-6" maxLength={5000} value={draft.message} onChange={e=>update({message:e.target.value})}/></label>
        <p className="text-right text-xs text-slate-400">{draft.message.length}/5000 characters</p>
      </div>
      <footer className="flex justify-end gap-3 border-t border-slate-200 px-6 py-4"><button className="btn-secondary" disabled={saving} onClick={()=>setDraft(null)}>Cancel</button><button className="btn-primary" disabled={saving||!canSend} onClick={onSend}><Mail size={16}/>{saving?"Sending…":"Send email"}</button></footer>
    </div>
  </div>;
}

function Info({label,value,icon}:{label:string;value:string;icon?:React.ReactNode}){return <div><p className="flex items-center gap-1 text-xs text-slate-400">{icon}{label}</p><p className="mt-1 leading-6">{value}</p></div>}
