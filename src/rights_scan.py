"""Rights scan of the extracted page text: one row per PDF in data/hf/RIGHTS_REVIEW.tsv.

The script counts lines that look like rights signals in each PDF's text and joins them with the
reviewer's decision for the whole report (classes below). The decisions were made by reading the
covers, front matter, author lists and colophons of every report and the context of the hits; they
are written in TNN and FLASH below so that the table can be rebuilt and checked.

    a  no other rights notice found
    b  figures/photos credited to others only (the text is NILIM's; the credit lines stay in the text)
    c  a rights notice or reprint restriction covering the whole report, or joint authorship or
       publication with another organisation
    d  unclear (no readable text, or text that may be quoted from others without credit)

Publication follows the classes: only classes a and b (NILIM's own works) are published. Every PDF
of a class c or d report is excluded, and this script writes data/hf/EXCLUDE.txt from the review
with one reason block per report (the merge reads that file and checks it against the review).

    python3 src/rights_scan.py    # writes data/hf/RIGHTS_REVIEW.tsv and data/hf/EXCLUDE.txt
"""
import argparse
import csv
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from merge_jsonl import CLASSES, SERIES, atomic_write, document_lines, plan  # noqa: E402

REPO=Path(__file__).resolve().parents[1]
PUBLISH_CLASSES=('a','b')
CLASS_NAMES={'a':'no other rights notice found','b':'figures/photos credited to others only',
             'c':'joint publication, co-authorship or rights notice of another party','d':'unclear'}
COLUMNS=['source_type','report_id','section','source_url','pages','empty_pages','class','other_parties','basis','evidence',
         'reserved_lines','copyright_lines','survey_lines','credit_lines','joint_lines','first_hit','excluded']

# Line patterns, strongest first. "(c)" sub-figure labels and the colophon's "本資料の転載・複写の問い合わせは"
# (a contact for reprint requests, not a restriction) are deliberately not matched.
SIGNALS={
    'reserved':re.compile(r'All rights reserved|無断(?:転載|複製|複写|使用)|転載を禁|複製を禁|承認を得ずして|許諾なく'),
    'copyright':re.compile(r'©|Ⓒ|Copyright|COPYRIGHT|著作権'),
    'survey':re.compile(r'測量法|承認番号|国土地理院|地理院地図|地理院タイル|電子国土|基盤地図情報'),
    'credit':re.compile(r'提供|出典|撮影|転載|引用|Google|ZENRIN|ゼンリン'),
    'joint':re.compile(r'土木研究所|建築研究所|港湾空港技術研究所|海上・港湾・航空技術研究所|P\.?W\.?R\.?I|\bBRI\b|\bPARI\b|MPAT'
                       r'|大学|学会|協会|研究機構|ベターリビング|コンソーシアム|高等専門学校|共同|合同'),
}

PWRI='国立研究開発法人土木研究所 (PWRI)'
BRI='国立研究開発法人建築研究所 (BRI)'
JOINT_TNN='joint publication: co-published as another institute\'s report series, with that institute\'s © in the colophon'

