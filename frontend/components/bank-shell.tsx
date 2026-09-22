"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {usePathname} from "next/navigation";
import {ChevronDown,ClipboardList,FileUp,LayoutDashboard,Lightbulb,LogOut,Menu,MessagesSquare,Route,ShieldAlert,Target,Users,X} from "lucide-react";
import {logout} from "@/lib/api";
import {NotificationMenu} from "./notification-menu";

const primary=[["/bank/dashboard","Dashboard",LayoutDashboard],["/bank/customers","Customer 360",Users],["/bank/conversations","Conversations",MessagesSquare],["/bank/leads","Leads",Target],["/bank/opportunities","Sales Opportunities",Lightbulb],["/bank/retention","Retention",ShieldAlert],["/bank/service-intelligence","Service Intelligence",Route],["/bank/service-requests","Service Requests",ClipboardList],["/bank/public-conversations","External Chats",MessagesSquare],["/bank/public-leads","External Leads",Target]] as const;
const admin=[["/bank/admin/knowledge","Knowledge Base / Upload PDF",FileUp]] as const;

export function BankShell({children}:{children:React.ReactNode}){
 const path=usePathname(),[open,setOpen]=useState(false),[role,setRole]=useState<string|null>(null),[name,setName]=useState("Bank User");
 useEffect(()=>{try{const user=JSON.parse(localStorage.getItem("user")||"{}");setRole(user.role||null);setName(user.display_name||"Bank User")}catch{setRole(null);setName("Bank User")}},[]);
 const isAdmin=role==="admin";
 const initials=name.split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0]).join("").toUpperCase()||"BU";
 const navigation=<><NavGroup label="Workspace" items={primary} path={path} close={()=>setOpen(false)}/>{isAdmin&&<NavGroup label="Administration" items={admin} path={path} close={()=>setOpen(false)}/>}</>;
 return <div className="bank-app">
  {open&&<button className="bank-scrim" aria-label="Close navigation" onClick={()=>setOpen(false)}/>}
  <aside className={`bank-sidebar ${open?"open":""}`}><div className="bank-brand"><img src="/Union_bank_small_icon.png" alt=""/><div><strong>Union Engage</strong><span>Digital Banking with<br/>a Personal Touch</span></div><button onClick={()=>setOpen(false)}><X/></button></div>{navigation}<button onClick={logout} className="bank-signout"><LogOut/>Sign out</button><p className="bank-tagline">Good people to bank with<br/>अच्छे लोग अच्छा बैंक<i/></p></aside>
  <main className="bank-main"><header className="bank-topbar"><div><button className="bank-menu" onClick={()=>setOpen(true)} aria-label="Open navigation"><Menu/></button><b>Bank Intelligence Portal</b></div><div className="bank-top-actions">{isAdmin&&<Link href="/bank/admin/knowledge"><FileUp/>Upload knowledge PDF</Link>}<NotificationMenu/><span className="bank-avatar" title={name}>{initials}</span><span className="bank-user-name">{name}</span><ChevronDown size={16}/></div></header><div className="bank-content">{children}</div></main>
 </div>
}
function NavGroup({label,items,path,close}:{label:string;items:readonly any[];path:string;close:()=>void}){return <><p className="bank-nav-label">{label}</p><nav className="bank-nav">{items.map(([href,text,Icon])=><Link key={href} href={href} onClick={close} className={path.startsWith(href)?"active":""}><Icon/>{text}</Link>)}</nav></>}
