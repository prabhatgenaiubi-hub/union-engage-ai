"use client";
import Link from "next/link";
export function CoachingPlan({plan,conversationId}:{plan:any;conversationId?:number}){
 if(!plan?.stage)return null;
 return <section className="mt-4 space-y-3 rounded-xl border border-blue-100 bg-white p-4 text-sm">
  <h3 className="font-semibold text-navy">Your financial picture · {plan.stage}</h3>
  <p className="leading-6 text-slate-600">{plan.summary}</p>
  {!!plan.unknown_fields?.length&&<p className="text-amber-700">Some details were skipped. These figures are provisional.</p>}
  <h4 className="font-semibold">Priorities to discuss</h4>
  <ul className="list-disc space-y-1 pl-5">{plan.priorities?.map((p:string)=><li key={p}>{p}</li>)}</ul>
  {!!plan.scenarios?.length&&<div className="overflow-x-auto"><table className="w-full text-left text-xs"><caption className="mb-2 text-left font-semibold">Illustrative goal alternatives</caption><thead><tr><th>Timeline</th><th>Monthly saving needed</th></tr></thead><tbody>{plan.scenarios.map((s:any,i:number)=><tr key={i}><td className="py-1">{s.timeline_months} months</td><td>₹{s.monthly_required.toLocaleString("en-IN")}</td></tr>)}</tbody></table></div>}
  {plan.confirmed&&!plan.actions?.length&&<p>In chat, choose an action: {plan.options?.map((o:any)=>`“choose ${o.id}” — ${o.title}`).join("; ")}.</p>}
  {!!plan.actions?.length&&<div className="rounded-lg bg-emerald-50 p-3"><h4 className="font-semibold">Agreed action</h4>{plan.actions.map((a:any)=><p className="mt-1" key={a.id}>{a.title}{a.monthly_amount!=null?` · ₹${a.monthly_amount.toLocaleString("en-IN")}/month`:""} · Review on {a.review_on}</p>)}</div>}
  {!!plan.reviews?.length&&<p className="text-xs text-slate-500">{plan.reviews.length} saved progress check-in(s). Latest: {plan.reviews[plan.reviews.length-1].note}</p>}
  <details className="text-xs text-slate-500"><summary className="cursor-pointer">Planning assumptions</summary><ul className="mt-2 list-disc pl-4">{plan.assumptions?.map((a:string)=><li key={a}>{a}</li>)}</ul></details>
  {conversationId&&<Link className="btn-secondary" href={`/customer/chat?mode=coach&conversation=${conversationId}`}>Continue coaching / review progress</Link>}
 </section>
}
