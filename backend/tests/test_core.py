from app.services.intelligence import provider,lead_score,retention,route
from app.services.knowledge import knowledge_retriever
from app.services.engagement import engagement_decision
def test_authentication(client): assert client.post("/api/auth/customer/login",json={"login_id":"T001","password":"Demo@123"}).status_code==200
def test_bad_authentication(client): assert client.post("/api/auth/customer/login",json={"login_id":"T001","password":"bad!"}).status_code==401
def test_public_login_assistant_uses_only_approved_knowledge(client):
 from app.db.session import SessionLocal
 from app.models import KnowledgeArticle
 db=SessionLocal();db.add(KnowledgeArticle(title="Minimum balance requirement",category="Accounts",keywords="minimum balance requirement",content="Approved minimum-balance guidance."));db.commit();db.close()
 response=client.post("/api/public/chat",json={"message":"What is the minimum balance requirement?"});assert response.status_code==200 and response.json()["grounded"] is True and response.json()["sources"]
 missing=client.post("/api/public/chat",json={"message":"Tell me my private account balance"});assert missing.status_code==200 and missing.json()["grounded"] is False
def test_public_login_assistant_greeting_does_not_retrieve_documents(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 def unexpected(*args,**kwargs):raise AssertionError("Greeting should not search knowledge")
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",unexpected)
 for greeting in ("Hi","Hello!","Good morning","Namaste"):
  response=client.post("/api/public/chat",json={"message":greeting})
  assert response.status_code==200
  assert "What would you like to know?" in response.json()["message"]
  assert response.json()["grounded"] is False
def test_public_login_assistant_combined_greeting(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 def unexpected(*args,**kwargs):raise AssertionError("Greeting should not search knowledge")
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",unexpected)
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",unexpected)
 for greeting in ("Hey, How are you?","Hi, how are you?","Hello! How is it going?"):
  answer=client.post("/api/public/chat",json={"message":greeting}).json()
  assert "ready to help" in answer["message"] and answer["sources"]==[]
def test_public_login_assistant_rejects_unrelated_pdf_match(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",lambda *args,**kwargs:[{"title":"MSE policy","page":9,"content":"Know your customer business account opening procedure"}])
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",lambda *args,**kwargs:[])
 response=client.post("/api/public/chat",json={"message":"What are the branch hours?"})
 assert response.status_code==200 and response.json()["grounded"] is False
def test_public_login_assistant_answers_broad_debit_card_request(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 def unexpected(*args,**kwargs):raise AssertionError("Broad help should not search PDF documents")
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",unexpected)
 response=client.post("/api/public/chat",json={"message":"Can you provide help with debit card?"})
 assert response.status_code==200
 assert "lost, blocked, not working" in response.json()["message"]
 assert response.json()["grounded"] is False
def test_public_login_assistant_explains_its_services_without_search(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 def unexpected(*args,**kwargs):raise AssertionError("Capabilities question should not search documents")
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",unexpected)
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",unexpected)
 for question in ("What services you provide?","What services do you offer?","How can you help me?"):
  response=client.post("/api/public/chat",json={"message":question})
  assert response.status_code==200
  assert "accounts, debit cards" in response.json()["message"]
  assert response.json()["grounded"] is False
def test_public_login_assistant_handles_small_talk_and_keeps_context(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 small_talk=client.post("/api/public/chat",json={"message":"How are you?"}).json()
 assert "ready to help" in small_talk["message"] and small_talk["sources"]==[]
 seen=[]
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",lambda db,query,limit:seen.append(query) or [])
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",lambda *args,**kwargs:[])
 first=client.post("/api/public/chat",json={"message":"How do I request a cheque book?"}).json()
 client.post("/api/public/chat",json={"message":"What about that?","session_id":first["session_id"]})
 assert "cheque book" in seen[-1].lower()
def test_public_login_assistant_does_not_answer_compensation_with_card_article(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 from app.services.knowledge import KnowledgeMatch
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",lambda *args,**kwargs:[KnowledgeMatch(1,"Debit card block","Cards","Block your debit card in mobile banking.",5)])
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",lambda *args,**kwargs:[])
 response=client.post("/api/public/chat",json={"message":"How does the bank compensate an accountholder for instruments lost in transit?"}).json()
 assert response["grounded"] is False and "debit card" not in response["message"].lower()
def test_public_interest_collects_contact_and_saves_external_lead(client,admin_headers):
 from app.db.session import SessionLocal
 from app.models import PublicLead
 first=client.post("/api/public/chat",json={"message":"I want a home loan."}).json()
 session_id=first["session_id"]
 assert first["contact_step"]=="name" and "name" in first["message"].lower()
 db=SessionLocal();assert db.query(PublicLead).count()==0;db.close()
 for value,step in (("Asha Sharma","phone"),("9876543210","email")):
  response=client.post("/api/public/chat",json={"message":value,"session_id":session_id}).json()
  assert response["contact_step"]==step
 final=client.post("/api/public/chat",json={"message":"asha@example.com","session_id":session_id}).json()
 assert final["contact_step"]=="" and "saved" in final["message"].lower()
 db=SessionLocal();lead=db.query(PublicLead).one();assert (lead.name,lead.phone,lead.email,lead.product)==("Asha Sharma","9876543210","asha@example.com","Home Loan");db.close()
 assert client.get("/api/bank/public-conversations").status_code==401
 rows=client.get("/api/bank/public-conversations",headers=admin_headers).json()
 assert rows[0]["lead"]["name"]=="Asha Sharma"
 detail=client.get(f"/api/bank/public-conversations/{rows[0]['id']}",headers=admin_headers).json()
 assert len(detail["messages"])==8
 history=client.get(f"/api/public/chat/{session_id}").json()
 assert len(history["messages"])==8
def test_public_information_question_does_not_capture_lead(client):
 response=client.post("/api/public/chat",json={"message":"What documents are needed for a home loan?"}).json()
 assert response["contact_step"]=="" and "phone number" not in response["message"].lower()
def test_public_lead_contact_can_be_skipped_or_corrected(client):
 from app.db.session import SessionLocal
 from app.models import PublicLead
 first=client.post("/api/public/chat",json={"message":"I am planning to buy a house."}).json()
 session_id=first["session_id"]
 assert first["contact_step"]=="name"
 assert client.post("/api/public/chat",json={"message":"Asha Sharma","session_id":session_id}).json()["contact_step"]=="phone"
 invalid=client.post("/api/public/chat",json={"message":"123","session_id":session_id}).json()
 assert invalid["contact_step"]=="phone"
 skipped=client.post("/api/public/chat",json={"message":"Skip","session_id":session_id}).json()
 assert skipped["contact_step"]==""
 db=SessionLocal();assert db.query(PublicLead).count()==0;db.close()
def test_public_atm_compensation_followups_use_session_topic(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 passage="It is mandatory to reimburse the customer the amount wrongfully debited on account of failed ATM transactions within a maximum period of 5 days. Beyond T+5 days, compensation of Rs.100/- per day shall be paid to the account holder."
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",lambda *args,**kwargs:[])
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",lambda *args,**kwargs:[{"title":"Compensation Policy","page":14,"content":passage,"score":0.8}])
 first=client.post("/api/public/chat",json={"message":"The amount wrongfully debited on account of failed ATM transactions?"}).json()
 assert "₹100 per day" in first["message"]
 for question in ("How much amount will you reimburse?","What will be the amount?","Am I eligible for any compensation?"):
  answer=client.post("/api/public/chat",json={"message":question,"session_id":first["session_id"]}).json()
  assert "₹100" in answer["message"] and "T+5" in answer["message"]
def test_public_assistant_uses_contextual_rewrite_for_retrieval(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 from app.services.public_context import Understanding
 queries=[]
 monkeypatch.setattr(agent_module,"understand",lambda message,history:Understanding("banking","cheque book request process"))
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",lambda db,query,limit:queries.append(query) or [])
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",lambda *args,**kwargs:[])
 client.post("/api/public/chat",json={"message":"How do I do that?"})
 assert queries==["cheque book request process"]
def test_public_followup_does_not_invent_documents(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 from app.services.public_context import Understanding
 from app.services.knowledge import KnowledgeMatch
 monkeypatch.setattr(agent_module,"understand",lambda message,history:Understanding("banking","cheque book request documents"))
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",lambda *args,**kwargs:[KnowledgeMatch(1,"Cheque book request","Accounts","You can request a cheque book through mobile banking or a branch.",10)])
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",lambda *args,**kwargs:[])
 answer=client.post("/api/public/chat",json={"message":"What documents do I need for that?"}).json()
 assert answer["grounded"] is False and answer["message"] == "This information is not available in the current knowledge base."
def test_public_context_rejects_social_label_for_substantive_questions(monkeypatch):
 from app.services import public_context
 class Response:
  def raise_for_status(self):pass
  def json(self):return {"response":'{"intent":"social","query":"what are the customer rights?"}'}
 monkeypatch.setattr(public_context.httpx,"post",lambda *args,**kwargs:Response())
 assert public_context.understand("what are the customer rights?").intent=="banking"
 assert public_context.understand("what are the services that you provide?").intent=="capabilities"
def test_public_agent_searches_wider_approved_rag_and_saves_source(client,monkeypatch):
 from app.services import public_assistant_agent as agent_module
 from app.services.public_context import Understanding
 limits=[]
 monkeypatch.setattr(agent_module,"understand",lambda message,history:Understanding("banking",message))
 monkeypatch.setattr(agent_module.knowledge_retriever,"search",lambda *args,**kwargs:[])
 def search(db,query,audience,limit):
  limits.append((audience,limit))
  return [{"title":f"Unrelated {index}","page":index,"content":"This passage discusses another subject entirely. "*5,"score":0.7} for index in range(5)]+[{"title":"Fixed Deposit Guide","page":6,"content":"The process for closing a fixed deposit is described here with branch and online options. "*3,"score":0.62}]
 monkeypatch.setattr(agent_module,"retrieve_pdf_chunks",search)
 monkeypatch.setattr(agent_module,"generated_answer",lambda *args,**kwargs:"You can close a fixed deposit through the available branch or online process.")
 answer=client.post("/api/public/chat",json={"message":"What is the process for closing a fixed deposit?"}).json()
 assert ("customer",12) in limits
 assert answer["sources"]==[{"title":"Fixed Deposit Guide","page":6,"type":"pdf"}]
 history=client.get(f"/api/public/chat/{answer['session_id']}").json()
 assert history["messages"][-1]["sources"]==answer["sources"]
def test_public_rights_summary_requires_enumerated_policy_source():
 from app.services.public_answers import policy_answer
 passage="Right to Fair Treatment. Right to Transparency, Fair and Honest Dealing. Right to Suitability. Right to Privacy. Right to Grievance Redressal and Compensation."
 answer=policy_answer("What are the customer rights?",passage)
 assert "fair treatment" in answer and "privacy" in answer and "grievance redressal" in answer
 assert policy_answer("What are the customer rights?","Customer Rights Policy introduction") is None
def test_lead_scoring():
 score,reasons=lead_score("I earn monthly and need a 40 lakh home loan this year",3); assert score>=70 and len(reasons)>=3
def test_personal_loan_lead_uses_conversation_context(client,customer_headers,admin_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"I am considering a personal loan of 10 lakh."}).json()
 second=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"I work as a software engineer and my monthly salary is 110000."}).json()
 assert second["lead"]["collected"]["employment_type"]=="Software Engineer"
 assert second["lead"]["collected"]["monthly_income"]==110000
 leads=client.get("/api/leads",headers=admin_headers).json();lead=next(item for item in leads if item["conversation_id"]==first["conversation_id"])
 assert lead["product"]=="Personal Loan" and lead["qualification_data"]["required_amount"]==1000000
 informational=client.post("/api/chat",headers=customer_headers,json={"message":"What does the term personal loan mean?"}).json()
 assert informational["lead"] is None
def test_attrition_scoring():
 a=provider.analyze("This is the third time. I am fed up and want to close my account"); score,level,reasons=retention(a); assert score>=80 and level=="Critical" and reasons

def test_multilingual_account_closure_intent_detection():
 from app.services.intelligence import is_account_closure_intent
 for message in [
  "Mujhe mera savings account close karna hai, woh kaise kar sakta hoon?",
  "मुझे मेरा करंट अकाउंट बंद करना है।",
  "How can I close my current account?",
 ]:
  assert is_account_closure_intent(message)
  assert provider.analyze(message).intent=="Account Closure"
 assert not is_account_closure_intent("I want to close my vehicle loan")
def test_routing_rules():
 a=provider.analyze("My account was wrongly debited and nobody helped"); queue,_=route(a); assert queue in ["Supervisor Review","Priority Service Queue"]
def test_service_sentiment_drives_operational_routing(client,customer_headers,admin_headers):
 chat=client.post("/api/chat",headers=customer_headers,json={"message":"My account has been wrongly debited and nobody has helped me for five days."}).json()
 assert chat["analysis"]["sentiment"]=="Highly Negative" and chat["analysis"]["urgency"]=="High" and chat["analysis"]["repeat_contact"]
 assert chat["routing"]["queue"]=="Supervisor Review" and chat["routing"]["escalation"]=="Supervisor"
 request=client.post("/api/service-requests",headers=customer_headers,json={"conversation_id":chat["conversation_id"],**chat["service_request_draft"]}).json()
 assert request["priority"]=="High" and request["assigned_queue"]=="Standard Queue" and request["escalation_level"]=="None" and request["routing_reason"]
 decisions=client.get("/api/routing",headers=admin_headers);assert decisions.status_code==200
 decision=next(item for item in decisions.json() if item["conversation_id"]==chat["conversation_id"])
 assert decision["issue"]=="Account debit dispute" and decision["service_request_id"]==request["id"] and decision["status"]=="Recommended"
 applied=client.patch(f"/api/routing/{decision['id']}",headers=admin_headers,json={"status":"Applied"});assert applied.status_code==200 and applied.json()["actioned_by"] and applied.json()["current_queue"]=="Supervisor Review"
 updated_request=next(item for item in client.get("/api/service-requests",headers=admin_headers).json() if item["id"]==request["id"])
 assert updated_request["assigned_queue"]=="Supervisor Review" and updated_request["escalation_level"]=="Supervisor"
 dismissed=client.patch(f"/api/routing/{decision['id']}",headers=admin_headers,json={"status":"Dismissed"});assert dismissed.status_code==200
 assert client.patch(f"/api/routing/{decision['id']}",headers=customer_headers,json={"status":"Applied"}).status_code==403
def test_routine_query_stays_in_standard_queue(client,customer_headers):
 chat=client.post("/api/chat",headers=customer_headers,json={"message":"What is the minimum balance requirement?"}).json()
 assert chat["routing"]["queue"]=="Standard Queue" and chat["routing"]["escalation"]=="None"
def test_chat_processing(client,customer_headers):
 r=client.post("/api/chat",headers=customer_headers,json={"message":"Mera debit card kal se kaam nahi kar raha hai."}); body=r.json(); assert r.status_code==200 and body["service_request_suggested"]; assert body["service_request_draft"]=={"category":"Debit Card","issue":"Mera debit card kal se kaam nahi kar raha hai.","priority":"Medium"}
def test_digital_banking_failure_preemptively_offers_service_request(client,customer_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"My Internet banking is not working."}).json()
 assert first["service_request_suggested"] is True
 assert first["service_request_draft"]=={"category":"Digital Banking","issue":"My Internet banking is not working.","priority":"Medium"}
 assert first["routing"]["issue"]=="Digital banking access failure"
 unrelated=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"What credit services do you provide?"}).json()
 assert unrelated["service_request_suggested"] is False
 assert unrelated["service_request_draft"] is None
def test_explicit_service_request_uses_prior_issue_and_never_refuses(client,customer_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"My Internet banking is not working."}).json()
 follow_up=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"Please raise a request for this."}).json()
 assert follow_up["service_request_suggested"] is True
 assert follow_up["service_request_draft"]["category"]=="Digital Banking"
 assert follow_up["service_request_draft"]["issue"]=="My Internet banking is not working."
 assert "Yes, raise request" in follow_up["message"]
 assert "cannot raise" not in follow_up["message"].lower()
def test_contextual_follow_up_inherits_unresolved_intent(client,customer_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"Internet banking shows invalid credentials although they are correct."}).json()
 follow_up=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"I tried resetting the password, but it is still not working."}).json()
 assert follow_up["analysis"]["intent"]=="Digital Banking Complaint"
 assert follow_up["analysis"]["complaint"] is True
 assert follow_up["analysis"]["repeat_contact"] is True
 assert follow_up["service_request_draft"]["category"]=="Digital Banking"
 assert follow_up["analysis"]["sentiment"] in ["Negative","Highly Negative"]
