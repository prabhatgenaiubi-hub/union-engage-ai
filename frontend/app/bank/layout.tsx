import "./bank.css";
import "./customers.css";
import "./conversations.css";
import "./leads.css";
import {BankShell} from "@/components/bank-shell";
export default function Layout({children}:{children:React.ReactNode}){return <BankShell>{children}</BankShell>}
