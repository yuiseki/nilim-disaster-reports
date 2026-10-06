import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('publish',ROOT/'src/publish.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

CARD='''---
license: other
license_name: nilim-pdl1.0-and-co-publisher-notices
license_link: LICENSE
configs:
- config_name: default
  default: true
  data_files:
  - split: train
    path:
    - tnn.jsonl
    - flash.jsonl
- config_name: tnn
  data_files:
  - split: train
    path: tnn.jsonl
- config_name: flash
  data_files:
  - split: train
    path: flash.jsonl
---
# card
Excluded: 国総研資料 798.
'''
ALL=['EXCLUDE.txt','LICENSE','MANIFEST.json','README.md','RIGHTS_REVIEW.tsv','flash.jsonl','provenance.yaml','tnn.jsonl']


def rights(c_included=1,d_included=0):
    z=dict(reports=0,pdfs=0,pages=0)
    return dict(included=dict(a=dict(reports=1,pdfs=1,pages=1),b=z,c=dict(z,reports=c_included,pdfs=c_included),d=dict(z,reports=d_included)),
                excluded=dict(a=z,b=z,c=dict(reports=1,pdfs=1,pages=2),d=z))


def build(tmp_path,card=CARD,manifest_rights=None):
    hf=tmp_path/'hf'; hf.mkdir(parents=True)
    files={}
    for name,body in (('tnn.jsonl',b'{"a": 1}\n'),('flash.jsonl',b'{"b": 2}\n{"b": 3}\n')):
        (hf/name).write_bytes(body)
        files[name]=dict(lines=body.count(b'\n'),bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
    excluded=[dict(url='https://www.nilim.go.jp/x.pdf',source_type='tnn',report_id='798',pages=2)]
    (hf/'MANIFEST.json').write_text(json.dumps(dict(files=files,excluded=excluded,rights=manifest_rights or rights())))
    (hf/'README.md').write_text(card); (hf/'LICENSE').write_text('PDL1.0\n'); (hf/'provenance.yaml').write_text('a: 1\n')
    (hf/'RIGHTS_REVIEW.tsv').write_text('source_url\tclass\n'); (hf/'EXCLUDE.txt').write_text('https://www.nilim.go.jp/x.pdf\n')
    return hf


def test_dry_run_lists_only_the_allowed_files_with_sizes(tmp_path):
    hf=build(tmp_path)
    plan=m.upload_plan(hf)
    assert [p.name for p,_ in plan]==ALL
    assert dict((p.name,s) for p,s in plan)['flash.jsonl']==len(b'{"b": 2}\n{"b": 3}\n')


@pytest.mark.parametrize('name',['notes.txt','tnn.jsonl.part','.DS_Store','ks1320_01.pdf','x.PDF','catalog.tsv'])
def test_refuses_any_file_outside_the_allowlist(tmp_path,name):
    hf=build(tmp_path); (hf/name).write_bytes(b'%PDF-1.4\n' if 'pdf' in name.lower() else b'x')
    with pytest.raises(m.PublishError): m.upload_plan(hf)


def test_refuses_pdf_content_even_under_an_allowed_name(tmp_path):
    hf=build(tmp_path); (hf/'extra.jsonl').write_bytes(b'%PDF-1.7\n')
    with pytest.raises(m.PublishError,match='PDF'): m.upload_plan(hf)
    hf=build(tmp_path/'b'); (hf/'LICENSE').write_bytes(b'%PDF-1.7\n')
    with pytest.raises(m.PublishError,match='PDF'): m.upload_plan(hf)


def test_refuses_subdirectories(tmp_path):
    hf=build(tmp_path); (hf/'pdf').mkdir(); (hf/'pdf/a.jsonl').write_text('{}\n')
    with pytest.raises(m.PublishError): m.upload_plan(hf)


def test_refuses_card_configs_that_do_not_match_the_files(tmp_path):
    hf=build(tmp_path,card=CARD.replace('    path: flash.jsonl','    path: flashes.jsonl'))
    with pytest.raises(m.PublishError,match='configs'): m.upload_plan(hf)
    hf2=build(tmp_path/'b',card=CARD.replace('    - flash.jsonl\n',''))
    (hf2/'other.jsonl').write_text('{}\n')
    with pytest.raises(m.PublishError): m.upload_plan(hf2)


def test_refuses_missing_required_file_and_manifest_mismatch(tmp_path):
    for name in ('LICENSE','RIGHTS_REVIEW.tsv','EXCLUDE.txt'):
        hf=build(tmp_path/name); (hf/name).unlink()
        with pytest.raises(m.PublishError,match=name.split('.')[0]): m.upload_plan(hf)
    hf=build(tmp_path/'b'); (hf/'flash.jsonl').write_bytes(b'{"b": 2}\n')
    with pytest.raises(m.PublishError,match='MANIFEST'): m.upload_plan(hf)


def test_licence_must_follow_the_rights_review(tmp_path):
    # class c or d text is included: cc-by-4.0 is refused, "other" needs a name and a link
    hf=build(tmp_path,card=CARD.replace('license: other\nlicense_name: nilim-pdl1.0-and-co-publisher-notices\nlicense_link: LICENSE','license: cc-by-4.0'))
    with pytest.raises(m.PublishError,match='licen'): m.upload_plan(hf)
    hf=build(tmp_path/'b',card=CARD.replace('license_name: nilim-pdl1.0-and-co-publisher-notices\n',''))
    with pytest.raises(m.PublishError,match='license_name'): m.upload_plan(hf)
    hf=build(tmp_path/'c',card=CARD.replace('license: other','license: mit'))
    with pytest.raises(m.PublishError,match='licen'): m.upload_plan(hf)
    # only class a/b text included: cc-by-4.0 is allowed
    hf=build(tmp_path/'d',card=CARD.replace('license: other\nlicense_name: nilim-pdl1.0-and-co-publisher-notices\nlicense_link: LICENSE','license: cc-by-4.0'),
             manifest_rights=rights(c_included=0))
    assert len(m.upload_plan(hf))==len(ALL)
    hf=build(tmp_path/'e',card=CARD.replace('license: other\nlicense_name: nilim-pdl1.0-and-co-publisher-notices\nlicense_link: LICENSE','license: cc-by-4.0'),
             manifest_rights=rights(c_included=0,d_included=1))
    with pytest.raises(m.PublishError,match='licen'): m.upload_plan(hf)


def test_card_must_name_every_excluded_report(tmp_path):
    hf=build(tmp_path,card=CARD.replace('Excluded: 国総研資料 798.','Nothing excluded.'))
    with pytest.raises(m.PublishError,match='798'): m.upload_plan(hf)


class FakeApi:
    def __init__(self): self.calls=[]
    def create_repo(self,**kw): self.calls.append(('create_repo',kw))
    def create_commit(self,**kw): self.calls.append(('create_commit',kw))


def test_push_creates_public_dataset_and_uploads_only_the_plan(tmp_path):
    hf=build(tmp_path); api=FakeApi()
    m.push(hf,'yuiseki/nilim-disaster-reports',api=api)
    (name,kw),(name2,kw2)=api.calls
    assert name=='create_repo' and kw['repo_type']=='dataset' and kw['private'] is False and kw['repo_id']=='yuiseki/nilim-disaster-reports'
    assert name2=='create_commit' and kw2['repo_type']=='dataset'
    assert sorted(op.path_in_repo for op in kw2['operations'])==sorted(ALL)


def test_push_checks_sha256_before_upload(tmp_path):
    hf=build(tmp_path); api=FakeApi()
    man=json.loads((hf/'MANIFEST.json').read_text()); man['files']['tnn.jsonl']['sha256']='0'*64
    (hf/'MANIFEST.json').write_text(json.dumps(man))
    with pytest.raises(m.PublishError,match='sha256'): m.push(hf,'yuiseki/nilim-disaster-reports',api=api)
    assert api.calls==[]


REAL=ROOT/'data/hf'

@pytest.mark.skipif(not (REAL/'MANIFEST.json').exists(),reason='merged data not built')
def test_real_card_matches_files_and_manifest_counts():
    m.upload_plan(REAL)
    card=(REAL/'README.md').read_text(encoding='utf-8')
    lic=(REAL/'LICENSE').read_text(encoding='utf-8')
    man=json.loads((REAL/'MANIFEST.json').read_text())
    for s,v in man['series'].items():
        for k in ('documents','pages','characters','empty_pages'):
            assert f'{v[k]:,}' in card, (s,k)
        assert f'{man["files"][s+".jsonl"]["bytes"]:,} bytes' in card
    assert f'{man["totals"]["pages"]:,}' in card and f'{man["totals"]["characters"]:,}' in card
    assert f'{man["excluded_totals"]["pages"]:,}' in card and f'{man["excluded_totals"]["documents"]}' in card
    for side in ('included','excluded'):
        for c,v in man['rights'][side].items():
            if v['pdfs']: assert f'{v["pdfs"]:,}' in card, (side,c)
    # the NILIM terms are quoted exactly as published (including the original's 「は、の著作権は」)
    quote='国土技術政策総合研究所ウェブサイト及び国土技術政策総合研究所のソーシャルメディアアカウントで掲載・発信している情報（以下「コンテンツ」といいます。）は、の著作権は、特記されていない限り国土技術政策総合研究所に帰属し、権利表記の記載がない限り「公共データ利用規約（第1.0版）」（PDL1.0）に準拠した利用条件の下で、利用することができます。'
    assert quote in lic and quote in card