def test_resolution_context_closes_negative_sentiment_trajectory(client,customer_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"My Internet banking is not working."}).json()
 resolved=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"It is working now, thank you."}).json()
 assert resolved["analysis"]["sentiment"]=="Positive"
 assert resolved["analysis"]["emotion"]=="Relieved"
 assert resolved["analysis"]["complaint"] is False
 assert resolved["service_request_suggested"] is False
def test_session_sentiment_aggregates_all_customer_interactions(client,customer_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"My Internet banking is not working."}).json()
 second=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"I tried the suggested reset but it is still not working."}).json()
 third=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"This is still unresolved and I need access urgently."}).json()
 assert first["analysis"]["sentiment"]=="Negative"
 assert second["analysis"]["score"]<first["analysis"]["score"]
 assert third["analysis"]["score"]<=second["analysis"]["score"]
 assert third["analysis"]["sentiment"]=="Highly Negative"
 detail=client.get(f"/api/conversations/{first['conversation_id']}",headers=customer_headers).json()
 assert len(detail["analysis"])==3
 assert detail["analysis"][-1]["score"]==third["analysis"]["score"]
def test_general_service_sentiment_language_changes_session_score(client,customer_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"I am very happy with your services."}).json()
 assert first["analysis"]["sentiment"]=="Positive"
 second=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"I am very sad with your services."}).json()
 assert second["analysis"]["sentiment"]=="Negative"
 final=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"I am going to stop all of your services."}).json()
 assert final["analysis"]["sentiment"]=="Highly Negative"
 assert final["analysis"]["emotion"]=="Angry"
