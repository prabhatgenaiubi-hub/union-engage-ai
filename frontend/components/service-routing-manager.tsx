"use client";
import {useEffect,useMemo,useState} from "react";
import {CheckCircle2,RefreshCw,Search} from "lucide-react";
import {api} from "@/lib/api";

const departments=["Customer Service","Cards","Accounts & Deposits","Loans","Digital Banking","Payments & Disputes","Fraud & Risk","Complaints & Escalations"] as const;
const escalationLevels=["None","Team Lead","Manager","Senior Management","Fraud / Risk Review"] as const;
type Decision={id:number;conversation_id:number;customer_name:string;message?:string;issue:string;status:string;routed_department?:string;admin_comment?:string;escalation?:string};
type Draft={department:string;escalationLevel:string;comment:string};

export function ServiceRoutingManager(){
 const [rows,setRows]=useState<Decision[]>([]),[q,setQ]=useState(""),[busy,setBusy]=useState<number|null>(null),[error,setError]=useState(""),[drafts,setDrafts]=useState<Record<number,Draft>>({});
 const load=()=>api<Decision[]>("/routing").then(items=>{setRows(items);setDrafts(current=>Object.fromEntries(items.map(item=>[item.id,current[item.id]||{department:item.routed_department||"",escalationLevel:item.escalation||"None",comment:item.admin_comment||""}])))}).catch((e:any)=>setError(e.message));
 useEffect(()=>{load()},[]);
 const visible=useMemo(()=>rows.filter(row=>JSON.stringify(row).toLowerCase().includes(q.toLowerCase())),[rows,q]);
 function update(id:number,field:keyof Draft,value:string){setDrafts(items=>({...items,[id]:{department:items[id]?.department||"",escalationLevel:items[id]?.escalationLevel||"None",comment:items[id]?.comment||"",[field]:value}}))}
 async function route(row:Decision){
  const draft=drafts[row.id];if(!draft?.department||!draft.comment.trim()){setError("Select a department and enter a comment before routing.");return}
  setBusy(row.id);setError("");
  try{const updated=await api<Decision>(`/routing/${row.id}`,{method:"PATCH",body:JSON.stringify({status:"Applied",department:draft.department,escalation_level:draft.escalationLevel,comment:draft.comment.trim()})});setRows(items=>items.map(item=>item.id===row.id?{...item,...updated}:item))}
  catch(e:any){setError(e.message)}finally{setBusy(null)}
 }
 return <>
  <div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-3xl font-bold text-navy">Route customer conversations</h1><p className="mt-1 text-slate-500">Select a department, add an internal comment, and route the conversation.</p></div><div className="flex gap-2"><label className="relative"><Search className="absolute left-3 top-3 text-slate-400" size={17}/><input className="input pl-9" placeholder="Search conversations" value={q} onChange={e=>setQ(e.target.value)}/></label><button className="btn-secondary" onClick={load}><RefreshCw size={16}/>Refresh</button></div></div>
  {error&&<p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
  <div className="mt-6 space-y-4">{visible.map(row=>{const draft=drafts[row.id]||{department:"",escalationLevel:"None",comment:""};return <article key={row.id} className="card p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-brand">Conversation #{row.conversation_id} · {row.customer_name}</p><h2 className="mt-1 text-lg font-bold text-navy">{row.issue}</h2></div>{row.status==="Applied"&&<span className="badge bg-emerald-50 text-emerald-700">Routed to {row.routed_department} · {row.escalation}</span>}</div>{row.message&&<blockquote className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-700">“{row.message}”</blockquote>}<div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr_2fr]"><label className="text-sm font-semibold">Department<select className="input mt-2" value={draft.department} onChange={e=>update(row.id,"department",e.target.value)}><option value="" disabled>Select department</option>{departments.map(department=><option key={department}>{department}</option>)}</select></label><label className="text-sm font-semibold">Escalation level<select className="input mt-2" value={draft.escalationLevel} onChange={e=>update(row.id,"escalationLevel",e.target.value)}>{escalationLevels.map(level=><option key={level}>{level}</option>)}</select></label><label className="text-sm font-semibold">Internal comment<textarea className="input mt-2 min-h-24" maxLength={2000} placeholder="Add routing instructions or context…" value={draft.comment} onChange={e=>update(row.id,"comment",e.target.value)}/></label></div><button className="btn-primary mt-4" disabled={busy===row.id||!draft.department||!draft.comment.trim()} onClick={()=>route(row)}><CheckCircle2 size={16}/>{busy===row.id?"Routing…":"Route this"}</button></article>})}{!visible.length&&<div className="card p-12 text-center text-slate-500">No matching conversations.</div>}</div>
 </>;
}
