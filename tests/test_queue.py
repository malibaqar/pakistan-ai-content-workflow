import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

spec=importlib.util.spec_from_file_location('app',Path(__file__).resolve().parents[1]/'worker/app.py')
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

class QueueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.old=a.DB_PATH
  a.DB_PATH=str(Path(self.tmp.name)/'test.sqlite')
  a.init()
 def tearDown(self):
  a.DB_PATH=self.old
  self.tmp.cleanup()
 def insert(self,ident='one',status='approved',age=0):
  stamp=(a.now()-dt.timedelta(hours=age)).isoformat()
  with a.connect() as c:
   c.execute('INSERT INTO stories VALUES(?,?,?,?,?,?)',(ident,'AI tools','https://example.org/'+ident,'Example',stamp,'AI example'))
   c.execute('INSERT INTO posts(id,story_id,text,status,created,notes) VALUES(?,?,?,?,?,?)',(ident,ident,'AI example',status,stamp,'checked'))
 def test_tracking_removed(self):
  self.assertEqual(a.canonical('https://example.org/a?utm_source=x&keep=1#hi'),'https://example.org/a?keep=1')
 def test_non_https_rejected(self):
  with self.assertRaises(ValueError):a.canonical('http://example.org')
 def test_feed_filters_old_missing_future_and_nonai(self):
  at=a.now()
  def item(title,d):return f'<item><title>{title}</title><link>https://example.org/{title}</link><pubDate>{d}</pubDate></item>'
  xml='<rss><channel>'+item('AI-new',at.isoformat())+item('AI-old',(at-dt.timedelta(days=5)).isoformat())+item('AI-future',(at+dt.timedelta(days=1)).isoformat())+item('AI-undated','')+item('sport',at.isoformat())+'</channel></rss>'
  self.assertEqual(len(a.parse_feed(xml,'Example',at)),1)
 def test_atom(self):
  xml=f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>AI study</title><link href="https://example.org/a"/><updated>{a.now().isoformat()}</updated></entry></feed>'
  self.assertEqual(len(a.parse_feed(xml,'Example')),1)
 def test_drafts_not_publishable(self):
  self.insert(status='draft')
  self.assertFalse(a.claim()['ready'])
 def test_concurrent_claim_only_one(self):
  self.insert()
  with ThreadPoolExecutor(max_workers=4) as ex: results=list(ex.map(lambda _:a.claim(),range(4)))
  self.assertEqual(sum(x['ready'] for x in results),1)
 def test_receipt_requires_real_identifier(self):
  self.insert();r=a.claim()
  with self.assertRaises(ValueError):a.receipt({**r,'receipt':'HTTP 200'})
  self.assertEqual(a.claim()['reason'],'pending_publish_needs_reconciliation')
 def test_receipt_token_and_duplicate(self):
  self.insert();r=a.claim()
  with self.assertRaises(ValueError):a.receipt({**r,'claim_token':'wrong','receipt':'urn:li:share:123'})
  a.receipt({**r,'receipt':'urn:li:share:123'})
  with self.assertRaises(ValueError):a.receipt({**r,'receipt':'urn:li:share:123'})
 def test_min_gap(self):
  self.insert();r=a.claim();a.receipt({**r,'receipt':'urn:li:share:123'})
  self.insert('two');self.assertEqual(a.claim()['reason'],'minimum_gap')
 def test_daily_max(self):
  self.insert('one','published');self.insert('two','published');self.insert('three')
  with a.connect() as c:c.execute("UPDATE posts SET claimed=? WHERE status='published'",(a.now().isoformat(),))
  self.assertEqual(a.claim()['reason'],'daily_limit')
 def test_stale_approval_not_published(self):
  self.insert(age=100);self.assertFalse(a.claim()['ready'])
 def test_campaign_ends(self):
  with a.connect() as c:c.execute("UPDATE meta SET value=? WHERE key='campaign_start'",((a.now()-dt.timedelta(days=31)).isoformat(),))
  self.insert();self.assertEqual(a.claim()['reason'],'campaign_ended')
 def test_approval_note_required(self):
  self.insert(status='draft')
  with self.assertRaises(ValueError):a.decide('one','approved','')
 def test_model_cannot_inject_source_url(self):
  with patch.dict(os.environ,{'AI_PROVIDER':'ollama'}),patch.object(a,'generate_local',return_value={'skip':False,'text':'AI '*80+'https://fake.example','review_notes':'x'}):
   with self.assertRaises(ValueError):a.generate({'source':'Example','url':'https://example.org'})
 def test_gemini_guard_no_network(self):
  with patch.dict(os.environ,{'AI_PROVIDER':'gemini','GEMINI_FREE_TIER_CONFIRMED':'false'}),patch.object(a.urllib.request,'urlopen') as request:
   with self.assertRaises(ValueError):a.generate({})
   request.assert_not_called()
 def test_generation_source_attached(self):
  with patch.dict(os.environ,{'AI_PROVIDER':'ollama'}),patch.object(a,'generate_local',return_value={'skip':False,'text':'AI learning example. '*15,'review_notes':'verify'}):
   result=a.generate({'source':'Example','url':'https://example.org'})
   self.assertIn('Source: Example\nhttps://example.org',result[0])
 def test_workflow_links_and_inactive(self):
  root=Path(__file__).resolve().parents[1]
  for path in (root/'workflows').glob('*.json'):
   w=json.loads(path.read_text());names={n['name'] for n in w['nodes']}
   self.assertFalse(w['active'])
   for source,con in w['connections'].items():
    self.assertIn(source,names)
    for branch in con['main']:
     for edge in branch:self.assertIn(edge['node'],names)

if __name__=='__main__':unittest.main()
