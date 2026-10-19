"""Currency-aware project finance and vendor travel commands; no external payments."""
import json
from pathlib import Path
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
CURRENCIES={c['code']:c for c in json.loads((Path(__file__).resolve().parent.parent/'shared/currencies.json').read_text())}
ACTIONS=['project_commercial','payment_term','consultant','trip','expense','change_request','change_decision']
def fail(m): raise HTTPException(422,m)
def auth(ok):
    if not ok: raise HTTPException(403,'Your role does not allow this action.')
def text(v,label,maxlen=180):
    if not isinstance(v,str) or not v.strip() or len(v.strip())>maxlen: fail(f'{label} is required (maximum {maxlen} characters).')
    return v.strip()
def day(v,label):
    try:
        if not isinstance(v,str) or len(v)!=10 or date.fromisoformat(v).isoformat()!=v: raise ValueError()
    except (ValueError,TypeError): fail(f'{label} must be a valid date.')
    return v
def num(v,label,lo=0,hi=1e10):
    if type(v) not in (int,float,Decimal): fail(f'{label} is invalid.')
    n=Decimal(str(v))
    if not n.is_finite() or not Decimal(str(lo))<=n<=Decimal(str(hi)): fail(f'{label} is invalid.')
    return n
def amount_in(v,p,label='Amount',minimum=0):
    n=num(v,label,minimum);digits=CURRENCIES[p.get('currency','USD')]['digits'];rounded=n.quantize(Decimal(10)**-digits,rounding=ROUND_HALF_UP)
    if n!=rounded: fail(f"{label} allows {digits} decimal places for {p.get('currency','USD')}.")
    return float(rounded)
def with_finance(s):
    return {**s,'projects':[{**p,'currency':p.get('currency') or 'USD','usdRate':p.get('usdRate') or 1,'rateDate':p.get('rateDate'),'vendorId':p.get('vendorId')} for p in s['projects']],'paymentTerms':s.get('paymentTerms',[]),'consultants':s.get('consultants',[]),'trips':s.get('trips',[]),'expenses':s.get('expenses',[]),'changeRequests':s.get('changeRequests',[])}
def finance_scope(s,projects):
    ids={p['id'] for p in projects};vendors={p.get('vendorId') for p in projects};trips=[t for t in s.get('trips',[]) if t['projectId'] in ids]
    return {'changeRequests':[c for c in s.get('changeRequests',[]) if c['projectId'] in ids],'expenses':[e for e in s.get('expenses',[]) if e['projectId'] in ids],'paymentTerms':[t for t in s.get('paymentTerms',[]) if t['projectId'] in ids],'trips':trips,'consultants':[c for c in s.get('consultants',[]) if (c['ownerProjectId'] in ids if c.get('ownerProjectId') else c['vendorId'] in vendors or any(t['consultantId']==c['id'] for t in trips))]}
def project_commercial(s,b,p,today):
    code=b.get('currency',p.get('currency','USD'))
    if code not in CURRENCIES: fail('Select a supported currency.')
    rate=Decimal(1) if code=='USD' else num(b.get('usdRate'),'USD exchange rate',1e-8,1e8)
    if rate!=rate.quantize(Decimal('.00000001')): fail('Exchange rate allows eight decimals.')
    vendor=b.get('vendorId') or None
    if vendor and not any(c['kind']=='vendor' and c['id']==vendor and (c['active'] or p.get('vendorId')==vendor) for c in s['catalogs']): fail('Select an active external vendor.')
    rate_date=None if code=='USD' else day(b.get('rateDate'),'Exchange rate date')
    if rate_date and rate_date>today: fail('Exchange rate date cannot be in the future.')
    return dict(currency=code,usdRate=float(rate),rateDate=rate_date,vendorId=vendor)
