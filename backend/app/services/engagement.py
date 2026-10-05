from app.services.intelligence import Analysis

def engagement_decision(sentiment:str,resolution_status:str,complaint:bool=False,has_open_request:bool=False,service_request_code:str|None=None)->dict:
    blockers=[]
    if sentiment in ["Negative","Highly Negative"]: blockers.append(f"Current sentiment is {sentiment.lower()}")
    if complaint: blockers.append("The interaction contains a complaint")
    if resolution_status=="Unresolved": blockers.append("The customer issue is unresolved")
    if has_open_request: blockers.append("An open service request requires attention")
    if blockers:
        return {"eligible":True,"warning":True,"state":"Service Recovery Warning","action":"Service recovery is active. Resolve the customer issue and confirm satisfaction before proceeding with promotional engagement.","reasons":blockers,"service_request_code":service_request_code}
    reasons=["No unresolved complaint or open service request is present"]
    if sentiment=="Positive":reasons.append("The latest interaction is positive")
    if resolution_status in ["Answered","Resolved"]:reasons.append(f"The interaction is {resolution_status.lower()}")
    return {"eligible":True,"warning":False,"state":"Engagement Opportunity","action":"A bank employee may review and send a relevant next-best action","reasons":reasons,"service_request_code":service_request_code}