# Decisions per 国総研資料 report_id: (class, other parties, basis, evidence quoted from the text).
TNN={
    '1320':('c',PWRI,JOINT_TNN,'ks1320_22.pdf p1 奥付: 「編集・発行 c 国土技術政策総合研究所 ○ c 国立研究開発法人土木研究所」 (© drawn as c+○); cover: 「土研資料 第 4459 号」'),
    '1151':('c',PWRI,JOINT_TNN,'ks1151_15.pdf p1 奥付: 「編集・発行 ©国土技術政策総合研究所 ©国立研究開発法人土木研究所」'),
    '758':('b','九州地方整備局; 江口希之建築都市研究所','NILIM authors only; photos/figures credited to others','ks075806.pdf p14: 「※九州地方整備局より提供」; ks075812.pdf p4: 「出典：一級建築士事務所 江口希之建築都市研究所」'),
    '115':('d','','no text layer: all 80 pages are empty, so cover, author list and colophon could not be read',''),
    '133':('d','','no text layer: all 88 pages are empty, so cover, author list and colophon could not be read',''),
    '233':('d','','no text layer: all 167 pages are empty, so cover, author list and colophon could not be read',''),
    '248':('c',f'{PWRI}; {BRI}','joint survey and authorship by three institutes (author list includes PWRI staff); a figure page also carries a PWRI copyright line','ks0248002.pdf p1: 「国土技術政策総合研究所、独立行政法人土木研究所、独立行政法人建築研究所の３機関が合同で地震被害状況調査を行った結果をとりまとめたものである。」; ks0248007.pdf p3: 「Copyright© 2004 Public Works Research Institute」'),
    '250':('c',f'{PWRI}; 東京大学, 広島大学, 九州大学, 日本大学, 東洋大学; 九州地方整備局','proceedings of a joint meeting; papers by universities and PWRI','ks0250002.pdf p1: 「この報告書には、同報告会において国土技術政策総合研究所、独立行政法人土木研究所、東京大学、広島大学、九州大学、日本大学、東洋大学、九州地方整備局の専門家らにより行われた調査報告と総合討論を収録した。」'),
    '273':('b','気象庁; 菜生海岸災害調査検討委員会','NILIM authors only; tables/figures credited to others','ks0273004.pdf p2: 「（出典：気象庁 HP）」; p19: 「（出典：菜生海岸災害調査検討委員会資料）」'),
    '415':('c',BRI,JOINT_TNN,'ks041514.pdf p1 奥付: 「編 集･発 行 ©国 土 技 術 政 策 総 合 研 究 所 ©独 立 行 政 法 人 建 築 研 究 所」'),
    '430':('c',BRI,JOINT_TNN,'ks043013.pdf p1 奥付: 「©独 立 行 政 法 人 建 築 研 究 所」'),
    '438':('c',f'{PWRI}; {BRI}',JOINT_TNN,'ks043816.pdf p1 奥付: 「編集・発行 Ⓒ 国土技術政策総合研究所 Ⓒ 独立行政法人土木研究所 Ⓒ 独立行政法人建築研究所」'),
    '439':('c',PWRI,'companion of 438; cover and colophon have no text, and the author list (text layer with wrong code points) repeats the code-point string that 438\'s author list uses for 独立行政法人土木研究所','ks043904.pdf p1: 「⁛┙ⴕ᡽ᴺੱ࿯ᧁ⎇ⓥᚲ」 (= 独立行政法人土木研究所 in 438 ks043804.pdf p1, whose cover ks043801.pdf names PWRI and BRI)'),
    '481':('c',BRI,JOINT_TNN,'ks048116.pdf p1 奥付: 「©独 立 行 政 法 人 建 築 研 究 所」'),
    '486':('c',f'{PWRI}; {BRI}',JOINT_TNN,'ks048615.pdf p1 奥付: 「編集・発行 © 国土技術政策総合研究所 © 独立行政法人土木研究所 © 独立行政法人建築研究所」'),
    '636':('c',BRI,JOINT_TNN,'ks063621.pdf p2 奥付: 「編集･発行 ©国 土技 術 政策総 合研 究所 ©独立行 政法 人建 築研 究所」; cover ks063601.pdf: 「建築研究資料 第 132 号」'),
    '646':('c',PWRI,JOINT_TNN+'; geological map figures used under an AIST approval','ks064616.pdf p1 奥付: 「編集・発行 ©国土技術政策総合研究所 ©独立行政法人土木研究所」; ks064606.pdf p4: 「産総研承認番号:第60635500-A-20110728-002号」'),
    '658':('b','国土地理院 (電子国土); Google','NILIM authors only; base maps and images credited to others','ks0658.pdf p8: 「背景図出典：電子国土」; p9: 「出典：GoogleEarth」'),
    '680':('c','独立行政法人港湾空港技術研究所 (PARI)','co-authorship: one of the four authors is a PARI researcher (the others are NILIM and MLIT staff); a photo is also credited to GSI','ks0680.pdf p2: 「坪川将丈 * ・水上純一 ** ・畑伊織 *** ・前川亮太 ****」「**** 独立行政法人港湾空港技術研究所 構造研究領域 空港舗装研究チーム 主任研究官」'),
    '703':('c',BRI,JOINT_TNN,'ks070313.pdf p1 奥付: 「編集・発行 ©国土技術政策総合研究所 ©独立行政法人建築研究所」'),
    '726':('a','','NILIM authors only (strong-motion records of MLIT stations); no credit to others found',''),
    '728':('c',PWRI,'joint publication: also 土研資料 No.4260, cover names PWRI as co-publisher; the colophon PDF is missing at the source (404)','ks072801.pdf p1: 「土木資料 第 4260 号」「独立行政法人土木研究所」'),
    '781':('b','国土地理院; Google; 富田孝史 (photographer)','NILIM authors only; aerial photos, base maps and one photo credited to others','ks0781.pdf p13: 「出典：国土地理院「被災地域の斜め写真」（2011年6月8日撮影）」; p19: 「（2011 年 3 月 18 日，富田孝史氏撮影，地点 2-d 付近）」'),
    '798':('c','国立研究開発法人港湾空港技術研究所 (PARI)','joint publication with PARI, whose colophon reserves all rights and forbids reprinting or copying any part without written approval','ks079843.pdf p1: 「Copyright ○ C （2015）by PARI」「All rights reserved. No part of this book must be reproduced by any means without the written permission of the President of PARI」「本報告書の全部または一部の転載、複写は港湾空港技術研究所理事長の文書による承認を得ずしてこれを行ってはならない。」'),
    '814':('c',PWRI,JOINT_TNN,'ks081412.pdf p1 奥付: 「編集・発行 ©国土技術政策総合研究所 ©独立行政法人土木研究所」'),
    '868':('c',PWRI,'joint publication; the cover verso reserves all rights for NILIM and PWRI and forbids reprinting or copying any part without written approval','ks086801.pdf p2: 「Copyright © (2015) by N.I.L.I.M. and P.W.R.I.」「All rights reserved.」「本報告書の全部又は一部の転載、複製は、国土交通省国土技術政策総合研究所所長及び国立研究開発法人土木研究所理事長の文書による承認を得ずしてこれを行ってはならない。」'),
    '875':('c',PWRI,'joint publication; the cover verso reserves all rights for NILIM and PWRI and forbids reprinting or copying any part without written approval','ks087501.pdf p2: 「Copyright © (2015) by N.I.L.I.M and P.W.R.I.」「All rights reserved.」「本報告書の全部又は一部の転載、複製は、国土技術政策総合研究所所長、国立研究開発法人土木研究所理事長の文書による承認を得ずしてこれを行ってはならない。」'),
    '936':('b','山口県; 萩市; 国土地理院','NILIM authors only; figures and photos credited to others','ks093605.pdf p7: 「（山口県提供）」; p9: 「（※地理院地図（http://maps.gsi.go.jp/）を元に作成）」'),
    '967':('c',PWRI,JOINT_TNN,'ks096715.pdf p1 奥付: 「編集・発行 c 国土技術政策総合研究所 ○ c 国立研究開発法人土木研究所」'),
    '980':('c',BRI,JOINT_TNN,'ks098014.pdf p1 奥付: 「編集・発行 ©国土技術政策総合研究所 ©国立研究開発法人建築研究所」'),
    '1042':('c','国立研究開発法人海上・港湾・航空技術研究所 (MPAT)','joint publication with MPAT (港湾空港技術研究所資料 No.1348), whose colophon reserves all rights and forbids reprinting or copying any part without written approval','ks1042.pdf p54: 「Copyright ○EC （2018）by MPAT」「All rights reserved.」「本報告書の全部または一部の転載、複写は海上・港湾・航空技術研究所理事長の文書による承認を得ずしてこれを行ってはならない。」'),
    '1069':('c',PWRI,JOINT_TNN,'ks106911.pdf p1 奥付: 「編集・発行 ©国土技術政策総合研究所 ©国立研究開発法人土木研究所」'),
    '1111':('c',f'{PWRI}; {BRI}',JOINT_TNN,'ks1111_15.pdf p1 奥付: 「編集・発行 ©国土技術政策総合研究所 ©国立研究開発法人土木研究所 ©国立研究開発法人建築研究所」'),
    '1202':('b','国土地理院','NILIM authors only; maps and aerial photos credited to GSI','ks1202.pdf p44: 「出典：地図・空中写真閲覧サービス 出典：地理院地図」'),
    '1356':('c',f'{BRI}; universities and private companies (authors)',JOINT_TNN+'; the author list also names university and company authors','ks1356_21.pdf p1 奥付: 「©国立研 究開 発法 人建 築研究 所」; ks1356_04_1.pdf p1: 「河合直人 工学院大学」「五十田博 京都大学」'),
}

