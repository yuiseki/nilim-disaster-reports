"""Merge the per-PDF page JSONL into one file per source type for the Hugging Face text corpus.

Each output line is the source JSONL line copied byte for byte (never re-serialised).
Documents follow data/catalog.tsv order and pages keep their order inside each document.
PDFs listed in data/hf/EXCLUDE.txt (one source_url per line) are left out; every document
must have a row in data/hf/RIGHTS_REVIEW.tsv (written by src/rights_scan.py).

    python3 src/merge_jsonl.py merge   # writes data/hf/{tnn,flash}.jsonl, MANIFEST.json, provenance.yaml
    python3 src/merge_jsonl.py verify  # re-reads everything and checks order, identity, exclusions and counts
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

SERIES=('tnn','flash')
CLASSES=('a','b','c','d')
JSON_VERSION='nilim-pages-jsonl-v1'
MANIFEST_VERSION='nilim-disaster-reports-hf-v1'
REPO=Path(__file__).resolve().parents[1]
CATALOG=dict(date='2026-10-07',file='catalog/catalog-20261007.tsv',
             source_indexes=['https://www.nilim.go.jp/lab/bbg/saigai/TEC-FORCE.html',
                             'https://www.nilim.go.jp/lab/bbg/saigai/index.html',
                             'https://www.nilim.go.jp/lab/ucg/research/02.html'],
             scope='国総研資料 (Technical Note of NILIM) reports on disaster field surveys linked from the indexes, split PDFs '
                   'including covers, front matter and colophons (whole-report PDFs skipped when split PDFs exist), plus '
                   'every 建築災害速報/field-survey bulletin PDF on the disaster index page; reports 1320 and 1356 added by hand')
SERIES_INFO={'tnn':dict(title='国総研資料 (Technical Note of NILIM): disaster survey reports',
                        index='https://www.nilim.go.jp/lab/bbg/saigai/TEC-FORCE.html'),
             'flash':dict(title='災害調査速報 (quick field-survey reports and bulletins, mostly 建築災害速報)',
                          index='https://www.nilim.go.jp/lab/bbg/saigai/index.html')}


def output_name(series):
    return f'{series}.jsonl'


def atomic_write(path,text):
    path=Path(path); part=path.with_name(path.name+'.part')
    with part.open('w',encoding='utf-8') as f:
        f.write(text); f.flush(); os.fsync(f.fileno())
    os.replace(part,path)


def read_catalog(data):
    with (Path(data)/'catalog.tsv').open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f,delimiter='\t'))


def read_exclude(hf):
    """Return the source URLs in EXCLUDE.txt in file order (blank lines and # comments ignored)."""
    path=Path(hf)/'EXCLUDE.txt'
    if not path.exists(): raise ValueError('EXCLUDE.txt is missing (an empty file means nothing is excluded)')
    urls=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        if line in urls: raise ValueError(f'EXCLUDE.txt lists a URL twice: {line}')
        urls.append(line)
    return urls


def read_review(hf):
    """Return {source_url: row} from RIGHTS_REVIEW.tsv."""
    path=Path(hf)/'RIGHTS_REVIEW.tsv'
    if not path.exists(): raise ValueError('RIGHTS_REVIEW.tsv is missing; run src/rights_scan.py')
    with path.open(encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f,delimiter='\t',quoting=csv.QUOTE_NONE))
    out={}
    for row in rows:
        if row['class'] not in CLASSES: raise ValueError(f'RIGHTS_REVIEW.tsv has an unknown class {row["class"]!r}: {row["source_url"]}')
        if row['source_url'] in out: raise ValueError(f'RIGHTS_REVIEW.tsv lists a URL twice: {row["source_url"]}')
        out[row['source_url']]=row
    return out


def plan(data):
    """Validate the JSONL stage and return ({series: [manifest record, ...]} in catalog order, source_missing)."""
    data=Path(data); jroot=data/'jsonl'
    status=json.loads((jroot/'status.json').read_text())
    missing=json.loads((jroot/'source-missing.json').read_text())
    errors=json.loads((jroot/'extraction-errors.json').read_text())
    if errors: raise ValueError(f'JSONL stage has {len(errors)} extraction errors')
    if status.get('state') not in ('finished','finished_with_missing') or status.get('missing',0)!=len(missing) \
       or (status['state']=='finished')!=(not missing):
        raise ValueError(f'JSONL stage is not finished cleanly: {status.get("state")}, missing={status.get("missing")}')
    records={}
    for line in (jroot/'manifest.jsonl').read_text(encoding='utf-8').splitlines():
        r=json.loads(line)
        if r['url'] in records: raise ValueError(f'duplicate manifest entry: {r["url"]}')
        records[r['url']]=r
    catalog=read_catalog(data)
    urls=[row['url'] for row in catalog]
    missing_urls={r['url'] for r in missing}
    if len(set(urls))!=len(urls) or not missing_urls<=set(urls) or set(urls)-missing_urls!=set(records):
        raise ValueError('catalog and JSONL manifest do not list the same documents (apart from source-missing.json)')
    out={s:[] for s in SERIES}
    for row in catalog:
        if row['url'] in missing_urls: continue
        r=records[row['url']]
        if r.get('status')!='complete': raise ValueError(f'manifest entry is not complete: {r["url"]}')
        if r.get('schema_version')!=JSON_VERSION: raise ValueError(f'unexpected schema version: {r["url"]}')
        if r['source_type']!=row['source_type'] or r['source_type'] not in out or str(r['report_id'])!=str(row['report_id']):
            raise ValueError(f'source_type/report_id mismatch: {r["url"]}')
        out[r['source_type']].append(r)
    return out,missing


