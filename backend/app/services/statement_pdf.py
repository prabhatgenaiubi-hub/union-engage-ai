from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY=colors.HexColor("#092B55")
BLUE=colors.HexColor("#0968B9")
RED=colors.HexColor("#D7192D")
GREEN=colors.HexColor("#078556")
MIST=colors.HexColor("#F2F7FB")
LINE=colors.HexColor("#D7E3EC")
TEXT=colors.HexColor("#233F5E")
MUTED=colors.HexColor("#667D94")

def _money(value:float)->str:
    return f"{float(value or 0):,.2f}"

def _masked(number:str)->str:
    return f"XXXX XXXX {number[-4:]}" if number else "Not available"

def build_statement_pdf(customer,accounts,transactions_by_account:dict[int,list])->bytes:
    output=BytesIO()
    document=SimpleDocTemplate(output,pagesize=landscape(A4),rightMargin=16*mm,leftMargin=16*mm,topMargin=28*mm,bottomMargin=18*mm,title="Union Bank of India Account Statement",author="Union Bank of India")
    styles=getSampleStyleSheet()
    title=ParagraphStyle("StatementTitle",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=20,leading=24,textColor=NAVY,alignment=TA_LEFT,spaceAfter=3*mm)
    heading=ParagraphStyle("AccountHeading",parent=styles["Heading2"],fontName="Helvetica-Bold",fontSize=12,leading=15,textColor=NAVY,spaceBefore=4*mm,spaceAfter=2*mm)
    body=ParagraphStyle("StatementBody",parent=styles["BodyText"],fontName="Helvetica",fontSize=8.5,leading=12,textColor=TEXT)
    small=ParagraphStyle("StatementSmall",parent=body,fontSize=7.5,leading=10,textColor=MUTED)
    right=ParagraphStyle("StatementRight",parent=body,alignment=TA_RIGHT)
    story=[Paragraph("Account Statement",title),Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}",small),Spacer(1,4*mm)]
    profile=[[Paragraph("Customer name",small),Paragraph("Customer ID",small),Paragraph("City",small),Paragraph("Relationship since",small)],[Paragraph(customer.name,body),Paragraph(customer.customer_code,body),Paragraph(customer.city or "-",body),Paragraph(customer.relationship_since or "-",body)]]
    profile_table=Table(profile,colWidths=[65*mm,48*mm,48*mm,48*mm])
    profile_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),MIST),("BOX",(0,0),(-1,-1),.6,LINE),("INNERGRID",(0,0),(-1,-1),.4,LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),("LEFTPADDING",(0,0),(-1,-1),9)]))
    story.extend([profile_table,Spacer(1,4*mm)])
    for index,account in enumerate(accounts):
        transactions=transactions_by_account.get(account.id,[])
        story.append(CondPageBreak((50+min(len(transactions),6)*8)*mm))
        summary=[[Paragraph("Account",small),Paragraph("Type",small),Paragraph("Status",small),Paragraph("Current balance (INR)",small)],[Paragraph(_masked(account.account_number),body),Paragraph(account.account_type,body),Paragraph(account.status,body),Paragraph(_money(account.balance),right)]]
        summary_table=Table(summary,colWidths=[65*mm,52*mm,45*mm,47*mm])
        summary_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EAF4FD")),("BOX",(0,0),(-1,-1),.6,LINE),("INNERGRID",(0,0),(-1,-1),.4,LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),8)]))
        story.extend([Paragraph(f"{account.account_type} - {_masked(account.account_number)}",heading),summary_table,Spacer(1,3*mm)])
        rows=[["Date","Description","Reference","Debit (INR)","Credit (INR)","Balance (INR)"]]
        if transactions:
            for item in transactions: rows.append([item.transaction_date.strftime("%d %b %Y"),Paragraph(item.description,body),item.reference,_money(item.debit) if item.debit else "-",_money(item.credit) if item.credit else "-",_money(item.balance)])
        else: rows.append(["-",Paragraph("No transactions available for this statement.",small),"-","-","-","-"])
        table=Table(rows,repeatRows=1,colWidths=[25*mm,77*mm,39*mm,29*mm,29*mm,32*mm])
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7.5),("FONTNAME",(0,1),(-1,-1),"Helvetica"),("FONTSIZE",(0,1),(-1,-1),7.5),("TEXTCOLOR",(0,1),(-1,-1),TEXT),("ALIGN",(3,1),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("GRID",(0,0),(-1,-1),.35,LINE),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F8FBFD")]),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6)]))
        story.append(table)
        if index<len(accounts)-1:story.append(Spacer(1,5*mm))
    story.extend([Spacer(1,5*mm),Paragraph("This statement is system-generated for informational purposes. Report any discrepancy to the bank promptly. Never share your PIN, OTP, CVV, or password.",small)])
    def page(canvas,doc):
        width,height=landscape(A4);canvas.saveState();canvas.setFillColor(NAVY);canvas.rect(0,height-20*mm,width,20*mm,fill=1,stroke=0);canvas.setFillColor(colors.white);canvas.setFont("Helvetica-Bold",13);canvas.drawString(16*mm,height-12*mm,"Union Bank of India");canvas.setFont("Helvetica",8);canvas.drawRightString(width-16*mm,height-12*mm,"Union Engage AI - Secure Banking Statement");canvas.setFillColor(RED);canvas.rect(16*mm,height-20.6*mm,34*mm,.9*mm,fill=1,stroke=0);canvas.setFillColor(BLUE);canvas.rect(50*mm,height-20.6*mm,34*mm,.9*mm,fill=1,stroke=0);canvas.setFillColor(GREEN);canvas.rect(84*mm,height-20.6*mm,34*mm,.9*mm,fill=1,stroke=0);canvas.setStrokeColor(LINE);canvas.line(16*mm,13*mm,width-16*mm,13*mm);canvas.setFillColor(MUTED);canvas.setFont("Helvetica",7);canvas.drawString(16*mm,8*mm,"Union Bank of India | Customer statement");canvas.drawRightString(width-16*mm,8*mm,f"Page {doc.page}");canvas.restoreState()
    document.build(story,onFirstPage=page,onLaterPages=page)
    return output.getvalue()
