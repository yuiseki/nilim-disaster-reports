"""Publish data/hf to the Hugging Face dataset repo yuiseki/nilim-disaster-reports.

Dry run by default: checks everything and lists the files that would be uploaded.

    python3 src/publish.py           # dry run
    python3 src/publish.py --push    # create the public dataset repo and upload

Only README.md, LICENSE, provenance.yaml, MANIFEST.json, RIGHTS_REVIEW.tsv, EXCLUDE.txt and *.jsonl
directly under data/hf are uploaded. Any other file, any subdirectory, any PDF, a card whose
configs do not name exactly the *.jsonl files, any included class c or d report, a card licence
other than cc-by-4.0, a card that does not name every excluded 国総研資料 report, or a file that
differs from MANIFEST.json stops the run.
"""
import argparse
import hashlib
import json
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
REPO_ID='yuiseki/nilim-disaster-reports'
REQUIRED=('README.md','LICENSE','provenance.yaml','MANIFEST.json','RIGHTS_REVIEW.tsv','EXCLUDE.txt')


class PublishError(Exception):
    pass


def card_text(readme):
    return Path(readme).read_text(encoding='utf-8')


def card_metadata(readme):
    import yaml
    text=card_text(readme)
    if not text.startswith('---\n'): raise PublishError('README.md has no YAML metadata')
    end=text.find('\n---\n',4)
    if end<0: raise PublishError('README.md YAML metadata is not closed')
    return yaml.safe_load(text[4:end]) or {}


def config_files(meta):
    configs=meta.get('configs') or []
    if not configs: raise PublishError('card has no configs')
    names=set()
    for config in configs:
        for entry in config.get('data_files') or []:
            paths=entry['path'] if isinstance(entry,dict) else entry
            names.update([paths] if isinstance(paths,str) else paths)
    return names


def check_licence(meta,manifest):
    """Only NILIM's own works (rights classes a and b) are published, under cc-by-4.0.

    Any included class c or d report stops the run, and the card licence must be cc-by-4.0.
    """
    included=manifest.get('rights',{}).get('included')
    if not included: raise PublishError('MANIFEST.json has no rights summary')
    if any(included[c]['pdfs'] or included[c]['reports'] for c in ('c','d')):
        raise PublishError('class c/d reports are included; only classes a and b may be published (see RIGHTS_REVIEW.tsv)')
    if meta.get('license')!='cc-by-4.0':
        raise PublishError(f'card licence must be cc-by-4.0, not {meta.get("license")!r}')


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
    return h.hexdigest()


def upload_plan(hf,check_sha=False):
    """Return [(path, bytes)] sorted by name, or raise PublishError."""
    hf=Path(hf)
    entries=sorted(hf.iterdir(),key=lambda p:p.name)
    plan=[]
    for p in entries:
        if not p.is_file() or p.is_symlink(): raise PublishError(f'not a regular file: {p.name}')
        if p.name.lower().endswith('.pdf'): raise PublishError(f'refusing to upload a PDF: {p.name}')
        with p.open('rb') as f:
            if f.read(5)==b'%PDF-': raise PublishError(f'refusing to upload PDF content: {p.name}')
        if p.name not in REQUIRED and not p.name.endswith('.jsonl'):
            raise PublishError(f'file outside the upload allowlist: {p.name}')
        plan.append((p,p.stat().st_size))
    names={p.name for p,_ in plan}
    for name in REQUIRED:
        if name not in names: raise PublishError(f'missing {name}')
    jsonl={n for n in names if n.endswith('.jsonl')}
    meta=card_metadata(hf/'README.md')
    if config_files(meta)!=jsonl:
        raise PublishError(f'card configs {sorted(config_files(meta))} do not match files {sorted(jsonl)}')
    manifest=json.loads((hf/'MANIFEST.json').read_text())
    if set(manifest.get('files',{}))!=jsonl: raise PublishError('MANIFEST.json does not list exactly the *.jsonl files')
    check_licence(meta,manifest)
    text=card_text(hf/'README.md')
    for x in manifest.get('excluded',[]):  # bulletins are named in EXCLUDE.txt, reports in the card
        if x['source_type']=='tnn' and x['report_id'] not in text:
            raise PublishError(f'card does not name the excluded report {x["report_id"]}')
    for p,size in plan:
        if p.name in jsonl:
            info=manifest['files'][p.name]
            if size!=info['bytes']: raise PublishError(f'{p.name} size differs from MANIFEST.json')
            if check_sha and sha256(p)!=info['sha256']: raise PublishError(f'{p.name} sha256 differs from MANIFEST.json')
    return plan


def push(hf,repo_id=REPO_ID,api=None):
    from huggingface_hub import CommitOperationAdd
    plan=upload_plan(hf,check_sha=True)
    if api is None:
        from huggingface_hub import HfApi
        api=HfApi()
    api.create_repo(repo_id=repo_id,repo_type='dataset',private=False,exist_ok=True)
    ops=[CommitOperationAdd(path_in_repo=p.name,path_or_fileobj=str(p)) for p,_ in plan]
    api.create_commit(repo_id=repo_id,repo_type='dataset',operations=ops,
        commit_message='Add NILIM disaster survey report page text (tnn reports, flash bulletins)')
    return plan


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--hf',type=Path,default=REPO/'data/hf')
    ap.add_argument('--data',type=Path,default=REPO/'data')
    ap.add_argument('--repo-id',default=REPO_ID)
    ap.add_argument('--push',action='store_true',help='actually create the repo and upload')
    args=ap.parse_args()
    import importlib.util
    import sys
    sys.path.insert(0,str(REPO/'src'))
    spec=importlib.util.spec_from_file_location('merge_jsonl',REPO/'src/merge_jsonl.py')
    merge=importlib.util.module_from_spec(spec); spec.loader.exec_module(merge)
    counts=merge.verify(args.data,args.hf)  # every included source line once, in order, byte-identical
    plan=upload_plan(args.hf,check_sha=True)
    print(f'verified: {json.dumps(counts)}')
    print(f'{"PUSH" if args.push else "DRY RUN"}: https://huggingface.co/datasets/{args.repo_id} (public)')
    for p,size in plan: print(f'{size:>12,}  {p.name}')
    print(f'{sum(s for _,s in plan):>12,}  total, {len(plan)} files')
    if args.push:
        push(args.hf,args.repo_id); print('uploaded')
    else:
        print('nothing uploaded; rerun with --push to publish')


if __name__=='__main__': main()
