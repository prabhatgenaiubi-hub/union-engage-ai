from app.services.intelligence import provider,lead_score,retention,route
from app.services.knowledge import knowledge_retriever
def test_authentication(client): assert client.post("/api/auth/customer/login",json={"login_id":"T001","password":"Demo@123"}).status_code==200
def test_bad_authentication(client): assert client.post("/api/auth/customer/login",json={"login_id":"T001","password":"bad!"}).status_code==401
def test_lead_scoring():
 score,reasons=lead_score("I earn monthly and need a 40 lakh home loan this year",3); assert score>=70 and len(reasons)>=3
def test_attrition_scoring():
 a=provider.analyze("This is the third time. I am fed up and want to close my account"); score,level,reasons=retention(a); assert score>=80 and level=="Critical" and reasons
def test_routing_rules():
 a=provider.analyze("My account was wrongly debited and nobody helped"); queue,_=route(a); assert queue in ["Supervisor Review","Priority Service Queue"]
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
 customer_reply=client.post(f"/api/service-requests/{item['id']}/messages",headers=customer_headers,json={"message":"Yes, both transaction types fail."}); assert customer_reply.status_code==200 and customer_reply.json()["sender_type"]=="customer"
 thread=client.get(f"/api/service-requests/{item['id']}/messages",headers=customer_headers); assert thread.status_code==200 and [message["sender_type"] for message in thread.json()]==["employee","customer"]
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
def test_authorization(client,customer_headers): assert client.get("/api/dashboard",headers=customer_headers).status_code==403
def test_opportunity_rule_explanation():
 score,reasons=lead_score("I want a home loan",1); assert score>0 and "Product intent explicitly expressed" in reasons
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
