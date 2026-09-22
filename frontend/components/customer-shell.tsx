"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
import {ChevronDown,ClipboardList,History,Home,LogOut,Menu,MessageSquareText,Target,UserRound,X} from "lucide-react";
import {flushPendingLeadDropoff,logout} from "@/lib/api";
import {useEffect,useState} from "react";
import {NotificationMenu} from "./notification-menu";

const links=[["/customer/dashboard","Home",Home],["/customer/profile","My profile",UserRound],["/customer/chat?mode=assistant","AI Assistant",MessageSquareText],["/customer/conversations","Conversations",History],["/customer/service-requests","Service requests",ClipboardList],["/customer/goals","Financial goals",Target]] as const;

export function CustomerShell({children}:{children:React.ReactNode}){
 const path=usePathname(),[open,setOpen]=useState(false),[name,setName]=useState("Customer");
 useEffect(()=>{try{const user=JSON.parse(localStorage.getItem("user")||"{}");setName(user.display_name||"Customer")}catch{setName("Customer")}void flushPendingLeadDropoff();const retry=()=>void flushPendingLeadDropoff();window.addEventListener("online",retry);return()=>window.removeEventListener("online",retry)},[]);
 const initials=name.split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0]).join("").toUpperCase()||"C";
 const navigation=<nav className="customer-nav">{links.map(([href,label,Icon])=>{const active=path===href.split("?")[0];const style=active?"active":"";return label==="AI Assistant"?<a key={href} href={href} onClick={()=>setOpen(false)} className={style}><Icon size={21}/>{label}</a>:<Link key={href} href={href} onClick={()=>setOpen(false)} className={style}><Icon size={21}/>{label}</Link>})}</nav>;
 return <div className="customer-app">
  <header className="customer-mobile-header"><Brand/><div><NotificationMenu customer/><button aria-label="Open menu" onClick={()=>setOpen(true)}><Menu/></button></div></header>
  {open&&<button className="customer-menu-scrim" aria-label="Close menu" onClick={()=>setOpen(false)}/>}
  <aside className={`customer-sidebar ${open?"open":""}`}><div className="sidebar-head"><Brand/><button aria-label="Close menu" onClick={()=>setOpen(false)}><X/></button></div>{navigation}<div className="sidebar-art"><img src="/Union_Bank_of_India_Logo.png" alt="Union Bank of India"/><span>Good people to bank with<br/><b>अच्छे लोग अच्छा बैंक</b></span><i/></div><button onClick={logout} className="customer-signout"><LogOut size={19}/>Sign out</button></aside>
  <main className="customer-main">
   <header className="customer-topbar"><div/><div className="topbar-actions"><NotificationMenu customer/><span className="topbar-divider"/><span className="customer-avatar">{initials}</span><b>{name}</b><ChevronDown size={17}/></div></header>
   <div className="customer-content">{children}</div>
  </main>
 </div>
}

function Brand(){return <div className="customer-brand"><img src="/Union_bank_small_icon.png" alt=""/><div><strong>Union Engage</strong><span>Digital Banking with<br/>a Personal Touch</span></div></div>}
