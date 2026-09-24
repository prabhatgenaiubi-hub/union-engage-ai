"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import {api} from "@/lib/api";

type ExternalLead={id:number;conversation_id:number;product:string;name:string;phone:string;email:string;requested_amount:number|null;enquiry:string;details:Record<string,unknown>;status:string;source:string;created_at:string};
const money=(value:number|null|undefined)=>value?`₹${Number(value).toLocaleString("en-IN")}`:"Not shared";

export default function ExternalLeads(){
 const [leads,setLeads]=useState<ExternalLead[]>([]),[query,setQuery]=useState(""),[error,setError]=useState("");
 useEffect(()=>{api<ExternalLead[]>("/bank/public-leads").then(setLeads).catch(e=>setError(e.message))},[]);
 const filtered=useMemo(()=>leads.filter(lead=>`${lead.name} ${lead.phone} ${lead.email} ${lead.product} ${lead.requested_amount||""} ${lead.enquiry}`.toLowerCase().includes(query.toLowerCase())),[leads,query]);
 return <div>
  <div className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-3xl font-bold text-navy">External leads</h1><p className="mt-2 text-sm text-slate-500">Contact details and requirements captured from interested login-page visitors.</p></div><Link className="btn-secondary" href="/bank/public-conversations">View external chats</Link></div>
  <div className="card mt-6 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold text-navy">Captured leads ({leads.length})</h2><input className="input max-w-sm" placeholder="Search name, amount, contact, or product" value={query} onChange={event=>setQuery(event.target.value)}/></div>{error&&<p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
   {filtered.length?<div className="mt-5 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Visitor</th><th className="px-3 py-3">Interest</th><th className="px-3 py-3">Requirement</th><th className="px-3 py-3">Contact</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Created</th><th className="px-3 py-3">Chat</th></tr></thead>
    <tbody>{filtered.map(lead=><tr key={lead.id} className="border-b align-top last:border-0 hover:bg-slate-50"><td className="px-3 py-4"><p className="font-semibold text-navy">{lead.name||"Name not shared"}</p><p className="mt-1 text-xs text-slate-400">Lead #{lead.id}</p></td><td className="px-3 py-4"><p className="font-medium">{lead.product}</p><p className="mt-1 font-semibold text-blue-700">{money(lead.requested_amount)}</p></td><td className="max-w-72 px-3 py-4"><p className="line-clamp-3 leading-5 text-slate-600">{lead.enquiry||"No additional requirement shared"}</p>{lead.details?.timeline_as_shared?<p className="mt-1 text-xs text-amber-700">Timeline: {String(lead.details.timeline_as_shared)}</p>:null}</td><td className="px-3 py-4"><p>{lead.phone||"Phone not shared"}</p><p className="mt-1 text-slate-500">{lead.email||"Email not shared"}</p></td><td className="px-3 py-4"><span className={`rounded-full px-2 py-1 text-xs font-medium ${lead.status==="New"?"bg-emerald-50 text-emerald-700":"bg-amber-50 text-amber-700"}`}>{lead.status}</span></td><td className="whitespace-nowrap px-3 py-4 text-slate-500">{new Date(lead.created_at).toLocaleString()}</td><td className="px-3 py-4"><Link className="whitespace-nowrap font-medium text-blue-700 hover:underline" href={`/bank/public-conversations?conversation=${lead.conversation_id}`}>Open chat</Link></td></tr>)}</tbody>
   </table></div>:<p className="mt-5 text-sm text-slate-500">{leads.length?"No leads match your search.":"No external leads captured yet."}</p>}
  </div>
 </div>
}
