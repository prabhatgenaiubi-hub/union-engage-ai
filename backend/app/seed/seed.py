from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models import *
from app.core.security import hash_password
from app.services.recommendations import identify_opportunities
from datetime import datetime, timedelta

CUSTOMERS=[("CUST001","Aarav Mehta","Privilege","Mumbai","2021",500000,180000,65000),("CUST002","Meera Nair","Classic","Kochi","2019",85000,95000,18000),("CUST003","Kabir Malhotra","Privilege","Delhi","2023",240000,150000,45000),("CUST004","Ishita Sen","Classic","Kolkata","2022",75000,85000,14000),("CUST005","Rohan Iyer","Classic","Bengaluru","2020",120000,70000,25000),("CUST006","Diya Kapoor","Classic","Pune","2024",65000,80000,16000),("CUST007","Vihaan Desai","Wealth","Ahmedabad","2017",900000,300000,110000),("CUST008","Saanvi Rao","Classic","Hyderabad","2018",40000,65000,7000),("CUST009","Arjun Bhat","Privilege","Chennai","2020",180000,125000,30000),("CUST010","Myra Joshi","Wealth","Jaipur","2016",750000,260000,90000)]
EXTRA_CUSTOMER_NAMES=[
 ("Advait Kulkarni","Pune"),("Anaya Reddy","Hyderabad"),("Reyansh Gupta","Delhi"),("Kiara Menon","Kochi"),("Dhruv Chawla","Chandigarh"),
 ("Aadhya Bose","Kolkata"),("Krish Shah","Ahmedabad"),("Navya Singh","Lucknow"),("Atharv Patil","Nagpur"),("Tara Krishnan","Chennai"),
 ("Vivaan Agarwal","Jaipur"),("Aisha Khan","Mumbai"),("Arnav Mishra","Bhopal"),("Nisha Thomas","Kochi"),("Yuvaan Sethi","Delhi"),
 ("Mira Banerjee","Kolkata"),("Shaurya Jain","Indore"),("Ira Subramanian","Chennai"),("Ayaan Sheikh","Hyderabad"),("Riya Saxena","Noida"),
 ("Kiaan Verma","Gurugram"),("Zoya Ali","Lucknow"),("Vedant Naik","Goa"),("Anvi Pillai","Thiruvananthapuram"),("Arush Dubey","Varanasi"),
 ("Siya Kaur","Amritsar"),("Neil Fernandes","Mumbai"),("Prisha Das","Bhubaneswar"),("Rudra Hegde","Bengaluru"),("Myra Sood","Shimla"),
 ("Kabir Dutta","Guwahati"),("Aarohi Yadav","Patna"),("Dev Malhotra","Delhi"),("Sahana Rao","Mysuru"),("Ishaan Parekh","Surat"),
 ("Avni Chopra","Chandigarh"),("Ritvik Nair","Kochi"),("Meher Kapoor","Mumbai"),("Darsh Bansal","Jaipur"),("Vanya Sen","Kolkata"),
]
CUSTOMERS += [(f"CUST{index+11:03d}",name,["Classic","Privilege","Classic","Wealth"][index%4],city,str(2015+index%11),45000+(index%10)*55000,60000+(index%8)*25000,8000+(index%7)*9000) for index,(name,city) in enumerate(EXTRA_CUSTOMER_NAMES)]
RELATIONSHIP_MANAGERS=["Ananya Rao","Vikram Singh","Neha Iyer","Rahul Mehta","Kavya Nair"]
DEMO_ADMIN_USERS=[
 ("ADMIN001","Admin@001","Priya Sharma","admin"),
 ("ADMIN002","Admin@002","Rakesh Verma","admin"),
 ("ADMIN003","Admin@003","Sunita Iyer","admin"),
]
ARTICLES=[("Home loan documents","Loans","home,loan,documents,house","For a home-loan application, commonly required documents include identity and address proof, income documents such as salary slips and bank statements, employment proof, and property documents. Final requirements depend on applicant and property type."),("Block a debit card","Cards","debit,card,block,stolen,lost","You can immediately block a debit card through mobile or net banking under Card Controls, or contact the bank's 24-hour support line. Never share your PIN or OTP."),("Cheque book request","Accounts","cheque,book,order","You can request a cheque book through mobile banking, net banking, an ATM, or your branch. Delivery typically takes 5–7 business days."),("Fixed deposits","Deposits","fixed,deposit,fd,interest","Fixed deposits offer a fixed return for a selected tenure. Rates and premature withdrawal conditions vary; review the current schedule before booking."),("Digital banking help","Digital","net,mobile,banking,password,login","Use the Forgot Password option to restore digital banking access. The bank will verify your registered mobile number; never disclose an OTP."),("Account statements","Accounts","account,statement,transactions","Account statements can be downloaded from mobile or net banking by choosing the account and date range.")]
EXTRA_ARTICLES=[
 ("Minimum balance requirement","Accounts","minimum,balance,requirement,amb,average monthly balance,न्यूनतम बैलेंस","Minimum balance requirements depend on the savings-account variant. Customers should check the account details shown in mobile or net banking, or contact the branch for the requirement applicable to their account. Any penalty must be confirmed from the current approved schedule of charges."),
]
def upsert_articles(db):
 for title,category,keywords,content in ARTICLES+EXTRA_ARTICLES:
  article=db.query(KnowledgeArticle).filter_by(title=title).first()
  if article:
   article.category=category; article.keywords=keywords; article.content=content; article.active=True
  else: db.add(KnowledgeArticle(title=title,category=category,keywords=keywords,content=content))
