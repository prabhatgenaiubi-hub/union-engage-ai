"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {api} from "@/lib/api";

const nav=[["users","Users"],["knowledge","Knowledge Base"],["products","Products"],["routing-rules","Routing Rules"],["audit","Audit Logs"],["ai-settings","AI Configuration"]];
const endpoints:any={users:"/admin/users",knowledge:"/knowledge","routing-rules":"/admin/routing-rules",audit:"/admin/audit-logs","ai-settings":"/admin/ai-settings"};

export function AdminPage({kind}:{kind:string}){
 const [data,setData]=useState<any>();
 useEffect(()=>{if(endpoints[kind])api(endpoints[kind]).then(setData).catch(()=>{})},[kind]);
 return <><h1 className="text-3xl font-bold text-navy">Administration</h1><div className="mt-5 flex flex-wrap gap-2">{nav.map(([href,label])=><Link key={href} className={`btn-secondary ${kind==href?"border-navy bg-navy text-white":""}`} href={`/bank/admin/${href}`}>{label}</Link>)}</div><div className="card mt-6 p-6"><h2 className="text-xl font-bold capitalize">{kind.replaceAll("-"," ")}</h2>{kind==="products"?<p className="mt-5 text-slate-500">Savings Account, Debit Card, Credit Card, Home Loan, Fixed Deposit</p>:kind==="ai-settings"?<ChatReplyModel data={data} onChange={setData}/>:data?<pre className="mt-5 max-h-[540px] overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-5 text-xs text-slate-200">{JSON.stringify(data,null,2)}</pre>:<p className="mt-5">Loading…</p>}</div></>;
}

function ChatReplyModel({data,onChange}:{data:any;onChange:(value:any)=>void}){
 const [selected,setSelected]=useState(""),[saving,setSaving]=useState(false),[error,setError]=useState(""),[saved,setSaved]=useState(false);
 useEffect(()=>{setSelected(data?.selected_provider||"")},[data?.selected_provider]);
 if(!data)return <p className="mt-5">Loading…</p>;
 async function save(){if(!selected||selected===data.selected_provider)return;setSaving(true);setError("");setSaved(false);try{onChange(await api("/admin/ai-settings/chat-reply-model",{method:"PATCH",body:JSON.stringify({provider:selected})}));setSaved(true)}catch(e:any){setError(e.message)}finally{setSaving(false)}}
 return <div className="mt-5 max-w-xl"><p className="text-sm text-slate-500">Select the model used only for chat replies. Other AI services remain unchanged.</p><div className="mt-4 flex flex-wrap items-end gap-3"><label className="min-w-72 flex-1 text-sm font-medium text-slate-700">Chat reply model<select className="input mt-1" value={selected} disabled={saving} onChange={event=>{setSelected(event.target.value);setSaved(false)}}>{data.options.map((option:any)=><option key={option.id} value={option.id}>{option.label}</option>)}</select></label><button className="btn-primary" disabled={saving||selected===data.selected_provider} onClick={save}>{saving?"Saving…":"Save chat model"}</button></div><p className="mt-2 text-xs text-slate-500">Active: {data.active.label} · {data.active.model}</p>{saved&&<p className="mt-3 text-sm text-emerald-700">Saved. New chat replies will use this model.</p>}{error&&<p className="mt-3 text-sm text-red-600">{error}</p>}</div>;
}
