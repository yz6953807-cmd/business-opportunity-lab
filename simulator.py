"""Reproducible synthetic buyer–seller experiment. No market forecast."""
import argparse, csv, json, random
from pathlib import Path
from decimal import Decimal
from finance import calculate

def simulate(config, seed=None, focal=None):
    seed=int(config['seed'] if seed is None else seed); rng=random.Random(seed)
    segments=[('Student renter',30,15,36),('Young professional',30,22,60),('Family renter',20,25,75),('Established renter',20,30,90)]
    buyers=[]
    for group,n,lo,hi in segments:
        for _ in range(n):
            buyers.append({'id':f'B{len(buyers)+1:03}','segment':group,'budget':rng.uniform(lo,hi),'entry':rng.randint(1,80),'interest':rng.random(),'preferences':{i:rng.random() for i in 'ABC'},'fit':{i:rng.random()>.20 for i in 'ABC'},'delay':rng.randint(1,5)})
    offers=config['products']; sellers={}
    for p in offers:
        # Focal runs retain the same buyers and one offer; joint runs offer all three.
        if focal and p['id']!=focal: continue
        f=calculate(p,config['budget'],config['inventory_limit'],config['protected_cash'])
        if not f['complete']: raise ValueError(f"Invalid simulation inputs: {p['id']}")
        q=int(p['quantity']) if p.get('in_stock') else 0
        sellers[p['id']]={'p':p,'remaining':q,'initial':q,'sales':0,'cash':float(Decimal(str(config['budget']))-Decimal(str(q))*Decimal(str(p['landed']))-Decimal(str(p['setup']))-Decimal(str(p['ads']))),'pending':[],'v':f['variable']}
    bought=set(); declined=set(); log=[]; rounds=[]
    for r in range(1,101):
        used=set()
        for s in sellers.values():
            due=[x for x in s['pending'] if x[0]<=r]; s['cash']+=sum(x[1] for x in due); s['pending']=[x for x in s['pending'] if x[0]>r]
        for b in buyers:
            if b['id'] in bought or b['id'] in declined or not b['entry']<=r<b['entry']+10: continue
            choices=[]
            for i,s in sellers.items():
                p=s['p']; price=float(p['price'])
                if s['remaining']<=0 or price>b['budget'] or not b['fit'][i]: continue
                score=.60*b['preferences'][i]+.30*b['interest']-.10*price/b['budget']
                if score>=.32: choices.append((score,i))
            if not choices: declined.add(b['id']); continue
            _,i=max(choices)
            if i in used: continue
            s=sellers[i]; p=s['p']; s['remaining']-=1; s['sales']+=1; s['cash']-=s['v']; s['pending'].append((r+b['delay'],float(p['price']))); used.add(i); bought.add(b['id'])
            log.append({'round':r,'buyer':b['id'],'segment':b['segment'],'seller':i,'price':p['price'],'settlement_round':r+b['delay']})
        for i,s in sellers.items():
            p=s['p']; profit=s['sales']*(p['price']-p['landed']-s['v'])-p['setup']-p['ads']
            rounds.append({'round':r,'product':i,'sales':s['sales'],'stock':s['remaining'],'profit':round(profit,2),'cash':round(s['cash'],2),'pending':round(sum(x[1] for x in s['pending']),2)})
    summary=[]
    for i,s in sellers.items():
        p=s['p']; pending=sum(x[1] for x in s['pending']); s['cash']+=pending; s['pending']=[]
        f=calculate(p,config['budget'],config['inventory_limit'],config['protected_cash'],s['sales'])
        summary.append({'product':i,'name':p['name'],'stocked':s['initial'],'sold':s['sales'],'remaining':s['remaining'],'profit':round(f['profit'],2),'required_cash':f['required_cash'],'financial_pass':f['valid'],'cash_after_settlement':round(s['cash'],2),'settled_after_round_100':round(pending,2),'pending_after_settlement':0})
    return {'label':'Synthetic software experiment, not real demand','seed':seed,'mode':focal or 'Joint market','rounds':100,'buyers':buyers,'summary':summary,'transactions':log,'round_log':rounds}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',default=str(Path(__file__).parent/'data/market.json')); ap.add_argument('--seed',type=int); ap.add_argument('--focal',choices=list('ABC')); ap.add_argument('--output',default='simulation_output'); a=ap.parse_args()
    config=json.loads(Path(a.input).read_text()); result=simulate(config,a.seed,a.focal); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(result,indent=2)); (out/'inputs.json').write_text(json.dumps(config,indent=2))
    for key in ('transactions','round_log','summary'):
        rows=result[key]; fields=list(rows[0]) if rows else (['round','buyer','segment','seller','price','settlement_round'] if key=='transactions' else [])
        with (out/f'{key}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(json.dumps(result['summary'],indent=2))
if __name__=='__main__': main()