C_FLASH=(BRI,'joint authorship: NILIM and BRI named as authors on page 1')
# Decisions per bulletin, keyed by the URL path under https://www.nilim.go.jp/lab/bbg/saigai/.
# Evidence None for class c: the first line of page 1 that names another organisation is quoted.
FLASH={
    'R8/kumamototekkinkonkurito.pdf':C_FLASH,
    'R8/kumamototetsukotsuzou.pdf':C_FLASH,
    'R8/kumamotokisojiban.pdf':C_FLASH,
    'R8/kumamotohikouzoubuzai.pdf':C_FLASH,
    'R8/kumamotokawarayanetyousa.pdf':C_FLASH,
    'R8/kumamotomokuzoutyousa.pdf':C_FLASH,
    'R8/kumamotomenshintyosa.pdf':(f'{BRI}; 日本免震構造協会; 福岡大学; 東京科学大学','joint authorship: NILIM and BRI named as authors; society and university members in the survey team'),
    'R7/oitakasaityousa.pdf':C_FLASH,
    'R7/notosetsubityousa.pdf':(f'{BRI}; 空気調和・衛生工学会; 建築設備技術者協会; 建築研究開発コンソーシアム','joint authorship: five organisations named as authors on page 1'),
    'R7/tsukubatatsumaki.pdf':C_FLASH,
    'R7/makinoharatatsumaki.pdf':C_FLASH,
    'R7/ofunatokasai.pdf':(f'{BRI}; 東京科学大学','joint authorship: NILIM and BRI, one author at a university'),
    'R5/notojishin07.pdf':C_FLASH,
    'R5/notojishin06.pdf':C_FLASH,
    'R5/notojishin03.pdf':C_FLASH,
    'R5/notojishin04.pdf':C_FLASH,
    'R5/notojishin05.pdf':C_FLASH,
    'R5/notojishin02.pdf':C_FLASH,
    'R5/notojishin.pdf':C_FLASH,
    'R4/fukushimajishin_2.pdf':C_FLASH,
    'R4/fukushimajishin_1.pdf':(f'{BRI}; 空気調和・衛生工学会','joint authorship: three organisations named as authors on page 1'),
    'R3/fukushimajishin.pdf':C_FLASH,
    'R2/fukushimajishin.pdf':C_FLASH,
    'R1/taihu19_2.pdf':C_FLASH,
    'R1/taihu19.pdf':C_FLASH,
    'R1/taihu15.pdf':C_FLASH,
    'h30/iburi3.pdf':(f'{BRI}; 一般財団法人ベターリビング','joint authorship: three organisations named as authors on page 1'),
    'h30/iburi2.pdf':(f'{BRI}; 一般財団法人ベターリビング; 北海道立総合研究機構','joint authorship: four organisations named as authors on page 1'),
    'h30/typhoon21.pdf':C_FLASH,
    'h30/iburi-ekijyouka.pdf':(f'{PWRI}; {BRI}','joint expert team of NILIM, PWRI and BRI named on page 1'),
    'h30/iburi.pdf':(f'{BRI}; 北海道立総合研究機構建築研究本部','joint authorship: BRI first, NILIM and the Hokkaido research organisation'),
    'h30/maibara.pdf':C_FLASH,
    'h28/itoigawa01.pdf':C_FLASH,
    'h28/tottori01.pdf':C_FLASH,
    'h28/20160803kumamotokentiku11.pdf':C_FLASH,
    'h28/20160608kumamotokentiku10.pdf':C_FLASH,
    'h28/20160524kumamotokentiku9.pdf':C_FLASH,
    'h28/20160429kumamotokentiku8.pdf':('d','','text layer unreadable (Japanese characters missing), authors cannot be read; the other reports of this NILIM/BRI series are joint',''),
    'h28/20160426kumamotokentiku7.pdf':C_FLASH,
    'h28/20160428kumamotokentiku6.pdf':('d','','text layer unreadable (wrong code points), authors cannot be read; the other reports of this NILIM/BRI series are joint',''),
    'h28/20160428kumamotokentiku5.pdf':C_FLASH,
    'h28/20160420kumamotokentiku4.pdf':('d','','text layer unreadable (Japanese characters missing), authors cannot be read; the other reports of this NILIM/BRI series are joint',''),
    'h28/20160417kumamotokentiku3.pdf':('d','','text layer mostly unreadable, authors cannot be read; the other reports of this NILIM/BRI series are joint',''),
    'h28/20160416kumamotokentiku2.pdf':('d','','text layer unreadable (Japanese characters missing), authors cannot be read; the other reports of this NILIM/BRI series are joint',''),
    'h28/20160421kumamotogesuidou.pdf':('a','','NILIM (下水道研究部) only; no credit to others found',''),
    'h28/20160415kumamotokentiku.pdf':('d','','text layer unreadable (Japanese characters missing), authors cannot be read; the other reports of this NILIM/BRI series are joint',''),
    'h27/20150910kinugawa.pdf':C_FLASH,
    'h27/20150915serisawa.pdf':(PWRI,'joint authorship: NILIM and PWRI named as authors on page 1'),
    'h27/20150722takamatsu.pdf':('b','気象庁','NILIM only; figures credited to JMA','p4: 「図－３ 台風 1511 号の諸元（気象庁速報値，左図：経路図，右図：中心気圧）」'),
    'h26/20150218ishinomaki.pdf':(PWRI,'joint authorship: NILIM and PWRI named as authors on page 1'),
    'h26/150114_nemuro_engan_bosai.pdf':('港湾空港技術研究所 (PARI); 土木研究所寒地土木研究所 (PWRI); 北海道開発局','joint survey team of three institutes and the Hokkaido bureau named on page 1'),
    'h26/141219_nemuro_engan_bosai.pdf':('港湾空港技術研究所 (PARI); 土木研究所寒地土木研究所 (PWRI); 北海道開発局','joint survey team of three institutes and the Hokkaido bureau named on page 1'),
    'h26/141129nagano_juutaku2.pdf':C_FLASH,
    'h26/141126nagano_kenchiku.pdf':C_FLASH,
    'h26/141124nagano_juutaku.pdf':C_FLASH,
    'h26/140928ontake.pdf':(PWRI,'survey by NILIM with PWRI researchers (no separate author line)'),
    'h26/140916hiroshima_kenchiku.pdf':C_FLASH,
    'h26/140822hiroshima_kabehigashi.pdf':('a','','NILIM (土砂災害研究部) only; no credit to others found',''),
    'h26/140822hiroshima_heli.pdf':('a','','NILIM (土砂災害研究部); a 中国地方整備局 (MLIT) officer in the survey team; no credit to others found',''),
    'h26/140821hiroshima_yagi.pdf':('a','','NILIM (土砂災害研究部) only; no credit to others found',''),
    'h26/140820hiroshima_yagi.pdf':('a','','NILIM (土砂災害研究部) only; no credit to others found',''),
    'h26/140612yokosuka.pdf':('a','','NILIM (土砂災害研究部) only; no credit to others found',''),
    'h25typhoon26/131018izuoshima.pdf':('a','','NILIM (砂防研究室) only; no credit to others found',''),
    'h25typhoon26/131018izuoshima_betten.pdf':('a','','attachment of the NILIM izuoshima report (no author line); no credit to others found',''),
    'h25typhoon18/130920shiga_ritto.pdf':(PWRI,'joint survey report of NILIM and PWRI (title says 国総研・土研)'),
    'h25typhoon18/130927_suigai.pdf':('a','','NILIM (水害研究室) only; no credit to others found',''),
    'h25typhoon18/130924fukui_obama.pdf':('b','国土地理院 (電子国土); 福井県 (survey participants)','written by NILIM staff; base map credited to 電子国土','p1: 「130924 国総研砂防研蒲原・江川・廣井作成」; p3: 「背景図は電子国土を利用」'),
    'h25koshigaya/130904tatsumaki.pdf':C_FLASH,
    'h25akita/130813akita_senboku.pdf':('a','','NILIM (砂防研究室) report; survey team includes MLIT and prefecture officers; no credit to others found',''),
    'h25niigata/20130802teradomari_yamada.pdf':(f'{PWRI}; 日本地すべり学会 (committee)','joint authorship: PWRI first, NILIM second, survey under a landslide society committee'),
    'h25yamaguchi/20130805suigai_result.pdf':('a','','NILIM (水害研究室) only; no credit to others found',''),
    'h25awaji/20130416awaji.pdf':C_FLASH,
    'h24ehime/20120911ehime_saijyoshi.pdf':(PWRI,'joint survey with a PWRI researcher listed first (no separate author line)'),
    'h24shiga/h24shiga.pdf':('c',PWRI,'joint authorship: NILIM and PWRI researchers named on page 1','p1: 「国総研砂防研究室 野村研究官」「土研火山・土石流 石塚上席研究員」'),
    'h24kumamoto/120728kawabegawa.pdf':(PWRI,'joint authorship: PWRI and NILIM named on page 1'),
    'h24kumamoto/aso120717.pdf':(PWRI,'joint survey teams of NILIM and PWRI named on page 1'),
    'h24oita/takemotokawa.pdf':('c',PWRI,'joint authorship: NILIM and PWRI researchers named on page 1','p1: 「国総研砂防研究室 岡本室長」「土研火山・土石流 武澤研究員」'),
    'h24tsukuba/h24tsukuba.pdf':C_FLASH,
    'h24tsukuba/h24tsukuba-e.pdf':(BRI,'joint authorship: NILIM and BRI named on page 1 (English version)'),
    'h24tsukuba/wind20130109.pdf':C_FLASH,
    'h24shimane/h24shimane.pdf':('b','出雲市立第二中学校; Google','NILIM author only; photos and a map credited to others','p4: 「出雲市立第二中学校 提供」; p3: 「（Google マップに加筆。…）」'),
    'h23kochi/h23kochi.pdf':(PWRI,'joint survey report: PWRI and NILIM researchers named as 調査実施者'),
    'h22amami/101031amami_report.pdf':(PWRI,'joint report of NILIM and PWRI named on page 1'),
    'h22shimane/h22shimane_saigai.pdf':('a','','NILIM (砂防研究室) only; no credit to others found',''),
    'h22shobara/h22shobara_saigai.pdf':(PWRI,'joint report of NILIM and PWRI named on page 1'),
    'h22yamaguchi/h22yamaguchi.pdf':('b','気象庁','NILIM (水害研究室) only; rainfall figure credited to JMA','p1: 「出典：気象庁 災害をもたらした気象事例」'),
    'h22gihu/h22gihu.pdf':('b','気象庁','NILIM (水害研究室) only; rainfall figure credited to JMA','p1: 「出典：気象庁 災害をもたらした気象事例」'),
    'h22kagoshima/h22kagoshima.pdf':('c',PWRI,'joint authorship: NILIM and PWRI researchers named on page 1','p1: 「国総研砂防研究室 小山内信智室長」「土研火山・土石流 武澤永純研究員」'),
    'h21mikawa/h21mikawa.pdf':('c','港湾空港技術研究所 (PARI, survey member); 中部地方整備局; 海上保安庁 (photos)','joint survey: a PARI researcher is listed first among the investigators (the header names only NILIM); photos credited to the Japan Coast Guard','p1: 「国土技術政策総合研究所は，独立行政法人港湾空港技術研究所及び国土交通省中部地方整備局とともに，…被害調査を行った」「（調査者）独立行政法人港湾空港技術研究所海洋・水工部海象情報研究チームリーダー」'),
    '091013tsuchiura-twister/091008tsuchiura-twister.pdf':(BRI,'joint authorship: one NILIM and one BRI author named on page 1'),
    'h21hyougo/h21hyougo3.pdf':('a','','no author line; listed by NILIM; no credit to others found',''),
    'h21hyougo/h21hyougo1.pdf':('d','','page 4 contains an uncredited narrative passage that reads like quoted press text','p4: 「水害を防ぐためには氾濫地点近くの川幅を変えるなどの抜本的な改修工事が必要という。」「川底に堆積（たいせき）した土砂を除去し」'),
    'h21hyougo/h21hyougo2.pdf':('明石工業高等専門学校 (survey member)','joint survey: a technical college professor listed with NILIM staff (no separate author line)'),
    'surugawan/surugawan.pdf':('b','防災科学技術研究所 (K-NET/KiK-net)','NILIM only; analysis of strong-motion records credited to NIED','p1: 「K-NET、KiK-net 記録（＊１）」「（独）防災科学技術研究所が運用している」'),
    'twister/tatebayashi.pdf':(BRI,'joint authorship: one NILIM and one BRI author named on page 1'),
    'twister/okayama.pdf':(BRI,'joint authorship: one NILIM and one BRI author named on page 1'),
    'h19toyota/toyota.pdf':(BRI,'joint survey: NILIM and BRI researchers named as 調査者'),
    'h19noto/noto-kenchiku.pdf':(BRI,'joint announcement of NILIM and BRI'),
    'miyagi-jishin/happyou.pdf':(f'国土交通省住宅局建築指導課; {BRI}','joint press release of the MLIT Housing Bureau, NILIM and BRI'),
    'miyagi-jishin/gaiyou.pdf':(f'国土交通省住宅局建築指導課; {BRI}','joint survey team of the MLIT Housing Bureau, NILIM and BRI'),
    'miyagi-jishin/tuuti.pdf':('c','国土交通省住宅局建築指導課','not a NILIM document: a technical advice notice issued by the MLIT Housing Bureau','p1: 「国住指第１４２７号」「国土交通省住宅局建築指導課長」'),
    'miyagi-jishin/houkoku.pdf':(f'国土交通省住宅局建築指導課; {BRI}','joint survey team of the MLIT Housing Bureau, NILIM and BRI'),
    'h17fukuoka/050325.pdf':C_FLASH,
    '2004924.pdf':('独立行政法人港湾空港技術研究所 (PARI)','joint press release of NILIM and PARI'),
    'h15tokachi/terminal030926.pdf':C_FLASH,
    'h15tokachi/kenchiku030926.pdf':(BRI,'joint authorship: one NILIM and one BRI author named on page 1'),
    'miyagi_0726/miyagi_0726.pdf':(PWRI,'joint authorship: NILIM and PWRI named on page 1'),
    'h15miyagi/chousa.pdf':C_FLASH,
    'h15dosha/minamata_dazaifu.pdf':(PWRI,'joint survey of NILIM and PWRI stated in the introduction'),
}
FLASH_PREFIX='https://www.nilim.go.jp/lab/bbg/saigai/'
# Two-element entries are class c with automatic evidence.
FLASH={k:(v if len(v)==4 else ('c',v[0],v[1],None)) for k,v in FLASH.items()}


