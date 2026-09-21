"use client";
import {useEffect,useState} from "react";
import {api} from "@/lib/api";
import {AlertTriangle,ArrowRight,Heart,Lightbulb,MessageSquareText,ShieldAlert,Star,TrendingUp,Users,UserRoundCheck,ClipboardList} from "lucide-react";
import {ResponsiveContainer,AreaChart,Area,XAxis,YAxis,Tooltip,BarChart,Bar,CartesianGrid,Cell} from "recharts";

export default function Page(){
 const [d,setD]=useState<any>();
 const [employeeName,setEmployeeName]=useState("Bank Admin");
 const [greeting,setGreeting]=useState("Hello");
 useEffect(()=>{api("/dashboard").then(setD).catch(()=>{});try{const user=JSON.parse(localStorage.getItem("user")||"{}");setEmployeeName(user.display_name?.split(" ")[0]||"Bank Admin")}catch{}const hour=new Date().getHours();setGreeting(hour<12?"Good morning":hour<17?"Good afternoon":"Good evening")},[]);
 if(!d)return <div className="bank-loading">Loading intelligence dashboard…</div>;
 const k=d.kpis;
 const stats=[
  [MessageSquareText,"Conversations",k.conversations,"Today","50%","blue"],
  [ClipboardList,"Open Service Requests",k.open_requests,"","20%","red"],
  [UserRoundCheck,"Hot Leads",k.hot_leads,"","100%","green"],
  [ShieldAlert,"High Attrition Risk",k.high_risk,"","100%","green"],
  [Users,"Total Customers",k.active_customers,"","5%","blue"],
  [AlertTriangle,"Pending Priority Escalations",k.priority_escalations,"","0%","red"],
  [Star,"Average CSAT",`${k.csat}/5`,"","25%","blue"],
  [Heart,"NPS Estimate",k.nps>0?`+${k.nps}`:k.nps,"","0%","purple"],
 ] as const;
 return <div className="executive-dashboard">
  <section className="executive-heading"><div><h1>Executive dashboard</h1><p>Unified customer engagement intelligence at a glance.</p></div><em>People. Progress. Prosperity.<i/></em></section>
  <section className="executive-insight"><div className="mini-bot"><span>⌣</span></div><div><h2>{greeting}, {employeeName}!</h2><p>Here’s your latest customer engagement overview. You’re on track to deliver a better banking experience.</p></div><div className="ai-insight"><span><Lightbulb/></span><div><b>AI Insight</b><p>Conversations are up 25% this week. Keep the momentum going!</p></div><ArrowRight/></div></section>
  <section className="executive-stats">{stats.map(([Icon,label,value,note,change,tone])=><Kpi key={label} icon={<Icon/>} label={label} value={value} note={note} change={change} tone={tone}/>)}</section>
  <section className="executive-charts">
   <Chart title="Conversation trend · last 7 days" subtitle="Total conversations across all channels"><div className="period-tabs"><b>7 days</b><span>30 days</span><span>90 days</span></div><ResponsiveContainer width="100%" height={220}><AreaChart data={d.conversation_trend}><defs><linearGradient id="bankArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#0878e4" stopOpacity={.35}/><stop offset="1" stopColor="#0878e4" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#dce8f2"/><XAxis dataKey="day" tickLine={false}/><YAxis allowDecimals={false} tickLine={false}/><Tooltip/><Area type="monotone" dataKey="count" stroke="#0878e4" strokeWidth={3} fill="url(#bankArea)"/></AreaChart></ResponsiveContainer></Chart>
   <Chart title="Lead funnel · current status" subtitle="Distribution of leads across stages"><ResponsiveContainer width="100%" height={220}><BarChart data={d.lead_funnel}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#dce8f2"/><XAxis dataKey="stage" tickLine={false}/><YAxis allowDecimals={false} tickLine={false}/><Tooltip/><Bar dataKey="value" radius={[6,6,0,0]}>{d.lead_funnel.map((_:any,i:number)=><Cell key={i} fill={["#df1733","#7ca7d4","#0878e4","#df1733","#16a36a"][i%5]}/>)}</Bar></BarChart></ResponsiveContainer></Chart>
  </section>
  <section className="key-takeaway"><span><Lightbulb/></span><div><b>Key takeaway</b><p>Conversations are up 25% this week. Focus on converting qualified leads to improve outcomes.</p></div></section>
 </div>
}
function Kpi({icon,label,value,note,change,tone}:{icon:React.ReactNode;label:string;value:any;note:string;change:string;tone:string}){return <article className={`executive-kpi ${tone}`}><span className="kpi-icon">{icon}</span><div><h3>{label}</h3>{note&&<p>{note}</p>}<strong>{value}</strong></div><div className="kpi-change"><b><TrendingUp/> {change}</b><span>vs. last week</span></div><svg viewBox="0 0 90 28" aria-hidden="true"><polyline points="0,25 18,23 34,15 52,18 72,7 90,10"/></svg></article>}
function Chart({title,subtitle,children}:{title:string;subtitle:string;children:React.ReactNode}){return <article className="executive-chart"><div className="chart-heading"><span><TrendingUp/></span><div><h2>{title}</h2><p>{subtitle}</p></div></div>{children}</article>}
