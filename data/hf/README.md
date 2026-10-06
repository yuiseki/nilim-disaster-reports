---
license: other
license_name: nilim-pdl1.0-and-co-publisher-notices
license_link: LICENSE
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
- 10K<n<100K
pretty_name: NILIM disaster survey reports, page text (国総研 災害調査報告), 2003-2026
tags:
- disaster
- earthquake
- flood
- landslide
- civil-engineering
- building
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

# NILIM disaster survey reports: page text (2003-2026)

Page-level text of disaster field-survey reports published by the National Institute for Land
and Infrastructure Management (NILIM, 国土交通省 国土技術政策総合研究所, 国総研), extracted from the
text layer of the official PDFs. One JSON line is one PDF page.

This dataset contains only text. The PDFs, figures, maps and photographs are not included;
every line gives the official PDF URL (`source_url`) and the SHA-256 of the PDF that was read
(`source_pdf_sha256`), so the original can be downloaded and checked.

This is not an official NILIM product and is not endorsed by NILIM or by any co-publishing
institute. Read the licence section before use: many reports are joint publications with other
institutes, so this dataset is not released under a single CC BY licence.

## Source and the two files

NILIM is the research institute of the Ministry of Land, Infrastructure, Transport and Tourism
(MLIT) for roads, rivers, sabo, coasts, ports, airports, sewerage, buildings and housing. After
major earthquakes, floods, typhoons, tornadoes, fires and landslides it sends researchers to the
sites (often as part of TEC-FORCE) and publishes what they found.

| config | file | series | PDFs | pages | characters | empty pages | size |
|---|---|---|---|---|---|---|---|
| `tnn` | `tnn.jsonl` | 国総研資料 (Technical Note of NILIM): 31 disaster survey reports | 445 | 8,742 | 12,346,948 | 351 | 27,993,652 bytes |
| `flash` | `flash.jsonl` | quick field-survey reports and bulletins (速報, mostly 建築災害) | 109 | 1,984 | 1,659,185 | 1 | 5,371,933 bytes |
| `default` | both files | both | 554 | 10,726 | 14,006,133 | 352 | 33,365,585 bytes |

- `tnn` (国総研資料): numbered technical reports, each published as a set of split PDFs (cover,
  front matter, chapters, appendices, colophon). The report numbers are listed below. Many are
  co-published with the Public Works Research Institute (PWRI, 土木研究所), the Building Research
  Institute (BRI, 建築研究所) or the Port and Airport Research Institute (PARI, 港湾空港技術研究所)
  under those institutes' own report numbers.