def clean(text):
    return re.sub(r'\s+',' ',str(text)).strip()


def signals(line):
    return {k:int(bool(p.search(line))) for k,p in SIGNALS.items()}


def scan(pages):
    """Count matching lines per signal over the pages of one PDF and quote the strongest first hit."""
    counts={f'{k}_lines':0 for k in SIGNALS}; first={}
    for number,text in enumerate(pages,1):
        for line in text.split('\n'):
            for k,v in signals(line).items():
                if v:
                    counts[f'{k}_lines']+=1
                    first.setdefault(k,f'p{number}: {clean(line)[:160]}')
    counts['first_hit']=next((first[k] for k in SIGNALS if k in first),'')
    return counts


def decision(record,tnn,flash):
    if record['source_type']=='tnn': d=tnn.get(str(record['report_id']))
    else: d=flash.get(record['url'][len(FLASH_PREFIX):] if record['url'].startswith(FLASH_PREFIX) else record['url'])
    if d is None: raise ValueError(f'no rights decision for {record["source_type"]} {record["report_id"]}: {record["url"]}')
    if d[0] not in CLASSES: raise ValueError(f'unknown class {d[0]!r} for {record["url"]}')
    return d


def auto_evidence(page):
    for line in page.split('\n'):
        if SIGNALS['joint'].search(line): return f'p1: {clean(line)[:160]}'
    return ''


