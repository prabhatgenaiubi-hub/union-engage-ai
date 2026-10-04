"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import {ArrowRight,Building2,CalendarDays,Check,ContactRound,Download,Heart,IndianRupee,Info,MapPin,MessageSquareText,Pencil,ShieldCheck,Target,UserRound,UsersRound,WalletCards} from "lucide-react";
import {api,apiDownload} from "@/lib/api";

export default function Page(){
 const [profile,setProfile]=useState<any>(),[error,setError]=useState(""),[notice,setNotice]=useState(""),[editing,setEditing]=useState(false),[phone,setPhone]=useState(""),[email,setEmail]=useState(""),[saving,setSaving]=useState(false);
 useEffect(()=>{api("/customer/profile").then(setProfile).catch((e:any)=>setError(e.message))},[]);
 const initials=useMemo(()=>profile?.name?.split(" ").map((part:string)=>part[0]).slice(0,2).join("").toUpperCase()||"C",[profile]);
 if(error)return <p className="profile-error">{error}</p>;
 if(!profile)return <p className="profile-loading">Loading your profile…</p>;
 async function downloadStatement(){try{const file=await apiDownload("/customer/statement");const url=URL.createObjectURL(file.blob);const anchor=document.createElement("a");anchor.href=url;anchor.download=file.filename;anchor.click();URL.revokeObjectURL(url);setNotice("Your account statement has been downloaded.")}catch(e:any){setNotice(e.message)}}
 function openContact(){setPhone(profile.phone_number||"");setEmail(profile.email_address||"");setEditing(true);setNotice("")}
 async function saveContact(event:React.FormEvent){event.preventDefault();setSaving(true);try{const updated=await api("/customer/profile/contact",{method:"PATCH",body:JSON.stringify({phone_number:phone,email_address:email})});setProfile({...profile,...updated});setEditing(false);setNotice("Your contact details were updated successfully.")}catch(e:any){setNotice(e.message)}finally{setSaving(false)}}
 const details=[
  [UserRound,"Customer ID",profile.customer_code,"red"],
  [WalletCards,"Customer segment",profile.segment,"blue"],
  [MapPin,"City",profile.city,"green"],
  [CalendarDays,"Customer since",profile.relationship_since,"blue"],
  [UsersRound,"Relationship manager",profile.rm_name,"red"],
  [IndianRupee,"Average balance",`₹${Number(profile.average_balance).toLocaleString("en-IN")}`,"green"],
 ] as const;
 return <div className="customer-profile-page">
  <header className="profile-heading"><p>Customer profile</p><h1>{profile.name}</h1><span>Your banking relationship details.</span><em>Good people to bank with<br/><b>अच्छे लोग अच्छा बैंक</b><i/></em></header>
  <section className="profile-hero">
   <div className="profile-identity"><div className="profile-avatar-large">{initials}<i/></div><div><h2>{profile.name}</h2><span className="profile-tier"><StarIcon/> {profile.segment||"Privilege"}</span><p>Primary relationship customer since {profile.relationship_since||"—"}</p><small>Thank you for being a valued member of our banking family.<br/>We’re committed to supporting your financial journey.</small></div></div>
   <div className="profile-verification"><Status icon={<ShieldCheck/>} title={profile.profile_verified?"Profile verified":"Verification pending"} text={profile.profile_verified?"Your identity is verified":"Identity review is in progress"} tone="green"/><Status icon={<ContactRound/>} title={`KYC ${String(profile.kyc_status).toLowerCase()}`} text={profile.kyc_updated_at?`Updated ${new Date(profile.kyc_updated_at).toLocaleDateString("en-IN",{month:"short",year:"numeric"})}`:"Update date unavailable"} tone="blue"/><Status icon={<Heart/>} title={profile.trusted_customer?"Trusted customer":"Banking customer"} text="A valued banking partner" tone="red"/></div>
   <div className="profile-actions"><button onClick={downloadStatement}><Download/>Download statement</button><button onClick={openContact}><Pencil/>Update contact</button><Link href="/customer/chat?mode=assistant&topic=virtual-relationship-manager"><UserRound/>Talk to VRM</Link></div>
  </section>
  {notice&&<div className="profile-action-notice" role="status"><Info/>{notice}<button onClick={()=>setNotice("")}>×</button></div>}
  <SectionTitle>Profile details</SectionTitle>
  <section className="profile-details-grid">{details.map(([Icon,label,value,tone])=><article key={label}><span className={tone}><Icon/></span><div><p>{label}</p><b>{value||"—"}</b></div></article>)}</section>
  <SectionTitle>Relationship snapshot</SectionTitle>
  <section className="relationship-grid"><Snapshot icon={<Building2/>} label="Products held" value={String(profile.products_held)} text="Accounts, cards, loans & more" tone="red" href="/customer/products"/><Snapshot icon={<Target/>} label="Active goals" value={String(profile.active_goals)} text="Dreams to Reality" tone="green" href="/customer/goals"/><Snapshot icon={<MessageSquareText/>} label="Recent conversations" value={String(profile.recent_conversations)} text="Your conversation history" tone="blue" href="/customer/conversations"/><Snapshot icon={<WalletCards/>} label="Service status" value={profile.service_status} text={profile.pending_requests?`${profile.pending_requests} request(s) need attention`:"No pending requests"} tone="red" href="/customer/service-requests"/></section>
  <div className="profile-data-notice"><Info/><p><b>Profile data notice:</b> These details are shown from your bank customer record. Contact your relationship manager if something needs updating.</p></div>
  {editing&&<div className="contact-modal" role="dialog" aria-modal="true" aria-labelledby="contact-title"><button className="contact-scrim" aria-label="Close" onClick={()=>setEditing(false)}/><form onSubmit={saveContact}><h2 id="contact-title">Update contact details</h2><p>Keep your registered mobile number and email address current.</p><label>Mobile number<input value={phone} onChange={e=>setPhone(e.target.value)} required minLength={8} maxLength={20}/></label><label>Email address<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required/></label><div><button type="button" onClick={()=>setEditing(false)}>Cancel</button><button disabled={saving}>{saving?"Saving…":"Save changes"}</button></div></form></div>}
 </div>
}
function SectionTitle({children}:{children:React.ReactNode}){return <h2 className="profile-section-title"><i/>{children}</h2>}
function Status({icon,title,text,tone}:{icon:React.ReactNode;title:string;text:string;tone:string}){return <div className="profile-status"><span className={tone}>{icon}</span><div><b>{title}</b><p>{text}</p></div></div>}
function Snapshot({icon,label,value,text,tone,href}:{icon:React.ReactNode;label:string;value:string;text:string;tone:string;href:string}){return <Link href={href} className="relationship-card"><span className={tone}>{icon}</span><div><p>{label}</p><b>{value}</b><small>{text}</small></div><i><ArrowRight/></i></Link>}
function StarIcon(){return <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="m12 2 3 6 7 .9-5 4.8 1.2 6.8L12 17.3l-6.2 3.2L7 13.7 2 8.9 9 8z"/></svg>}
