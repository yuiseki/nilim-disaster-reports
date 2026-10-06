import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

spec = importlib.util.spec_from_file_location('fetch', Path(__file__).parents[1] / 'src/fetch.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ROW = {'url': 'https://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn1320pdf/ks1320_01.pdf', 'report_id': 1320}

def test_path_keeps_series_and_blocks_unsafe_urls(tmp_path):
    assert m.document_path(tmp_path, ROW) == tmp_path / 'pdf/ks1320_01.pdf'
    for url in ['https://example.com/data/bull-gsj/a.pdf', 'https://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn1320pdf/../a.pdf', 'https://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn1320pdf/a.txt']:
        with pytest.raises(ValueError):
            m.document_path(tmp_path, dict(ROW, url=url))

def transport(tmp_path, status=200, body=b'%PDF-1.4\ntest', code=0):
    calls = []
    def fake(cmd, **kwargs):
        calls.append(cmd)
        Path(cmd[cmd.index('--output') + 1]).write_bytes(body)
        Path(cmd[cmd.index('--dump-header') + 1]).write_text(f'HTTP/1.1 {status}\r\nContent-Length: {len(body)}\r\n\r\n')
        return SimpleNamespace(returncode=code, stdout=str(status), stderr='')
    return fake, calls

def test_success_validates_and_records_sha256(tmp_path):
    fake, calls = transport(tmp_path)
    result = m.fetch_one(tmp_path, ROW, {}, runner=fake)
    assert result['status'] == 'complete'
    target = m.document_path(tmp_path, ROW)
    assert result['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert calls[0][calls[0].index('--limit-rate') + 1] == '512K'
    assert '--retry' not in calls[0]

def test_restart_skips_verified_file_without_network(tmp_path):
    fake, calls = transport(tmp_path)
    record = m.fetch_one(tmp_path, ROW, {}, runner=fake)
    assert m.fetch_one(tmp_path, ROW, {ROW['url']: record}, runner=fake)['status'] == 'skipped'
    assert len(calls) == 1

def test_corrupt_completed_file_is_not_silently_skipped(tmp_path):
    fake, _ = transport(tmp_path)
    record = m.fetch_one(tmp_path, ROW, {}, runner=fake)
    m.document_path(tmp_path, ROW).write_bytes(b'%PDF-different')
    with pytest.raises(m.CollectionStopped):
        m.fetch_one(tmp_path, ROW, {ROW['url']: record}, runner=fake)

@pytest.mark.parametrize('status', [403, 429])
def test_refusal_stops_without_publishing_file(tmp_path, status):
    fake, calls = transport(tmp_path, status=status, body=b'blocked', code=22)
    with pytest.raises(m.CollectionStopped):
        m.fetch_one(tmp_path, ROW, {}, runner=fake)
    assert not m.document_path(tmp_path, ROW).exists()
    assert len(calls) == 1

def test_html_200_is_rejected(tmp_path):
    fake, _ = transport(tmp_path, body=b'<html>error</html>')
    with pytest.raises(m.Retryable):
        m.fetch_one(tmp_path, ROW, {}, runner=fake)
    assert not m.document_path(tmp_path, ROW).exists()

def test_interrupted_transfer_keeps_partial_and_is_retryable(tmp_path):
    fake, _ = transport(tmp_path, body=b'%PDF-incomplete', code=18)
    with pytest.raises(m.Retryable):
        m.fetch_one(tmp_path, ROW, {}, runner=fake)
    target = m.document_path(tmp_path, ROW)
    assert not target.exists() and target.with_suffix('.pdf.part').exists()

def test_404_is_recorded_as_missing(tmp_path):
    fake, _ = transport(tmp_path, status=404, body=b'not found', code=22)
    assert m.fetch_one(tmp_path, ROW, {}, runner=fake)['status'] == 'missing'

def test_manifest_allows_partial_last_line_but_not_interior_corruption(tmp_path):
    f = tmp_path / 'manifest.jsonl'
    f.write_text(json.dumps(dict(ROW, status='complete')) + '\n{"url":')
    assert ROW['url'] in m.load_records(f)
    f.write_text('invalid\n' + json.dumps(ROW) + '\n')
    with pytest.raises(ValueError):
        m.load_records(f)

def test_run_waits_between_requests_and_marks_complete(tmp_path, monkeypatch):
    second = dict(ROW, url=ROW['url'].replace('_01.pdf', '_02.pdf'))
    fake, _ = transport(tmp_path)
    monkeypatch.setattr(m, 'fetch_one', lambda root, row, records: m.original_fetch_one(root, row, records, runner=fake))
    waits = []
    m.run(tmp_path, [ROW, second], sleeper=waits.append)
    state = json.loads((tmp_path / 'status.json').read_text())
    assert state['state'] == 'finished' and state['complete'] == 2
    assert waits and all(n >= 3 for n in waits)

def test_run_stops_after_bounded_retries(tmp_path, monkeypatch):
    calls=[]
    def fail(*args, **kwargs):
        calls.append(1)
        raise m.Retryable('temporary')
    monkeypatch.setattr(m, 'fetch_one', fail)
    with pytest.raises(m.CollectionStopped):
        m.run(tmp_path, [ROW], sleeper=lambda _: None)
    assert len(calls) == 4
    assert json.loads((tmp_path / 'status.json').read_text())['state'] == 'stopped'

def test_content_length_mismatch_is_rejected(tmp_path):
    fake, _ = transport(tmp_path)
    def mismatched(cmd, **kwargs):
        result = fake(cmd, **kwargs)
        Path(cmd[cmd.index('--dump-header') + 1]).write_text('HTTP/1.1 200\nContent-Length: 9999\n\n')
        return result
    with pytest.raises(m.Retryable):
        m.fetch_one(tmp_path, ROW, {}, runner=mismatched)
    assert not m.document_path(tmp_path, ROW).exists()

def test_interrupted_manifest_tail_is_preserved_and_future_records_readable(tmp_path):
    f = tmp_path / 'manifest.jsonl'
    first = dict(ROW, status='missing')
    f.write_text(json.dumps(first) + '\n{"url":')
    m.repair_manifest(f)
    second = dict(first, url=ROW['url'].replace('_01.pdf', '_02.pdf'))
    with f.open('a') as out:
        out.write(json.dumps(second) + '\n')
    assert len(m.load_records(f)) == 2
    assert next(tmp_path.glob('manifest-interrupted-*.txt')).read_text() == '{"url":'

def test_successful_retry_does_not_count_partial_as_complete(tmp_path, monkeypatch):
    fake, _ = transport(tmp_path)
    calls=[]
    def fetch(root, row, records):
        calls.append(1)
        if len(calls)==1:
            raise m.Retryable('interrupted')
        return m.original_fetch_one(root,row,records,runner=fake)
    monkeypatch.setattr(m,'fetch_one',fetch)
    waits=[]
    m.run(tmp_path,[ROW],sleeper=waits.append)
    assert waits == [30,3]
    assert len(m.load_records(tmp_path/'manifest.jsonl'))==1


def test_report_id_must_match_url(tmp_path):
    with pytest.raises(ValueError):
        m.document_path(tmp_path, dict(ROW, report_id=1151))

def test_whole_and_legacy_split_names_are_supported(tmp_path):
    for name in ['ks1320.pdf','ks1320_01a.pdf','ks132001.pdf']:
        url=ROW['url'].rsplit('/',1)[0]+'/'+name
        assert m.document_path(tmp_path,dict(ROW,url=url)).name==name

def test_flash_urls_are_scoped_and_collision_safe(tmp_path):
    row=dict(ROW,source_type='flash',report_id='flash-test',url='https://www.nilim.go.jp/lab/bbg/saigai/R6/noto.pdf')
    path=m.document_path(tmp_path,row)
    other=m.document_path(tmp_path,dict(row,url='https://www.nilim.go.jp/lab/bbg/saigai/R5/noto.pdf'))
    assert path!=other and path.parent==tmp_path/'pdf/flash'
    for bad in ['https://example.com/lab/bbg/saigai/R6/noto.pdf','https://www.nilim.go.jp/lab/bbg/saigai/%2e%2e/a.pdf']:
        with pytest.raises(ValueError): m.document_path(tmp_path,dict(row,url=bad))