def build(data,hf,tnn=TNN,flash=FLASH):
    data=Path(data); hf=Path(hf); jroot=data/'jsonl'
    groups,_=plan(data)
    by_url={r['url']:r for s in SERIES for r in groups[s]}
    with (data/'catalog.tsv').open(encoding='utf-8',newline='') as f:
        catalog=list(csv.DictReader(f,delimiter='\t'))
    rows=[]
    for meta in catalog:
        record=by_url.get(meta['url'])
        if record is None: continue  # listed in source-missing.json
        cls,parties,basis,evidence=decision(record,tnn,flash)
        pages=[json.loads(line)['text'] for line in document_lines(jroot,record)]
        if evidence is None: evidence=auto_evidence(pages[0]) if cls=='c' else ''
        row=dict(source_type=record['source_type'],report_id=str(record['report_id']),section=meta['section'],source_url=meta['url'],
                 pages=record['pages'],empty_pages=record['empty_pages'],**{'class':cls},other_parties=parties,basis=basis,
                 evidence=evidence,**scan(pages),excluded='no' if cls in PUBLISH_CLASSES else 'yes')
        rows.append({k:clean(row[k]) for k in COLUMNS})
    atomic_write(hf/'RIGHTS_REVIEW.tsv','\t'.join(COLUMNS)+'\n'+''.join('\t'.join(r[k] for k in COLUMNS)+'\n' for r in rows))
    atomic_write(hf/'EXCLUDE.txt',exclude_text(rows))
    return rows


