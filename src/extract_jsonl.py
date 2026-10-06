"""Local NILIM PDF text extraction, one UTF-8 JSON line per PDF page."""
import argparse
import csv
import fcntl
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from fetch import sha256, load_records, repair_manifest

VERSION='nilim-pages-jsonl-v1'


class ExtractionError(Exception):
    pass


def atomic_json(path,value):
    part=path.with_suffix(path.suffix+'.part')
    with part.open('w',encoding='utf-8') as f:
        f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n'); f.flush(); os.fsync(f.fileno())
    os.replace(part,path)


def split_pages(text,expected):
    pages=text.split('\f')
    if len(pages)>1 and not pages[-1].strip(): pages.pop()
    if expected<1 or len(pages)!=expected: raise ExtractionError(f'page mismatch: PDF={expected}, text={len(pages)}')
    return pages


@lru_cache(maxsize=1)
def backend_version():
    result=subprocess.run(['pdftotext','-v'],capture_output=True,text=True,check=True,timeout=20)
    return (result.stderr or result.stdout).splitlines()[0]


def extract_pages(path):
    try:
        info=subprocess.run(['pdfinfo',str(path)],capture_output=True,check=True,timeout=120,env=dict(os.environ,LC_ALL='C'))
        match=re.search(rb'^Pages:\s*(\d+)\s*$',info.stdout,re.M)
        if not match: raise ExtractionError('pdfinfo did not report pages')
        result=subprocess.run(['pdftotext','-enc','UTF-8','-layout',str(path),'-'],capture_output=True,check=True,timeout=600)
        return split_pages(result.stdout.decode('utf-8'),int(match[1])),backend_version()
    except (subprocess.SubprocessError,UnicodeError) as exc:
        raise ExtractionError(str(exc)) from exc


def extract_one(root,out,row,records,extractor=extract_pages):
    root=Path(root); out=Path(out); source=(root/row['local_path']).resolve()
    if not source.is_relative_to(root.resolve()): raise ValueError('source path escapes data root')
    if not source.is_file() or source.stat().st_size!=row['bytes'] or sha256(source)!=row['sha256']:
        raise ValueError('source size/SHA256 mismatch')
    doc_id=hashlib.sha256(row['url'].encode()).hexdigest(); target=out/'documents'/f'{doc_id}.jsonl'
    old=records.get(row['url'])
    if target.exists():
        if old and old.get('status')=='complete' and old.get('schema_version')==VERSION and old.get('source_sha256')==row['sha256'] and sha256(target)==old['output_sha256']:
            return dict(old,status='skipped')
        raise ValueError('unverified or corrupted existing JSONL')
    pages,version=extractor(source)
    if not pages: raise ExtractionError('PDF has no pages')
    values=[]
    for number,text in enumerate(pages,1):
        nonwhite=len(re.sub(r'\s','',text))
        values.append(dict(document_id=doc_id,source_type=row.get('source_type') or 'tnn',
            report_id=str(row['report_id']),report_title=row.get('report_title',''),event=row.get('event','要調査'),
            section=row.get('section',''),source_url=row['url'],index_url=row.get('index_url',''),
            source_pdf_path=row['local_path'],source_pdf_sha256=row['sha256'],source_pdf_bytes=row['bytes'],
            page_number=number,text=text,characters=len(text),non_whitespace_characters=nonwhite,
            has_text=nonwhite>0,needs_ocr_review=nonwhite==0,replacement_characters=text.count('\ufffd'),
            extraction_method='pdftotext-layout',extractor_version=version,
            license_policy_url=row.get('license_policy_url',''),rights_review=row.get('rights_review','要調査')))
    target.parent.mkdir(parents=True,exist_ok=True); part=target.with_suffix('.jsonl.part')
    with part.open('w',encoding='utf-8') as f:
        for value in values: f.write(json.dumps(value,ensure_ascii=False)+'\n')
        f.flush(); os.fsync(f.fileno())
    os.replace(part,target)
    return dict(url=row['url'],document_id=doc_id,source_type=row.get('source_type') or 'tnn',
        report_id=str(row['report_id']),status='complete',schema_version=VERSION,source_sha256=row['sha256'],
        output_path=str(target.relative_to(out)),output_sha256=sha256(target),output_bytes=target.stat().st_size,
        pages=len(values),characters=sum(v['characters'] for v in values),empty_pages=sum(not v['has_text'] for v in values),
        low_text_pages=sum(v['non_whitespace_characters']<20 for v in values),
        replacement_characters=sum(v['replacement_characters'] for v in values),extractor_version=version,timestamp=time.time())


