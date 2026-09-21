from app.services.intelligence import provider,lead_score,retention,route
from app.services.knowledge import knowledge_retriever
from app.services.engagement import engagement_decision
def test_authentication(client): assert client.post("/api/auth/customer/login",json={"login_id":"T001","password":"Demo@123"}).status_code==200
def test_bad_authentication(client): assert client.post("/api/auth/customer/login",json={"login_id":"T001","password":"bad!"}).status_code==401
def test_lead_scoring():
 score,reasons=lead_score("I earn monthly and need a 40 lakh home loan this year",3); assert score>=70 and len(reasons)>=3
def test_attrition_scoring():
 a=provider.analyze("This is the third time. I am fed up and want to close my account"); score,level,reasons=retention(a); assert score>=80 and level=="Critical" and reasons
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
def test_service_request(client,customer_headers):
 r=client.post("/api/service-requests",headers=customer_headers,json={"category":"Debit Card","issue":"Card not working","priority":"Medium"}); assert r.status_code==200 and r.json()["request_code"].startswith("SR-")
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
def test_personalized_financial_coaching_plan(client,customer_headers):
 response=client.post("/api/chat",headers=customer_headers,json={"message":"I earn ₹70,000 per month. My expenses are around ₹45,000. I want to save 5 lakh for a car."}).json()
 assert response["analysis"]["intent"]=="Financial Coaching" and response["goal"]["status"]=="Planning" and response["goal"]["next_question"]
 response=client.post("/api/chat",headers=customer_headers,json={"message":"24 months","conversation_id":response["conversation_id"]}).json();goal=response["goal"]
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
 monkeypatch.setattr("app.api.routes.send_transactional_email",lambda *args:"brevo-message-id")
 client.post("/api/chat",headers=customer_headers,json={"message":"Thank you, my query is resolved."})
 sent=client.post(f"/api/opportunities/{item_id}/send-email",headers=admin_headers);assert sent.status_code==200 and sent.json()["status"]=="Email Sent" and sent.json()["recipient"]=="customer@example.com"
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
