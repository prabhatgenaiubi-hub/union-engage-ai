const BASE=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000/api";
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const token=typeof window!=="undefined"?localStorage.getItem("token"):null;
 const isForm=typeof FormData!=="undefined"&&options.body instanceof FormData;
 const response=await fetch(`${BASE}${path}`,{...options,headers:{...(!isForm?{"Content-Type":"application/json"}:{}),...(token?{Authorization:`Bearer ${token}`}:{}) ,...options.headers}});
 if(!response.ok)throw new Error((await response.json().catch(()=>({detail:"Request failed"}))).detail||"Request failed");
 return response.json();
}
export function logout(){localStorage.clear();location.href="/login"}