def split_excluded(groups,exclude,review):
    known={r['url'] for s in SERIES for r in groups[s]}
    for url in exclude:
        if url not in known: raise ValueError(f'EXCLUDE.txt lists a URL that is not an extracted document: {url}')
    if set(review)!=known: raise ValueError('RIGHTS_REVIEW.tsv does not list exactly the extracted documents')
    for url,row in review.items():
        if (row.get('excluded')=='yes')!=(url in exclude): raise ValueError(f'RIGHTS_REVIEW.tsv excluded column disagrees with EXCLUDE.txt: {url}')
    ex=set(exclude)
    keep={s:[r for r in groups[s] if r['url'] not in ex] for s in SERIES}
    drop={s:[r for r in groups[s] if r['url'] in ex] for s in SERIES}
    return keep,drop


def document_lines(jroot,record):
    """Return the raw lines (without the newline) of one document after checking it against the manifest."""
    path=(Path(jroot)/record['output_path']).resolve()
    if not path.is_relative_to(Path(jroot).resolve()): raise ValueError('document path escapes JSONL root')
    body=path.read_bytes()
    if len(body)!=record['output_bytes'] or hashlib.sha256(body).hexdigest()!=record['output_sha256']:
        raise ValueError(f'document size/sha256 differs from manifest: {record["url"]}')
    if not body.endswith(b'\n'): raise ValueError(f'document does not end with a newline: {record["url"]}')
    lines=body[:-1].split(b'\n')  # split on LF only; U+2028 etc. inside text stay in the line
    if len(lines)!=record['pages']: raise ValueError(f'page count differs from manifest: {record["url"]}')
    return lines


def check_page(line,record,number):
    v=json.loads(line)
    if v['source_url']!=record['url'] or v['source_type']!=record['source_type'] or v['page_number']!=number \
       or v['source_pdf_sha256']!=record['source_sha256'] or v['document_id']!=record['document_id'] \
       or v['report_id']!=str(record['report_id']):
        raise ValueError(f'page provenance/order mismatch: {record["url"]} page {number}')
    return v


class Stats:
    def __init__(self): self.pages=self.characters=self.empty=self.repl=self.documents=0
    def add(self,v): self.pages+=1; self.characters+=v['characters']; self.empty+=not v['has_text']; self.repl+=v['replacement_characters']
    def add_record(self,r):
        self.documents+=1; self.pages+=r['pages']; self.characters+=r['characters']; self.empty+=r['empty_pages']; self.repl+=r['replacement_characters']
    def series(self): return dict(documents=self.documents,pages=self.pages,characters=self.characters,
                                  empty_pages=self.empty,replacement_characters=self.repl)


def rights_summary(groups,review,exclude):
    ex=set(exclude); out={}
    for side in ('included','excluded'):
        out[side]={}
        for c in CLASSES:
            recs=[r for s in SERIES for r in groups[s] if review[r['url']]['class']==c and ((r['url'] in ex)==(side=='excluded'))]
            out[side][c]=dict(reports=len({(r['source_type'],str(r['report_id'])) for r in recs}),pdfs=len(recs),pages=sum(r['pages'] for r in recs))
    return out


def excluded_list(drop,review):
    return [dict(url=r['url'],source_type=r['source_type'],report_id=str(r['report_id']),pages=r['pages'],
                 characters=r['characters'],rights_class=review[r['url']]['class'],basis=review[r['url']]['basis'])
            for s in SERIES for r in drop[s]]