def test_explicit_request_recalls_issue_after_intervening_messages(client,customer_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"My Internet banking is not working."}).json()
 second=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"What else can I try?"}).json()
 third=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"Where can I track complaints?"}).json()
 final=client.post("/api/chat",headers=customer_headers,json={"conversation_id":first["conversation_id"],"message":"Please raise a service request for this."}).json()
 assert second["conversation_id"]==third["conversation_id"]==final["conversation_id"]
 assert final["analysis"]["intent"]=="Digital Banking Complaint"
 assert final["service_request_draft"]["category"]=="Digital Banking"
 assert final["service_request_draft"]["issue"]=="My Internet banking is not working."
def test_service_request(client,customer_headers):
 r=client.post("/api/service-requests",headers=customer_headers,json={"category":"Debit Card","issue":"Card not working","priority":"Medium"}); assert r.status_code==200 and r.json()["request_code"].startswith("SR-")
def test_customer_can_close_own_service_request(client,customer_headers):
 item=client.post("/api/service-requests",headers=customer_headers,json={"category":"Debit Card","issue":"Card not working","priority":"Medium"}).json()
 closed=client.patch(f"/api/service-requests/{item['id']}",headers=customer_headers,json={"status":"Closed"}); assert closed.status_code==200 and closed.json()["status"]=="Closed"
 assert client.post(f"/api/service-requests/{item['id']}/messages",headers=customer_headers,json={"message":"A late reply"}).status_code==409
 assert client.patch(f"/api/service-requests/{item['id']}",headers=customer_headers,json={"status":"Open"}).status_code==403
