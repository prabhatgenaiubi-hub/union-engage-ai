const BASE=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000/api";
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const token=typeof window!=="undefined"?localStorage.getItem("token"):null;
 const isForm=typeof FormData!=="undefined"&&options.body instanceof FormData;
 const response=await fetch(`${BASE}${path}`,{...options,headers:{...(!isForm?{"Content-Type":"application/json"}:{}),...(token?{Authorization:`Bearer ${token}`}:{}) ,...options.headers}});
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
export function logout(){localStorage.clear();location.href="/login"}
