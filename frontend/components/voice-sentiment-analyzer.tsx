"use client";
import {useEffect,useState} from "react";
import {AlertCircle,AudioLines,FileAudio,RefreshCw,Upload} from "lucide-react";
import {api} from "@/lib/api";
type Result={conversation_id:number;customer_name:string;transcript:string;summary:string;language_code:string;sentiment:string;sentiment_score:number;emotion:string;intent:string;urgency:string;recommended_route:string;routing_reason:string};
type Customer={id:number;customer_code:string;name:string};
export function VoiceSentimentAnalyzer({onSaved}:{onSaved?:()=>void}){
 const [file,setFile]=useState<File|null>(null),[customers,setCustomers]=useState<Customer[]>([]),[customerId,setCustomerId]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState(""),[result,setResult]=useState<Result|null>(null);
 useEffect(()=>{api<Customer[]>("/customers").then(setCustomers).catch((error:any)=>setError(error.message))},[]);
 async function analyze(event:React.FormEvent){event.preventDefault();if(!file||!customerId)return;setBusy(true);setError("");setResult(null);const form=new FormData();form.append("file",file);form.append("customer_id",customerId);try{const saved=await api<Result>("/admin/voice-sentiment",{method:"POST",body:form});setResult(saved);onSaved?.()}catch(error:any){setError(error.message)}finally{setBusy(false)}}
 const tone=result?.sentiment==="Highly Negative"?"bg-red-50 text-red-700":result?.sentiment==="Negative"?"bg-amber-50 text-amber-700":result?.sentiment==="Positive"?"bg-emerald-50 text-emerald-700":"bg-slate-100 text-slate-700";
 return <section className="card p-5">
  <div className="flex items-center gap-2 font-bold text-navy"><AudioLines className="text-brand" size={18}/>Analyze voice sentiment</div>
  <p className="mt-2 text-xs text-slate-500">Choose a customer and upload an English recording. The transcript and analysis are saved to conversation history; audio is not stored.</p>
  <form onSubmit={analyze}>
   <label className="mt-4 block text-xs font-medium">Customer<select className="input mt-1" value={customerId} onChange={event=>setCustomerId(event.target.value)} required><option value="" disabled>Select customer</option>{customers.map(customer=><option key={customer.id} value={customer.id}>{customer.customer_code} · {customer.name}</option>)}</select></label>
   <div className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-700"><strong>Language:</strong> English</div>
   <label className="mt-3 block text-xs font-medium">Recording<input className="mt-2 block w-full text-xs" type="file" accept="audio/*,video/webm" onChange={event=>setFile(event.target.files?.[0]||null)} required/></label>
   {file&&<div className="mt-2 flex items-center gap-2 rounded-lg bg-slate-50 p-2 text-xs"><FileAudio size={14}/><span className="min-w-0 flex-1 truncate">{file.name}</span><span>{(file.size/1024/1024).toFixed(1)} MB</span></div>}
   <button disabled={!file||!customerId||busy} className="btn-primary mt-4 w-full">{busy?<><RefreshCw className="animate-spin" size={15}/>Batch transcription running…</>:<><Upload size={15}/>Analyze and save</>}</button>
   {busy&&<p className="mt-2 text-xs text-slate-500">Long recordings can take several minutes.</p>}{error&&<p className="mt-3 flex gap-2 text-xs text-red-600" role="alert"><AlertCircle className="shrink-0" size={15}/>{error}</p>}
  </form>
  {result&&<div className="mt-5 border-t pt-4">
   <div className="flex items-center justify-between gap-2"><p className="font-semibold text-navy">Saved for {result.customer_name}</p><span className={`badge ${tone}`}>{result.sentiment}</span></div>
   <div className="mt-3 rounded-lg border border-blue-100 bg-blue-50 p-3"><p className="text-[10px] font-semibold uppercase text-blue-500">Interaction summary</p><p className="mt-1 text-xs leading-5 text-navy">{result.summary}</p></div>
   <div className="mt-3 max-h-64 overflow-y-auto rounded-lg bg-slate-50 p-3 [scrollbar-gutter:stable]"><p className="text-[10px] font-semibold uppercase text-slate-400">English transcript</p><p className="mt-1 text-xs leading-5">{result.transcript}</p></div>
   <dl className="mt-3 grid grid-cols-2 gap-3 text-xs"><Metric label="Score" value={String(result.sentiment_score)}/><Metric label="Emotion" value={result.emotion}/><Metric label="Intent" value={result.intent}/><Metric label="Urgency" value={result.urgency}/></dl>
   <div className="mt-3 rounded-lg bg-blue-50 p-3"><p className="text-[10px] uppercase text-blue-500">Recommended route</p><p className="mt-1 text-xs font-semibold text-blue-900">{result.recommended_route}</p><p className="mt-1 text-xs text-blue-700">{result.routing_reason}</p></div>
  </div>}
  <p className="mt-3 text-[10px] text-slate-400">Batch processing supports recordings up to 2 hours and 100 MB.</p>
 </section>
}
function Metric({label,value}:{label:string;value:string}){return <div><dt className="text-slate-400">{label}</dt><dd className="mt-0.5 font-semibold text-navy">{value}</dd></div>}