def merge(data,out):
    data=Path(data); out=Path(out); jroot=data/'jsonl'
    groups,missing=plan(data)
    exclude=read_exclude(out); review=read_review(out)
    keep,drop=split_excluded(groups,exclude,review)
    out.mkdir(parents=True,exist_ok=True)
    parts={s:out/(output_name(s)+'.part') for s in SERIES}
    files={}; series={}
    try:
        for s in SERIES:
            h=hashlib.sha256(); size=0; stats=Stats()
            with parts[s].open('wb') as f:
                for record in keep[s]:
                    for number,line in enumerate(document_lines(jroot,record),1):
                        v=check_page(line,record,number); stats.add(v)
                        f.write(line+b'\n'); h.update(line+b'\n'); size+=len(line)+1
                    stats.documents+=1
                for record in drop[s]: document_lines(jroot,record)  # excluded documents must still match the manifest
                f.flush(); os.fsync(f.fileno())
            files[output_name(s)]=dict(source_type=s,lines=stats.pages,documents=stats.documents,bytes=size,sha256=h.hexdigest())
            series[s]=stats.series()
    except BaseException:
        for p in parts.values(): p.unlink(missing_ok=True)
        raise
    for s in SERIES: os.replace(parts[s],out/output_name(s))
    totals={k:sum(x[k] for x in series.values()) for k in next(iter(series.values()))}
    ex=Stats()
    for s in SERIES:
        for r in drop[s]: ex.add_record(r)
    dataset=json.loads((jroot/'dataset.json').read_text())
    manifest=dict(schema_version=MANIFEST_VERSION,source_schema_version=JSON_VERSION,
        line_format='each line is the source per-PDF JSONL line, byte-identical; documents in catalog order, pages in PDF order',
        files=files,series=series,totals=totals,
        excluded=excluded_list(drop,review),excluded_totals=ex.series(),
        rights=rights_summary(groups,review,exclude),
        source_missing=[dict(url=r['url'],report_id=str(r.get('report_id','')),section=r.get('section',''),
                             http_status=r.get('http_status')) for r in missing],
        source_dataset=dict(documents=dataset['documents'],pages=dataset['pages'],characters=dataset['characters'],
                            empty_pages=dataset['empty_pages'],bytes=dataset['bytes']))
    atomic_write(out/'MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    write_provenance(data,out,keep,drop,missing,manifest)
    return manifest


def iso(ts):
    return dt.datetime.fromtimestamp(ts,dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')


def write_provenance(data,out,keep,drop,missing,manifest):
    import yaml
    data=Path(data)
    fetched=[json.loads(x) for x in (data/'manifest.jsonl').read_text(encoding='utf-8').splitlines()]
    done=[r for r in fetched if r.get('status')=='complete']
    records=[r for s in SERIES for r in keep[s]+drop[s]]
    versions={}
    for r in records: versions[r['extractor_version']]=versions.get(r['extractor_version'],0)+1
    doc=dict(
        dataset='yuiseki/nilim-disaster-reports',
        publisher_of_source='National Institute for Land and Infrastructure Management (NILIM), MLIT, Japan / 国土交通省 国土技術政策総合研究所',
        series={s:dict(title=SERIES_INFO[s]['title'],index=SERIES_INFO[s]['index'],documents=manifest['series'][s]['documents'],
                       pages=manifest['series'][s]['pages'],file=output_name(s)) for s in SERIES},
        catalog=dict(date=CATALOG['date'],file=CATALOG['file'],source_indexes=CATALOG['source_indexes'],
                     urls=len(read_catalog(data)),catalog_sha256=hashlib.sha256((data/'catalog.tsv').read_bytes()).hexdigest(),
                     scope=CATALOG['scope']),
        fetch=dict(documents=len(done),bytes=sum(r['bytes'] for r in done),
                   first=iso(min(r['timestamp'] for r in done)),last=iso(max(r['timestamp'] for r in done)),
                   missing=[dict(url=r['url'],http_status=r.get('http_status'),report_id=str(r.get('report_id','')),
                                 section=r.get('section','')) for r in missing],
                   method='one sequential HTTP GET per PDF URL listed in the catalog (512 KiB/s, 3 s between requests); size and SHA-256 recorded'),
        extraction=dict(tool='pdftotext -enc UTF-8 -layout (Poppler)',method='text layer of each PDF, split on form feed into pages; page count checked against pdfinfo',
                        new_ocr=False,normalisation='none',extractor_versions=versions,schema_version=JSON_VERSION,
                        jsonl_written_first=iso(min(r['timestamp'] for r in records)),jsonl_written_last=iso(max(r['timestamp'] for r in records))),
        counts=dict(documents=manifest['totals']['documents'],pages=manifest['totals']['pages'],
                    characters=manifest['totals']['characters'],empty_pages=manifest['totals']['empty_pages']),
        excluded=dict(list='EXCLUDE.txt',documents=manifest['excluded_totals']['documents'],pages=manifest['excluded_totals']['pages'],
                      reports=sorted({f'{x["source_type"]} {x["report_id"]}' for x in manifest['excluded']}),
                      reason='see RIGHTS_REVIEW.tsv and the card; the excluded PDFs carry a notice that forbids reproduction without written permission'),
        rights_review=dict(file='RIGHTS_REVIEW.tsv',classes=dict(a='no other rights notice found',b='figures/photos credited to others only',
                           c='rights notice or reprint restriction for the whole report, or joint authorship with another organisation',d='unclear'),
                           summary=manifest['rights']),
        changes=['none to the text or to any field: every line is the per-PDF JSONL line copied byte for byte',
                 'the per-PDF JSONL files were concatenated into one file per source type, documents in catalog order, pages in PDF order',
                 'the PDFs listed in EXCLUDE.txt were left out',
                 'the PDFs themselves are not included; source_url names the official PDF and source_pdf_sha256 identifies the copy that was read'],
        licence='other (NILIM site terms: PDL1.0 for NILIM content unless a rights notice says otherwise; co-published reports also carry rights notices of other institutes); see LICENSE')
    atomic_write(Path(out)/'provenance.yaml',yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=1000))


def verify(data,out):
    """Check that every non-excluded source line appears exactly once, in order, byte-identical, in its file."""
    data=Path(data); out=Path(out); jroot=data/'jsonl'
    groups,missing=plan(data)
    exclude=read_exclude(out); review=read_review(out)
    keep,drop=split_excluded(groups,exclude,review)
    manifest=json.loads((out/'MANIFEST.json').read_text())
    if [x['url'] for x in manifest['excluded']]!=[r['url'] for s in SERIES for r in drop[s]]:
        raise ValueError('MANIFEST.json was built with a different EXCLUDE.txt; run merge again')
    if manifest['rights']!=rights_summary(groups,review,exclude): raise ValueError('MANIFEST.json rights summary differs from RIGHTS_REVIEW.tsv')
    totals=Stats(); excluded_urls=set(exclude)
    for s in SERIES:
        path=out/output_name(s); body=path.read_bytes()
        info=manifest['files'][output_name(s)]
        if len(body)!=info['bytes'] or hashlib.sha256(body).hexdigest()!=info['sha256']:
            raise ValueError(f'{path.name} differs from MANIFEST.json')
        if not body.endswith(b'\n'): raise ValueError(f'{path.name} does not end with a newline')
        merged=body[:-1].split(b'\n'); i=0; stats=Stats()
        for record in keep[s]:
            for number,line in enumerate(document_lines(jroot,record),1):
                if i>=len(merged) or merged[i]!=line:
                    raise ValueError(f'{path.name} line {i+1} is not the source line for {record["url"]} page {number}')
                v=check_page(merged[i],record,number); stats.add(v); totals.add(v); i+=1
            stats.documents+=1; totals.documents+=1
        if i!=len(merged): raise ValueError(f'{path.name} has {len(merged)-i} extra lines')
        for line in merged:  # redundant with the exact match above, kept as an explicit check
            if json.loads(line)['source_url'] in excluded_urls: raise ValueError(f'{path.name} contains an excluded document')
        if info['lines']!=stats.pages or info['documents']!=stats.documents or manifest['series'][s]!=stats.series():
            raise ValueError(f'MANIFEST.json counts differ for {s}')
    ex=Stats()
    for s in SERIES:
        for r in drop[s]: document_lines(jroot,r); ex.add_record(r)
    if manifest['excluded_totals']!=ex.series(): raise ValueError('MANIFEST.json excluded counts differ')
    dataset=json.loads((jroot/'dataset.json').read_text())
    got=dict(documents=totals.documents+ex.documents,pages=totals.pages+ex.pages,characters=totals.characters+ex.characters,
             empty_pages=totals.empty+ex.empty)
    for k,v in got.items():
        if dataset[k]!=v: raise ValueError(f'{k} differs from data/jsonl/dataset.json: {v} != {dataset[k]}')
    return dict(documents=totals.documents,pages=totals.pages,characters=totals.characters,empty_pages=totals.empty,
                excluded_documents=ex.documents,excluded_pages=ex.pages,source_missing=len(missing))


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command',choices=('merge','verify'))
    ap.add_argument('--data',type=Path,default=REPO/'data')
    ap.add_argument('--out',type=Path,default=REPO/'data/hf')
    args=ap.parse_args()
    if args.command=='merge':
        result=merge(args.data,args.out)
        print(json.dumps(dict(files=result['files'],series=result['series'],excluded_totals=result['excluded_totals']),ensure_ascii=False,indent=2))
    else:
        print(json.dumps(dict(verified=True,**verify(args.data,args.out)),ensure_ascii=False))


if __name__=='__main__': main()
