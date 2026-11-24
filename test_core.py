import unittest,json,copy
from pathlib import Path
from finance import calculate,decide
from simulator import simulate
from reviews import parse_reviews,analyze
C=json.loads((Path(__file__).parent/'data/market.json').read_text()); B=C['products'][1]
class Core(unittest.TestCase):
 def test_report(self):
  f=calculate(B,500,100,150); self.assertTrue(f['valid']); self.assertEqual([f[k] for k in ['margin','inventory','required_cash','break_even','cash_recovery','profit']],[13.9,90,390,6,8,59]); self.assertEqual(decide(B,f)[0],'RESEARCH FURTHER')
 def test_revised(self):
  p=dict(B,setup=100,ads=120); self.assertEqual(calculate(p,500,100,150)['profit'],-81); p.update(moq=100,quantity=100); f=calculate(p,500,100,150); self.assertEqual(f['required_cash'],1970); self.assertFalse(f['valid']); self.assertEqual(decide(p,f)[0],'REVISE / STOP')
 def test_constraints(self):
  for p in [dict(B,moq=100),dict(B,price=1),dict(B,in_stock=False),dict(B,landed=None),dict(B,quantity=1.5),dict(B,landed=-1)]: self.assertFalse(calculate(p,500,100,150)['valid'])
  self.assertFalse(calculate(B,200,100,150)['valid']); self.assertFalse(calculate(B,500,80,150)['valid'])
 def test_verified(self):
  p=dict(B,dimensions='10 x 5 in',quote_status='Verified',fit_status='Verified',source='supplier confirmation'); f=calculate(p,500,100,150); self.assertEqual(decide(p,f,True,True,True)[0],'SMALL TEST'); self.assertEqual(decide(p,f,True,False,True)[0],'RESEARCH FURTHER')
 def test_reviews(self):
  rows=parse_reviews('Adhesive pulled paint off.\nAdhesive pulled paint off.\nFits my door.'); self.assertEqual(len(rows),2); self.assertTrue(all(r in rows for t in analyze(rows) for r in t['evidence']))
 def test_simulation(self):
  a=simulate(C,1401); self.assertEqual(a,simulate(C,1401)); self.assertEqual(a['rounds'],100); self.assertEqual(len(a['round_log']),300); self.assertEqual(len(a['buyers']),100); self.assertEqual(len({r['buyer'] for r in a['transactions']}),len(a['transactions'])); self.assertEqual(len({(r['round'],r['seller']) for r in a['transactions']}),len(a['transactions'])); self.assertTrue(all(r['stock']>=0 for r in a['round_log'])); self.assertTrue(all(r['pending_after_settlement']==0 for r in a['summary'])); self.assertEqual(a['buyers'],simulate(C,1401,'B')['buyers']); self.assertNotEqual(a['buyers'],simulate(C,1402)['buyers'])
if __name__=='__main__': unittest.main()
