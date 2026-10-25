import sys,json,ast,io,contextlib
from pathlib import Path
import unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import source_quality as q
from dutch_translation_agent import DutchToEnglishAgent
from handbook_quality import validate_findings,build_handbook,render_handbook,validate_document
from file_saver_agent import FileSaverAgent
from handbook_agent import HandbookAgent
import tester_agent
import uuid

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=ROOT/'test_runs'/('test-'+uuid.uuid4().hex);self.tmp.mkdir(parents=True)
 def test_source_metadata_preserved(self):
  m,b=q.split_source('Title\n\nBron: CBS\nURL: https://cbs.nl/x\nPublicatie: 2025\n\nHet aantal is 17.')
  self.assertEqual(m['publisher'],'CBS');self.assertEqual(b,'Het aantal is 17.')
  self.assertEqual(q.unwrap_translation(q.wrap_translation(m,'Count is 17.')),(m,'Count is 17.'))
 def test_public_names_and_private_contact(self):
  text=DutchToEnglishAgent().anonymize_text('Centraal Bureau voor de Statistiek (CBS), NHL Stenden Hogeschool and Nike. Jan Jansen: jan@example.com')
  self.assertIn('Centraal Bureau voor de Statistiek',text)
  self.assertIn('NHL Stenden Hogeschool',text)
  self.assertIn('Nike',text)
  self.assertNotIn('Jan Jansen',text);self.assertNotIn('jan@example.com',text)
 def test_numbers_and_known_mistranslations(self):
  self.assertTrue(q.translation_errors('Horeca: 6; 3; 2.','Horticulture: 6; 3; 2.'))
  self.assertTrue(q.translation_errors('15 procent','One in six'))
  self.assertTrue(q.translation_errors('45; 20','45; 21'))
  self.assertFalse(q.translation_errors('17; 13; 8.','17; 13; 8.'))
 def test_literal_protection(self):
  protected,mapping=q.protect_translation_literals("Horeca 6; 3; 2 and [Person_1]")
  self.assertNotIn("Horeca",protected)
  self.assertIn("[Person_1]",protected)
  self.assertEqual(q.restore_literals(protected,mapping),"hospitality 6; 3; 2 and [Person_1]")
 def test_placeholder_integrity(self):
  self.assertTrue(q.translation_errors('[Person_1] zegt 5.','[Person_2] says 5.'))
 def test_invalid_audit_blocks(self):
  with self.assertRaises(ValueError):q.validate_audit({'verdict':'PASS'})
  self.assertFalse(q.validate_audit({'verdict':'PASS','issues':['Contradiction']}))
 def test_fabricated_evidence_blocks(self):
  with self.assertRaises(ValueError):validate_findings({'findings':[{'claim':'AI saves 20%.','quote':'AI saves 20 percent.'}]},'No savings were measured.')
 def test_changed_numbers_in_claim_blocks(self):
  with self.assertRaises(ValueError):validate_findings({'findings':[{'claim':'35% of businesses.','quote':'17% of businesses used AI.'}]},'17% of businesses used AI.')
 def test_rejected_paraphrase_is_replaced_by_verbatim_evidence(self):
  sources=[{'id':'S1','filename':'a.txt','metadata':{'title':'Title'},'body':'A prototype is being researched.'}]
  answers=iter([json.dumps({'findings':[{'claim':'A prototype is being researched.','quote':'A prototype is being researched.'}]}),json.dumps({'verdict':'FAIL','issues':['Unsupported claim']})])
  md,report=build_handbook(sources,lambda *_:next(answers))
  self.assertEqual(report['mode'],'verbatim-evidence-fallback')
  self.assertEqual(report['findings'][0]['findings'][0]['claim'],sources[0]['body'])
 def test_bibliography_and_no_invented_costs(self):
  source={'id':'S1','filename':'a.txt','metadata':{'title':'<bad>','url':'javascript:alert(1)','publisher':'CBS'},'body':'A prototype is being researched.'}
  findings=[{'id':'S1','findings':[{'claim':source['body'],'quote':source['body']}]}]
  md=render_handbook([source],findings)
  validate_document(md,[source]);self.assertIn('[S1](#source-s1)',md)
  self.assertNotIn('javascript:',md);self.assertNotIn('<bad>',md)
  self.assertIn('Not established',md);self.assertNotIn('$500',md)
 def test_legacy_translation_requires_retranslation(self):
  p=self.tmp/'legacy.txt';p.write_text('A legacy translation')
  with self.assertRaisesRegex(ValueError,'Re-translate'):q.load_verified_translation(p)
 def test_save_preserves_previous_and_sidecars(self):
  m={'title':'Title'};text=q.wrap_translation(m,'17.')
  rec={'metadata':m,'safe_original':'17.','safe_original_sha256':q.fingerprint('17.'),'quality':{'status':'PASS'},'translation_sha256':q.fingerprint(text)}
  saver=FileSaverAgent(output_dir=self.tmp)
  with patch.object(saver,'generate_filename',return_value='same.txt'),contextlib.redirect_stdout(io.StringIO()):
   a=saver.save(text,rec);b=saver.save(text,rec)
  self.assertNotEqual(a,b);q.load_verified_translation(a)
  a.write_text(text+'changed',encoding='utf-8')
  with self.assertRaisesRegex(ValueError,'changed'):q.load_verified_translation(a)
 def test_incomplete_model_response_rejected(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self):return json.dumps({'done':True,'done_reason':'length','message':{'content':'partial'}}).encode()
  with patch('urllib.request.urlopen',return_value=Response()):
   with self.assertRaises(RuntimeError):DutchToEnglishAgent().ask_ai('test','data')
 def test_pdf_not_created_on_quality_failure(self):
  # The input gate is tested elsewhere; isolate the post-generation gate.
  p=self.tmp/'a.txt';p.write_text('fixture')
  agent=HandbookAgent(input_dir=self.tmp,output_dir=self.tmp/'pdf')
  with patch.object(agent,'run_test_gate_for_files',return_value=True),patch('handbook_agent.load_verified_translation',return_value=({'title':'A'},'Source',{})),patch.object(agent,'generate_handbook',side_effect=ValueError('Unsupported claim')),patch('handbook_agent.subprocess.run') as process,contextlib.redirect_stdout(io.StringIO()):
   result=agent.run(source_filename='a.txt')
  self.assertIsNone(result);process.assert_not_called();self.assertFalse(list(self.tmp.rglob('*.pdf')))
  self.assertTrue(list(self.tmp.rglob('failed_*.json')))
 def test_gate_blocks_legacy_before_model(self):
  p=self.tmp/"legacy.txt";p.write_text("Legacy translation",encoding="utf-8")
  with patch.object(tester_agent,"evaluate_text") as model,contextlib.redirect_stdout(io.StringIO()):
   self.assertEqual(tester_agent.main(["--input-dir",str(self.tmp),"--files",p.name]),2)
  model.assert_not_called()
 def test_known_tables_preserve_values(self):
  source="Gebruik AI, bedrijfsgrootte\nTotaal (2 of meer werkzame personen): 17; 13; 8.\n* Voorlopige cijfers."
  translated=q.translate_known_table(source)
  self.assertIsNotNone(translated)
  self.assertEqual(q.numeric_tokens(source),q.numeric_tokens(translated))
 def test_selected_missing_input_fails(self):
  with contextlib.redirect_stderr(io.StringIO()):
   self.assertEqual(tester_agent.main(['--input-dir',str(self.tmp),'--files','missing.txt']),2)

if __name__=='__main__':unittest.main(verbosity=2)

