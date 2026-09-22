"use client";
import Link from "next/link";
import {ArrowRight,CreditCard,Heart,Home,MessageCircle,MessageSquareText,ShieldCheck,Sparkles,Target,TrendingUp,UsersRound} from "lucide-react";
import {useEffect,useState} from "react";

export default function Page(){
 const [name,setName]=useState("Aarav");
 const [greeting,setGreeting]=useState("Hello");
 useEffect(()=>{try{const user=JSON.parse(localStorage.getItem("user")||"{}");setName(user.display_name?.split(" ")[0]||"Customer")}catch{}const hour=new Date().getHours();setGreeting(hour<12?"Good morning":hour<17?"Good afternoon":"Good evening")},[]);
 const date=new Intl.DateTimeFormat("en-IN",{weekday:"long",day:"numeric",month:"long"}).format(new Date());
 return <div className="dashboard">
  <section className="dashboard-welcome"><p>{date}</p><h1>{greeting}, <span>{name}</span></h1><h2>How can we help with your banking today?</h2><em>Hum Wahi Hain • हम वही हैं</em></section>
  <div className="dashboard-primary">
   <section className="assistant-hero">
    <div className="assistant-copy"><p className="section-kicker"><i/>Your AI banking assistant</p><h2>Ask, plan, or get things done<br/>with Union Engage</h2><p>Get instant answers, report an issue, plan your goals,<br/>explore loan options and more — all in one place.</p><div className="prompt-chips"><span>Check my account balance</span><span>How can I apply for a loan?</span><span>Help me plan a goal</span></div><Link href="/customer/chat" className="conversation-button"><MessageCircle size={19}/>Start conversation<ArrowRight size={19}/></Link></div>
    <div className="assistant-visual"><div className="speech-bubble"><b>Hi {name}!</b><span>How can I help you today?</span></div><div className="bot"><span className="bot-antenna"/><div className="bot-head"><i/><b>⌣</b><i/></div><div className="bot-body"><img src="/Union_bank_small_icon.png" alt=""/></div></div></div>
   </section>
   <Link href="/customer/goals" className="goal-card" aria-label="View all financial goals"><div className="goal-heading"><span><Target/></span><div><h3>Financial Goals</h3><p>View and manage your goals</p></div><span className="goal-menu">•••</span></div><div className="goal-generic-icon"><Target size={88}/></div><div className="goal-generic-copy"><b>Plan for what matters to you</b><p>Create a goal, track your progress, and adjust your plan anytime.</p></div><div className="goal-status"><span><TrendingUp/></span><div><b>Your goals, your pace</b><p>Open financial goals to view your personal plans.</p></div><ArrowRight/></div></Link>
  </div>
  <div className="suggested-title"><h2><i/>Suggested actions</h2><Link href="/customer/chat">View all <ArrowRight size={17}/></Link></div>
  <section className="action-grid"><Action icon={<CreditCard/>} title="Card controls" text="Manage or block a debit card" detail="Keep your cards safe and secure every time." tone="red"/><Action icon={<Target/>} title="Plan a goal" text="Create a practical savings plan" detail="Set a goal, build a plan, and bring your dreams closer." tone="blue"/><Action icon={<Home/>} title="Home loan" text="Check documents and eligibility" detail="Take the next step towards your dream home." tone="green"/></section>
  <section className="trust-strip"><Trust icon={<UsersRound/>} label="Trusted by" value="3+ Crore Customers"/><Trust icon={<ShieldCheck/>} label="A Legacy of" value="100+ Years"/><Trust icon={<TrendingUp/>} label="Pan India Presence" value="9,000+ Branches"/><Trust icon={<Heart/>} label="Committed to" value="Trust & Service"/><p>Good people to bank with<br/><span>अच्छे लोग अच्छा बैंक</span><i/></p></section>
 </div>
}

function Action({icon,title,text,detail,tone}:{icon:React.ReactNode;title:string;text:string;detail:string;tone:string}){return <Link href="/customer/chat" className={`action-card ${tone}`}><span className="action-icon">{icon}</span><div><h3>{title}</h3><p>{text}</p><small>{detail}</small></div><span className="action-arrow"><ArrowRight/></span></Link>}
function Trust({icon,label,value}:{icon:React.ReactNode;label:string;value:string}){return <div className="trust-item"><span>{icon}</span><div><p>{label}</p><b>{value}</b></div></div>}