def mutate_commercial(s,u,action,b,uid,today):
    s=with_finance(s);p=next((p for p in s['projects'] if p['id']==b.get('projectId')),None);planner=u['role']=='admin' or p and u['role']=='head' and p['department']==u['department'];fin=u['role'] in ['admin','finance']
    if action=='project_commercial':
        auth(planner and p)
        if b.get('budget')!=p['budget']: fail('Use a budget change request to revise the approved budget.')
        fields=project_commercial(s,b,p,today)
        if fields['currency']!=p['currency'] and any(x['projectId']==p['id'] for key in ['pos','paymentTerms','trips','changeRequests'] for x in s[key]): fail('Currency is locked after financial or travel records exist.')
        p.update(fields);p['budget']=amount_in(b.get('budget'),p,'Budget')
        if sum(Decimal(str(x['amount'])) for x in s['pos'] if x['projectId']==p['id'])>Decimal(str(p['budget'])) or sum(Decimal(str(x['amount'])) for x in s['paymentTerms'] if x['projectId']==p['id'] and not x['cancelled'])>Decimal(str(p['budget'])): fail('Budget cannot be below commitments or payment conditions.')
        label=f"Updated commercial settings · {p['title']} · {p['currency']} · USD rate {p['usdRate']}"
    elif action=='change_request':
        auth((planner or fin) and p)
        if b.get('id'): fail('Submitted change requests cannot be overwritten.')
        row=dict(id=uid,projectId=p['id'],title=text(b.get('title'),'Change title',100),reason=text(b.get('reason'),'Business justification',2000),amount=amount_in(b.get('amount'),p,'Additional budget',.0001),status='Pending',requestedById=u['id'],requestedBy=u['name'],requestedDate=today,decidedById=None,decidedBy=None,decisionDate=None,decisionNote=None,budgetBefore=None,budgetAfter=None)
        s['changeRequests'].append(row);label='Submitted budget change · '+row['title']
    elif action=='change_decision':
        auth(fin and p);row=next((c for c in s['changeRequests'] if c['id']==b.get('id') and c['projectId']==p['id']),None)
        if not row: fail('Change request not found.')
        if row['status']!='Pending': fail('This request has already been decided.')
        if row['requestedById']==u['id']: fail('A different administrator or finance user must review this request.')
        if b.get('decision') not in ['Approved','Rejected']: fail('Select Approve or Reject.')
        note=text(b.get('decisionNote'),'Decision reason',2000)
        if b['decision']=='Approved':
            row['budgetBefore']=p['budget'];p['budget']=amount_in(Decimal(str(p['budget']))+Decimal(str(row['amount'])),p,'Revised budget');row['budgetAfter']=p['budget']
        row.update(status=b['decision'],decidedById=u['id'],decidedBy=u['name'],decisionDate=today,decisionNote=note);label=row['status']+' budget change · '+row['title']
    elif action=='payment_term':
        auth(fin and p);old=next((x for x in s['paymentTerms'] if x['id']==b.get('id')),None)
        if b.get('id') and (not old or old['projectId']!=p['id']): fail('Payment condition not found.')
        if old and any(i.get('termId')==old['id'] for i in s['invoices']): fail('An invoiced condition is locked.')
        if b.get('trigger') not in ['date','milestone'] or type(b.get('cancelled')) is not bool: fail('Select a payment trigger and status.')
        milestone=next((t for t in s['tasks'] if t['id']==b.get('milestoneId') and t['projectId']==p['id'] and t.get('isMilestone')),None) if b['trigger']=='milestone' else None
        if b['trigger']=='milestone' and not milestone: fail('Select a milestone in this project.')
        row=dict(id=old['id'] if old else uid,projectId=p['id'],title=text(b.get('title'),'Condition name',100),amount=amount_in(b.get('amount'),p,'Scheduled amount',.0001),trigger=b['trigger'],dueDate=day(b.get('dueDate'),'Payment due date') if b['trigger']=='date' else None,milestoneId=milestone['id'] if milestone else None,cancelled=b['cancelled'])
        if not row['cancelled'] and sum(Decimal(str(x['amount'])) for x in s['paymentTerms'] if x['projectId']==p['id'] and x['id']!=row['id'] and not x['cancelled'])+Decimal(str(row['amount']))>Decimal(str(p['budget'])): fail('Payment conditions cannot exceed project budget.')
        s['paymentTerms']=[row if x['id']==row['id'] else x for x in s['paymentTerms']] if old else s['paymentTerms']+[row];label=('Updated' if old else 'Created')+' payment condition · '+row['title']
    elif action=='consultant':
        auth(planner);old=next((x for x in s['consultants'] if x['id']==b.get('id')),None)
        if b.get('id') and not old: fail('Consultant not found.')
        if old and u['role']!='admin': auth(old.get('ownerProjectId')==(p['id'] if p else None))
        vendor=b.get('vendorId') or (p.get('vendorId') if p else None)
        if not any(c['kind']=='vendor' and c['id']==vendor and (c['active'] or old and old['vendorId']==vendor) for c in s['catalogs']): fail('Select an active vendor.')
        if p and not p.get('vendorId'):
            if b.get('assignProjectVendor') is not True: fail('Confirm assigning this vendor to the project.')
            p['vendorId']=vendor
        if p and vendor!=p.get('vendorId'): fail('Select the project vendor, or change it under Finance first.')
        if u['role']!='admin' and vendor!=p.get('vendorId'): fail('Consultant must belong to the project vendor.')
        if old and vendor!=old['vendorId'] and any(t['consultantId']==old['id'] for t in s['trips']): fail('Vendor is locked after travel is recorded.')
        if type(b.get('active')) is not bool: fail('Choose consultant status.')
        row=dict(id=old['id'] if old else uid,vendorId=vendor,ownerProjectId=old.get('ownerProjectId') if old else None if u['role']=='admin' else p['id'],name=text(b.get('name'),'Consultant name',100),designation=text(b['designation'],'Designation',100) if b.get('designation') is not None else (old or {}).get('designation',''),active=b['active'])
        if any(x['id']!=row['id'] and x['vendorId']==vendor and x['name'].lower()==row['name'].lower() for x in s['consultants']): fail('This consultant already exists for the vendor.')
        s['consultants']=[row if x['id']==row['id'] else x for x in s['consultants']] if old else s['consultants']+[row];label=('Updated' if old else 'Added')+' vendor consultant · '+row['name']
    elif action=='expense':
        auth((planner or fin) and p);old=next((x for x in s['expenses'] if x['id']==b.get('id')),None)
        if b.get('id') and (not old or old['projectId']!=p['id']): fail('Expense not found.')
        if b.get('kind') not in ['spares','miscellaneous']: fail('Select an expense category.')
        if old and old['kind']!=b['kind']: fail('Expense category cannot change.')
        remarks=b.get('remarks','')
        if not isinstance(remarks,str) or len(remarks)>1000: fail('Remarks allow 1000 characters.')
        row=dict(id=old['id'] if old else uid,projectId=p['id'],kind=b['kind'],date=day(b.get('date'),'Expense date'),prNumber=text(b.get('prNumber'),'PR number',60),amountJod=amount_in(b.get('amountJod'),{'currency':'JOD'},'Amount',.001),remarks=remarks.strip())
        if row['date']>today: fail('Expense date cannot be in the future.')
        if any(x['id']!=row['id'] and x['projectId']==p['id'] and x['kind']==row['kind'] and x['prNumber'].lower()==row['prNumber'].lower() for x in s['expenses']): fail('This PR number is already recorded in this category.')
        s['expenses']=[row if x['id']==row['id'] else x for x in s['expenses']] if old else s['expenses']+[row];label=('Updated' if old else 'Added')+' '+row['kind']+' expense · '+row['prNumber']
    else:
        auth(planner and p);old=next((x for x in s['trips'] if x['id']==b.get('id')),None)
        if b.get('id') and (not old or old['projectId']!=p['id']): fail('Travel record not found.')
        c=next((c for c in s['consultants'] if c['id']==b.get('consultantId') and (c['active'] or old and old['consultantId']==c['id'])),None)
        if not c or (c['vendorId']!=p.get('vendorId') and (not old or old['consultantId']!=c['id'])) or c.get('ownerProjectId') and c['ownerProjectId']!=p['id']: fail('Select an active consultant for this project vendor.')
        if any(type(b.get(k)) is not bool for k in ['biaFlight','biaAccommodation','flightBooked']): fail('Choose BIA travel provisions.')
        start=day(b.get('start'),'Arrival date');end=day(b.get('end'),'Departure date')
        if end<start: fail('Departure must follow arrival.')
        if b['flightBooked'] and not b['biaFlight']: fail('A BIA flight booking requires BIA flight provision.')
        if b['biaAccommodation'] and b.get('stayType') not in ['campus','external']: fail('Select campus or external accommodation.')
        booked=day(b.get('bookedDate'),'Booking date') if b['flightBooked'] else None
        if booked and (booked>today or booked>start): fail('Booking date must be on or before today and arrival.')
        notes=b.get('notes','')
        if not isinstance(notes,str) or len(notes)>1000: fail('Travel notes allow 1000 characters.')
        row=dict(id=old['id'] if old else uid,projectId=p['id'],consultantId=c['id'],start=start,end=end,biaFlight=b['biaFlight'],biaAccommodation=b['biaAccommodation'],biaFood=(old or {}).get('biaFood',False),stayType=b.get('stayType') if b['biaAccommodation'] else None,flightBooked=b['flightBooked'],flightCost=amount_in(b.get('flightCostJod',b.get('flightCost')),{'currency':'JOD'} if b.get('flightCostJod') is not None else p,'Flight cost',.0001) if b['flightBooked'] else None,bookedDate=booked,notes=notes.strip())
        if any(k in b for k in ['visaCostJod','flightCostJod','hotelBookedBy']):
            hotel=b['biaAccommodation'] and b.get('stayType')=='external'
            if hotel and b.get('hotelBookedBy') not in ['bia','vendor']: fail('Choose who booked the hotel.')
            row.update(flightCostJod=amount_in(b.get('flightCostJod'),{'currency':'JOD'},'Flight cost',.001) if b['flightBooked'] else None,hotelBookedBy=b.get('hotelBookedBy') if hotel else None,hotelCostJod=amount_in(b.get('hotelCostJod'),{'currency':'JOD'},'Hotel cost') if hotel and b.get('hotelBookedBy')=='bia' else 0,visaCostJod=amount_in(b.get('visaCostJod',0),{'currency':'JOD'},'Visa cost'))
        elif old and 'visaCostJod' in old: fail('Reload the updated travel form before editing this visit.')
        s['trips']=[row if x['id']==row['id'] else x for x in s['trips']] if old else s['trips']+[row];label=('Updated' if old else 'Added')+f" consultant visit · {c['name']} · {start}–{end}"
    return s,label

def invoice_term(s,b,po,amount):
    if not b.get('termId'): return None
    t=next((t for t in s['paymentTerms'] if t['id']==b['termId'] and t['projectId']==po['projectId'] and not t['cancelled']),None)
    if not t or any(i.get('termId')==t['id'] for i in s['invoices']) or Decimal(str(t['amount']))!=Decimal(str(amount)): fail('Select an unused payment condition in this project and invoice its exact amount.')
    return t['id']

def invoice_change(s,b,po,amount):
    if not b.get('changeRequestId'): return None
    c=next((c for c in s['changeRequests'] if c['id']==b['changeRequestId'] and c['projectId']==po['projectId'] and c['status']=='Approved'),None)
    if not c: fail('Select an approved change request in this project.')
    used=sum(Decimal(str(i['amount'])) for i in s['invoices'] if i.get('changeRequestId')==c['id'])
    if used+Decimal(str(amount))>Decimal(str(c['amount'])): fail('Invoices exceed the approved change amount.')
    return c['id']
