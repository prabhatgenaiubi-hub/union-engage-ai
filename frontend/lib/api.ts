const BASE=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000/api";
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const token=typeof window!=="undefined"?localStorage.getItem("token"):null;
 const isForm=typeof FormData!=="undefined"&&options.body instanceof FormData;
 let response:Response;
 try{response=await fetch(`${BASE}${path}`,{cache:options.cache||"no-store",...options,headers:{...(!isForm?{"Content-Type":"application/json"}:{}),...(token?{Authorization:`Bearer ${token}`}:{}) ,...options.headers}})}catch{throw new Error("The banking service is temporarily unreachable. Please try again in a moment.")}
 if(!response.ok)throw new Error((await response.json().catch(()=>({detail:"Request failed"}))).detail||"Request failed");
 return response.json();
}
export async function apiDownload(path:string):Promise<{blob:Blob;filename:string}>{
 const token=typeof window!=="undefined"?localStorage.getItem("token"):null;
 const response=await fetch(`${BASE}${path}`,{headers:{...(token?{Authorization:`Bearer ${token}`}:{})}});
 if(!response.ok)throw new Error((await response.json().catch(()=>({detail:"Download failed"}))).detail||"Download failed");
 const disposition=response.headers.get("Content-Disposition")||"";
 return {blob:await response.blob(),filename:disposition.match(/filename=([^;]+)/)?.[1]?.replaceAll('"',"")||"download"};
}
export async function queueLeadDropoff(leadId:number){
 localStorage.setItem("pending_lead_dropoff",String(leadId));
 const token=localStorage.getItem("token");if(!token)return false;
 try{const response=await fetch(`${BASE}/leads/${leadId}/abandon`,{method:"POST",headers:{Authorization:`Bearer ${token}`},keepalive:true});if(!response.ok)return false;localStorage.removeItem("pending_lead_dropoff");localStorage.removeItem("active_lead_id");localStorage.removeItem("active_lead_status");return true}catch{return false}
}
export async function flushPendingLeadDropoff(){const leadId=Number(localStorage.getItem("pending_lead_dropoff"));if(leadId)await queueLeadDropoff(leadId)}
export async function logout(){
 const token=localStorage.getItem("token"),leadId=localStorage.getItem("active_lead_id"),leadStatus=localStorage.getItem("active_lead_status");
 if(token&&leadId&&leadStatus!=="Qualified"){
  await queueLeadDropoff(Number(leadId));
 }
 localStorage.clear();location.href="/login";
}