def exclude_text(rows):
    """EXCLUDE.txt: every PDF of a report outside PUBLISH_CLASSES, grouped by report with the reason."""
    out=['# Generated by src/rights_scan.py from RIGHTS_REVIEW.tsv; do not edit by hand.',
         '# PDFs left out of data/hf/{tnn,flash}.jsonl by src/merge_jsonl.py: one source_url per line;',
         '# blank lines and lines starting with # are ignored.',
         f'# Published: classes {", ".join(PUBLISH_CLASSES)} only (reports NILIM published alone with no other rights notice).',
         '# Left out: every PDF of a class c report (joint publication, co-authorship or rights notice of another',
         '# party) and of a class d report (unclear). To change this, change the decisions or PUBLISH_CLASSES',
         '# in src/rights_scan.py and run it again.']
    reports={}
    for r in rows:
        if r['excluded']=='yes': reports.setdefault((r['source_type'],r['report_id']),[]).append(r)
    for (kind,rid),group in reports.items():
        r=group[0]; cls=r['class']
        name=f'{kind} {rid}' if kind=='tnn' else f'{kind} {rid} ({r["source_url"].rsplit("/saigai/",1)[-1]})'
        pages=sum(int(x['pages']) for x in group)
        out+=['',f'# {name}: class {cls} ({CLASS_NAMES[cls]}); {len(group)} PDFs, {pages} pages; '
                 f'other parties: {r["other_parties"] or "-"}; basis: {r["basis"]}']
        if r['evidence']: out.append(f'#   evidence: {r["evidence"]}')
        reserved=[x for x in group if int(x['reserved_lines'])]
        for x in reserved:
            out.append(f'#   ALL RIGHTS RESERVED notice, reprint/copy forbidden without written approval: {x["source_url"].rsplit("/",1)[-1]} {x["first_hit"]}')
        out+=[x['source_url'] for x in group]
    return '\n'.join(out)+'\n'


def summary(rows):
    out={}
    for r in rows:
        key=(r['source_type'],r['class']); s=out.setdefault(key,dict(reports=set(),pdfs=0,pages=0))
        s['reports'].add(r['report_id']); s['pdfs']+=1; s['pages']+=int(r['pages'])
    return {f'{k[0]} {k[1]}':dict(reports=len(v['reports']),pdfs=v['pdfs'],pages=v['pages']) for k,v in sorted(out.items())}


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data',type=Path,default=REPO/'data')
    ap.add_argument('--hf',type=Path,default=REPO/'data/hf')
    args=ap.parse_args()
    rows=build(args.data,args.hf)
    print(json.dumps(summary(rows),ensure_ascii=False,indent=1))


if __name__=='__main__': main()
