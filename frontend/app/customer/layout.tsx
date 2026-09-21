import "./customer.css";
import "./chat.css";
import "./conversations.css";
import "./requests.css";
import {CustomerShell} from "@/components/customer-shell";
export default function Layout({children}:{children:React.ReactNode}){return <CustomerShell>{children}</CustomerShell>}
