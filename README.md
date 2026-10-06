# nilim-disaster-reports

国総研の災害現地調査報告のローカル収集標本。2026-10-06。

データ本体は `data/` に置きGit対象外。能登地震・2020年7月豪雨・2012年九州北部豪雨から3章、26,957,091バイト、90ページを取得。
`data/catalog.json` は3報告の分割URL49件（前付け等を含む）。全文PDFとの重複を避ける。
`data/sample-manifest.json` に出典・SHA256・サイズ・ページ数・抽出文字数を保存。
`data/pdf/` 原本、`data/text/` pdftotext抽出、`data/indices/` 索引・共通規約。

逐次1接続、512KiB/s、要求間3秒で取得。systemdユーザーサービス `nilim-disaster-reports-download.service` で49件を順次取得中。取得済み3標本はSHA256検証後に再利用。対象は確認済みの3報告に限定し、国総研の災害資料全体ではない。
共通規約は原則PDL1.0。共同著作・第三者の図表写真は要調査。HuggingFace未公開。
詳細カード: /Workspaces/repos/__yuiseki/_research_ai/YuisekinText/docs/datasets/nilim-disaster-reports.md

## 運用

Python標準ライブラリとcurlを使用。検証: `python -m pytest -q tests`（16件）。
進捗: `cat data/status.json`、ログ: `tail -n 10 data/download.log`。
停止: `systemctl --user stop nilim-disaster-reports-download`。
再開は下記の起動スクリプトを実行。ロックで二重起動を防ぎ、サイズ・SHA256が一致する完了ファイルをスキップ。
401/403/429で停止。通信失敗等は30/120/300秒待機し最大4試行。404/410は欠落として記録。
不明な既存PDFは上書きせず停止。中断したpartは先頭から再取得。
Nice=15、I/O idle、CPUQuota=25%、MemoryMax=256M。再起動・完全ログアウト後の自動再開は設定していない。
権利確認・本文抽出・HF公開はこのジョブの対象外。
