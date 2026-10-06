import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('catalog',Path(__file__).parents[1]/'src/catalog.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
BASE='https://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn0438.htm'
def test_reports_are_normalized_deduplicated_and_externals_excluded():
 html='<a href="http://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn0438.htm">能登地震</a><a href="'+BASE+'">same</a><a href="https://example.com/tnn0438.htm">external</a>'
 assert m.report_links(html,BASE)==[(438,BASE,'能登地震')]
def test_split_prefers_chapters_to_full_and_keeps_title():
 html='<a href="tnn0438pdf/ks0438.pdf">全　文</a><a href="tnn0438pdf/ks0438_1.pdf">地形・地質</a><a href="https://example.com/x.pdf">other</a>'
 rows=m.report_pdfs(html,BASE,438,'能登地震')
 assert len(rows)==1 and rows[0]['section']=='地形・地質' and rows[0]['url'].endswith('_1.pdf')
def test_whole_only_report_is_not_lost():
 rows=m.report_pdfs('<a href="tnn0438pdf/ks0438.pdf">PDF</a>',BASE,438,'能登')
 assert len(rows)==1
def test_flash_reports_only_use_official_disaster_path():
 html='<a href="R6/noto.pdf">能登速報</a><a href="https://kenken.go.jp/a.pdf">共同外部</a><a href="/other/a.pdf">other</a>'
 rows=m.flash_pdfs(html,'https://www.nilim.go.jp/lab/bbg/saigai/index.html')
 assert len(rows)==1 and rows[0]['source_type']=='flash'

def test_legacy_cp932_title_survives_decoding():
    html='<a href="tnn0438pdf/ks043801.pdf">新潟の現地調査</a>'.encode('cp932')
    assert m.report_pdfs(html,BASE,438,'能登')[0]['section']=='新潟の現地調査'
