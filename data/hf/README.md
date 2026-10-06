---
license: cc-by-4.0
language:
- ja
- en
task_categories:
- text-generation
- fill-mask
task_ids:
- language-modeling
- masked-language-modeling
size_categories:
- n<1K
pretty_name: NILIM disaster survey reports, page text of NILIM's own works (国総研 災害調査報告)
tags:
- disaster
- flood
- landslide
- tsunami
- earthquake
- civil-engineering
- japan
- government-reports
- pdf-text
configs:
- config_name: default
  default: true
  data_files:
  - split: train
    path:
    - tnn.jsonl
    - flash.jsonl
- config_name: tnn
  data_files:
  - split: train
    path: tnn.jsonl
- config_name: flash
  data_files:
  - split: train
    path: flash.jsonl
---

# NILIM disaster survey reports: page text of NILIM's own works

Page-level text of disaster field-survey reports published by the National Institute for Land
and Infrastructure Management (NILIM, 国土交通省 国土技術政策総合研究所, 国総研), extracted from the
text layer of the official PDFs. One JSON line is one PDF page.

**What is in, and what is left out.** The dataset owner chose to publish only reports whose text
NILIM published alone with no other rights notice: rights classes **a** (no other rights notice
found) and **b** (NILIM's text, with figures or photos credited to others). Every report that was
jointly published or co-authored with another organisation (the Public Works Research Institute
PWRI, the Building Research Institute BRI, the Port and Airport Research Institute PARI, the
National Institute of Maritime, Port and Aviation Technology MPAT, universities, academic societies,
the MLIT Housing Bureau and others), every report with an all-rights-reserved notice, and every
report whose rights could not be assessed (classes **c** and **d**) is left out.

| | reports | PDFs | pages |
|---|---|---|---|
| **in**: class a | 14 | 23 | 313 |
| **in**: class b | 12 | 42 | 570 |
| **in**: total | 26 | 65 | 883 |
| **out**: class c (joint publication, co-authorship or rights notice of another party) | 108 | 503 | 12,764 |
| **out**: class d (unclear) | 10 | 61 | 478 |
| **out**: total | 118 | 564 | 13,242 |

So this is a small part (65 of 629 collected PDFs) of NILIM's disaster survey output. The class
of every PDF and the evidence for it are in `RIGHTS_REVIEW.tsv`; every left-out PDF is listed in
`EXCLUDE.txt` with one reason per report. Class b reports keep their credit lines (for example
`（山口県提供）`, `出典：地理院地図`) because they are part of the text; the credited figures and photos
themselves are not in this text corpus.

This dataset contains only text. The PDFs, figures, maps and photographs are not included; every
line gives the official PDF URL (`source_url`) and the SHA-256 of the PDF that was read
(`source_pdf_sha256`), so the original can be downloaded and checked. It is not an official NILIM
product and is not endorsed by NILIM.

## Source and the two files

NILIM is the research institute of the Ministry of Land, Infrastructure, Transport and Tourism
(MLIT) for roads, rivers, sabo, coasts, ports, airports, sewerage, buildings and housing. After
earthquakes, floods, typhoons, landslides and storm surges it sends researchers to the sites (often
as part of TEC-FORCE) and publishes what they found.

| config | file | series | reports | PDFs | pages | characters | empty pages | size |
|---|---|---|---|---|---|---|---|---|
| `tnn` | `tnn.jsonl` | 国総研資料 (Technical Note of NILIM) | 7 | 46 | 781 | 2,101,307 | 5 | 3,547,292 bytes |
| `flash` | `flash.jsonl` | quick field-survey reports (速報) | 19 | 19 | 102 | 68,322 | 0 | 254,747 bytes |
| `default` | both files | both | 26 | 65 | 883 | 2,169,629 | 5 | 3,802,039 bytes |

By series and class:

| series | class | reports in | PDFs in | pages in | reports out | PDFs out | pages out |
|---|---|---|---|---|---|---|---|
| `tnn` | a | 1 | 10 | 243 | 0 | 0 | 0 |
| `tnn` | b | 6 | 36 | 538 | 0 | 0 | 0 |
| `tnn` | c | 0 | 0 | 0 | 25 | 420 | 11,025 |
| `tnn` | d | 0 | 0 | 0 | 3 | 54 | 335 |
| `flash` | a | 13 | 13 | 70 | 0 | 0 | 0 |
| `flash` | b | 6 | 6 | 32 | 0 | 0 | 0 |
| `flash` | c | 0 | 0 | 0 | 83 | 83 | 1,739 |
| `flash` | d | 0 | 0 | 0 | 7 | 7 | 143 |

- `tnn` (国総研資料): numbered technical reports, each published as a set of split PDFs (cover,
  front matter, chapters, appendices, colophon) linked from the report's page.
- `flash`: PDFs linked from NILIM's page 「国内で生じた災害の調査報告」
  (https://www.nilim.go.jp/lab/bbg/saigai/index.html): short reports written within days of an
  event. One PDF is one report (`report_id` is `flash-` plus 16 hex digits of the URL's SHA-256).

`source_type` only records which index the PDF came from. Load one file with
`load_dataset("yuiseki/nilim-disaster-reports", "tnn")` or `"flash"`; the `default` config reads
both. The text is Japanese, with English titles and abstracts on report covers.

### Coverage

The catalog of 2026-10-07 has 630 PDF URLs: 521 split PDFs of 35 国総研資料 reports found from
NILIM's TEC-FORCE page (https://www.nilim.go.jp/lab/bbg/saigai/TEC-FORCE.html), the structures
and foundations division page (https://www.nilim.go.jp/lab/ucg/research/02.html) and two reports
added by hand (1320, 1356), plus 109 bulletins. 629 PDFs were downloaded on 2026-10-06/07 (the
colophon of report 728 returned 404) and all 629 were reviewed; 65 are published.

国総研資料 reports, all 35 (in: classes a and b; out: c and d):

| report | title | PDFs | pages | class | other parties / reason | in dataset |
|---|---|---|---|---|---|---|
| 115 | 平成１５年５月２６日宮城県沖地震被害に係わる現地調査報告書 | 17 | 80 | d | no text layer, authors and notices unreadable | out |
| 133 | 平成15年7月26日宮城県北部地震被害に係わる現地調査報告書 | 16 | 88 | d | no text layer, authors and notices unreadable | out |
| 233 | 平成15年（2003年）十勝沖地震被害に係わる現地調査報告書 | 21 | 167 | d | no text layer, authors and notices unreadable | out |
| 248 | 平成16年（2004年）新潟県中越地震被害に係わる現地調査概要 | 38 | 214 | c | joint survey with PWRI and BRI | out |
| 250 | 平成15年7月九州豪雨災害に関する調査報告会 | 18 | 141 | c | proceedings with PWRI and five universities | out |
| 273 | 2004年の高潮・高波災害 | 10 | 102 | b | credits: 気象庁, 菜生海岸災害調査検討委員会 | **in** |
| 415 | 平成19年（2007年）能登半島地震建築物被害調査報告 | 14 | 170 | c | co-published with BRI | out |
| 430 | 平成19年（2007年）新潟県中越沖地震建築物被害調査報告 | 13 | 210 | c | co-published with BRI | out |
| 438 | 平成19年（2007年）能登半島地震被害調査報告 | 16 | 250 | c | co-published with PWRI and BRI | out |
| 439 | 平成19年（2007年）新潟県中越沖地震被害調査報告 | 15 | 253 | c | co-authored with PWRI | out |
| 481 | 平成20年(2008年)岩手・宮城内陸地震建築物被害調査報告 | 16 | 206 | c | co-published with BRI | out |
| 486 | 平成20年（2008年）岩手・宮城内陸地震被害調査報告 | 15 | 246 | c | co-published with PWRI and BRI | out |
| 636 | 平成23年（2011年）東北地方太平洋沖地震調査研究（速報） | 22 | 577 | c | co-published with BRI | out |
| 646 | 平成23年（2011年）東北地方太平洋沖地震 土木施設災害調査速報 | 17 | 497 | c | co-published with PWRI | out |
| 658 | 2011年東北地方太平洋沖地震津波による海岸保全施設の被害調査 | 1 | 45 | b | credits: 電子国土, Google Earth | **in** |
| 680 | 平成23年（2011年）東北地方太平洋沖地震による仙台空港の舗装に関する被害報告 | 1 | 26 | c | co-authored by a PARI researcher | out |
| 703 | 平成24年（2012年）5月6日に茨城県つくば市で発生した建築物等の竜巻被害調査報告 | 13 | 89 | c | co-published with BRI | out |
| 726 | 平成23年(2011年)東北地方太平洋沖地震による強震記録 | 10 | 243 | a | - | **in** |
| 728 | 平成23年（2011年）紀伊半島台風12号土砂災害調査報告 | 23 | 219 | c | co-published with PWRI | out |
| 758 | 平成24年7月九州北部豪雨災害に関する調査 | 13 | 101 | b | credits: 九州地方整備局, 江口希之建築都市研究所 | **in** |
| 781 | 2011年東北地方太平洋沖地震津波による海岸保全施設の被害調査（その2） | 1 | 56 | b | credits: 国土地理院, Google Earth, one photographer | **in** |
| 798 | 平成23年(2011年)東北地方太平洋沖地震による港湾施設等被害報告 | 43 | 3,156 | c | co-published with PARI; all rights reserved | out |
| 814 | 平成23年（2011年）東北地方太平洋沖地震による道路橋等の被害調査報告 | 12 | 767 | c | co-published with PWRI | out |
| 868 | 平成26年（2014年）北海道地方被災橋梁等調査報告 | 15 | 85 | c | co-published with PWRI; all rights reserved | out |
| 875 | 平成25年（2013年）台風26号伊豆大島土砂災害調査報告 | 16 | 104 | c | co-published with PWRI; all rights reserved | out |
| 936 | 平成25年山口・島根豪雨災害及び台風第18号災害に関する調査 | 10 | 96 | b | credits: 山口県, 萩市, 地理院地図 | **in** |
| 967 | 平成28年（2016年）熊本地震土木施設被害調査報告 | 15 | 363 | c | co-published with PWRI | out |
| 980 | 平成28年（2016年）12月22日に発生した新潟県糸魚川市における大規模火災に係る建物被害調査報告書 | 14 | 93 | c | co-published with BRI | out |
| 1042 | 平成28年（2016年）熊本地震による港湾施設等被害報告 | 1 | 54 | c | co-published with MPAT; all rights reserved | out |
| 1069 | 平成28年（2016年）台風10号等に伴う豪雨による北海道地方被災橋梁等調査報告 | 11 | 88 | c | co-published with PWRI | out |
| 1111 | 令和元年（2019年）房総半島台風および東日本台風による土木施設・建築物等災害調査報告 | 15 | 417 | c | co-published with PWRI and BRI | out |
| 1151 | 令和2年（2020年）7月豪雨 道路災害調査報告 | 15 | 164 | c | co-published with PWRI | out |
| 1202 | 道路橋の洗掘による被災リスク要因に関する研究 －被災事例の統計分析等による検討及び令和3年(2021年)の豪雨災害調査－ | 1 | 138 | b | credits: 地理院地図, 地図・空中写真閲覧サービス | **in** |
| 1320 | 令和６年能登半島地震土木施設被害調査等報告 | 21 | 740 | c | co-published with PWRI | out |
| 1356 | 令和６年能登半島地震建築物被害調査等報告 | 21 | 1,896 | c | co-published with BRI; university and company authors | out |

The 19 published bulletins (`flash`), by path under https://www.nilim.go.jp/lab/bbg/saigai/:

- class a (13): sabo surveys of 2013-2014 (`h26/140612yokosuka.pdf`, `h26/140820hiroshima_yagi.pdf`,
  `h26/140821hiroshima_yagi.pdf`, `h26/140822hiroshima_heli.pdf`, `h26/140822hiroshima_kabehigashi.pdf`,
  `h25typhoon26/131018izuoshima.pdf`, `h25typhoon26/131018izuoshima_betten.pdf`,
  `h25akita/130813akita_senboku.pdf`), `h22shimane/h22shimane_saigai.pdf` (2010 rockfall), flood
  surveys (`h25typhoon18/130927_suigai.pdf`, `h25yamaguchi/20130805suigai_result.pdf`,
  `h21hyougo/h21hyougo3.pdf`) and the 2016 Kumamoto sewerage survey
  (`h28/20160421kumamotogesuidou.pdf`).
- class b (6): `h27/20150722takamatsu.pdf` (storm surge, JMA figures), `h25typhoon18/130924fukui_obama.pdf`
  (電子国土 base map), `h24shimane/h24shimane.pdf` (gust; photos from a school, Google map),
  `h22yamaguchi/h22yamaguchi.pdf` and `h22gihu/h22gihu.pdf` (floods; JMA rainfall),
  `surugawan/surugawan.pdf` (2009 earthquake; NIED K-NET/KiK-net records).

The 90 bulletins left out are written jointly by NILIM with BRI (most building-damage bulletins,
2003-2026), PWRI (most sabo bulletins), PARI, academic societies, universities or the MLIT Housing
Bureau, or surveyed with them (class c, 83), or have unreadable text or a passage that may be quoted from others (class d,
7). Each is in `EXCLUDE.txt` with its reason.

## Files and order

- `tnn.jsonl`, `flash.jsonl`: UTF-8 JSON Lines, one page per line, separated by `\n` only.
  Documents are in the order of the source catalog, pages in PDF order. Each line is the per-PDF
  extraction line copied byte for byte; nothing was re-serialised. Split on `\n`, not on every
  Unicode line break, if you read the files yourself.
- `MANIFEST.json`: lines, documents, bytes and SHA-256 of each file; pages, characters, empty
  pages and U+FFFD counts; the excluded PDFs with their class and reason; the class summary.
- `provenance.yaml`: source indexes, catalog date and SHA-256, fetch and extraction dates, tool
  versions, exclusion rule, and what was changed (nothing in the text).
- `RIGHTS_REVIEW.tsv`: the rights review, one row per collected PDF (629 rows, published or not).
- `EXCLUDE.txt`: the 564 `source_url`s left out, grouped by report, each group with its class,
  other parties, basis, quoted evidence and, for four reports, the all-rights-reserved notice.
- `LICENSE`: licence, exact quotation of the NILIM terms, attribution.

Hugging Face converts the JSONL to Parquet automatically for the viewer and `datasets`; no
Parquet is published separately.

## Schema

All 22 fields are present on every line.

| field | type | meaning |
|---|---|---|
| `document_id` | string | SHA-256 (hex) of `source_url`. Same for every page of one PDF. |
| `source_type` | string | `tnn` (国総研資料) or `flash` (bulletin from the disaster index page). Index of origin only. |
| `report_id` | string | 国総研資料 number (e.g. `758`) for `tnn`; `flash-` plus the first 16 hex digits of `document_id` for `flash`. |
| `report_title` | string | Title as written on the index or report page. For 18 of the 19 `flash` PDFs it ends with the link text, e.g. `（PDF ファイル：490KB ）`. |
| `event` | string | `rainfall` (report 758, 13 PDFs) or `要調査` ("to be checked") for the other 52 PDFs. Not inferred from the text; read the title. |
| `section` | string | Link text of the PDF on the report page (e.g. `表紙`, `奥付`, a chapter title, `全文`); for `flash` the same as the title. |
| `source_url` | string | Official URL of the PDF on www.nilim.go.jp. |
| `index_url` | string | Official page that links the PDF (the report page for `tnn`, the disaster index for `flash`). |
| `source_pdf_path` | string | Path of the PDF in the compiler's local collection (`pdf/ks075801.pdf`, `pdf/flash/<24 hex>.pdf`). The PDFs are not in this dataset. |
| `source_pdf_sha256` | string | SHA-256 of the PDF that was downloaded and read. |
| `source_pdf_bytes` | int | Size of that PDF in bytes. |
| `page_number` | int | 1-based physical page index in the PDF. Not the printed page number. |
| `text` | string | Text of the page from `pdftotext -layout`, as extracted. Empty string for a page without a text layer. |
| `characters` | int | Length of `text` in Unicode code points. |
| `non_whitespace_characters` | int | Code points of `text` that are not whitespace. |
| `has_text` | bool | `non_whitespace_characters > 0`. |
| `needs_ocr_review` | bool | `not has_text`. Marks empty pages only; it does not detect bad text layers. |
| `replacement_characters` | int | Number of U+FFFD in `text` (0 on every line). |
| `extraction_method` | string | Always `pdftotext-layout`. |
| `extractor_version` | string | Always `pdftotext version 24.02.0`. |
| `license_policy_url` | string | Always `https://www.nilim.go.jp/aboutlink.htm`, the NILIM terms page. |
| `rights_review` | string | Note in Japanese written at collection time, before the rights review (`原則PDL1.0、共同著作・第三者素材・個別条件は要調査` or, for report 758, `原則PDL1.0、個別素材・共著部分は要確認`). Superseded by `RIGHTS_REVIEW.tsv`. |

## How the text was made

1. The PDF URLs were collected from the indexes above into a fixed catalog (2026-10-07, 630 URLs).
   Each PDF was downloaded once, sequentially and slowly, recording its size and SHA-256
   (2026-10-06 10:27 to 22:24 UTC).
2. Each PDF was converted with Poppler `pdftotext -enc UTF-8 -layout`, which reads the PDF's own
   text layer. The output was split on form feeds into pages and the page count was checked against
   `pdfinfo`. No new OCR was run, and no correction, normalisation (width, old kanji, punctuation),
   header removal or de-hyphenation was applied. Whitespace from the layout is kept.
3. The rights of all 629 PDFs were reviewed (below). The per-PDF JSONL of the class a and b reports
   was concatenated into one file per `source_type` and checked line by line against the per-PDF
   files.

## Quality caveats

The text is the PDF text layer as it is. It is not cleaned training text.

- 5 pages are empty (`has_text = false`): 2 in report 726 and 3 in report 1202.
- `-layout` keeps the physical layout. Two-column pages put both columns on one text line,
  separated by runs of spaces. Running heads, page numbers, captions, table cells and text inside
  figures are mixed into the page text. Report 726 is mostly tables of strong-motion records.
- `report_title` of most bulletins contains index link text such as `（PDF ファイル：490KB ）`, and
  `event` is `要調査` (unknown) for 52 of 65 PDFs.
- A PDF is not always body text: covers, tables of contents, author lists and colophons of the
  国総研資料 are included as they are.
- No U+FFFD and no garbled text layer was found in the published files, but `has_text = true` does
  not mean every character is right.

## Rights review

The page text of all 629 collected PDFs was scanned for signs of another rights holder or licence:
copyright notices (`©`, `Copyright`, 著作権), reservation and reprint restrictions (`All rights
reserved`, 無断転載, 承認を得ずして), joint authorship or publication (other institutes, universities,
societies), credits (提供, 出典, 撮影, 転載, 引用, Google, ZENRIN) and Survey Act or GSI map notices
(測量法, 承認番号, 国土地理院, 地理院地図, 電子国土). The covers, front matter, author lists and colophons
of every report were read, and the hits were read in context. Each report was put in one class:
**a** no other rights notice found; **b** figures or photos credited to others only; **c** a
rights notice or reprint restriction covering the whole report, or joint authorship or publication
with another organisation; **d** unclear. `RIGHTS_REVIEW.tsv` has one row per PDF with the class,
other parties, basis, a quoted line of evidence (file, page, text), counts of lines matching each
signal, its first hit, and whether it is excluded.

What it found in the left-out reports:

- **Joint publications.** Most left-out 国総研資料 reports are also published in a co-publisher's
  series (土研資料 of PWRI, 建築研究資料 of BRI, 港湾空港技術研究所資料 of PARI or MPAT), and their
  colophons carry the co-publisher's mark, e.g. 1151 `ks1151_15.pdf` page 1
  「編集・発行 ©国土技術政策総合研究所 ©国立研究開発法人土木研究所」. Reports 248 and 250 are joint surveys
  or meeting proceedings with PWRI, BRI and universities.
- **All rights reserved.** 798 (with PARI), 868 and 875 (with PWRI) and 1042 (with MPAT) state that
  all rights are reserved and that no part may be reprinted or copied without written approval,
  e.g. 868 `ks086801.pdf` page 2: 「Copyright © (2015) by N.I.L.I.M. and P.W.R.I.」「All rights
  reserved.」「本報告書の全部又は一部の転載、複製は、…文書による承認を得ずしてこれを行ってはならない。」
- **Co-authors and joint surveys.** Report 680 has a PARI researcher among its four authors
  (`ks0680.pdf` page 2). 83 bulletins name BRI, PWRI, PARI, academic societies, universities or the
  MLIT Housing Bureau as authors or survey members next to NILIM, e.g. `R8/kumamototekkinkonkurito.pdf` page 1
  「国土交通省国土技術政策総合研究所 / 国立研究開発法人建築研究所」.
- **Unclear.** Reports 115, 133 and 233 have no text layer; six 2016 Kumamoto bulletins have
  unreadable text layers; `h21hyougo/h21hyougo1.pdf` page 4 contains an uncredited passage that
  reads like quoted press text.

In the published reports: the 国総研資料 colophons carry NILIM's own mark and a contact for
reprint requests (「編集・発行 ©国土技術政策総合研究所」「本資料の転載・複写の問い合わせは」). This names NILIM,
the default rights holder under its terms, and asks for no approval, so it was not treated as
another rights notice. Class b credit lines name the owners of figures and photos (GSI, JMA,
prefectures and cities, Google, NIED, a regional bureau of MLIT, a private
architect's office for one questionnaire figure in 758) that are not reproduced here; a few tables
in 273 are JMA data cited with 「出典：気象庁 HP」. No 測量法 (Survey Act) approval notice was found.

The review is a reading of the text, not legal advice, and it can miss notices that exist only as
images or on pages without text.

## Getting and checking the original PDF

`source_url` is the official PDF. Download it and compare its SHA-256 with `source_pdf_sha256`
(and its size with `source_pdf_bytes`). If they differ, NILIM has replaced the file since
2026-10-06 and the text may not match. `page_number` is the page index in that PDF.

```sh
curl -sO "https://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn0758pdf/ks075801.pdf"
sha256sum ks075801.pdf   # compare with source_pdf_sha256 of its lines
```

## Licence

CC BY 4.0. The dataset owner chose to publish only NILIM's own works (classes a and b): reports
NILIM published alone with no rights notice of another party. Jointly published and co-authored
reports (with PWRI, BRI, PARI, MPAT, universities, societies and others) and unclear reports are
left out (118 reports, 564 PDFs, 13,242 pages; see `EXCLUDE.txt` and `RIGHTS_REVIEW.tsv`), so the
published text is NILIM content covered by NILIM's own terms.

NILIM's terms (「リンク・著作権等について」, https://www.nilim.go.jp/aboutlink.htm, read on
2026-10-07, Last-Modified 2025-12-19) say, quoted exactly (the duplicated 「は、の」 is in the original):

> 国土技術政策総合研究所ウェブサイト及び国土技術政策総合研究所のソーシャルメディアアカウントで掲載・発信している情報（以下「コンテンツ」といいます。）は、の著作権は、特記されていない限り国土技術政策総合研究所に帰属し、権利表記の記載がない限り「公共データ利用規約（第1.0版）」（PDL1.0）に準拠した利用条件の下で、利用することができます。

(In English: unless otherwise stated, the copyright of content on the NILIM website belongs to
NILIM, and unless there is a rights notice it may be used under the Public Data License 1.0,
https://www.digital.go.jp/resources/open_data/public_data_license_v1.0.) PDL1.0 is compatible
with CC BY 4.0, which is why the card uses `cc-by-4.0`. The same page asks for the source in the
form 「出典：「○○動向調査」（国土技術政策総合研究所） （当該ページのURL）（○年○月○日に利用）」 and, when content
is edited, a separate statement that it was edited, without presenting the result as made by the
government. The full section is quoted in `LICENSE`.

Credit lines in class b reports name the owners of figures and photos that are not included; the
licence of this dataset does not extend to those images or to any third-party material quoted in
the text.

## Attribution

In the form requested by the NILIM terms (出典 and a note on editing):

> 出典：「国総研資料（災害調査報告）」（国土技術政策総合研究所）（https://www.nilim.go.jp/lab/bbg/saigai/TEC-FORCE.html）（2026年10月6日〜7日に利用）
> 出典：「国内で生じた災害の調査報告」（国土技術政策総合研究所）（https://www.nilim.go.jp/lab/bbg/saigai/index.html）（2026年10月6日〜7日に利用）
> 国土技術政策総合研究所の各PDF（各行の source_url）の文字層から pdftotext で本文を抽出し、yuiseki がページ単位の JSONL に収録したもの（Hugging Face: yuiseki/nilim-disaster-reports）を加工して作成。本文の訂正・正規化は行っていない。

In English: Source: NILIM disaster survey reports (国総研資料) and field-survey bulletins, National
Institute for Land and Infrastructure Management, MLIT (index URLs above). Text extracted with
pdftotext from each PDF's text layer and compiled into page-level JSONL by yuiseki
(yuiseki/nilim-disaster-reports); not corrected or normalised; not made or endorsed by NILIM. When
you cite one report, cite the report itself (authors, title, report number, year) and give its
`source_url`.
