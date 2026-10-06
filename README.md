# nilim-disaster-reports

国総研の災害現地調査報告のローカル収集標本。2026-10-06開始、2026-10-07に拡張。

データ本体は `data/` に置きGit対象外。能登地震・2020年7月豪雨・2012年九州北部豪雨から3章、26,957,091バイト、90ページを取得。
`data/catalog.json` は3報告の分割URL49件（前付け等を含む）。全文PDFとの重複を避ける。
`data/sample-manifest.json` に出典・SHA256・サイズ・ページ数・抽出文字数を保存。
`data/pdf/` 原本、`data/text/` pdftotext抽出、`data/indices/` 索引・共通規約。

逐次1接続、512KiB/s、要求間3秒で取得。systemdユーザーサービス `nilim-disaster-reports-download.service` で49件を順次取得中。取得済み3標本はSHA256検証後に再利用。2026-10-07から35冊の国総研資料と109件の建築災害速報、計630 PDFを対象。旧49件の完了分は再利用。国総研の災害資料全体の網羅は未確認。
共通規約は原則PDL1.0。共同著作・第三者の図表写真の確認結果は下記「Hugging Face公開（本文のみ）」と `data/hf/RIGHTS_REVIEW.tsv`。HuggingFace未公開（ドライランのみ）。
詳細カード: /Workspaces/repos/__yuiseki/_research_ai/YuisekinText/docs/datasets/nilim-disaster-reports.md

## 運用

Python標準ライブラリとcurlを使用（HF公開用の結合・公開スクリプトはPyYAML、公開時のみhuggingface_hub）。検証: `python3 -m pytest -q tests`（83件）。
進捗: `cat data/status.json`、ログ: `tail -n 10 data/download.log`。
停止: `systemctl --user stop nilim-disaster-reports-download`。
再開は下記の起動スクリプトを実行。ロックで二重起動を防ぎ、サイズ・SHA256が一致する完了ファイルをスキップ。
401/403/429で停止。通信失敗等は30/120/300秒待機し最大4試行。404/410は欠落として記録。
不明な既存PDFは上書きせず停止。中断したpartは先頭から再取得。
Nice=15、I/O idle、CPUQuota=25%、MemoryMax=256M。再起動・完全ログアウト後の自動再開は設定していない。
権利確認・本文抽出・HF公開はこのジョブの対象外。

## 対象拡張（2026-10-07）

固定目録 `catalog/catalog-20261007.tsv`。総630件（追加581件）、35冊の国総研資料から521 PDF、建築災害速報109 PDF。
主な災害・事故一覧、建築災害報告一覧、構造・基礎研究室の被災調査報告を確認。
https://www.nilim.go.jp/lab/bbg/saigai/TEC-FORCE.html
https://www.nilim.go.jp/lab/bbg/saigai/index.html
https://www.nilim.go.jp/lab/ucg/research/02.html
資料1320と1356も加えた。要約・図表・付録・表紙を含む。速報の改訂版等の内容重複は未調査。
全文PDFと分割PDFの両方がある場合、全文というラベルのリンクも除外。URL重複は統合、索引に別の章名で同じURLがある場合は両方の名称を保持。
外部機関だけで公開するPDFは自動取得対象外。主要災害の国総研研究報告（ys系列）・国外災害報告は今後の調査対象。
旧HTMLはCP932、現在のHTMLはUTF-8。保存した索引HTMLもdata/indicesに保持。
共通規約の適用範囲・共同著作・第三者素材は要調査。今回の追加収集もローカル保存のみ。
再収集時は `src/catalog.py --repo <repo>`。固定目録の同日上書きは防ぐ。現在の目録で取得再開する場合は `sh start.sh`。
30分監視は `/Workspaces/ops/data-download-monitor/`。停止・ブロック・進捗停止・完了を通知する。

## JSONL化

取得済み629 PDFをページ別JSONLへ変換する処理を追加。原本SHA256・出典・報告名・資料番号・章名を保持し、資料と速報を2本へ結合する。手順と保存先は [docs/JSONL.md](docs/JSONL.md)。

2026-10-07、629 PDFのJSONL化完了。14,125ページ・約44.6MiB、抽出エラー0件。結合済みJSONLは `data/jsonl/corpus/tnn.jsonl` と `data/jsonl/corpus/flash.jsonl`。

## Hugging Face公開（本文のみ）

2026-10-07、`yuiseki/nilim-disaster-reports`（HF）と `yuiseki/nilim-disaster-reports`（GitHub）として公開する準備を整えた。アップロード・pushはしていない（ドライランのみ）。

判断：