def upsert_demo_users(db,customers):
 for index,customer in enumerate(customers,1):
  login_id=f"CUST{index:03d}";user=db.query(User).filter_by(login_id=login_id).first()
  if not user:user=User(login_id=login_id);db.add(user)
  user.password_hash=hash_password(f"Customer@{index:03d}");user.user_type="customer";user.role="customer";user.display_name=customer.name;user.customer_id=customer.id
 for login_id,password,name,role in DEMO_ADMIN_USERS:
  user=db.query(User).filter_by(login_id=login_id).first()
  if not user:user=User(login_id=login_id);db.add(user)
  user.password_hash=hash_password(password);user.user_type="employee";user.role=role;user.display_name=name;user.customer_id=None
 for login_id in ["EMP001","EMP002","EMP003"]:
  user=db.query(User).filter_by(login_id=login_id).first()
  if user:user.user_type="disabled";user.role="disabled";user.password_hash=hash_password(f"Disabled@{login_id}")
def run():
 Base.metadata.create_all(engine); db=SessionLocal()
 try:
  had_customers=db.query(Customer).count()>0;customers=[]
  for index,(code,name,segment,city,since,balance,income,surplus) in enumerate(CUSTOMERS):
   c=db.query(Customer).filter_by(customer_code=code).first()
   if not c:c=Customer(customer_code=code);db.add(c)
   c.name=name;c.phone_number=f"+91 {9000000001+index}";c.email_address="prabhatkumar025dec@gmail.com" if code=="CUST007" else f"customer{index+1:03d}@example.com";c.segment=segment;c.city=city;c.relationship_since=since;c.average_balance=balance;c.monthly_income=income;c.monthly_surplus=surplus;c.rm_name=RELATIONSHIP_MANAGERS[index%len(RELATIONSHIP_MANAGERS)];customers.append(c)
  db.flush()
  upsert_demo_users(db,customers)
  for index,customer in enumerate(customers):
   customer.profile_verified=True;customer.kyc_status="Up to date";customer.kyc_updated_at=datetime.utcnow()-timedelta(days=90+(index%6)*30);customer.trusted_customer=True
   product_types=["Savings Account","Debit Card"]+(["Fixed Deposit","Credit Card"] if customer.segment in ["Privilege","Wealth"] else [])
   for product_index,account_type in enumerate(product_types):
    account_number=f"UBI{customer.customer_code.replace('CUST','')}{product_index+1:02d}"
    account=db.query(BankAccount).filter_by(account_number=account_number).first()
    if not account:
     account=BankAccount(customer_id=customer.id,account_number=account_number,account_type=account_type,balance=customer.average_balance if product_index==0 else 0,status="Active");db.add(account);db.flush()
    if product_index==0 and db.query(AccountTransaction).filter_by(account_id=account.id).count()==0:
     running=float(customer.average_balance)
     entries=[("Opening balance",0,50000),("UPI payment",2450,0),("Salary credit",0,float(customer.monthly_income)),("Utility bill payment",3200,0),("Interest credit",0,875)]
     for offset,(description,debit,credit) in enumerate(entries):
      running=running-debit+credit
      db.add(AccountTransaction(account_id=account.id,transaction_date=datetime.utcnow()-timedelta(days=(len(entries)-offset)*6),description=description,reference=f"TXN-{customer.customer_code}-{offset+1:03d}",debit=debit,credit=credit,balance=running))
  if had_customers:
   upsert_articles(db);db.commit();return
  upsert_articles(db)
  for c,title,intent,sentiment,status in [(customers[1],"Repeated debit card complaint","Debit Card Complaint","Highly Negative","Unresolved"),(customers[2],"Planning a new home purchase","Home Loan Interest","Positive","In Progress"),(customers[7],"Considering account closure","Account Closure","Highly Negative","Unresolved")]: db.add(Conversation(customer_id=c.id,title=title,primary_intent=intent,sentiment=sentiment,resolution_status=status,summary=f"Customer interaction regarding {intent.lower()}."))
  db.flush()
  db.add_all([ServiceRequest(request_code="SR-2026-000124",customer_id=customers[1].id,conversation_id=1,category="Debit Card",issue="Card not working",priority="High",status="Open"),ServiceRequest(request_code="SR-2026-000125",customer_id=customers[8].id,category="Account",issue="Incorrect debit",priority="High",status="Escalated"),Lead(customer_id=customers[2].id,conversation_id=2,product="Home Loan",score=86,temperature="Hot",journey_stage="Eligibility",status="Qualified",next_action="RM callback",reasons=["Product intent explicitly expressed","Desired loan amount provided","Income disclosed","Timeline within 3 months"]),Lead(customer_id=customers[3].id,product="Home Loan",score=58,temperature="Warm",journey_stage="Income",status="Abandoned",next_action="Send reminder",reasons=["Journey 60% complete","Customer exited at eligibility stage"]),FinancialGoal(customer_id=customers[4].id,name="Car Goal",target_amount=500000,saved_amount=120000,timeline_months=24,monthly_required=15834),Opportunity(customer_id=customers[0].id,product="Fixed Deposit",score=88,reason="Sustained high average balance with no active term deposit",trigger="High idle balance",suggested_action="Explain suitable fixed-deposit tenure options"),Opportunity(customer_id=customers[6].id,product="FD Renewal",score=82,reason="Existing fixed deposit is approaching maturity",trigger="FD maturity in 30 days",suggested_action="Review maturity and renewal options"),RetentionScore(customer_id=customers[1].id,score=91,level="Critical",reasons=["Three unresolved complaints","Highly negative sentiment","CSAT 1/5","Repeat contact"],suggested_action="Priority RM intervention"),RetentionScore(customer_id=customers[7].id,score=88,level="Critical",reasons=["Account closure intent detected","Negative recent sentiment"],suggested_action="Senior service recovery call"),RoutingDecision(conversation_id=1,recommended_queue="Priority Service Queue",reason="Highly negative repeat contact"),RoutingDecision(conversation_id=3,recommended_queue="Supervisor Review",reason="Account closure intent with highly negative sentiment"),Notification(title="Critical attrition risk detected",severity="critical",customer_id=customers[1].id),Notification(title="Hot home-loan lead generated",severity="info",customer_id=customers[2].id),Notification(title="Customer abandoned loan qualification",severity="warning",customer_id=customers[3].id)])
  db.flush();identify_opportunities(db);db.commit()
 finally: db.close()
if __name__=="__main__": run()
