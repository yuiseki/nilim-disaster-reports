import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('rights_scan',ROOT/'src/rights_scan.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
spec2=importlib.util.spec_from_file_location('test_merge_helpers',ROOT/'tests/test_merge_jsonl.py')
h=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(h)


@pytest.mark.parametrize('line,signal',[
    ('All rights reserved. No part of this book may be reproduced','reserved'),
    ('本報告書の全部又は一部の転載、複製は、文書による承認を得ずしてこれを行ってはならない。','reserved'),
    ('編集・発行 ©国土技術政策総合研究所','copyright'),
    ('Copyright © (2015) by N.I.L.I.M. and P.W.R.I.','copyright'),
    ('図-2.2.7 氾濫流の状況（※地理院地図を元に作成）','survey'),
    ('（山口県提供）','credit'),
    ('出典：気象庁 HP','credit'),
    ('国立研究開発法人 建築研究所','joint'),
])
def test_signals_detect_each_kind(line,signal):
    assert m.signals(line)[signal]==1


@pytest.mark.parametrize('line',['(c) 縦断図（上流面側から）','写真-6.11 クラック（図-6.8 のⓒ）','本資料の転載・複写の問い合わせは'])
def test_signals_ignore_figure_labels_and_reprint_contact_lines(line):
    s=m.signals(line)
    assert s['reserved']==0 and s['copyright']==0


def test_scan_counts_lines_and_quotes_strongest_first_hit():
    pages=['表紙\n国立研究開発法人土木研究所\n','（山口県提供）\n','\n','Copyright © (2015) by N.I.L.I.M. and P.W.R.I.\nAll rights reserved.\n']
    got=m.scan(pages)
    assert got['joint_lines']==2 and got['credit_lines']==1  # the copyright line names P.W.R.I. too
    assert got['copyright_lines']==1 and got['reserved_lines']==1
    assert got['first_hit']=='p4: All rights reserved.'


DECISIONS_TNN={'1320':('c','PWRI','joint publication','ks1320_22.pdf p1: ©PWRI'),'758':('a','','none found','')}
DECISIONS_FLASH={'R8/a.pdf':('b','','credits only','p1: 提供'),'h28/b.pdf':('d','','text unreadable',None)}


def test_build_writes_one_row_per_document_in_catalog_order(tmp_path):
    data,records=h.build(tmp_path,exclude=h.urls(1))
    (data/'hf/RIGHTS_REVIEW.tsv').unlink()
    rows=m.build(data,data/'hf',tnn=DECISIONS_TNN,flash=DECISIONS_FLASH)
    with (data/'hf/RIGHTS_REVIEW.tsv').open(encoding='utf-8',newline='') as f:
        back=list(csv.DictReader(f,delimiter='\t',quoting=csv.QUOTE_NONE))
    assert [r['source_url'] for r in back]==[d[0] for d in h.DOCS]==[r['source_url'] for r in rows]
    assert [r['class'] for r in back]==['c','c','b','a','d']
    assert [r['excluded'] for r in back]==['no','yes','no','no','no']
    assert back[1]['copyright_lines']=='1' and back[0]['pages']=='3' and back[0]['empty_pages']=='1'
    assert back[4]['evidence']=='' and back[3]['evidence']==''
    assert list(back[0])==m.COLUMNS
    assert all('\t' not in v and '\n' not in v for r in back for v in r.values())


def test_build_quotes_the_first_joint_line_of_page_one_when_no_evidence_is_given(tmp_path):
    docs=[(h.F+'R8/c.pdf','flash','flash-cccc',['令和8年9月7日\n国立研究開発法人\t建築研究所\n'],False,'c')]
    data,records=h.build(tmp_path,docs=docs,missing=False)
    rows=m.build(data,data/'hf',tnn={},flash={'R8/c.pdf':('c','BRI','joint',None)})
    assert rows[0]['evidence']=='p1: 国立研究開発法人 建築研究所'


def test_build_refuses_a_document_without_a_decision(tmp_path):
    data,records=h.build(tmp_path)
    with pytest.raises(ValueError,match='no rights decision'): m.build(data,data/'hf',tnn={'1320':DECISIONS_TNN['1320']},flash=DECISIONS_FLASH)
    with pytest.raises(ValueError,match='class'): m.build(data,data/'hf',tnn=dict(DECISIONS_TNN,**{'758':('e','','','')}),flash=DECISIONS_FLASH)


def test_build_output_is_accepted_by_merge(tmp_path):
    spec3=importlib.util.spec_from_file_location('merge_jsonl',ROOT/'src/merge_jsonl.py')
    mj=importlib.util.module_from_spec(spec3); spec3.loader.exec_module(mj)
    data,records=h.build(tmp_path,exclude=h.urls(0,1))
    m.build(data,data/'hf',tnn=DECISIONS_TNN,flash=DECISIONS_FLASH)
    man=mj.merge(data,data/'hf')
    assert man['rights']['excluded']['c']==dict(reports=1,pdfs=2,pages=4)


REAL=ROOT/'data/hf/RIGHTS_REVIEW.tsv'

@pytest.mark.skipif(not REAL.exists(),reason='rights review not built')
def test_real_review_covers_the_catalog_and_excludes_only_class_c():
    rows=list(csv.DictReader(REAL.open(encoding='utf-8',newline=''),delimiter='\t',quoting=csv.QUOTE_NONE))
    cat=list(csv.DictReader((ROOT/'data/catalog.tsv').open(encoding='utf-8',newline=''),delimiter='\t'))
    missing={r['url'] for r in json.loads((ROOT/'data/jsonl/source-missing.json').read_text())}
    assert [r['source_url'] for r in rows]==[c['url'] for c in cat if c['url'] not in missing]
    assert {r['class'] for r in rows if r['excluded']=='yes'}<={'c'}
    for r in rows:  # one class per report
        assert r['class']==next(x['class'] for x in rows if x['report_id']==r['report_id'] and x['source_type']==r['source_type'])
