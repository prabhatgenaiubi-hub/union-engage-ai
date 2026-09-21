"use client";
import {useEffect,useRef,useState} from "react";
import Link from "next/link";
import {Bell,CheckCheck} from "lucide-react";
import {api} from "@/lib/api";

type Notification={id:number;title:string;severity:string;read:boolean;created_at:string};

export function NotificationMenu({customer=false}:{customer?:boolean}){
 const [open,setOpen]=useState(false),[items,setItems]=useState<Notification[]>([]),[loading,setLoading]=useState(false),[loaded,setLoaded]=useState(false);
 const root=useRef<HTMLDivElement>(null);
 const unread=items.filter(item=>!item.read).length;
 useEffect(()=>{const close=(event:MouseEvent)=>{if(root.current&&!root.current.contains(event.target as Node))setOpen(false)};document.addEventListener("mousedown",close);return()=>document.removeEventListener("mousedown",close)},[]);
 async function toggle(){const next=!open;setOpen(next);if(next&&!loaded){setLoading(true);try{setItems(await api<Notification[]>("/notifications"));setLoaded(true)}finally{setLoading(false)}}}
 async function markRead(item:Notification){if(item.read)return;setItems(list=>list.map(entry=>entry.id===item.id?{...entry,read:true}:entry));try{await api(`/notifications/${item.id}/read`,{method:"POST"})}catch{setLoaded(false)}}
 async function markAll(){const pending=items.filter(item=>!item.read);setItems(list=>list.map(item=>({...item,read:true})));await Promise.allSettled(pending.map(item=>api(`/notifications/${item.id}/read`,{method:"POST"})))}
 return <div className="notification-menu" ref={root}><button className={customer?"notification":"bank-bell"} aria-label={`Notifications${unread?` (${unread} unread)`:""}`} aria-expanded={open} onClick={toggle}><Bell size={21}/>{(!loaded||unread>0)&&<i/>}</button>{open&&<section className="notification-popover"><header><div><b>Notifications</b><span>{unread} unread</span></div>{unread>0&&<button onClick={markAll}><CheckCheck/>Mark all read</button>}</header><div className="notification-list">{loading?<p className="notification-state">Loading notifications…</p>:items.length?items.map(item=><Link href={customer?"/customer/service-requests":"/bank/service-requests"} key={item.id} className={item.read?"":"unread"} onClick={()=>markRead(item)}><i className={item.severity}/><span><b>{item.title}</b><small>{new Date(item.created_at).toLocaleString()}</small></span></Link>):<p className="notification-state">You’re all caught up.</p>}</div>{!customer&&<Link className="notification-view-all" href="/bank/notifications" onClick={()=>setOpen(false)}>View all notifications</Link>}</section>}</div>
}
