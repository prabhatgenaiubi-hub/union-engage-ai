"use client";
import {useState} from "react";
import {useRouter} from "next/navigation";
import {api} from "@/lib/api";
import {Logo} from "./logo";

export function LoginForm({type}:{type:"customer"|"employee"}){
 const router=useRouter();
 const [id,setId]=useState("");
 const [password,setPassword]=useState("");
 const [error,setError]=useState(""),[loading,setLoading]=useState(false);
 async function submit(e:React.FormEvent){
  e.preventDefault();setLoading(true);setError("");
  try{
   const d=await api<any>(`/auth/${type==="customer"?"customer":"employee"}/login`,{method:"POST",body:JSON.stringify({login_id:id,password})});
   localStorage.setItem("token",d.access_token);localStorage.setItem("user",JSON.stringify(d));
   router.push(type==="customer"?"/customer/dashboard":"/bank/dashboard");
  }catch(e:any){setError(e.message)}finally{setLoading(false)}
 }
 return <main className="grid min-h-screen place-items-center bg-mist p-5"><div className="card w-full max-w-md p-8"><Logo/><h1 className="mt-8 text-2xl font-bold text-navy">{type==="customer"?"Customer banking":"Bank admin portal"}</h1><form onSubmit={submit} className="mt-6 space-y-4"><label className="block text-sm font-medium">{type==="customer"?"Customer ID":"Admin ID"}<input className="input mt-1" autoComplete="username" value={id} onChange={e=>setId(e.target.value)}/></label><label className="block text-sm font-medium">Password<input className="input mt-1" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label>{error&&<p className="text-sm text-red-600">{error}</p>}<button disabled={loading||!id||!password} className="btn-primary w-full">{loading?"Signing in…":"Sign in"}</button></form></div></main>;
}