def test_duplicate_active_service_request_returns_existing_ticket(client,customer_headers,admin_headers):
 first=client.post("/api/service-requests",headers=customer_headers,json={"category":"Digital Banking","issue":"Internet banking shows invalid credentials","priority":"Medium"}).json()
 duplicate=client.post("/api/service-requests",headers=customer_headers,json={"category":"Digital Banking","issue":"My internet banking credentials are invalid and login is not working","priority":"Medium"}).json()
 assert first["created"] is True and duplicate["created"] is False and duplicate["duplicate"] is True
 assert duplicate["id"]==first["id"] and duplicate["request_code"]==first["request_code"]
 assert "Service Requests tab" in duplicate["message"]
 client.patch(f"/api/service-requests/{first['id']}",headers=admin_headers,json={"status":"Resolved"})
 reopened=client.post("/api/service-requests",headers=customer_headers,json={"category":"Digital Banking","issue":"Internet banking shows invalid credentials","priority":"Medium"}).json()
 assert reopened["created"] is True and reopened["id"]!=first["id"]
def test_bank_can_update_and_comment_on_service_request(client,customer_headers,admin_headers):
 item=client.post("/api/service-requests",headers=customer_headers,json={"category":"Debit Card","issue":"Card not working","priority":"Medium"}).json()
 updated=client.patch(f"/api/service-requests/{item['id']}",headers=admin_headers,json={"status":"In Progress"}); assert updated.status_code==200 and updated.json()["status"]=="In Progress"
 added=client.post(f"/api/service-requests/{item['id']}/comments",headers=admin_headers,json={"comment":"Customer contacted; card controls checked."}); assert added.status_code==200 and added.json()["author_name"]=="Admin"
 comments=client.get(f"/api/service-requests/{item['id']}/comments",headers=admin_headers); assert comments.status_code==200 and comments.json()[0]["comment"].startswith("Customer contacted")
 assert client.get(f"/api/service-requests/{item['id']}/comments",headers=customer_headers).status_code==403
