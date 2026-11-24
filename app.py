import copy, hashlib, json, os
from pathlib import Path
import pandas as pd
import streamlit as st
from finance import calculate, decide
from reviews import parse_reviews, analyze, llm_analyze
from simulator import simulate
from storage import save, history

ROOT=Path(__file__).parent
st.set_page_config(page_title='Business Opportunity Lab',page_icon='◈',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--accent:#176c58} .stApp{background:#f6f8f6;color:#142d28} [data-testid="stSidebar"]{background:#eaf1ed;border-right:1px solid #d5e0da} html,body,[class*="css"]{font-family:Manrope,system-ui,sans-serif} .block-container{padding-top:2rem;max-width:1240px} h1,h2,h3{letter-spacing:-.045em;color:#173d32} .eyebrow{font-size:11px;letter-spacing:.16em;color:#53746a;text-transform:uppercase;font-weight:800;margin-bottom:8px} .hero{background:#163f35;color:#fff;padding:25px 30px;border-radius:18px;margin-bottom:22px} .hero h1{color:white;font-size:34px;margin:0 0 6px} .hero p{color:#cae0d8;margin:0;font-size:15px} [data-testid="stMetric"]{background:#fff;border:1px solid #dce7df;border-radius:14px;padding:16px} [data-testid="stMetricValue"]{color:#194e40;font-weight:700} [data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border-radius:14px} .stButton button[kind="primary"]{background:#176c58;border:0;color:white} .stButton button{border-radius:8px} .stTabs [data-baseweb="tab-list"]{gap:15px} .subtle{font-size:13px;color:#577267} footer{visibility:hidden}
</style>''',unsafe_allow_html=True)
PAGES=['01  Setup','02  Compare','03  Check costs','04  Decide']
S=st.session_state
if 'config' not in S:
    S.config=json.loads((ROOT/'data/market.json').read_text()); S.reviews=parse_reviews((ROOT/'data/reviews.csv').read_text(),True); S.selected='B'; S.page=PAGES[0]; S.analysis=None; S.analysis_label='Keyword matching'; S.sim=None; S.review_verified=False; S.demand_checked=False; S.confirmed=False; S.evidence_note=''; S.project='Kitchen storage for US renters'; S.revision=0

def go(page): S.page=PAGES[page]
def money(v): return f'${v:,.2f}'
def config_fingerprint(): return hashlib.sha256(json.dumps(S.config,sort_keys=True).encode()).hexdigest()
def calc(p,sold=None): return calculate(p,S.config['budget'],S.config['inventory_limit'],S.config['protected_cash'],sold)
def current(): return next(p for p in S.config['products'] if p['id']==S.selected)
def nav(prev=None,nxt=None):
    a,b=st.columns(2)
    if prev is not None: a.button('← Back',on_click=go,args=(prev,),use_container_width=True)
    if nxt is not None: b.button('Continue →',on_click=go,args=(nxt,),type='primary',use_container_width=True)
def title(n,name,desc):
    st.markdown(f'<div class="eyebrow">Business Opportunity Lab / STEP {n} OF 4</div><div class="hero"><h1>{name}</h1><p>{desc}</p></div>',unsafe_allow_html=True)
def show_metrics(f):
    if not f['complete']: st.error('; '.join(f['errors'])); return
    cols=st.columns(4)
    for col,l,v in zip(cols,['Contribution / sale','Required cash','Break-even sales','Profit at sell-out'],[money(f['margin']),money(f['required_cash']),f['break_even'] if f['break_even'] is not None else 'N/A',money(f['full_profit'])]): col.metric(l,v)

def edit_offer(p):
    id=p['id']; prefix=f'{S.revision}_{id}_'; st.caption('Assumed costs are editable. Blank inputs remain missing; they are never silently set to zero.')
    a,b=st.columns(2)
    for idx,(k,label) in enumerate([('price','Selling price ($)'),('landed','Landed unit cost ($)'),('delivery','Delivery per sale ($)'),('fees','Platform fees per sale ($)'),('refund','Expected refunds per sale ($)'),('setup','Setup cost ($)'),('ads','Advertising ($)')]):
        p[k]=[a,b][idx%2].number_input(label,min_value=0.0,value=float(p[k]) if p.get(k) is not None else None,step=.1,key=prefix+k)
    a,b=st.columns(2)
    p['moq']=a.number_input('Minimum order quantity',min_value=1,value=int(p['moq']) if p.get('moq') is not None else None,step=1,key=prefix+'moq')
    p['quantity']=b.number_input('Proposed order quantity',min_value=1,value=int(p['quantity']) if p.get('quantity') is not None else None,step=1,key=prefix+'quantity')
    p['dimensions']=st.text_input('Product measurements / cabinet clearance',p.get('dimensions',''),key=prefix+'dimensions'); p['features']=st.text_input('Product features',p['features'],key=prefix+'features')
    a,b=st.columns(2)
    p['quote_status']=a.selectbox('Quote evidence',['Assumed','Unverified','Verified'],index=['Assumed','Unverified','Verified'].index(p['quote_status']),key=prefix+'quote_status'); p['fit_status']=b.selectbox('Product fit',['Unverified','Verified'],index=['Unverified','Verified'].index(p['fit_status']),key=prefix+'fit_status'); p['source']=st.text_input('Supplier / listing source and verification reference',p.get('source',''),key=prefix+'source'); p['in_stock']=st.checkbox('Supplier has stock',p['in_stock'],key=prefix+'in_stock')

with st.sidebar:
    st.markdown('### ◈ Opportunity Lab')
    st.caption('GROUP 14  ·  MIS3012')
    st.radio('WORKSPACE',PAGES,key='page')
    st.divider(); st.caption('SELLER PROFILE'); st.metric('Available cash',money(S.config['budget'])); st.caption(f"Inventory limit {money(S.config['inventory_limit'])}  ·  Reserve {money(S.config['protected_cash'])}")
    st.divider(); st.caption('Decision support, not a sales prediction. Sample offers and reviews are synthetic or assumed.')
    with st.expander('Optional AI settings'):
        api=st.text_input('API key',type='password',value=os.getenv('LLM_API_KEY','')); base=st.text_input('OpenAI-compatible API base',value=os.getenv('LLM_BASE_URL','https://api.openai.com/v1')); model=st.text_input('Model',value=os.getenv('LLM_MODEL','gpt-4o-mini')); st.caption('Only click AI analysis after confirming you have permission to send the review text to the provider. Keys are not saved in decision records.')

if S.page==PAGES[0]:
    title(1,'Set up your opportunity','Start with your cash constraints, customer evidence and three comparable product offers.')
    with st.container(border=True):
        st.subheader('Seller profile'); S.project=st.text_input('Project / market',S.project)
        a,b,c=st.columns(3)
        for col,k,l in [(a,'budget','Available budget ($)'),(b,'inventory_limit','Inventory spending limit ($)'),(c,'protected_cash','Protected cash ($)')]: S.config[k]=col.number_input(l,min_value=0.,value=float(S.config[k]),step=10.,key=f'{S.revision}_{k}')
    left,right=st.columns([1,1])
    with left,st.container(border=True):
        st.subheader('Customer reviews'); st.caption('CSV with review, optional review_id, product and source_type. TXT: one review per line.')
        file=st.file_uploader('Upload CSV or TXT',type=['csv','txt']);
        if file and st.button('Import reviews',type='primary'):
            try:
                rows=parse_reviews(file.getvalue().decode('utf-8-sig'),file.name.lower().endswith('.csv')); S.reviews=rows; S.analysis=None; S.review_verified=False; S.confirmed=False; st.success(f'{len(rows)} unique reviews imported.')
            except Exception as e: st.error(str(e))
        if st.button('Use synthetic sample reviews'):
            S.reviews=parse_reviews((ROOT/'data/reviews.csv').read_text(),True); S.analysis=None; S.review_verified=False; S.confirmed=False
        st.download_button('Download sample CSV',(ROOT/'data/reviews.csv').read_bytes(),'sample_reviews.csv','text/csv')
        st.metric('Unique reviews',len(S.reviews)); st.dataframe(pd.DataFrame(S.reviews),hide_index=True,use_container_width=True,height=210)
    with right,st.container(border=True):
        st.subheader('Three product offers'); st.caption('Edit each supplier offer. All prefilled values are assumed, not observed quotes.')
        for p in S.config['products']:
            with st.expander(f"{p['id']} · {p['name']}"): edit_offer(p)
        st.download_button('Export current inputs',json.dumps(S.config,indent=2),'market.json','application/json')
    nav(nxt=1)
elif S.page==PAGES[1]:
    title(2,'Compare the opportunities','Use customer evidence and comparable product information to shortlist a product.')
    with st.container(border=True):
        st.subheader('Customer evidence'); a,b=st.columns(2)
        if a.button('Analyze reviews (offline)',use_container_width=True): S.analysis=analyze(S.reviews); S.analysis_label='Keyword matching (not LLM)'
        if b.button('Analyze with AI',use_container_width=True,disabled=not bool(api)):
            try:
                with st.spinner('Analyzing review themes...'): S.analysis=llm_analyze(S.reviews,api,base,model); S.analysis_label='LLM themes with original source quotations'
            except Exception as e: st.error(f'AI analysis unavailable: {type(e).__name__}. Use offline analysis or check settings.')
        results=S.analysis if S.analysis is not None else analyze(S.reviews); st.caption((S.analysis_label if S.analysis is not None else 'Offline keyword preview')+' · Topic counts overlap. Review excerpts do not establish market demand.')
        for t in results:
            with st.expander(f"{t['topic']} · {t['count']} excerpts",expanded=True):
                st.write(t['summary'])
                for r in t['evidence']: st.write(f"“{r['review']}” — {r['review_id']} / {r['product']} / {r['source_type']}")
        if not results: st.info('No matching evidence. Add reviews or research more.')
        st.caption('Mark as verified only when genuine reviews have been checked against their sources.')
        observed=any(r['source_type']=='Observed' for r in S.reviews)
        S.review_verified=st.checkbox('I verified the observed review sources',value=S.review_verified if observed else False,disabled=not observed)
        S.evidence_note=st.text_area('Evidence corrections / uncertainties',S.evidence_note,placeholder='Record contradictory comments, source links or limitations.')
    st.subheader('Product comparison'); cards=st.columns(3)
    rows=[]
    for col,p in zip(cards,S.config['products']):
        f=calc(p); rows.append({'Product':p['id']+' · '+p['name'],'Price':p['price'],'Landed cost':p['landed'],'MOQ':p['moq'],'Quantity':p['quantity'],'Required cash':f.get('required_cash'),'Quote':p['quote_status'],'Dimensions':p['dimensions'] or 'Missing','Fit':p['fit_status'],'Finance':'Pass' if f['valid'] else 'Check / revise'})
        with col,st.container(border=True):
            st.caption('PRODUCT '+p['id']); st.subheader(p['name']); st.metric('Selling price',money(p['price']) if p['price'] is not None else 'Missing'); st.write('**Strength:** '+p['strength']); st.write('**Risk:** '+p['weakness']); st.write(p['features']); st.caption('Dimensions: '+(p['dimensions'] or 'Missing')); st.caption('Quote: '+p['quote_status']); st.write('Financial checks: '+('Pass' if f['valid'] else 'Needs revision'))
    st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    S.selected=st.radio('Shortlist a candidate',['A','B','C'],index=['A','B','C'].index(S.selected),horizontal=True,format_func=lambda i:next(p['name'] for p in S.config['products'] if p['id']==i)); nav(prev=0,nxt=2)
elif S.page==PAGES[2]:
    title(3,'Check profit & cash','Calculate whether the proposed order fits your limits, before committing any money.')
    p=current(); st.subheader(p['id']+' · '+p['name']); st.caption('Update inputs in Setup; all calculations and decisions refresh using the latest saved session inputs.')
    st.button('Edit supplier offer / MOQ',on_click=go,args=(0,)); f=calc(p); show_metrics(f)
    if f['complete']:
        a,b=st.columns([1,1])
        with a,st.container(border=True):
            st.subheader('Cash allocation'); items={'Inventory':f['inventory'],'Selling-cost reserve':p['quantity']*f['variable'],'Setup + advertising':f['fixed'],'Protected cash':f['protected_cash']}; st.bar_chart(pd.DataFrame({'USD':items}),horizontal=True); st.metric('Cash remaining above reserves',money(f['headroom'])); st.caption('Selling-cost reserve is for liquidity; it is not an extra profit expense.')
        with b,st.container(border=True):
            st.subheader('Financial guardrails')
            for k,v in f['checks'].items(): st.write(('✓ ' if v else '✗ ')+k)
            if f['valid']: st.success('Proposed order passes financial checks.')
            else: st.error('Real test blocked. Revise or stop.')
            st.metric('Cash recovery sales (no salvage)',f['cash_recovery'] if f['cash_recovery'] is not None else 'N/A'); st.caption('Cash recovery assumes unsold inventory has no recoverable value.')
        with st.container(border=True):
            st.subheader('What if fewer units sell?'); sold=st.slider('Units sold',0,int(p['quantity']),int(p['quantity']),key=f'sold_{p["id"]}_{p["quantity"]}'); st.metric('Estimated accounting profit',money(calc(p,sold)['profit'])); q=int(p['quantity']); step=max(1,q//200); xs=sorted(set(range(0,q+1,step))|{q,sold}); st.line_chart(pd.DataFrame({'Units sold':xs,'Estimated profit':[calc(p,x)['profit'] for x in xs]}).set_index('Units sold'))
            with st.expander('Calculation formulas'):
                st.latex(r'm=P-c-v,\quad \Pi(Q)=Qm-A-K'); st.latex(r'I=qc,\quad C=qc+qv+A+K+H'); st.latex(r'Q_{BE}=\lceil(A+K)/m\rceil'); st.latex(r'Q_{cash}=\lceil(qc+A+K)/(P-v)\rceil')
    nav(prev=1,nxt=3)
else:
    title(4,'Choose your next action','Make a traceable decision, experiment with synthetic buyers, and save the result.')
    p=current(); f=calc(p); fingerprint=config_fingerprint(); show_metrics(f)
    st.subheader('Evidence and confirmation'); observed=any(r['source_type']=='Observed' for r in S.reviews)
    evidence_key=hashlib.sha256(json.dumps([S.config,S.reviews,S.selected,S.review_verified],sort_keys=True).encode()).hexdigest()[:20]
    demand=st.checkbox('I have independently checked real demand evidence',key='demand_'+evidence_key); note=st.text_input('Demand evidence source / pilot reference',key='demand_note_'+evidence_key,disabled=not demand); confirmed=st.checkbox('I confirm the proposed test quantity and spending ceiling',key='confirm_'+evidence_key,disabled=not f['valid'])
    action,reason=decide(p,f,S.review_verified and observed,demand and bool(note.strip()),confirmed)
    with st.container(border=True):
        st.markdown('**RECOMMENDED NEXT ACTION**'); st.subheader(action); st.write(reason); st.write(f"Candidate: **{p['name']}** · Proposed quantity: **{p.get('quantity')}**")
        if f['complete']: st.write(f"Spending ceiling excluding protected cash: **{money(f['required_cash']-f['protected_cash'])}**")
        next_steps=['Check product dimensions / cabinet clearance','Confirm supplier quote, delivery and MOQ','Verify customer evidence and demand','Set advertising ceiling and pilot success criteria']
        if not f['valid'] and f['complete']: next_steps=['Resolve '+x for x in f['errors']]+next_steps
        checked=[x for i,x in enumerate(next_steps) if st.checkbox(x,key=f'next_{evidence_key}_{i}')]
        choices=['Research further','Revise','Stop'] if action!='SMALL TEST' else ['Small test','Research further','Revise','Stop']; default='Small test' if action=='SMALL TEST' else 'Revise' if action=='REVISE / STOP' else 'Research further'; chosen=st.selectbox('Record your decision',choices,index=choices.index(default),key='decision_'+evidence_key+action); reason_note=st.text_area('Decision notes / reason for revision',key='reason_'+evidence_key)
    st.subheader('100-round market simulation'); st.warning('Synthetic software experiment only. The simulation may include unaffordable offers for comparison; it does not authorize a purchase or prove demand.')
    a,b=st.columns(2); seed=a.number_input('Random seed',min_value=0,value=int(S.config['seed']),step=1); mode=b.selectbox('Experiment mode',['Joint market — A, B, C','Matched focal markets — separately'])
    if st.button('Run 100-round simulation',type='primary'):
        try:
            out=[simulate(S.config,int(seed),x) for x in 'ABC'] if mode.startswith('Matched') else [simulate(S.config,int(seed))]; S.sim={'fingerprint':fingerprint,'results':out,'inputs':copy.deepcopy(S.config)}
        except Exception as e: st.error(f'Simulation failed: {e}')
    if S.sim:
        if S.sim['fingerprint']!=fingerprint: st.info('Inputs have changed since this run. Rerun to evaluate current inputs; old results are retained separately.')
        else:
            results=S.sim['results']; summary=[r for run in results for r in run['summary']]; st.dataframe(pd.DataFrame(summary),hide_index=True,use_container_width=True); st.bar_chart(pd.DataFrame(summary).set_index('product')[['sold','remaining']]); st.caption(f"Seed {results[0]['seed']} · exactly 100 trading rounds per market · 100 synthetic buyer profiles per market")
            st.download_button('Download results + buyer profiles + transaction / round logs',json.dumps(S.sim,indent=2),'simulation_results.json','application/json')
    if st.button('Save decision to history',type='primary'):
        payload={'project':S.project,'inputs':copy.deepcopy(S.config),'candidate':p['id'],'recommendation':action,'chosen_decision':chosen,'reason':reason,'notes':reason_note,'financial_results':f,'quantity':p.get('quantity'),'spending_ceiling':f.get('required_cash',0)-f.get('protected_cash',0) if f['complete'] else None,'next_checks':next_steps,'completed_checks':checked,'reviews':S.reviews,'review_corrections':S.evidence_note,'review_verified':S.review_verified,'demand_reference':note,'confirmed':confirmed,'simulation':S.sim if S.sim and S.sim['fingerprint']==fingerprint else None}; rid=save(payload); st.success(f'Decision #{rid} saved. Revisions create new records.')
    with st.expander('Saved decision history'):
        records=history(); st.caption('Local SQLite history; previous revisions remain unchanged.')
        for i,t,r in records:
            st.write(f"#{i} · {t[:19]} UTC · {r['candidate']} · {r['chosen_decision']}"); st.download_button(f'Export record #{i}',json.dumps(r,indent=2),f'decision_{i}.json','application/json',key=f'export_{i}')
    nav(prev=2)
