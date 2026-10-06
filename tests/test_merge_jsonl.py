import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).parents[1]/'src'))
spec=importlib.util.spec_from_file_location('merge_jsonl',Path(__file__).parents[1]/'src/merge_jsonl.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

COLUMNS=['report_id','report_title','event','section','url','index_url','license_policy_url','rights_review','source_type','discovery_url']
REVIEW_COLUMNS=['source_type','report_id','section','source_url','pages','empty_pages','class','other_parties','basis','evidence',
                'reserved_lines','copyright_lines','survey_lines','credit_lines','joint_lines','first_hit','excluded']


def page(url,kind,rid,sha,number,text,ascii=False):
    value=dict(document_id=hashlib.sha256(url.encode()).hexdigest(),source_type=kind,report_id=rid,
        report_title='能登半島地震 （PDFファイル:5.8MB）',event='要調査',section='表紙',source_url=url,
        index_url='https://www.nilim.go.jp/index.htm',source_pdf_path=f'pdf/{kind}/x.pdf',source_pdf_sha256=sha,
        source_pdf_bytes=10,page_number=number,text=text,characters=len(text),
        non_whitespace_characters=len(''.join(text.split())),has_text=bool(text.strip()),
        needs_ocr_review=not text.strip(),replacement_characters=text.count('�'),
        extraction_method='pdftotext-layout',extractor_version='test',
        license_policy_url='https://www.nilim.go.jp/aboutlink.htm',rights_review='r')
    # ensure_ascii=True for some documents: re-serialising would change the bytes.
    return json.dumps(value,ensure_ascii=ascii)


T='https://www.nilim.go.jp/lab/bcg/siryou/tnn/'
F='https://www.nilim.go.jp/lab/bbg/saigai/'
DOCS=[  # catalog order: url, source_type, report_id, pages, ensure_ascii, rights class
    (T+'tnn1320pdf/ks1320_01.pdf','tnn','1320',['輪島の被害\n','','珠洲\n'],True,'c'),
    (T+'tnn1320pdf/ks1320_22.pdf','tnn','1320',['奥付 ©\n'],False,'c'),
    (F+'R8/a.pdf','flash','flash-aaaa',['熊本�\n','Kumamoto\n'],False,'b'),
    (T+'tnn0758pdf/ks075801.pdf','tnn','758',['九州北部豪雨\n'],False,'a'),
    (F+'h28/b.pdf','flash','flash-bbbb',['速報\n'],False,'d'),
]
MISSING=T+'tnn0728pdf/ks072824.pdf'


def build(root,docs=DOCS,manifest_order=None,exclude=(),missing=True):
    data=root/'data'; j=data/'jsonl'; (j/'documents').mkdir(parents=True); hf=data/'hf'; hf.mkdir()
    catalog=['\t'.join(COLUMNS)]
    records={}
    rows=[]
    for url,kind,rid,pages,ascii,cls in docs:
        catalog.append('\t'.join([rid,'title','要調査','表紙',url,'https://www.nilim.go.jp/index.htm',
                                  'https://www.nilim.go.jp/aboutlink.htm','r',kind,'https://www.nilim.go.jp/d.html']))
        sha=hashlib.sha256(url.encode()+b'pdf').hexdigest()
        body=''.join(page(url,kind,rid,sha,i,t,ascii)+'\n' for i,t in enumerate(pages,1)).encode()
        doc=hashlib.sha256(url.encode()).hexdigest(); path=f'documents/{doc}.jsonl'
        (j/path).write_bytes(body)
        records[url]=dict(url=url,document_id=doc,source_type=kind,report_id=rid,status='complete',
            schema_version='nilim-pages-jsonl-v1',source_sha256=sha,output_path=path,
            output_bytes=len(body),output_sha256=hashlib.sha256(body).hexdigest(),pages=len(pages),
            characters=sum(len(t) for t in pages),empty_pages=sum(not t.strip() for t in pages),
            low_text_pages=0,replacement_characters=sum(t.count('�') for t in pages),
            extractor_version='test',timestamp=1791326544.0)
        rows.append([kind,rid,'表紙',url,str(len(pages)),str(sum(not t.strip() for t in pages)),cls,
                     'PWRI' if cls=='c' else '','basis','evidence','0','0','0','0','0','',
                     'yes' if url in exclude else 'no'])
    if missing:
        catalog.append('\t'.join(['728','紀伊半島','要調査','奥付',MISSING,'https://www.nilim.go.jp/index.htm',
                                  'https://www.nilim.go.jp/aboutlink.htm','r','tnn','https://www.nilim.go.jp/d.html']))
    (data/'catalog.tsv').write_text('\n'.join(catalog)+'\n')
    order=manifest_order or [d[0] for d in docs]
    (j/'manifest.jsonl').write_text(''.join(json.dumps(records[u],ensure_ascii=False)+'\n' for u in order))
    rs=list(records.values())
    miss=[dict(report_id='728',url=MISSING,status='missing',http_status=404,source_type='tnn')] if missing else []
    (j/'dataset.json').write_text(json.dumps(dict(schema_version='nilim-pages-jsonl-v1',documents=len(rs),
        pages=sum(r['pages'] for r in rs),characters=sum(r['characters'] for r in rs),
        empty_pages=sum(r['empty_pages'] for r in rs),bytes=sum(r['output_bytes'] for r in rs),
        source_total=len(rs)+len(miss),source_missing=miss,extraction_errors=[])))
    (j/'status.json').write_text(json.dumps(dict(state='finished_with_missing' if miss else 'finished',
        total=len(rs)+len(miss),complete=len(rs),missing=len(miss))))
    (j/'source-missing.json').write_text(json.dumps(miss))
    (j/'extraction-errors.json').write_text('[]')
    fetched=[dict(url=u,status='complete',bytes=10,timestamp=1791282468.0+i) for i,u in enumerate(records)]
    fetched+=[dict(url=MISSING,status='missing',timestamp=1791319400.0)] if missing else []
    (data/'manifest.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in fetched))
    (hf/'EXCLUDE.txt').write_text('# test exclusions\n'+''.join(u+'\n' for u in exclude))
    (hf/'RIGHTS_REVIEW.tsv').write_text('\t'.join(REVIEW_COLUMNS)+'\n'+''.join('\t'.join(r)+'\n' for r in rows))
    return data,records


def source_lines(data,records,urls):
    out=[]
    for u in urls: out+=(data/'jsonl'/records[u]['output_path']).read_bytes().split(b'\n')[:-1]
    return out


def urls(*idx): return [DOCS[i][0] for i in idx]


def test_merge_copies_lines_byte_identical_in_catalog_order(tmp_path):
    data,records=build(tmp_path,manifest_order=urls(4,3,2,1,0))
    hf=data/'hf'; result=m.merge(data,hf)
    tnn=(hf/'tnn.jsonl').read_bytes(); flash=(hf/'flash.jsonl').read_bytes()
    assert tnn.split(b'\n')[:-1]==source_lines(data,records,urls(0,1,3))
    assert flash.split(b'\n')[:-1]==source_lines(data,records,urls(2,4))
    assert b'\\u8f2a' in tnn  # ensure_ascii line kept as written, not re-serialised
    assert ' '.encode() in tnn and tnn.count(b'\n')==5
    assert not list(hf.glob('*.part'))
    man=json.loads((hf/'MANIFEST.json').read_text())
    assert man==result
    f=man['files']['tnn.jsonl']
    assert f['lines']==5 and f['documents']==3 and f['bytes']==len(tnn) and f['sha256']==hashlib.sha256(tnn).hexdigest()
    assert man['series']['tnn']['empty_pages']==1 and man['series']['flash']['pages']==3
    assert man['series']['flash']['replacement_characters']==1
    assert man['excluded']==[] and man['source_missing'][0]['url']==MISSING


def test_merge_leaves_out_excluded_documents_and_records_them(tmp_path):
    data,records=build(tmp_path,exclude=urls(1,4))
    hf=data/'hf'; man=m.merge(data,hf)
    assert (hf/'tnn.jsonl').read_bytes().split(b'\n')[:-1]==source_lines(data,records,urls(0,3))
    assert (hf/'flash.jsonl').read_bytes().split(b'\n')[:-1]==source_lines(data,records,urls(2))
    assert [x['url'] for x in man['excluded']]==urls(1,4)
    assert man['excluded'][0]['report_id']=='1320' and man['excluded'][0]['pages']==1 and man['excluded'][0]['rights_class']=='c'
    assert man['totals']['documents']==3 and man['excluded_totals']['documents']==2 and man['excluded_totals']['pages']==2
    rights=man['rights']
    assert rights['included']['c']==dict(reports=1,pdfs=1,pages=3) and rights['excluded']['c']==dict(reports=1,pdfs=1,pages=1)
    assert rights['included']['d']==dict(reports=0,pdfs=0,pages=0) and rights['excluded']['d']['pdfs']==1
    assert m.verify(data,hf)['documents']==3


def test_merge_refuses_unknown_or_duplicate_exclusions(tmp_path):
    data,records=build(tmp_path,exclude=[T+'nothere.pdf'])
    with pytest.raises(ValueError,match='EXCLUDE'): m.merge(data,data/'hf')
    data,records=build(tmp_path/'b',exclude=urls(0,0))
    with pytest.raises(ValueError,match='EXCLUDE'): m.merge(data,data/'hf')
    data,records=build(tmp_path/'c',exclude=[MISSING])
    with pytest.raises(ValueError,match='EXCLUDE'): m.merge(data,data/'hf')


def test_merge_refuses_rights_review_that_does_not_cover_every_document(tmp_path):
    data,records=build(tmp_path)
    p=data/'hf/RIGHTS_REVIEW.tsv'; lines=p.read_text().splitlines(); p.write_text('\n'.join(lines[:-1])+'\n')
    with pytest.raises(ValueError,match='RIGHTS_REVIEW'): m.merge(data,data/'hf')
    data,records=build(tmp_path/'b')
    p=data/'hf/RIGHTS_REVIEW.tsv'; p.write_text(p.read_text().replace('\tc\tPWRI','\tx\tPWRI',1))
    with pytest.raises(ValueError,match='class'): m.merge(data,data/'hf')


def test_merge_refuses_incomplete_manifest_entry(tmp_path):
    data,records=build(tmp_path)
    p=data/'jsonl/manifest.jsonl'; lines=p.read_text().splitlines()
    r=json.loads(lines[1]); r['status']='failed'; lines[1]=json.dumps(r); p.write_text('\n'.join(lines)+'\n')
    with pytest.raises(ValueError,match='not complete'): m.merge(data,data/'hf')
    assert not list((data/'hf').glob('*.jsonl'))


def test_merge_refuses_document_sha_mismatch_and_leaves_no_output(tmp_path):
    data,records=build(tmp_path)
    doc=data/'jsonl'/records[DOCS[2][0]]['output_path']; doc.write_bytes(doc.read_bytes().replace(b'Kumamoto',b'Kumamotx'))
    with pytest.raises(ValueError,match='sha256'): m.merge(data,data/'hf')
    assert not list((data/'hf').glob('*.jsonl')) and not list((data/'hf').glob('*.part'))


def test_merge_refuses_catalog_manifest_disagreement(tmp_path):
    data,records=build(tmp_path)
    with (data/'catalog.tsv').open('a') as f:
        f.write('\t'.join(['9','t','要調査','s',T+'other.pdf','i','p','r','tnn','d'])+'\n')
    with pytest.raises(ValueError,match='catalog'): m.merge(data,data/'hf')


def test_merge_accepts_only_the_recorded_source_missing(tmp_path):
    data,records=build(tmp_path,missing=False)
    assert m.merge(data,data/'hf')['source_missing']==[]
    data,records=build(tmp_path/'b')
    (data/'jsonl/status.json').write_text(json.dumps(dict(state='finished_with_missing',total=6,complete=5,missing=2)))
    with pytest.raises(ValueError,match='finished'): m.merge(data,data/'hf')
    data,records=build(tmp_path/'c')
    (data/'jsonl/extraction-errors.json').write_text(json.dumps([dict(url=DOCS[0][0],error='bad')]))
    with pytest.raises(ValueError,match='extraction'): m.merge(data,data/'hf')
    data,records=build(tmp_path/'d')
    (data/'jsonl/status.json').write_text(json.dumps(dict(state='running',missing=1)))
    with pytest.raises(ValueError,match='finished'): m.merge(data,data/'hf')


def test_existing_outputs_survive_a_failed_rebuild(tmp_path):
    data,records=build(tmp_path)
    m.merge(data,data/'hf'); before=(data/'hf/flash.jsonl').read_bytes()
    doc=data/'jsonl'/records[DOCS[2][0]]['output_path']; doc.write_bytes(b'{}\n')
    with pytest.raises(ValueError): m.merge(data,data/'hf')
    assert (data/'hf/flash.jsonl').read_bytes()==before


def test_verify_passes_and_reports_counts(tmp_path):
    data,records=build(tmp_path); m.merge(data,data/'hf')
    report=m.verify(data,data/'hf')
    assert report['pages']==8 and report['documents']==5 and report['empty_pages']==1 and report['excluded_documents']==0


@pytest.mark.parametrize('tamper',['swap','drop','duplicate','wrong_file','reserialise','add_excluded'])
def test_verify_detects_tampering(tmp_path,tamper):
    data,records=build(tmp_path,exclude=urls(1)); hf=data/'hf'; m.merge(data,hf)
    tnn=hf/'tnn.jsonl'; flash=hf/'flash.jsonl'
    a=tnn.read_bytes().split(b'\n')[:-1]; b=flash.read_bytes().split(b'\n')[:-1]
    if tamper=='swap': a[0],a[1]=a[1],a[0]
    elif tamper=='drop': a.pop()
    elif tamper=='duplicate': a.append(a[0])
    elif tamper=='wrong_file': b.append(a.pop())
    elif tamper=='reserialise': a[0]=json.dumps(json.loads(a[0]),ensure_ascii=False).encode()
    elif tamper=='add_excluded': a+=source_lines(data,records,urls(1))
    tnn.write_bytes(b'\n'.join(a)+b'\n'); flash.write_bytes(b'\n'.join(b)+b'\n')
    with pytest.raises(ValueError): m.verify(data,hf)


def test_verify_notices_a_changed_exclusion_list(tmp_path):
    data,records=build(tmp_path); hf=data/'hf'; m.merge(data,hf)
    (hf/'EXCLUDE.txt').write_text(DOCS[4][0]+'\n')
    with pytest.raises(ValueError,match='EXCLUDE'): m.verify(data,hf)


def test_verify_checks_dataset_json_totals(tmp_path):
    data,records=build(tmp_path); m.merge(data,data/'hf')
    d=json.loads((data/'jsonl/dataset.json').read_text()); d['empty_pages']+=1
    (data/'jsonl/dataset.json').write_text(json.dumps(d))
    with pytest.raises(ValueError,match='dataset.json'): m.verify(data,data/'hf')


def test_provenance_records_counts_dates_and_no_text_changes(tmp_path):
    import yaml
    data,records=build(tmp_path,exclude=urls(4)); m.merge(data,data/'hf')
    p=yaml.safe_load((data/'hf/provenance.yaml').read_text())
    assert p['counts']==dict(documents=4,pages=7,characters=sum(len(t) for d in DOCS[:4] for t in d[3]),empty_pages=1)
    assert p['excluded']['documents']==1 and p['excluded']['list']=='EXCLUDE.txt'
    assert p['fetch']['first']=='2026-10-06T10:27:48Z' and p['fetch']['documents']==5 and p['fetch']['missing'][0]['url']==MISSING
    assert p['extraction']['new_ocr'] is False and p['extraction']['normalisation']=='none'
    assert p['series']['flash']['file']=='flash.jsonl' and p['series']['tnn']['documents']==3