def test_customer_and_bank_can_exchange_service_request_messages(client,customer_headers,admin_headers):
 item=client.post("/api/service-requests",headers=customer_headers,json={"category":"Debit Card","issue":"Card not working","priority":"Medium"}).json()
 bank_reply=client.post(f"/api/service-requests/{item['id']}/messages",headers=admin_headers,json={"message":"Please confirm whether ATM and online transactions both fail."}); assert bank_reply.status_code==200 and bank_reply.json()["sender_type"]=="employee"
 customer_notifications=client.get("/api/notifications",headers=customer_headers); assert customer_notifications.status_code==200 and [notice["title"] for notice in customer_notifications.json()]==[f"Bank replied on {item['request_code']}"]
 customer_reply=client.post(f"/api/service-requests/{item['id']}/messages",headers=customer_headers,json={"message":"Yes, both transaction types fail."}); assert customer_reply.status_code==200 and customer_reply.json()["sender_type"]=="customer"
 bank_notifications=client.get("/api/notifications",headers=admin_headers); assert bank_notifications.status_code==200 and bank_notifications.json()[0]["title"]==f"Customer replied on {item['request_code']}"
 thread=client.get(f"/api/service-requests/{item['id']}/messages",headers=customer_headers); assert thread.status_code==200 and [message["sender_type"] for message in thread.json()]==["employee","customer"]
def test_customer_statement_downloads_as_valid_pdf(client,customer_headers):
 from io import BytesIO
 from pypdf import PdfReader
 from app.db.session import SessionLocal
 from app.models import BankAccount,AccountTransaction,Customer
 db=SessionLocal();customer=db.query(Customer).filter_by(customer_code="T001").one();account=BankAccount(customer_id=customer.id,account_number="123456789012",account_type="Savings",balance=12500,status="Active");db.add(account);db.flush();db.add(AccountTransaction(account_id=account.id,description="Salary credit",reference="TXN-001",credit=15000,debit=0,balance=12500));db.commit();db.close()
 response=client.get("/api/customer/statement",headers=customer_headers)
 assert response.status_code==200 and response.headers["content-type"]=="application/pdf"
 assert response.content.startswith(b"%PDF-") and response.headers["content-disposition"].endswith('.pdf"')
 text="\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.content)).pages)
 assert "Union Bank of India" in text and "Account Statement" in text and "Current balance" in text
def test_conversation_sentiment_summary_and_feedback(client,customer_headers,admin_headers):
 chat=client.post("/api/chat",headers=customer_headers,json={"message":"This is the third time I am contacting the bank and nobody has resolved my issue."}).json()
 conversation_id=chat["conversation_id"]
 detail=client.get(f"/api/conversations/{conversation_id}",headers=admin_headers); assert detail.status_code==200
 insights=detail.json()["insights"]; assert insights["sentiment"]=="Highly Negative" and insights["emotion"]=="Frustrated" and insights["interaction_quality"]=="At Risk" and insights["resolution_status"]=="Unresolved"; assert insights["dissatisfaction_reasons"] and insights["suggested_next_action"]
 assert insights["sentiment_progression"][0]["message"]=="This is the third time I am contacting the bank and nobody has resolved my issue."
 feedback=client.post("/api/feedback",headers=customer_headers,json={"conversation_id":conversation_id,"csat":1,"nps":2}); assert feedback.status_code==200
 updated=client.get(f"/api/conversations/{conversation_id}",headers=admin_headers).json(); assert updated["insights"]["feedback"]["csat"]==1 and updated["insights"]["feedback"]["nps"]==2
def test_admin_recent_sentiment_monitor(client,customer_headers,admin_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"Thank you for helping me."}).json()
 client.post("/api/chat",headers=customer_headers,json={"message":"This is the third time and nobody helped me.","conversation_id":first["conversation_id"]})
 recent=client.get("/api/sentiment/recent?limit=10",headers=admin_headers); assert recent.status_code==200 and len(recent.json())==2; assert recent.json()[-1]["sentiment"]=="Highly Negative" and recent.json()[-1]["conversation_id"]==first["conversation_id"]
 assert client.get("/api/sentiment/recent?limit=10",headers=customer_headers).status_code==403
