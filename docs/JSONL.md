# 国総研PDFのページ別JSONL

2026-10-07。取得済み629 PDFの文字層から、GSJと同じ方法でJSONLを作る。GSJのコード・データには依存せず変更しない。
Python標準ライブラリとPopplerのpdfinfo/pdftotextを使用。新OCR・AI訂正・Parquet生成・HFへのアップロードは行わない。

## 出力

保存先: `/sata_hdd_24tb/hf_data/nilim-disaster-reports/data/jsonl/`

- `documents/<出典URLのSHA256>.jsonl`: PDF単位、1行が1ページ。空ページも保持。
- `manifest.jsonl`: PDFとJSONLのSHA256・サイズ・ページ数・文字数・空ページ数等。
- `dataset.json`: 最終集計と結合ファイルの件数・SHA256。
- `corpus/tnn.jsonl`: 国総研資料のページを結合。
- `corpus/flash.jsonl`: 災害調査速報のページを結合。
- `source-missing.json`: 取得元の404等。現在は資料728の奥付1件。
- `extraction-errors.json`: 取得済みPDFの抽出失敗。取得元の欠落とは区別。
- `status.json`, `extract.log`: 進捗とログ。

結合ファイルは全件抽出後に生成。試行3件のcorpus・dataset.jsonが先にあるため、全件版として使う前にstatus.jsonの完了状態と集計を確認する。
本文はUTF-8 JSONL。改行はJSON内でエスケープし、結合はソース行のバイトをそのままコピー。目録順・PDFページ順を保持。
source_typeのtnn/flashは刊行資料/速報の取得経路で、共同著作者やライセンスの区分ではない。

## スキーマ

document_id、source_type、report_id、report_title、event、sectionで報告を識別。
source_url、index_url、source_pdf_path、source_pdf_sha256、source_pdf_bytes、page_numberで原本に戻れる。
report_idは文字列に統一。eventは索引の値を保持し、未確認の場合は要調査。災害の発生日を自動推定しない。
textはpdftotext -layoutの結果。印刷されたページ番号とは別に、PDF内の物理ページ番号を1始まりで付与。
characters、non_whitespace_characters、has_text、needs_ocr_review、replacement_charactersを保持。
非空白文字0のページだけneeds_ocr_review=true。文字層があっても誤認識・段組の読み順・欠落はあり得る。
extraction_method、extractor_version、license_policy_url、rights_reviewも保持。原本の第三者素材等の再配布確認は引き続き要調査。

## 運用

```sh
python -m pytest -q tests
sh start-jsonl.sh
cat data/jsonl/status.json
tail -n 5 data/jsonl/extract.log
systemctl --user stop nilim-disaster-reports-jsonl
```

Nice=15、I/O idle、CPUQuota=50%、MemoryMax=512M、単一ワーカー。本サイトへの通信なし。
原本のサイズ・SHA256を確認してから抽出し、pdfinfoのページ数と文字列のページ区切りを照合する。
再開時は同じstart-jsonl.shを使い、原本・JSONLが記録のSHA256と一致する完了分のみ再利用。
抽出エラーは記録して続行。原本破損・JSONL破損・不明な既存出力は上書きせず停止。中断したmanifest末尾は保存して復旧。
二重起動をロックで防ぐ。再起動後の自動再開は未設定。
status.totalは目録630件、completeはJSONL化した件数、missingは取得元欠落と抽出エラーの合計。取得元1件の欠落により、抽出エラー0でもfinished_with_missingになる。
30分監視に追加済み。停止・1時間の更新停止・完了をDiscord通知。
30テスト合格。実PDF3件・4ページの抽出・結合確認済み。
