"""Build a fixed PDF catalog from explicit official disaster indexes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup

POLICY='https://www.nilim.go.jp/aboutlink.htm'

def normalize(url):
    u=urlsplit(url)
    if u.netloc!='www.nilim.go.jp' or u.scheme not in ('http','https') or u.query or u.fragment:
        return None
    return urlunsplit(('https',u.netloc,u.path,'',''))


def soup_html(html):
    if isinstance(html, bytes):
        try: html=html.decode('utf-8')
        except UnicodeDecodeError: html=html.decode('cp932')
    return BeautifulSoup(html,'html.parser')


def report_links(html,base):
    found={}
    for a in soup_html(html).find_all('a',href=True):
        url=normalize(urljoin(base,a['href']))
        if not url: continue
        match=re.fullmatch(r'/lab/bcg/siryou/tnn/tnn(\d+)\.htm',urlsplit(url).path)
        if match:
            rid=int(match[1]); found.setdefault(rid,(rid,url,a.get_text(' ',strip=True)))
    return list(found.values())


def row(rid,title,section,url,index,source_type='tnn'):
    return dict(report_id=rid,report_title=title,event='要調査',section=section,url=url,index_url=index,
                license_policy_url=POLICY,rights_review='原則PDL1.0、共同著作・第三者素材・個別条件は要調査',
                source_type=source_type,discovery_url=index)


def report_pdfs(html,base,rid,title):
    soup=soup_html(html)
    # Use the title on the actual report page, rather than search result text.
    for tr in soup.find_all('tr'):
        cells=tr.find_all(['td','th'],recursive=False)
        if len(cells)>1 and '資料名' in re.sub(r'\s','',cells[0].get_text()):
            title=cells[1].get_text(' ',strip=True); break
    links={}
    for a in soup.find_all('a',href=True):
        url=normalize(urljoin(base,a['href']))
        if not url or not url.lower().endswith('.pdf'): continue
        section=a.get_text(' ',strip=True)
        if url in links:
            if section and section not in links[url]['section']: links[url]['section']+=' / '+section
        else: links[url]=row(rid,title,section,url,base)
    # Whole copies may have numbered filenames too; inspect their labels.
    split=[r for r in links.values() if '全文' not in re.sub(r'\s','',r['section']) and
           Path(urlsplit(r['url']).path).name!=f'ks{rid:04}.pdf']
    return split if split else list(links.values())[:1]


def flash_pdfs(html,base):
    links={}
    for a in soup_html(html).find_all('a',href=True):
        url=normalize(urljoin(base,a['href']))
        if not url or not urlsplit(url).path.startswith('/lab/bbg/saigai/') or not url.lower().endswith('.pdf'): continue
        title=a.get_text(' ',strip=True)
        links.setdefault(url,row('flash-'+hashlib.sha256(url.encode()).hexdigest()[:16],title,title,url,base,'flash'))
    return list(links.values())


def build(repo):
    root=repo/'data'; indices=root/'indices'; indices.mkdir(parents=True,exist_ok=True)
    fetched={}
    def get(url):
        if url in fetched: return fetched[url]
        data=urlopen(Request(url,headers={'User-Agent':'nilim-disaster-reports-local-archive/1.0'}),timeout=45).read()
        (indices/('index-'+hashlib.sha256(url.encode()).hexdigest()[:16]+'.html')).write_bytes(data)
        fetched[url]=data
        print(json.dumps(dict(event='index',url=url,bytes=len(data))),flush=True)
        time.sleep(3)
        return data
    main='https://www.nilim.go.jp/lab/bbg/saigai/TEC-FORCE.html'
    flash='https://www.nilim.go.jp/lab/bbg/saigai/index.html'
    bridge='https://www.nilim.go.jp/lab/ucg/research/02.html'
    reports={rid:(rid,url,title) for rid,url,title in report_links(get(main),main)}
    # Additional observed field-survey reports; exclude unrelated analytical studies.
    for rid,url,title in report_links(get(bridge),bridge):
        if '災害調査' in title or '被災橋梁等調査報告' in title: reports.setdefault(rid,(rid,url,title))
    for rid in [1320,1356,758,1151]:
        reports.setdefault(rid,(rid,f'https://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn{rid:04}.htm',''))
    prior=json.loads((root/'catalog.json').read_text())
    allrows={r['url']:dict(r,source_type='tnn',discovery_url=r['index_url']) for r in prior}
    rejected=[]
    from fetch import document_path
    for rid,url,title in sorted(reports.values()):
        for r in report_pdfs(get(url),url,rid,title):
            r['discovery_url']=main if rid not in [1356,1320] else url
            try: document_path(root,r)
            except ValueError as exc:
                rejected.append(dict(r,reason=str(exc))); continue
            allrows.setdefault(r['url'],r)
    for r in flash_pdfs(get(flash),flash):
        try: document_path(root,r)
        except ValueError as exc:
            rejected.append(dict(r,reason=str(exc))); continue
        allrows.setdefault(r['url'],r)
    rows=list(allrows.values())
    fields=list(rows[0])
    stamp=time.strftime('%Y%m%d')
    snapshot=repo/'catalog'/f'catalog-{stamp}.tsv'
    assert not snapshot.exists(), 'catalog snapshot exists; preserve it'
    for output in [snapshot,root/'catalog.tsv.new']:
        with output.open('w') as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n'); w.writeheader(); w.writerows(rows)
    (root/'catalog.tsv.new').replace(root/'catalog.tsv')
    (root/f'catalog-expanded-{stamp}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    summary=dict(total=len(rows),prior=len(prior),added=len(rows)-len(prior),tnn_reports=len({str(r['report_id']) for r in rows if r['source_type']=='tnn'}),flash=sum(r['source_type']=='flash' for r in rows),rejected=rejected,sources=[main,flash,bridge])
    (repo/'catalog'/f'summary-{stamp}.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--repo',type=Path,required=True)
    build(ap.parse_args().repo)
