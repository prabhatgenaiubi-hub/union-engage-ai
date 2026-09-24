"use client";
import {useEffect,useState} from "react";
import {api} from "@/lib/api";

type Lead={id:number;product:string;name:string;phone:string;email:string;status:string;requested_amount?:number|null;enquiry?:string;details?:Record<string,unknown>};
type Summary={id:number;title:string;created_at:string;message_count:number;lead:Lead|null;contact_step:string;pending_product:string};
type Detail={id:number;title:string;messages:{id:number;role:string;content:string;created_at:string}[];lead:Lead|null;pending_product:string;contact_step:string};

export default function PublicConversations(){
 const [items,setItems]=useState<Summary[]>([]),[selected,setSelected]=useState<Detail|null>(null),[error,setError]=useState("");
 useEffect(()=>{api<Summary[]>("/bank/public-conversations").then(setItems).catch(e=>setError(e.message));const requested=Number(new URLSearchParams(window.location.search).get("conversation"));if(requested)api<Detail>(`/bank/public-conversations/${requested}`).then(setSelected).catch(e=>setError(e.message))},[]);
 function open(id:number){api<Detail>(`/bank/public-conversations/${id}`).then(setSelected).catch(e=>setError(e.message))}
 return <div>
  <h1 className="text-3xl font-bold text-navy">External chats</h1><p className="mt-2 text-sm text-slate-500">Login-page assistant conversations and contact details from interested visitors.</p>{error&&<p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
  <div className="mt-6 grid gap-5 xl:grid-cols-[380px_1fr]">
   <section className="card max-h-[75vh] overflow-y-auto p-4"><h2 className="mb-3 font-semibold text-navy">Public conversations ({items.length})</h2>{items.length?items.map(item=><button key={item.id} onClick={()=>open(item.id)} className={`mb-2 w-full rounded-xl border p-3 text-left hover:bg-blue-50 ${selected?.id===item.id?"border-blue-500 bg-blue-50":"border-slate-200"}`}><span className="block truncate text-sm font-semibold">{item.lead?.name||item.title}</span><span className="mt-1 block text-xs text-slate-500">{new Date(item.created_at).toLocaleString()} · {item.message_count} messages</span>{item.lead?<span className="mt-2 inline-block rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">Lead · {item.lead.product}</span>:item.pending_product?<span className="mt-2 inline-block rounded-full bg-amber-50 px-2 py-1 text-xs text-amber-700">Contact pending · {item.pending_product}</span>:null}</button>):<p className="text-sm text-slate-500">No public conversations yet.</p>}</section>
   <section className="card min-h-80 p-5">{selected?<><div className="border-b pb-4"><h2 className="font-semibold text-navy">Conversation #{selected.id}</h2>{selected.lead&&<div className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm"><p className="font-semibold">{selected.lead.product} lead · {selected.lead.status}</p><p className="mt-1">{selected.lead.name} · {selected.lead.phone} · {selected.lead.email}</p>{selected.lead.requested_amount?<p className="mt-1 font-semibold text-blue-700">Requested amount: ₹{Number(selected.lead.requested_amount).toLocaleString("en-IN")}</p>:null}{selected.lead.enquiry?<p className="mt-2 text-slate-700">{selected.lead.enquiry}</p>:null}</div>}{!selected.lead&&selected.pending_product&&<p className="mt-2 text-sm text-amber-700">Contact details in progress for {selected.pending_product}</p>}</div><div className="mt-4 max-h-[60vh] space-y-3 overflow-y-auto">{selected.messages.map(message=><div key={message.id} className={`max-w-[85%] rounded-xl p-3 text-sm leading-6 ${message.role==="user"?"ml-auto bg-navy text-white":"bg-slate-100 text-slate-700"}`}>{message.content}</div>)}</div></>:<p className="text-sm text-slate-500">Select a conversation to read the chat and any captured lead.</p>}</section>
  </div>
 </div>
}