def test_customer_sentiment_history_is_scoped_to_same_customer(client,customer_headers,admin_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"Thank you."}).json()
 second=client.post("/api/chat",headers=customer_headers,json={"message":"My debit card is not working."}).json()
 client.post("/api/feedback",headers=customer_headers,json={"conversation_id":second["conversation_id"],"csat":2,"nps":4})
 detail=client.get(f"/api/conversations/{second['conversation_id']}",headers=admin_headers).json()
 history=client.get(f"/api/customers/{detail['customer_id']}/sentiment-history?limit=10",headers=admin_headers); assert history.status_code==200
 sessions=history.json()["sessions"]; assert [item["conversation_id"] for item in sessions]==[first["conversation_id"],second["conversation_id"]]
 assert all(item["conversation_id"] in [first["conversation_id"],second["conversation_id"]] for item in sessions)
 assert sessions[0]["csat"] is None and sessions[0]["nps"] is None
 assert sessions[1]["csat"]==2 and sessions[1]["nps"]==4
def test_sentiment_controls_subsequent_engagement():
 blocked=engagement_decision("Highly Negative","Unresolved",complaint=True); assert not blocked["eligible"] and blocked["state"]=="Service Recovery"
 eligible=engagement_decision("Positive","Answered"); assert eligible["eligible"] and eligible["state"]=="Engagement Opportunity"
 open_case=engagement_decision("Positive","Resolved",has_open_request=True); assert not open_case["eligible"]
 assert engagement_decision("Neutral","In Progress")["eligible"]
def test_home_loan_qualification_journey(client,customer_headers):
 response=client.post("/api/chat",headers=customer_headers,json={"message":"I am thinking about buying a house."}).json(); conversation_id=response["conversation_id"]
 assert response["lead"]["stage"]=="Amount" and response["lead"]["next_question"]
 for message,stage in [("40 lakh","Income"),("150000 per month","Employment"),("Salaried","Existing EMI"),("zero","Location"),("Pune","Timeline")]:
  response=client.post("/api/chat",headers=customer_headers,json={"message":message,"conversation_id":conversation_id}).json(); assert response["lead"]["stage"]==stage
 response=client.post("/api/chat",headers=customer_headers,json={"message":"Within 3 months","conversation_id":conversation_id}).json(); assert response["lead"]["status"]=="Qualified" and response["lead"]["temperature"]=="Hot" and response["lead"]["score"]>=80
def test_incomplete_home_loan_journey_creates_dropoff(client,customer_headers):
 response=client.post("/api/chat",headers=customer_headers,json={"message":"I want a home loan."}).json(); conversation_id=response["conversation_id"]
 response=client.post("/api/chat",headers=customer_headers,json={"message":"40 lakh","conversation_id":conversation_id}).json()
 dropped=client.post(f"/api/leads/{response['lead']['id']}/abandon",headers=customer_headers); assert dropped.status_code==200 and dropped.json()["drop_off_detected"] and dropped.json()["status"]=="Abandoned" and dropped.json()["drop_off_created"]
 repeated=client.post(f"/api/leads/{response['lead']['id']}/abandon",headers=customer_headers); assert repeated.status_code==200 and repeated.json()["drop_off_created"] is False
def test_personalized_financial_coaching_plan(client,customer_headers):
 response=client.post("/api/chat",headers=customer_headers,json={"message":"I earn ₹70,000 per month. My expenses are around ₹45,000. I want to save 5 lakh for a car."}).json()
 assert response["analysis"]["intent"]=="Financial Coaching" and response["goal"]["status"]=="Planning" and response["goal"]["next_question"]
 response=client.post("/api/chat",headers=customer_headers,json={"message":"24 months","conversation_id":response["conversation_id"]}).json();goal=response["goal"]
 for answer in ["0","0","regular","0","0","confirm"]:
  response=client.post("/api/chat",headers=customer_headers,json={"message":answer,"conversation_id":response["conversation_id"]}).json();goal=response["goal"]
 assert goal["status"]=="Active" and goal["monthly_income"]==70000 and goal["monthly_expenses"]==45000 and goal["target_amount"]==500000 and goal["timeline_months"]==24
 assert goal["plan"]["monthly_surplus"]==25000 and goal["plan"]["emergency_fund_target"]==135000 and goal["plan"]["feasible"] is False and goal["plan"]["guidance"]
 goal_id=client.get("/api/financial-goals",headers=customer_headers).json()[0]["id"]
 updated=client.put(f"/api/financial-goals/{goal_id}",headers=customer_headers,json={"name":"New Car Goal","target_amount":480000,"saved_amount":80000,"timeline_months":20,"monthly_income":80000,"monthly_expenses":40000})
 assert updated.status_code==200
 edited=updated.json();assert edited["name"]=="New Car Goal" and edited["monthly_required"]==20000 and edited["coaching_plan"]["monthly_surplus"]==40000 and edited["coaching_plan"]["feasible"] is True
 removed=client.delete(f"/api/financial-goals/{goal_id}",headers=customer_headers);assert removed.status_code==200 and client.get("/api/financial-goals",headers=customer_headers).json()==[]