- `flash`: every PDF linked from NILIM's page 「国内で生じた災害の調査報告」
  (https://www.nilim.go.jp/lab/bbg/saigai/index.html): short reports written within days or
  months of an event, dated from 2003 to 18 September 2026. Most are building-damage reports
  written jointly with BRI; others are sabo, flood, coastal, sewerage and press-release documents.
  One PDF is one report (`report_id` is `flash-` plus 16 hex digits of the URL's SHA-256).

`source_type` (`tnn` / `flash`) only records which index the PDF came from; it says nothing about
authorship or licence. Load one file with `load_dataset("yuiseki/nilim-disaster-reports", "tnn")`
or `"flash"`; the `default` config reads both. Most text is Japanese; covers and abstracts often
have English, and one bulletin (`h24tsukuba-e.pdf`) is in English.

### Coverage

The catalog of 2026-10-07 has 630 PDF URLs: 521 split PDFs of 35 国総研資料 reports found from
NILIM's TEC-FORCE page (https://www.nilim.go.jp/lab/bbg/saigai/TEC-FORCE.html), the structures
and foundations division page (https://www.nilim.go.jp/lab/ucg/research/02.html) and two reports
added by hand (1320, 1356), plus the 109 bulletins. 629 PDFs were downloaded on 2026-10-06/07; the
colophon of report 728 returned 404. Of the 629, 75 PDFs of four reports are excluded (see
[Rights review](#rights-review-and-exclusions)), leaving 554. Where a report page offered both a
whole-report PDF and split PDFs, only the split PDFs were taken.

| report | title | PDFs | pages | rights class | in dataset |
|---|---|---|---|---|---|
| 115 | 平成１５年５月２６日宮城県沖地震被害に係わる現地調査報告書 | 17 | 80 | d | yes (no text layer) |
| 133 | 平成15年7月26日宮城県北部地震被害に係わる現地調査報告書 | 16 | 88 | d | yes (no text layer) |
| 233 | 平成15年（2003年）十勝沖地震被害に係わる現地調査報告書 | 21 | 167 | d | yes (no text layer) |
| 248 | 平成16年（2004年）新潟県中越地震被害に係わる現地調査概要 | 38 | 214 | c | yes |
| 250 | 平成15年7月九州豪雨災害に関する調査報告会 | 18 | 141 | c | yes |
| 273 | 2004年の高潮・高波災害 | 10 | 102 | b | yes |
| 415 | 平成19年（2007年）能登半島地震建築物被害調査報告 | 14 | 170 | c | yes |
| 430 | 平成19年（2007年）新潟県中越沖地震建築物被害調査報告 | 13 | 210 | c | yes |
| 438 | 平成19年（2007年）能登半島地震被害調査報告 | 16 | 250 | c | yes |
| 439 | 平成19年（2007年）新潟県中越沖地震被害調査報告 | 15 | 253 | c | yes |
| 481 | 平成20年(2008年)岩手・宮城内陸地震建築物被害調査報告 / 平成20年7月24日岩手沿岸北部の地震建築物被害調査報告 | 16 | 206 | c | yes |
| 486 | 平成20年（2008年）岩手・宮城内陸地震被害調査報告 | 15 | 246 | c | yes |
| 636 | 平成23年（2011年）東北地方太平洋沖地震調査研究（速報）（東日本大震災） | 22 | 577 | c | yes |
| 646 | 平成23年（2011年）東北地方太平洋沖地震 土木施設災害調査速報 | 17 | 497 | c | yes |
| 658 | 2011年東北地方太平洋沖地震津波による海岸保全施設の被害調査 | 1 | 45 | b | yes |
| 680 | 平成23年（2011年）東北地方太平洋沖地震による仙台空港の舗装に関する被害報告 | 1 | 26 | b | yes |
| 703 | 平成24年（2012年）5月6日に茨城県つくば市で発生した建築物等の竜巻被害調査報告 | 13 | 89 | c | yes |
| 726 | 平成23年(2011年)東北地方太平洋沖地震による強震記録 | 10 | 243 | a | yes |
| 728 | 平成23年（2011年）紀伊半島台風12号土砂災害調査報告 | 23 | 219 | c | yes (colophon missing at source) |
| 758 | 平成24年7月九州北部豪雨災害に関する調査 | 13 | 101 | b | yes |
| 781 | 2011年東北地方太平洋沖地震津波による海岸保全施設の被害調査（その2） | 1 | 56 | b | yes |
| 798 | 平成23年(2011年)東北地方太平洋沖地震による港湾施設等被害報告 | 43 | 3,156 | c | **no**, excluded |
| 814 | 平成23年（2011年）東北地方太平洋沖地震による道路橋等の被害調査報告 | 12 | 767 | c | yes |
| 868 | 平成26年（2014年）北海道地方被災橋梁等調査報告 | 15 | 85 | c | **no**, excluded |
| 875 | 平成25年（2013年）台風26号伊豆大島土砂災害調査報告 | 16 | 104 | c | **no**, excluded |
| 936 | 平成25年山口・島根豪雨災害及び台風第18号災害に関する調査 | 10 | 96 | b | yes |
| 967 | 平成28年（2016年）熊本地震土木施設被害調査報告 | 15 | 363 | c | yes |
| 980 | 平成28年（2016年）12月22日に発生した新潟県糸魚川市における大規模火災に係る建物被害調査報告書 | 14 | 93 | c | yes |
| 1042 | 平成28年（2016年）熊本地震による港湾施設等被害報告 | 1 | 54 | c | **no**, excluded |
| 1069 | 平成28年（2016年）台風10号等に伴う豪雨による北海道地方被災橋梁等調査報告 | 11 | 88 | c | yes |
| 1111 | 令和元年（2019年）房総半島台風および東日本台風による土木施設・建築物等災害調査報告 | 15 | 417 | c | yes |
| 1151 | 令和2年（2020年）7月豪雨 道路災害調査報告 | 15 | 164 | c | yes |
| 1202 | 道路橋の洗掘による被災リスク要因に関する研究 －被災事例の統計分析等による検討及び令和3年(2021年)の豪雨災害調査－ | 1 | 138 | b | yes |
| 1320 | 令和６年能登半島地震土木施設被害調査等報告 | 21 | 740 | c | yes |
| 1356 | 令和６年能登半島地震建築物被害調査等報告 | 21 | 1,896 | c | yes |

The `flash` bulletins cover, among others: the 2003 Miyagi and Tokachi-oki earthquakes, 2005
Fukuoka-ken Seiho-oki earthquake and the Sendai pool ceiling collapse, tornadoes (2009 Tatebayashi,
Mimasaka, Tsuchiura; 2012 Tsukuba; 2013 Koshigaya; 2018 Maibara; 2019 Ichihara; 2025 Makinohara and
Tsukuba), typhoons and heavy rain (2009 Sayo, 2010-2015 landslides and floods, 2014 Hiroshima, 2015
Kinugawa, 2018 Typhoon Jebi, 2019 Faxai/Hagibis), the 2014 Nagano-ken Hokubu earthquake, the 2014
Ontake eruption, storm surges (2004, 2009 Mikawa, 2014 Nemuro, 2015 Takamatsu), the 2016 Kumamoto
earthquake (12 bulletins), the 2016 Tottori-ken Chubu earthquake, the 2016 Itoigawa fire, the 2018
Hokkaido Iburi-Tobu earthquake, the 2021/2022 Fukushima-ken-oki earthquakes, the 2023 and 2024 Noto
earthquakes, the 2025 Ofunato forest fire and Oita (Saganoseki) fire, and the 2026 Kumamoto earthquake
(7 bulletins).

## Files and order

- `tnn.jsonl`, `flash.jsonl`: UTF-8 JSON Lines, one page per line, separated by `\n` only.
  Documents are in the order of the source catalog (for `tnn`: report by report, PDFs in the order
  the report page lists them; for `flash`: the order of the index page, newest first), pages in PDF
  order. Each line is the per-PDF extraction line copied byte for byte; nothing was re-serialised.
  Split on `\n`, not on every Unicode line break, if you read the files yourself.
- `MANIFEST.json`: lines, documents, bytes and SHA-256 of each file; pages, characters, empty
  pages and U+FFFD counts of each file; the excluded PDFs; the rights-class summary.
- `provenance.yaml`: source indexes, catalog date and SHA-256, fetch and extraction dates, tool
  versions, and what was changed (nothing in the text).
- `RIGHTS_REVIEW.tsv`: the rights review, one row per PDF (see below).
- `EXCLUDE.txt`: the `source_url`s left out, with the reason as comments.
- `LICENSE`: licence, quotations of the NILIM terms and of the co-publishers' notices, attribution.

Hugging Face converts the JSONL to Parquet automatically for the viewer and `datasets`; no
Parquet is published separately.

## Schema

All 22 fields are present on every line.

| field | type | meaning |
|---|---|---|
| `document_id` | string | SHA-256 (hex) of `source_url`. Same for every page of one PDF. |
| `source_type` | string | `tnn` (国総研資料) or `flash` (bulletin from the disaster index page). Index of origin only. |
| `report_id` | string | 国総研資料 number (e.g. `1320`) for `tnn`; `flash-` plus the first 16 hex digits of `document_id` for `flash`. |
| `report_title` | string | Title as written on the index or report page. For 91 of the 109 `flash` PDFs it ends with the link text, e.g. `（PDFファイル:5.8MB）`; the 15 PDFs of report 1151 have a tab inside the title. |
| `event` | string | `earthquake` (report 1320, 21 PDFs), `rainfall` (reports 1151 and 758, 28 PDFs) or `要調査` ("to be checked") for the other 505 PDFs. Not inferred from the text; read the title. |
| `section` | string | Link text of the PDF on the report page (e.g. `表紙`, `奥付`, a chapter title, `全文`); for `flash` the same as the title. |
| `source_url` | string | Official URL of the PDF on www.nilim.go.jp. |
| `index_url` | string | Official page that links the PDF (the report page for `tnn`, the disaster index for `flash`). |
| `source_pdf_path` | string | Path of the PDF in the compiler's local collection (`pdf/ks1320_01.pdf`, `pdf/flash/<24 hex>.pdf`). The PDFs are not in this dataset. |
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
| `extractor_version` | string | `pdftotext version 24.02.0` (551 PDFs) or `pdftotext version 24.08.0` (3 PDFs of report 1320). |
| `license_policy_url` | string | Always `https://www.nilim.go.jp/aboutlink.htm`, the NILIM terms page. |
| `rights_review` | string | Note in Japanese written at collection time, before the rights review: `原則PDL1.0、共同著作・第三者素材・個別条件は要調査` or, for reports 1320, 1151 and 758 (49 PDFs), `原則PDL1.0、個別素材・共著部分は要確認`. Superseded by `RIGHTS_REVIEW.tsv`. |

## How the text was made

1. The PDF URLs were collected from the indexes above into a fixed catalog (2026-10-07, 630 URLs).
   Each PDF was downloaded once, sequentially and slowly, recording its size and SHA-256
   (2026-10-06 10:27 to 22:24 UTC).
2. Each PDF was converted with Poppler `pdftotext -enc UTF-8 -layout`, which reads the PDF's own
   text layer. The output was split on form feeds into pages and the page count was checked against
   `pdfinfo`. No new OCR was run, and no correction, normalisation (width, old kanji, punctuation),
   header removal or de-hyphenation was applied. Whitespace from the layout is kept. All 629 PDFs
   were extracted without errors.
3. The per-PDF JSONL files were concatenated into one file per `source_type`, leaving out the PDFs
   in `EXCLUDE.txt`, and checked line by line against the per-PDF files.

## Quality caveats

The text is the PDF text layer as it is. It is not cleaned training text.

- 352 pages are empty (`has_text = false`): reports 115, 133 and 233 (2003 earthquakes, 335 pages)
  have no text layer at all, so only their empty pages and metadata are here; the rest are blank or
  image-only pages. Their content is only in the PDF.
- Some text layers use wrong code points, so the Japanese comes out as unrelated characters (for
  example `࿖࿯ᛛⴚ᡽╷✚ว⎇ⓥᚲ` for 国土技術政策総合研究所). By a simple character-class check about
  1,260 pages are mostly such characters: most of report 814 (752 of 767 pages), most of 438 (230
  pages) and 439 (239 pages), most of `20160428kumamotokentiku6.pdf` and part of
  `20160417kumamotokentiku3.pdf` (2016 Kumamoto earthquake). In four more bulletins of that series (`20160415kumamotokentiku.pdf`, `20160416kumamotokentiku2.pdf`,
  `20160420kumamotokentiku4.pdf`, `20160429kumamotokentiku8.pdf`) the Japanese characters are
  missing and only digits and Latin letters remain. There are no U+FFFD characters, so
  `replacement_characters = 0` does not mean the text is right.
- `-layout` keeps the physical layout. Two-column pages put both columns on one text line,
  separated by runs of spaces. Running heads, page numbers, captions, table cells and text inside
  figures are mixed into the page text; some pages also carry editors' line numbers (e.g. `5`, `10`
  at the left margin of recent bulletins).
- `report_title` contains index link text such as `（PDFファイル:5.8MB）` for most bulletins, and
  report 1151's title contains a tab. `event` is `要調査` (unknown) for 505 of 554 PDFs.
- The colophon (奥付) of report 728 (`ks072824.pdf`) returned HTTP 404 when collected, so that
  report has no colophon in this dataset.
- A PDF is not always body text: covers, tables of contents, author lists, errata (636, 646),
  correction notices (726) and press releases are included as they are.
- Bulletins can be revised in place by NILIM (several say 修正 with a date); the text is that of the
  copy whose SHA-256 is given.

## Rights review and exclusions

Before deciding what to publish, the page text of all 629 PDFs was scanned for signs of another
rights holder or licence: copyright notices (`©`, `Copyright`, 著作権), reservation and reprint
restrictions (`All rights reserved`, 無断転載, 承認を得ずして), joint authorship or publication
(other institutes, universities, societies), credits (提供, 出典, 撮影, 転載, 引用, Google, ZENRIN) and
Survey Act or GSI map notices (測量法, 承認番号, 国土地理院, 地理院地図, 電子国土). The covers, front
matter, author lists and colophons of every report were read, and the hits were read in context.
Each report was put in one class:

- **a**: no other rights notice found.
- **b**: figures or photos credited to others only. The text is NILIM's; the credited images are
  not in a text corpus, but the credit lines (e.g. `（山口県提供）`, `出典：地理院地図`) remain in the text.
- **c**: a rights notice or reprint restriction covering the whole report, or joint authorship or
  publication with another organisation.
- **d**: unclear.

| class | reports included | PDFs included | pages included | reports excluded | PDFs excluded | pages excluded |
|---|---|---|---|---|---|---|
| a | 14 | 23 | 313 | 0 | 0 | 0 |
| b | 14 | 44 | 601 | 0 | 0 | 0 |
| c | 102 | 426 | 9,334 | 4 | 75 | 3,399 |
| d | 10 | 61 | 478 | 0 | 0 | 0 |

(`tnn`: 1 a, 7 b, 24 c, 3 d reports; `flash`: 13 a, 7 b, 82 c, 7 d bulletins.) `RIGHTS_REVIEW.tsv`
has one row per PDF with the class, the other parties, the basis and a quoted line of evidence
(file, page, text), the counts of lines matching each signal in that PDF, its first hit, and
whether it is excluded. What the review found:

- **Joint publications (class c, kept).** 18 of the 31 included 国総研資料 reports are also
  published as 土研資料 (PWRI), 建築研究資料 (BRI) or both. In 16 of them the colophon carries the
  co-publisher's copyright mark next to NILIM's (439's colophon has no text layer and 728's is
  missing), e.g. report 1151, `ks1151_15.pdf` page 1:
  「編集・発行 ©国土技術政策総合研究所 ©国立研究開発法人土木研究所」. Reports 248 and 250 are joint
  surveys or meeting proceedings with PWRI, BRI and universities. 82 bulletins name BRI, PWRI, PARI,
  academic societies, universities or the MLIT Housing Bureau as authors next to NILIM, e.g.
  `R8/kumamototekkinkonkurito.pdf` page 1: 「国土交通省国土技術政策総合研究所 / 国立研究開発法人建築研究所」;
  `miyagi-jishin/tuuti.pdf` is an MLIT Housing Bureau notice (国住指第１４２７号), not a NILIM text.
- **Reservation of all rights (class c, excluded).** Four reports state in their own text that all
  rights are reserved and that no part may be reprinted or copied without written approval:
  - 798 (43 PDFs, with PARI as 港湾空港技術研究所資料 No.1291), `ks079843.pdf` page 1:
    「Copyright ○ C （2015）by PARI」「All rights reserved. No part of this book must be reproduced by any
    means without the written permission of the President of PARI」「本報告書の全部または一部の転載、
    複写は港湾空港技術研究所理事長の文書による承認を得ずしてこれを行ってはならない。」
  - 868 (15 PDFs, with PWRI), `ks086801.pdf` page 2: 「Copyright © (2015) by N.I.L.I.M. and P.W.R.I.」
    「All rights reserved.」「本報告書の全部又は一部の転載、複製は、国土交通省国土技術政策総合研究所所長及び
    国立研究開発法人土木研究所理事長の文書による承認を得ずしてこれを行ってはならない。」
  - 875 (16 PDFs, with PWRI), `ks087501.pdf` page 2: the same notice for NILIM and PWRI.
  - 1042 (1 PDF, with MPAT/PARI as 港空研資料 No.1348), `ks1042.pdf` page 54:
    「Copyright ○EC （2018）by MPAT」「All rights reserved.」「本報告書の全部または一部の転載、複写は
    海上・港湾・航空技術研究所理事長の文書による承認を得ずしてこれを行ってはならない。」

  Such a notice is a rights notice (権利表記) in the sense of the NILIM terms quoted below, so the
  default PDL1.0 terms do not apply to these reports. Their 75 PDFs (3,399 pages, 9,002,626
  characters) are listed in `EXCLUDE.txt` and are not in the JSONL files. Other reports of the
  same co-publishers may carry the same notice on a cover verso that is not part of the split PDFs
  (for example the one-page covers of 1320, 1151, 967 and 1069); none was found in their text.
- **Credits only (class b).** Reports 273, 658, 680, 758, 781, 936 and 1202 and seven bulletins
  credit figures or photos to JMA, GSI (地理院地図, 電子国土), prefectures and cities, Google/ZENRIN or
  the Japan Coast Guard, e.g. 936 `ks093605.pdf` page 7 「（山口県提供）」. Report 646 (class c for
  joint publication) also uses geological maps under an AIST approval 「産総研承認番号:第60635500-A-20110728-002号」.
  No 測量法 (Survey Act) approval notice was found.
- **Unclear (class d).** Reports 115, 133 and 233 have no text, so their authorship and notices
  could not be read; six 2016 Kumamoto bulletins have unreadable text layers (the other bulletins of
  the series are NILIM/BRI joint reports); `h21hyougo/h21hyougo1.pdf` page 4 contains an uncredited
  narrative passage that reads like quoted press text (「…抜本的な改修工事が必要という。」「川底に堆積
  （たいせき）した土砂を除去し」).
- Every 国総研資料 colophon also carries NILIM's own mark and a contact for reprint requests
  (「編集・発行 ©国土技術政策総合研究所」「本資料の転載・複写の問い合わせは」). This was not treated as a
  restriction: it names NILIM, the default rights holder under its terms, and asks for no approval.

The scan is a reading of the text, not legal advice, and it can miss notices that exist only as
images or on pages without text.

## Getting and checking the original PDF

`source_url` is the official PDF. Download it and compare its SHA-256 with `source_pdf_sha256`
(and its size with `source_pdf_bytes`). If they differ, NILIM has replaced the file since
2026-10-06 and the text may not match. `page_number` is the page index in that PDF.

```sh
curl -sO "https://www.nilim.go.jp/lab/bcg/siryou/tnn/tnn1320pdf/ks1320_01.pdf"
sha256sum ks1320_01.pdf   # f165fddaf8d7b1159aafabcd430842dadad4fc2919895e2038f522137f27f5e8
```

## Licence

This dataset is published under `license: other`, not CC BY 4.0, because the rights review does
not support a single CC BY licence for all included text. Full quotations are in `LICENSE`.

NILIM's terms (「リンク・著作権等について」, https://www.nilim.go.jp/aboutlink.htm, read on
2026-10-07, Last-Modified 2025-12-19) say, quoted exactly (the duplicated 「は、の」 is in the original):

> 国土技術政策総合研究所ウェブサイト及び国土技術政策総合研究所のソーシャルメディアアカウントで掲載・発信している情報（以下「コンテンツ」といいます。）は、の著作権は、特記されていない限り国土技術政策総合研究所に帰属し、権利表記の記載がない限り「公共データ利用規約（第1.0版）」（PDL1.0）に準拠した利用条件の下で、利用することができます。

(In English: unless otherwise stated, the copyright of content on the NILIM website belongs to
NILIM, and unless there is a rights notice it may be used under the Public Data License 1.0,
https://www.digital.go.jp/resources/open_data/public_data_license_v1.0. PDL1.0 is compatible with
CC BY 4.0.) The same page asks for the source in the form
「出典：「○○動向調査」（国土技術政策総合研究所） （当該ページのURL）（○年○月○日に利用）」 and, when content is
edited, a separate statement that it was edited, without presenting the result as made by the
government.

What this means here:

- Text of NILIM-only reports and bulletins (classes a and b, 28 reports, 67 PDFs, 914 pages) is
  NILIM content under PDL1.0. Credit lines in the text name the owners of figures that are not
  included.
- Text of joint publications (class c, 102 reports, 426 PDFs, 9,334 pages) is co-owned by NILIM and
  the institutes, societies or universities named in `RIGHTS_REVIEW.tsv`, and the colophons carry
  their copyright marks. The NILIM terms are the published terms of the site that distributes these
  PDFs, but they speak only for NILIM; the co-publishers' own terms were not checked for this
  dataset. Use of these parts is at your own judgement; you may need to check the co-publisher's
  terms (for example PWRI or BRI) or ask them.
- Class d text (61 PDFs, 478 pages, most of them empty pages) could not be assessed.
- Reports that reserve all rights (798, 868, 875, 1042) are not included.

To use only NILIM-only text, filter on the classes in `RIGHTS_REVIEW.tsv` (join on `source_url`).
The compiler (yuiseki) claims no rights of its own in the compilation and gives no warranty.

## Attribution

In the form requested by the NILIM terms (出典 and a note on editing):

> 出典：「国総研資料（災害調査報告）」（国土技術政策総合研究所）（https://www.nilim.go.jp/lab/bbg/saigai/TEC-FORCE.html）（2026年10月6日〜7日に利用）
> 出典：「国内で生じた災害の調査報告」（国土技術政策総合研究所）（https://www.nilim.go.jp/lab/bbg/saigai/index.html）（2026年10月6日〜7日に利用）
> 国土技術政策総合研究所の各PDF（各行の source_url）の文字層から pdftotext で本文を抽出し、yuiseki がページ単位の JSONL に収録したもの（Hugging Face: yuiseki/nilim-disaster-reports）を加工して作成。本文の訂正・正規化は行っていない。共同刊行の報告は土木研究所・建築研究所等との共同著作物である。

In English: Source: NILIM disaster survey reports (国総研資料) and field-survey bulletins, National
Institute for Land and Infrastructure Management, MLIT (index URLs above). Text extracted with
pdftotext from each PDF's text layer and compiled into page-level JSONL by yuiseki
(yuiseki/nilim-disaster-reports); not corrected or normalised; not made or endorsed by NILIM or the
co-publishing institutes. When you cite one report, cite the report itself (authors, title,
report number, year; for joint publications also the co-publisher's report number) and give its
`source_url`.
