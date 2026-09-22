"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import {api} from "@/lib/api";

type ExternalLead={id:number;conversation_id:number;product:string;name:string;phone:string;email:string;status:string;source:string;created_at:string};

export default function ExternalLeads(){
 const [leads,setLeads]=useState<ExternalLead[]>([]),[query,setQuery]=useState(""),[error,setError]=useState("");
 useEffect(()=>{api<ExternalLead[]>("/bank/public-leads").then(setLeads).catch(e=>setError(e.message))},[]);
 const filtered=useMemo(()=>leads.filter(lead=>`${lead.name} ${lead.phone} ${lead.email} ${lead.product}`.toLowerCase().includes(query.toLowerCase())),[leads,query]);
 return <div><div className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-3xl font-bold text-navy">External leads</h1><p className="mt-2 text-sm text-slate-500">Visitors who shared contact details after expressing product interest in the login-page assistant.</p></div><Link className="btn-secondary" href="/bank/public-conversations">View external chats</Link></div><div className="card mt-6 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold text-navy">Captured leads ({leads.length})</h2><input className="input max-w-sm" placeholder="Search name, contact, or product" value={query} onChange={event=>setQuery(event.target.value)}/></div>{error&&<p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}{filtered.length?<div className="mt-5 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">Visitor</th><th className="px-3 py-3">Interest</th><th className="px-3 py-3">Contact</th><th className="px-3 py-3">Created</th><th className="px-3 py-3">Chat</th></tr></thead><tbody>{filtered.map(lead=><tr key={lead.id} className="border-b last:border-0"><td className="px-3 py-4 font-semibold">{lead.name}</td><td className="px-3 py-4">{lead.product}</td><td className="px-3 py-4"><p>{lead.phone}</p><p className="text-slate-500">{lead.email}</p></td><td className="px-3 py-4 text-slate-500">{new Date(lead.created_at).toLocaleString()}</td><td className="px-3 py-4"><Link className="font-medium text-blue-700 hover:underline" href={`/bank/public-conversations?conversation=${lead.conversation_id}`}>Open chat</Link></td></tr>)}</tbody></table></div>:<p className="mt-5 text-sm text-slate-500">{leads.length?"No leads match your search.":"No external leads captured yet."}</p>}</div></div>
}