def test_chat_auto_language_uses_message_script():
 from app.services.chat import detected_language
 from app.services.intelligence import provider
 assert detected_language("Create an emergency fund")=="en-IN"
 assert detected_language("आपातकालीन निधि बनाएं")=="hi-IN"
 assert provider.analyze("Plan to buy a home").intent=="Financial Coaching"

def test_customer_voice_transcription_preserves_requested_language(client,customer_headers,monkeypatch):
 captured={}
 def transcribe(data,filename,content_type,language_code):
  captured["language_code"]=language_code
  return {"transcript":"मुझे मेरा सेविंग्स अकाउंट बंद करना है।","language_code":"hi-IN","language_probability":.99}
 monkeypatch.setattr("app.api.routes.transcribe_audio",transcribe)
 response=client.post("/api/speech-to-text",headers=customer_headers,data={"language_code":"auto"},files={"file":("recording.webm",b"voice","audio/webm")})
 assert response.status_code==200
 assert captured["language_code"]=="auto"
 assert response.json()["transcript"]=="मुझे मेरा सेविंग्स अकाउंट बंद करना है।"

def test_sarvam_response_script_validation():
 from app.services.intelligence import SarvamAIProvider
 assert SarvamAIProvider._uses_target_script("मैं आपकी सहायता कर सकता हूँ।","hi-IN")
 assert not SarvamAIProvider._uses_target_script("I can help you.","hi-IN")
 assert SarvamAIProvider._uses_target_script("আমি সাহায্য করতে পারি।","bn-IN")
def test_product_recommendation_generation_and_review(client,customer_headers,admin_headers):
 from app.db.session import SessionLocal
 from app.models import Customer
 db=SessionLocal();customer=db.query(Customer).first();customer.average_balance=500000;customer.monthly_income=180000;customer.monthly_surplus=65000;db.commit();db.close()
 refreshed=client.post("/api/opportunities/refresh",headers=admin_headers);assert refreshed.status_code==200 and refreshed.json()["created"]>=1
 client.post("/api/chat",headers=customer_headers,json={"message":"Thank you, my question is resolved."})
 opportunities=client.get("/api/opportunities",headers=admin_headers).json();fixed=next(item for item in opportunities if item["product"]=="Fixed Deposit")
 assert fixed["reason"] and fixed["trigger"] and fixed["suggested_action"] and fixed["communication_draft"] and fixed["engagement"]["eligible"]
 approved=client.patch(f"/api/opportunities/{fixed['id']}",headers=admin_headers,json={"status":"Approved","communication_draft":fixed["communication_draft"]});assert approved.status_code==200 and approved.json()["status"]=="Approved" and approved.json()["reviewed_by"]
def test_approved_opportunity_email_uses_provider(client,customer_headers,admin_headers,monkeypatch):
 from app.db.session import SessionLocal
 from app.models import Customer,Opportunity
 db=SessionLocal();customer=db.query(Customer).first();customer.email_address="customer@example.com";item=Opportunity(customer_id=customer.id,product="Fixed Deposit",score=80,reason="Test",trigger="Test",suggested_action="Review",communication_draft="Approved message",status="Approved");db.add(item);db.commit();item_id=item.id;db.close()
 captured={}
 def send(*args):captured["args"]=args;return "provider-message-id"
 monkeypatch.setattr("app.api.routes.send_transactional_email",send)
 client.post("/api/chat",headers=customer_headers,json={"message":"Thank you, my query is resolved."})
 payload={"recipient":"edited@example.com","subject":"A reviewed subject","message":"A reviewed email message"}
 sent=client.post(f"/api/opportunities/{item_id}/send-email",headers=admin_headers,json=payload)
 assert sent.status_code==200 and sent.json()["status"]=="Email Sent" and sent.json()["recipient"]=="edited@example.com" and sent.json()["subject"]=="A reviewed subject"
 assert captured["args"][0]=="edited@example.com" and captured["args"][2]=="A reviewed subject"
 assert captured["args"][3].startswith("Dear Test User,") and captured["args"][3].endswith("Regards,\nUnion Bank of India")
def test_authorization(client,customer_headers): assert client.get("/api/dashboard",headers=customer_headers).status_code==403
def test_customer_and_employee_self_registration(client):
 customer=client.post("/api/auth/register",json={"user_type":"customer","display_name":"New Customer","login_id":"new.customer","password":"SecurePass123"})
 assert customer.status_code==201 and customer.json()["role"]=="customer" and customer.json()["customer_id"]
 duplicate=client.post("/api/auth/register",json={"user_type":"employee","display_name":"Duplicate","login_id":"NEW.CUSTOMER","password":"SecurePass123"})
 assert duplicate.status_code==409
 employee=client.post("/api/auth/register",json={"user_type":"employee","display_name":"New Employee","login_id":"new.employee","password":"SecurePass123"})
 assert employee.status_code==201 and employee.json()["role"]=="employee" and employee.json()["customer_id"] is None
 login=client.post("/api/auth/employee/login",json={"login_id":"new.employee","password":"SecurePass123"})
 assert login.status_code==200
