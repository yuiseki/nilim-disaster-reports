# nilim-disaster-reports

国総研の災害現地調査報告のローカル収集標本。2026-10-06開始、2026-10-07に拡張。

データ本体は `data/` に置きGit対象外。能登地震・2020年7月豪雨・2012年九州北部豪雨から3章、26,957,091バイト、90ページを取得。
`data/catalog.json` は3報告の分割URL49件（前付け等を含む）。全文PDFとの重複を避ける。
`data/sample-manifest.json` に出典・SHA256・サイズ・ページ数・抽出文字数を保存。
`data/pdf/` 原本、`data/text/` pdftotext抽出、`data/indices/` 索引・共通規約。

逐次1接続、512KiB/s、要求間3秒で取得。systemdユーザーサービス `nilim-disaster-reports-download.service` で49件を順次取得中。取得済み3標本はSHA256検証後に再利用。2026-10-07から35冊の国総研資料と109件の建築災害速報、計630 PDFを対象。旧49件の完了分は再利用。国総研の災害資料全体の網羅は未確認。
共通規約は原則PDL1.0。共同著作・第三者の図表写真は要調査。HuggingFace未公開。
詳細カード: /Workspaces/repos/__yuiseki/_research_ai/YuisekinText/docs/datasets/nilim-disaster-reports.md

## 運用

Python標準ライブラリとcurlを使用。検証: `python -m pytest -q tests`（23件）。
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
