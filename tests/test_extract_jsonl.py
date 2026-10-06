import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'src'))
spec=importlib.util.spec_from_file_location('extract_jsonl',Path(__file__).parents[1]/'src/extract_jsonl.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def source(root):
 p=root/'pdf/example.pdf'; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'%PDF-test')
 return dict(url='https://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn1320pdf/ks1320_14.pdf',report_id=1320,
 report_title='能登半島地震',source_type='tnn',section='道路被害',event='earthquake',index_url='https://www.nilim.go.jp/index.htm',
 license_policy_url='https://www.nilim.go.jp/aboutlink.htm',rights_review='共同著作は要調査',local_path='pdf/example.pdf',
 bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status='complete')

def extractor(path): return ['輪島・珠洲の道路被害\n','', '球磨川\n'], 'test Poppler'

def test_pages_keep_japanese_empty_page_and_provenance(tmp_path):
 row=source(tmp_path); out=tmp_path/'jsonl'
 record=m.extract_one(tmp_path,out,row,{},extractor=extractor)
 pages=[json.loads(x) for x in (out/record['output_path']).read_text().splitlines()]
 assert [x['page_number'] for x in pages]==[1,2,3]
 assert pages[0]['text'].startswith('輪島') and pages[0]['report_id']=='1320'
 assert pages[1]['needs_ocr_review'] and not pages[1]['has_text']
 assert pages[0]['source_pdf_sha256']==row['sha256'] and pages[0]['rights_review']==row['rights_review']
 assert record['pages']==3 and record['empty_pages']==1

def test_resume_checks_original_and_jsonl(tmp_path):
 row=source(tmp_path); out=tmp_path/'jsonl'; record=m.extract_one(tmp_path,out,row,{},extractor=extractor)
 def fail(_): raise AssertionError('do not extract again')
 assert m.extract_one(tmp_path,out,row,{row['url']:record},extractor=fail)['status']=='skipped'
 (out/record['output_path']).write_text('corrupt')
 with pytest.raises(ValueError): m.extract_one(tmp_path,out,row,{row['url']:record},extractor=fail)

def test_original_corruption_or_escaping_path_stops(tmp_path):
 row=source(tmp_path)
 with pytest.raises(ValueError): m.extract_one(tmp_path,tmp_path/'jsonl',dict(row,local_path='../outside.pdf'),{},extractor=extractor)
 (tmp_path/row['local_path']).write_bytes(b'changed')
 with pytest.raises(ValueError): m.extract_one(tmp_path,tmp_path/'jsonl',row,{},extractor=extractor)

def test_page_boundaries_include_blank_last_page():
 assert m.split_pages('a\f\f',2)==['a','']
 with pytest.raises(m.ExtractionError): m.split_pages('a\f',2)

def test_failed_extraction_publishes_nothing(tmp_path):
 row=source(tmp_path)
 def fail(_): raise m.ExtractionError('bad PDF')
 with pytest.raises(m.ExtractionError): m.extract_one(tmp_path,tmp_path/'jsonl',row,{},extractor=fail)
 assert not list((tmp_path/'jsonl').rglob('*.jsonl'))

def test_merge_is_byte_identical_and_keeps_categories(tmp_path):
 row=source(tmp_path); out=tmp_path/'jsonl'
 a=m.extract_one(tmp_path,out,row,{},extractor=extractor)
 b=m.extract_one(tmp_path,out,dict(row,url=row['url']+'?example=flash',source_type='flash',report_id='flash-test'),{},extractor=extractor)
 summary=m.merge(out,[a,b])
 assert summary['pages']==6 and summary['documents']==2
 for record in [a,b]:
  assert (out/'corpus'/f"{record['source_type']}.jsonl").read_bytes()==(out/record['output_path']).read_bytes()

def test_merge_rejects_corruption_before_writing(tmp_path):
 row=source(tmp_path); out=tmp_path/'jsonl'; r=m.extract_one(tmp_path,out,row,{},extractor=extractor)
 (out/r['output_path']).write_text('bad')
 with pytest.raises(ValueError): m.merge(out,[r])
 assert not list((out/'corpus').glob('*.jsonl'))