def test_dashboard_experience_scores_are_dynamic_by_customer(client,customer_headers,admin_headers):
 from app.db.session import SessionLocal
 from app.models import Customer
 db=SessionLocal();db.add(Customer(customer_code="T002",name="No Conversation",city="Mumbai",relationship_since="2025"));db.commit();db.close()
 rated=client.post("/api/chat",headers=customer_headers,json={"message":"Thank you."}).json()
 client.post("/api/feedback",headers=customer_headers,json={"conversation_id":rated["conversation_id"],"csat":5})
 client.post("/api/chat",headers=customer_headers,json={"message":"What are your branch hours?"})
 kpis=client.get("/api/dashboard",headers=admin_headers).json()["kpis"]
 assert kpis["csat"]==3.5 and kpis["nps"]==25
 assert kpis["experience_customers"]==2 and kpis["experience_sessions"]==2 and kpis["defaulted_sessions"]==1
 dashboard=client.get("/api/dashboard",headers=admin_headers).json()
 assert kpis["conversations"]==2 and kpis["active_customers"]==2
 assert sum(day["count"] for day in dashboard["conversation_trend"])==2
 assert [stage["stage"] for stage in dashboard["lead_funnel"]]==["New","In Qualification","Qualified","Abandoned","Converted"]
def test_retention_engine_aggregates_customer_signals(client,customer_headers,admin_headers):
 chat=client.post("/api/chat",headers=customer_headers,json={"message":"This is the third time I am contacting the bank and nobody has resolved my issue."}).json()
 feedback=client.post("/api/feedback",headers=customer_headers,json={"conversation_id":chat["conversation_id"],"csat":1,"nps":2});assert feedback.status_code==200
 cases=client.get("/api/retention",headers=admin_headers);assert cases.status_code==200
 case=next(item for item in cases.json() if item["customer_name"]=="Test User")
 assert case["level"] in ["High","Critical"] and case["score"]>=60
 assert any("negative interaction" in reason for reason in case["reasons"])
 assert any("Low CSAT" in reason for reason in case["reasons"])
 assert case["suggested_action"] and case["communication_draft"]
 reviewed=client.patch(f"/api/retention/{case['id']}",headers=admin_headers,json={"status":"Intervention Planned","communication_draft":case["communication_draft"]})
 assert reviewed.status_code==200 and reviewed.json()["status"]=="Intervention Planned" and reviewed.json()["reviewed_by"]
 assert client.patch(f"/api/retention/{case['id']}",headers=customer_headers,json={"status":"Closed","communication_draft":"x"}).status_code==403
def test_account_closure_intent_creates_high_risk_winback_case(client,customer_headers,admin_headers):
 client.post("/api/chat",headers=customer_headers,json={"message":"I am fed up. I am going to close my account."})
 case=next(item for item in client.get("/api/retention",headers=admin_headers).json() if item["customer_name"]=="Test User")
 assert case["case_type"]=="Win-back" and case["level"] in ["High","Critical"]
 assert "Account-closure intent detected" in case["reasons"]
def test_opportunity_rule_explanation():
 score,reasons=lead_score("I want a home loan",1); assert score>0 and "Product intent explicitly expressed" in reasons
def test_chat_dynamically_creates_and_updates_sales_opportunity(client,customer_headers,admin_headers):
 first=client.post("/api/chat",headers=customer_headers,json={"message":"I want a car loan for 12 lakh this year."});assert first.status_code==200
 opportunity=first.json()["opportunity"];assert opportunity["product"]=="Vehicle Loan" and opportunity["score"]>=80
 items=client.get("/api/opportunities",headers=admin_headers).json();item=next(row for row in items if row["product"]=="Vehicle Loan")
 assert "conversation" in item["reason"].lower() and item["trigger"].startswith("Chat signal")
 second=client.post("/api/chat",headers=customer_headers,json={"message":"My salary is 150000 per month and I am still interested in the car loan.","conversation_id":first.json()["conversation_id"]});assert second.status_code==200
 assert second.json()["opportunity"]["id"]==opportunity["id"] and second.json()["opportunity"]["score"]>=opportunity["score"]
def test_customer_can_view_only_own_profile(client,customer_headers,admin_headers):
 profile=client.get("/api/customer/profile",headers=customer_headers);assert profile.status_code==200
 assert profile.json()["customer_code"]=="T001" and profile.json()["name"]=="Test User"
 assert client.get("/api/customer/profile",headers=admin_headers).status_code==403
def test_information_query_does_not_become_complaint():
 a=provider.analyze("How can I block my debit card?"); assert a.intent=="Debit Card Information" and not a.complaint
def test_non_working_card_phrase_becomes_complaint():
 a=provider.analyze("My debit card has not been working since yesterday."); assert a.intent=="Debit Card Complaint" and a.complaint
def test_multilingual_knowledge_retrieval():
 from app.db.session import SessionLocal
 from app.models import KnowledgeArticle
 db=SessionLocal(); db.add(KnowledgeArticle(title="Cheque book request",category="Accounts",keywords="cheque,book,order",content="Approved cheque-book process")); db.commit()
 try: assert knowledge_retriever.search(db,"Mujhe cheque book order karni hai")[0].title=="Cheque book request"
 finally: db.close()
