"use client";
import "./login.css";
import {useEffect,useState} from "react";
import {useRouter} from "next/navigation";
import {ArrowRight,BarChart3,Eye,EyeOff,LockKeyhole,ShieldCheck,UserRound,UsersRound} from "lucide-react";
import {api} from "@/lib/api";
import {FloatingAiAssistant} from "@/components/floating-ai-assistant";

type UserType="customer"|"employee";
type Mode="login"|"register";

export default function Login(){
 const router=useRouter();
 const [userType,setUserType]=useState<UserType>("customer");
 const [mode,setMode]=useState<Mode>("login");
 const [name,setName]=useState("");
 const [username,setUsername]=useState("");
 const [password,setPassword]=useState("");
 const [confirm,setConfirm]=useState("");
 const [showPassword,setShowPassword]=useState(false);
 const [remember,setRemember]=useState(true);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(false);

 useEffect(()=>setUsername(localStorage.getItem("remembered_login")||""),[]);

 function changeMode(next:Mode){
  setMode(next);setError("");setPassword("");setConfirm("");setShowPassword(false);
 }

 async function submit(event:React.FormEvent){
  event.preventDefault();setError("");
  if(mode==="register"&&password!==confirm){setError("Passwords do not match.");return}
  setLoading(true);
  try{
   const path=mode==="register"?"/auth/register":`/auth/${userType}/login`;
   const body=mode==="register"?{user_type:userType,display_name:name,login_id:username,password}:{login_id:username,password};
   const result=await api<any>(path,{method:"POST",body:JSON.stringify(body)});
   localStorage.setItem("token",result.access_token);localStorage.setItem("user",JSON.stringify(result));
   if(mode==="login"&&remember)localStorage.setItem("remembered_login",username);
   else if(mode==="login")localStorage.removeItem("remembered_login");
   router.push(userType==="customer"?"/customer/dashboard":"/bank/dashboard");
  }catch(e:any){setError(e.message)}finally{setLoading(false)}
 }

 const idLabel=userType==="customer"?"Customer ID / Mobile Number":"Employee ID";
 return <main className="login-page">
  <div className="wash wash-one"/><div className="wash wash-two"/>
  <header className="login-header"><div className="engage-brand"><img src="/Union_bank_small_icon.png" alt=""/><div><strong>Union Engage</strong><span>Intelligent Customer Engagement Platform</span></div></div></header>
  <section className="login-layout">
   <div className="login-intro"><p className="eyebrow">100+ Years of Trust &amp; Service</p><h1>Secure access to<br className="desktop-break"/> intelligent banking <em>engagement.</em></h1><p className="intro-copy">Digital Banking with a Personal Touch—connecting conversations, insights and banking intelligence for customers and bank teams.</p><div className="benefit-row"><Benefit icon={<UsersRound/>} label={<>Better<br/>conversations</>} tone="red"/><Benefit icon={<BarChart3/>} label={<>Deeper<br/>insights</>} tone="green"/><Benefit icon={<ShieldCheck/>} label={<>Smarter<br/>service</>} tone="red"/></div></div>
   <div className="building-scene"><img className="bank-building" src="/bank-building.png" alt="Union Bank of India headquarters with the Union Bank logo"/><div className="people-first">Hum Wahi Hain<br/><span>हम वही हैं</span><i/></div></div><p className="side-motto side-motto-left">Good people<br/>to bank with<br/>अच्छे लोग<br/>अच्छा बैंक</p>
   <div className="login-panel">
    <h2>{mode==="login"?"Welcome back":"Create your account"}</h2>
    <p className="panel-subtitle">{mode==="login"?"Sign in to continue to Union Engage":"Register for secure access to Union Engage"}</p>
    <div className="role-switch" role="group" aria-label="Choose account type"><button type="button" onClick={()=>{setUserType("customer");setError("")}} className={userType==="customer"?"active":""}><UserRound size={20}/>Customer</button><button type="button" onClick={()=>{setUserType("employee");setError("")}} className={userType==="employee"?"active":""}><ShieldCheck size={20}/>Bank Employee</button></div>
    <form onSubmit={submit}>
     {mode==="register"&&<label>Full Name<span className="input-wrap"><UserRound size={21}/><input autoComplete="name" placeholder="Enter your full name" value={name} onChange={e=>setName(e.target.value)} required minLength={2}/></span></label>}
     <label>{idLabel}<span className="input-wrap"><UserRound size={21}/><input autoComplete="username" placeholder={userType==="customer"?"Enter customer ID or mobile number":"Enter employee ID"} value={username} onChange={e=>setUsername(e.target.value)} required minLength={3}/></span></label>
     <label>Password<span className="input-wrap"><LockKeyhole size={20}/><input type={showPassword?"text":"password"} autoComplete={mode==="login"?"current-password":"new-password"} placeholder={mode==="login"?"Enter your password":"Minimum 8 characters"} value={password} onChange={e=>setPassword(e.target.value)} required minLength={mode==="register"?8:4}/><button type="button" className="password-toggle" aria-label={showPassword?"Hide password":"Show password"} onClick={()=>setShowPassword(v=>!v)}>{showPassword?<EyeOff size={21}/>:<Eye size={21}/>}</button></span></label>
     {mode==="register"&&<label>Confirm Password<span className="input-wrap"><LockKeyhole size={20}/><input type={showPassword?"text":"password"} autoComplete="new-password" placeholder="Re-enter your password" value={confirm} onChange={e=>setConfirm(e.target.value)} required minLength={8}/></span></label>}
     {mode==="login"&&<div className="form-options"><label className="remember"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)}/><span>Remember me</span></label><button type="button" className="forgot" onClick={()=>setError("Please contact your bank administrator to reset your password.")}>Forgot password?</button></div>}
     {error&&<p role="alert" className="login-error">{error}</p>}
     <button className="sign-in" disabled={loading}>{loading?"Please wait…":mode==="login"?"Sign in securely":"Create account"}<ArrowRight size={22}/></button>
    </form>
    <div className="divider"><span/>OR<span/></div>
    <button type="button" className="microsoft-button" onClick={()=>changeMode(mode==="login"?"register":"login")}>{mode==="login"?"Register a new account":"Already registered? Sign in"}</button>
    <p className="secure-note"><LockKeyhole size={15}/>Secure banking access</p>
   </div>
  </section>
  <footer><span>© Union Bank of India</span><nav><a href="#">Privacy</a><i/><a href="#">Help</a></nav></footer>
  <FloatingAiAssistant/>
 </main>
}
function Benefit({icon,label,tone}:{icon:React.ReactNode;label:React.ReactNode;tone:"red"|"green"}){return <div className="benefit"><span className={tone}>{icon}</span><b>{label}</b></div>}
