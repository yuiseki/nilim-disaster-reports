"""Sequential, bandwidth-limited NILIM disaster PDF collection; data remains local."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from urllib.parse import urlsplit, unquote


class CollectionStopped(Exception):
    pass


class Retryable(Exception):
    pass


def document_path(root, row):
    u = urlsplit(row['url'])
    report_id = str(row['report_id'])
    if not re.fullmatch(r'[0-9]{1,6}', report_id):
        raise ValueError('unexpected report ID')
    if u.scheme != 'https' or u.netloc != 'www.nilim.go.jp' or u.query or u.fragment:
        raise ValueError('unexpected source URL')
    folder = 'tnn' + report_id.zfill(4) + 'pdf'
    filename = 'ks' + report_id.zfill(4)
    pattern = r'/lab/bcg/siryou/tnn/' + folder + '/' + filename + r'(?:_[0-9]+|[0-9]{2})\.pdf'
    if not re.fullmatch(pattern, unquote(u.path)):
        raise ValueError('unexpected PDF path')
    return Path(root) / 'pdf' / Path(u.path).name



def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_records(path):
    if not path.exists():
        return {}
    lines = path.read_text().splitlines()
    records = {}
    for i, line in enumerate(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            if i == len(lines) - 1:
                break
            raise ValueError('manifest interior corruption')
        records[row['url']] = row
    return records


def repair_manifest(path):
    if not path.exists():
        return
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    if not lines:
        return
    try:
        json.loads(lines[-1])
    except json.JSONDecodeError:
        # Preserve the interrupted record before trimming it for future appends.
        backup = path.with_name(f'manifest-interrupted-{time.time_ns()}.txt')
        backup.write_bytes(lines[-1])
        with path.open('r+b') as f:
            f.truncate(len(raw) - len(lines[-1]))
    else:
        if not raw.endswith(b'\n'):
            with path.open('ab') as f:
                f.write(b'\n')


def fetch_one(root, row, records, runner=subprocess.run):
    target = document_path(root, row)
    previous = records.get(row['url'])
    if target.exists():
        if previous and previous.get('status') == 'complete' and target.stat().st_size == previous['bytes'] and sha256(target) == previous['sha256']:
            return dict(previous, status='skipped')
        raise CollectionStopped(f'unverified existing file: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix('.pdf.part')
    headers = target.with_suffix('.pdf.headers')
    url = row['url'].replace('http://', 'https://', 1)
    cmd = ['curl', '--silent', '--show-error', '--fail', '--location',
           '--proto', '=https', '--proto-redir', '=https',
           '--connect-timeout', '20', '--max-time', '1800',
           '--limit-rate', '512K', '--user-agent', 'nilim-disaster-reports-local-archive/1.0',
           '--dump-header', str(headers), '--output', str(part),
           '--write-out', '%{http_code}', url]
    result = runner(cmd, capture_output=True, text=True)
    try:
        status = int(result.stdout.strip())
    except ValueError:
        status = 0
    if status in (401, 403, 429):
        raise CollectionStopped(f'HTTP {status}; collection stopped, no automatic retry')
    if status in (404, 410):
        return dict(row, status='missing', http_status=status, timestamp=time.time())
    if result.returncode or status != 200:
        raise Retryable(f'curl={result.returncode}, HTTP={status}: {result.stderr[-200:]}')
    with part.open('rb') as f:
        if not f.read(5).startswith(b'%PDF'):
            raise Retryable('response was not a PDF')
    # curl checks transfer length too; retain an explicit check for auditability.
    header_text = headers.read_text(errors='replace')
    lengths = re.findall(r'^Content-Length:\s*(\d+)\s*$', header_text, re.I | re.M)
    size = part.stat().st_size
    if lengths and size != int(lengths[-1]):
        raise Retryable('Content-Length mismatch')
    record = dict(row, status='complete', bytes=size, sha256=sha256(part),
                  local_path=str(target.relative_to(root)), timestamp=time.time())
    with part.open('rb') as f:
        os.fsync(f.fileno())
    os.replace(part, target)
    return record


original_fetch_one = fetch_one


def write_status(root, state, total, records, detail=''):
    completed = [r for r in records.values() if r.get('status') == 'complete']
    obj = dict(state=state, total=total, complete=len(completed),
               missing=sum(r.get('status') == 'missing' for r in records.values()),
               bytes=sum(r['bytes'] for r in completed), detail=detail, updated=time.time())
    tmp = root / 'status.json.tmp'
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, root / 'status.json')


def run(root, rows, sleeper=time.sleep):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / 'manifest.jsonl'
    records = load_records(manifest)
    repair_manifest(manifest)
    write_status(root, 'running', len(rows), records)
    try:
        for row in rows:
            # Previously confirmed missing URLs are kept in the coverage report.
            if records.get(row['url'], {}).get('status') == 'missing':
                continue
            for attempt in range(4):
                try:
                    result = fetch_one(root, row, records)
                    break
                except Retryable as exc:
                    print(json.dumps(dict(event='retry', url=row['url'], attempt=attempt + 1, error=str(exc))), flush=True)
                    if attempt == 3:
                        raise CollectionStopped(f'four attempts failed: {row["url"]}') from exc
                    sleeper([30, 120, 300][attempt])
            if result['status'] == 'skipped':
                continue
            with manifest.open('a') as f:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
                f.flush()
                os.fsync(f.fileno())
            records[row['url']] = result
            write_status(root, 'running', len(rows), records, row['url'])
            print(json.dumps(dict(event=result['status'], url=row['url'], bytes=result.get('bytes'), complete=sum(r.get('status') == 'complete' for r in records.values())), ensure_ascii=False), flush=True)
            sleeper(3)
        state = 'finished_with_missing' if any(r.get('status') == 'missing' for r in records.values()) else 'finished'
        write_status(root, state, len(rows), records)
        print(json.dumps(dict(event=state, total=len(rows))), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        write_status(root, 'stopped', len(rows), records, str(exc))
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    with (args.root / 'fetch.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('another fetch is already running')
        with (args.root / 'catalog.tsv').open() as f:
            rows = list(csv.DictReader(f, delimiter='\t'))
        if len({r['url'] for r in rows}) != len(rows):
            raise SystemExit('duplicate catalog URLs')
        for row in rows:
            document_path(args.root, row)
        if args.limit is not None:
            if args.limit <= 0:
                raise SystemExit('--limit must be positive')
            rows = rows[:args.limit]
        def interrupted(signum, frame):
            raise KeyboardInterrupt('terminated')
        signal.signal(signal.SIGTERM, interrupted)
        run(args.root, rows)


if __name__ == '__main__':
    main()