- 公開するのは抽出テキストだけ。PDF（629件・約3.6GiB）は公開せず手元に残す。各行の `source_url` と `source_pdf_sha256` で原本の入手と照合ができる。
- 公開するのは国総研が単独で出し、他者の権利表示がない報告（権利分類 a・b）だけ。オーナーの判断（2026-10-07）。土研・建研・港空研・海上・港湾・航空技術研究所・大学・学会・住宅局などとの共同刊行・共著・共同調査の報告（c）と、判断できない報告（d）はすべて除外する。
- ライセンスは `cc-by-4.0`。収録分は国総研のコンテンツだけで、国総研の規約（https://www.nilim.go.jp/aboutlink.htm）では他の権利表記がない限りPDL1.0、PDL1.0はCC BY 4.0と互換。規約の原文・取得日・SHA256と出典の書き方は `data/hf/LICENSE`。b の報告に残る図表写真のクレジット行は本文の一部として残し、画像そのものは含まない。
- 独自のParquetは作らない。HFがJSONLから自動でParquetに変換する。
- `source_type` 別に2ファイルへ結合する。`tnn.jsonl`（国総研資料）と `flash.jsonl`（災害調査速報）。各行は元のページJSONLの行をバイト単位でそのまま写す。文書は `data/catalog.tsv` の順、ページはPDF内の順。
- カードは英語。冒頭とLicence節に、a・bだけを公開したこと、除外した報告の相手機関と件数を書いた。

権利確認（rights scan）：

- 全629 PDFのページ本文から、著作権表示・転載禁止・共同著作・図表写真のクレジット・測量法や地理院地図の表示を探し、全報告の表紙・前付け・執筆者一覧・奥付を読んで、報告ごとに a（他の権利表示なし）・b（図表写真のクレジットのみ）・c（報告全体への権利表示・転載制限、または他機関との共同著作・共同刊行・共同調査）・d（不明）に分類した。
- 判断は `src/rights_scan.py` の `TNN`・`FLASH` に根拠の引用つきで書く。`python3 src/rights_scan.py` が `data/hf/RIGHTS_REVIEW.tsv`（1 PDF 1行）と `data/hf/EXCLUDE.txt` を作る。`EXCLUDE.txt` は分類から生成し、c・d の報告の全PDFを、報告ごとの理由（分類・相手機関・根拠・引用）つきで並べる。手で編集しない。公開する分類は `PUBLISH_CLASSES`。
- 本文に「All rights reserved」と文書承認なしの転載・複製の禁止がある4報告（798 港空研共同、868・875 土研共同、1042 海上・港湾・航空技術研究所共同）は、`EXCLUDE.txt` で `ALL RIGHTS RESERVED` と明記している。
- 報告680は著者4人のうち1人が港空研の研究員、速報 h21mikawa は港空研の研究員が調査者に入っているため c とした。

手順（リポジトリルートで実行）：

```sh
python3 -m pytest -q tests
python3 src/rights_scan.py          # data/hf/RIGHTS_REVIEW.tsv と EXCLUDE.txt
python3 src/merge_jsonl.py merge    # data/hf/{tnn,flash}.jsonl, MANIFEST.json, provenance.yaml
python3 src/merge_jsonl.py verify   # 除外以外の全ソース行が一度だけ・順序どおり・バイト一致で入り、除外行がなく、件数がdataset.jsonと一致
python3 src/publish.py              # ドライラン：検証とアップロード対象の一覧
python3 src/publish.py --push       # 公開（public）。実行はまだしていない
```

`merge` はJSONL段階の欠落が `source-missing.json` の1件（資料728の奥付、404）以外にある場合、抽出エラーがある場合、manifestに未完了の行がある場合、文書のSHA256がmanifestと違う場合、目録とmanifestの文書が食い違う場合、`EXCLUDE.txt` に未知・重複のURLがある場合、`RIGHTS_REVIEW.tsv` が全文書を覆わないか除外列が `EXCLUDE.txt` と食い違う場合は何も書かずに止まる。出力は `.part` に書いてから置き換える。
`MANIFEST.json` と `provenance.yaml` は `merge` が毎回作り直す。`README.md`（HFのデータセットカード）と `LICENSE` は手書きで、件数や除外を変えたらカードも直す（テストが `MANIFEST.json` の数値・権利分類の件数・相手機関名・規約の引用とカードの一致を確認する）。
`publish.py` は `data/hf` 直下の `README.md`・`LICENSE`・`provenance.yaml`・`MANIFEST.json`・`RIGHTS_REVIEW.tsv`・`EXCLUDE.txt`・`*.jsonl` だけを送る。それ以外のファイルやサブディレクトリ、PDF（拡張子または中身）、カードのconfigsとファイルの不一致、c・d の報告が1件でも収録されている場合、カードのライセンスが `cc-by-4.0` でない場合、除外した国総研資料をカードが名指ししない場合、`MANIFEST.json` とのサイズ・SHA256の不一致があれば止まる。
Git管理するのは `data/hf/` のうち上記6ファイルだけで、結合済み `*.jsonl` と他の `data/` は管理外。

2026-10-07の結合結果：

| 区分 | ファイル | 報告 | PDF | ページ（行） | 文字数 | 空ページ | バイト |
|---|---|---|---|---|---|---|---|
| tnn | tnn.jsonl | 7 | 46 | 781 | 2,101,307 | 5 | 3,547,292 |
| flash | flash.jsonl | 19 | 19 | 102 | 68,322 | 0 | 254,747 |
| 計 | | 26 | 65 | 883 | 2,169,629 | 5 | 3,802,039 |
| 除外 | | 118 | 564 | 13,242 | 20,839,130 | 347 | |

分類別（報告・PDF・ページ）：収録 a 14・23・313、b 12・42・570。除外 c 108・503・12,764、d 10・61・478。
