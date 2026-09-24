"use client";
import {GripVertical,Send,X} from "lucide-react";
import {useEffect,useRef,useState} from "react";
import {api} from "@/lib/api";

type Point={x:number;y:number};
type Message={role:"user"|"assistant";content:string};
const SIZE=76,EDGE=18;
const clamp=(value:number,min:number,max:number)=>Math.min(Math.max(value,min),max);

export function FloatingAiAssistant(){
 const [position,setPosition]=useState<Point>({x:0,y:0}),[ready,setReady]=useState(false),[open,setOpen]=useState(false),[messages,setMessages]=useState<Message[]>([{role:"assistant",content:"Hello. I can answer general banking questions using approved Union Bank knowledge. How may I help?"}]),[text,setText]=useState(""),[busy,setBusy]=useState(false);
 const drag=useRef<{pointerId:number;offsetX:number;offsetY:number;startX:number;startY:number;moved:boolean}|null>(null),threadRef=useRef<HTMLDivElement>(null);
 const sessionRef=useRef<string|null>(null);
 useEffect(()=>{const saved=localStorage.getItem("public_chat_session_id");if(!saved)return;sessionRef.current=saved;api<{messages:Message[]}>(`/public/chat/${saved}`).then(result=>{if(result.messages.length)setMessages(result.messages)}).catch(()=>{sessionRef.current=null;localStorage.removeItem("public_chat_session_id")})},[]);
 useEffect(()=>{const saved=localStorage.getItem("ai_widget_position");let point:Point|undefined;try{if(saved)point=JSON.parse(saved)}catch{}setPosition({x:clamp(point?.x??window.innerWidth-SIZE-EDGE,EDGE,window.innerWidth-SIZE-EDGE),y:clamp(point?.y??window.innerHeight-SIZE-EDGE,EDGE,window.innerHeight-SIZE-EDGE)});setReady(true);const resize=()=>setPosition(current=>({x:clamp(current.x,EDGE,window.innerWidth-SIZE-EDGE),y:clamp(current.y,EDGE,window.innerHeight-SIZE-EDGE)}));window.addEventListener("resize",resize);return()=>window.removeEventListener("resize",resize)},[]);
 useEffect(()=>{if(ready)localStorage.setItem("ai_widget_position",JSON.stringify(position))},[position,ready]);
 useEffect(()=>{threadRef.current?.scrollTo({top:threadRef.current.scrollHeight,behavior:"smooth"})},[messages,busy,open]);
 function down(event:React.PointerEvent<HTMLButtonElement>){event.currentTarget.setPointerCapture(event.pointerId);drag.current={pointerId:event.pointerId,offsetX:event.clientX-position.x,offsetY:event.clientY-position.y,startX:event.clientX,startY:event.clientY,moved:false}}
 function move(event:React.PointerEvent<HTMLButtonElement>){if(!drag.current||drag.current.pointerId!==event.pointerId)return;if(Math.hypot(event.clientX-drag.current.startX,event.clientY-drag.current.startY)>5)drag.current.moved=true;if(drag.current.moved)setPosition({x:clamp(event.clientX-drag.current.offsetX,EDGE,window.innerWidth-SIZE-EDGE),y:clamp(event.clientY-drag.current.offsetY,EDGE,window.innerHeight-SIZE-EDGE)})}
 function up(event:React.PointerEvent<HTMLButtonElement>){if(!drag.current||drag.current.pointerId!==event.pointerId)return;const moved=drag.current.moved;drag.current=null;if(!moved)setOpen(value=>!value)}
 async function send(){const value=text.trim();if(!value||busy)return;setMessages(items=>[...items,{role:"user",content:value}]);setText("");setBusy(true);try{const result=await api<any>("/public/chat",{method:"POST",body:JSON.stringify({message:value,session_id:sessionRef.current})});if(result.session_id){sessionRef.current=result.session_id;localStorage.setItem("public_chat_session_id",result.session_id)}setMessages(items=>[...items,{role:"assistant",content:result.message}])}catch(error:any){setMessages(items=>[...items,{role:"assistant",content:error.message}])}finally{setBusy(false)}}
 if(!ready)return null;
 const panelWidth=Math.min(380,window.innerWidth-24),panelHeight=Math.min(510,window.innerHeight-110);
 const panelLeft=clamp(position.x+SIZE-panelWidth,12,window.innerWidth-panelWidth-12);
 const panelTop=position.y>window.innerHeight/2?Math.max(12,position.y-panelHeight-12):Math.min(window.innerHeight-panelHeight-12,position.y+SIZE+12);
 return <>
  {open&&<section role="dialog" aria-label="AI banking assistant" className="fixed z-[119] flex overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl" style={{left:panelLeft,top:panelTop,width:panelWidth,height:panelHeight,flexDirection:"column"}}>
   <header className="flex items-center justify-between bg-navy px-4 py-3 text-white"><div className="flex items-center gap-2"><span className="grid h-10 w-10 place-items-center overflow-hidden rounded-full border-2 border-white/80 bg-white shadow"><img src="/assistant-avatar.png" alt="" width={40} height={40} draggable={false} className="pointer-events-none h-full w-full object-cover"/></span><div><p className="text-sm font-bold">Union Engage</p><p className="text-[10px] text-blue-100">Public Knowledge Assistant</p></div></div><button className="rounded-full p-2 hover:bg-white/10" onClick={()=>setOpen(false)} aria-label="Close assistant"><X size={18}/></button></header>
   <div ref={threadRef} className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-4">{messages.map((message,index)=><div key={index} className={`max-w-[88%] rounded-2xl px-3 py-2 text-xs leading-5 ${message.role==="user"?"ml-auto bg-navy text-white":"border bg-white text-slate-700"}`}>{message.content}</div>)}{busy&&<p className="text-xs text-slate-400">Preparing an answer…</p>}</div>
   <div className="border-t bg-white p-3"><div className="flex gap-2"><input className="input text-sm" value={text} onChange={event=>setText(event.target.value)} onKeyDown={event=>event.key==="Enter"&&void send()} placeholder="Ask a general banking question…"/><button className="btn-primary px-3" onClick={()=>void send()} disabled={busy||!text.trim()} aria-label="Send"><Send size={17}/></button></div><p className="mt-2 text-center text-[10px] text-slate-400">Sign in for account-specific help and service requests.</p></div>
  </section>}
  <button aria-label={open?"Move or close AI assistant":"Move or open AI assistant"} title="Drag to move · Click to chat" onPointerDown={down} onPointerMove={move} onPointerUp={up} className="fixed z-[120] grid touch-none select-none place-items-center overflow-visible rounded-full bg-white text-navy shadow-[0_10px_35px_rgba(37,99,235,.45)] ring-4 ring-white transition-transform hover:scale-110" style={{left:position.x,top:position.y,width:SIZE,height:SIZE}}><img src="/assistant-avatar.png" alt="Virtual banking assistant" width={76} height={76} draggable={false} className="pointer-events-none h-full w-full rounded-full object-cover motion-safe:animate-[robot-float_4s_ease-in-out_infinite]"/><GripVertical className="absolute -left-1 top-7 rounded-full bg-white text-slate-400 shadow" size={15}/><span className="absolute right-0 top-0 h-4 w-4 rounded-full border-[3px] border-white bg-emerald-400 shadow"/></button>
 </>
}