def merge(out,records):
    out=Path(out); folder=out/'corpus'; folder.mkdir(parents=True,exist_ok=True)
    for record in records:
        source=(out/record['output_path']).resolve()
        if not source.is_relative_to(out.resolve()) or sha256(source)!=record['output_sha256']:
            raise ValueError('JSONL checksum mismatch before merge')
        if record['source_type'] not in ('tnn','flash'): raise ValueError('unexpected source type')
    files={}
    for kind in ('tnn','flash'):
        group=[r for r in records if r['source_type']==kind]
        if not group: continue
        target=folder/f'{kind}.jsonl'; part=target.with_suffix('.jsonl.part'); count=0
        with part.open('wb') as f:
            for record in group:
                page=0
                with (out/record['output_path']).open('rb') as source:
                    for line in source:
                        row=json.loads(line); page+=1
                        if row['source_url']!=record['url'] or row['source_pdf_sha256']!=record['source_sha256'] or row['page_number']!=page or row['source_type']!=kind:
                            raise ValueError('JSONL provenance/page mismatch')
                        f.write(line); count+=1
                if page!=record['pages']: raise ValueError('JSONL page count mismatch')
            f.flush(); os.fsync(f.fileno())
        os.replace(part,target)
        files[kind]=dict(path=str(target.relative_to(out)),documents=len(group),pages=count,bytes=target.stat().st_size,sha256=sha256(target))
    return dict(schema_version=VERSION,documents=len(records),pages=sum(r['pages'] for r in records),
        characters=sum(r['characters'] for r in records),empty_pages=sum(r['empty_pages'] for r in records),
        low_text_pages=sum(r['low_text_pages'] for r in records),replacement_characters=sum(r['replacement_characters'] for r in records),
        bytes=sum(r['output_bytes'] for r in records),files=files)


def run(root,out,rows,source_missing=None):
    root=Path(root); out=Path(out); out.mkdir(parents=True,exist_ok=True)
    manifest=out/'manifest.jsonl'; records=load_records(manifest); repair_manifest(manifest)
    current=[]; failures=[]; source_missing=source_missing or []
    def status(state,detail=''):
        atomic_json(out/'status.json',dict(state=state,total=len(rows)+len(source_missing),complete=len(current),
            missing=len(source_missing)+len(failures),bytes=sum(r['output_bytes'] for r in current),detail=detail,updated=time.time()))
    status('running')
    atomic_json(out/'source-missing.json',source_missing)
    try:
        for row in rows:
            try: record=extract_one(root,out,row,records)
            except ExtractionError as exc:
                failures.append(dict(url=row['url'],error=str(exc)))
                atomic_json(out/'extraction-errors.json',failures); status('running',str(exc)); continue
            if record['status']=='skipped': record=dict(record,status='complete')
            else:
                with manifest.open('a') as f:
                    f.write(json.dumps(record,ensure_ascii=False)+'\n'); f.flush(); os.fsync(f.fileno())
                records[row['url']]=record
            current.append(record); status('running',row['url'])
            print(json.dumps(dict(event='jsonl',complete=len(current),total=len(rows),url=row['url'],pages=record['pages'],empty_pages=record['empty_pages']),ensure_ascii=False),flush=True)
        atomic_json(out/'extraction-errors.json',failures); status('running','merging JSONL by source type')
        summary=merge(out,current)
        summary.update(source_total=len(rows)+len(source_missing),source_missing=source_missing,extraction_errors=failures)
        atomic_json(out/'dataset.json',summary)
        status('finished_with_missing' if source_missing or failures else 'finished')
        print(json.dumps(dict(event='finished',**summary),ensure_ascii=False),flush=True)
    except BaseException as exc:
        status('stopped',str(exc)); raise


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True); ap.add_argument('--limit',type=int)
    args=ap.parse_args()
    if args.limit is not None and args.limit<=0: ap.error('--limit must be positive')
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/'extract.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fetched=load_records(args.root/'manifest.jsonl'); rows=[]; missing=[]
        with (args.root/'catalog.tsv').open() as f:
            catalog=list(csv.DictReader(f,delimiter='\t'))
        if len({r['url'] for r in catalog})!=len(catalog): raise ValueError('duplicate source URLs')
        for meta in catalog:
            record=fetched.get(meta['url'])
            if record and record['status']=='complete': rows.append(dict(record,**meta))
            elif record and record['status']=='missing': missing.append(record)
            else: raise ValueError('source collection is not finished')
        if args.limit is not None: rows=rows[:args.limit]; missing=[]
        def stopped(*_): raise KeyboardInterrupt('terminated')
        signal.signal(signal.SIGTERM,stopped)
        run(args.root,args.out,rows,source_missing=missing)

if __name__=='__main__': main()
