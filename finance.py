from decimal import Decimal, ROUND_CEILING

D = lambda x: Decimal(str(x))
MONEY_FIELDS = ('price','landed','delivery','fees','refund','setup','ads')

def calculate(p, budget, inventory_limit, protected_cash, sold=None):
    missing = [k for k in (*MONEY_FIELDS,'quantity','moq') if p.get(k) is None or p.get(k)=='']
    if missing: return {'valid':False,'errors':['Missing: '+', '.join(missing)],'complete':False}
    try:
        P,c,delivery,fees,refund,K,A = (D(p[k]) for k in MONEY_FIELDS)
        q,moq = int(p['quantity']),int(p['moq'])
        B,Imax,H = map(D,(budget,inventory_limit,protected_cash))
        Q = q if sold is None else int(sold)
        if not all(x.is_finite() for x in (P,c,delivery,fees,refund,K,A,B,Imax,H)): raise ValueError()
        if min(P,c,delivery,fees,refund,K,A,B,Imax,H)<0 or q<1 or moq<1 or not 0<=Q<=q or D(p['quantity'])!=q or D(p['moq'])!=moq or (sold is not None and D(sold)!=Q): raise ValueError()
    except (ValueError,TypeError,ArithmeticError,OverflowError): return {'valid':False,'complete':False,'errors':['Costs must be nonnegative; quantities must be valid whole numbers.']}
    v=delivery+fees+refund; m=P-c-v; I=q*c; C=I+q*v+A+K+H
    ceil=lambda n,d: int((n/d).to_integral_value(rounding=ROUND_CEILING)) if d>0 else None
    be=ceil(A+K,m); recovery=ceil(I+A+K,P-v)
    checks={'Available cash':C<=B,'Inventory limit':I<=Imax,'Minimum order quantity':q>=moq,'Positive contribution':m>0,'Break-even within order':be is not None and be<=q,'Supplier stock available':bool(p.get('in_stock',False))}
    return {'complete':True,'valid':all(checks.values()),'errors':[k for k,vv in checks.items() if not vv],'checks':checks,'margin':float(m),'inventory':float(I),'required_cash':float(C),'headroom':float(B-C),'break_even':be,'cash_recovery':recovery,'profit':float(Q*m-A-K),'full_profit':float(q*m-A-K),'variable':float(v),'sold':Q,'quantity':q,'protected_cash':float(H),'fixed':float(A+K)}

def decide(p,f,review_verified=False,demand_checked=False,confirmed=False):
    if not f['complete']: return 'RESEARCH FURTHER','Complete the missing or invalid financial inputs.'
    if not f['valid']: return 'REVISE / STOP','Failed checks: '+', '.join(f['errors'])+'. No real test is permitted under this plan.'
    if p.get('quote_status')!='Verified' or p.get('fit_status')!='Verified' or not str(p.get('dimensions','')).strip() or not str(p.get('source','')).strip() or not review_verified or not demand_checked:
        return 'RESEARCH FURTHER','The financial checks pass, but review evidence, product fit, demand or supplier terms remain unverified.'
    if not confirmed: return 'RESEARCH FURTHER','The checks pass. Confirm the limited test quantity and spending ceiling before proceeding.'
    return 'SMALL TEST','Verified inputs and financial checks support a limited test, subject to the seller’s confirmation. This is not a purchase order or a sales forecast.'
