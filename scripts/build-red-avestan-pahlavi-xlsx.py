"""Build an Excel alignment of the red Avestan forms in GitHub.docx (Y 9.8, 9.10)."""

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


WORKSPACE = Path(__file__).resolve().parent.parent
OUTPUT = WORKSPACE / "Y9.8-Y9.10-red-Avestan-Pahlavi.xlsx"

# The red spans were read from GitHub.docx. A partial form records cases where
# the document colors only the stem rather than the whole inflected word.
ROWS = [
    ("Y9.8a", "janat̰", "janat̰", "zad", "high", "finite verb: ‘killed’"),
    ("Y9.8a", "ažīm", "ažīm", "az ī", "high", "first member of Aži Dahāka"),
    ("Y9.8a", "dahākəm", "dahākəm", "dahāg", "high", "Aži Dahāka"),
    ("Y9.8a", "ϑri.zafanəm", "ϑri.zafanəm", "sē zafar", "high", "‘three-jawed’"),
    ("Y9.8a", "ϑri.kamərəδəm", "ϑri.kamərəδəm", "sē kamāl", "high", "‘three-headed’"),
    ("Y9.8a", "xšuuaš.ašīm", "xšuuaš.ašīm", "šaš aš", "high", "‘six-eyed’"),
    ("Y9.8a", "hazaŋhrā.yaōxštīm", "hazaŋhrā.yaōxštīm", "hazār wizōstār", "high", "‘of a thousand powers/skills’"),
    ("Y9.8b", "daēuuīm", "daēuuīm", "dēw", "high", "‘demonic’"),
    ("Y9.8b", "drujim", "drujim", "druz", "high", "first occurrence in Y9.8b"),
    ("Y9.8b", "gaēϑ", "gaēϑāuuiiō", "gēhānān", "medium", "only the stem gaēϑ- is red in the DOCX"),
    ("Y9.8b", "druuaṇtəm", "druuaṇtəm", "druwand", "high", "‘possessing the Lie; wicked’"),
    ("Y9.8c", "drujim", "drujim", "druz", "high", "second occurrence, in Y9.8c"),
    ("Y9.8c", "kərəṇtat̰", "kərəṇtat̰", "kirrēnīd", "high", "‘fashioned/formed’"),
    ("Y9.8c", "aŋhrō", "aŋhrō", "gannāg", "high", "first member of Aŋhra Maińiiu"),
    ("Y9.8c", "maińiiuš", "maińiiuš", "mēnōy", "high", "second member of Aŋhra Maińiiu"),
    ("Y9.8c", "mahrkāi", "mahrkāi", "margīh", "high", "Pahlavi construction: pad margīh"),
    ("Y9.8c", "aṣ̌a", "aṣ̌ahe", "ahlāyīh", "medium", "only the stem aṣ̌a- is red in the DOCX"),
    ("Y9.10b", "ϑritō", "ϑritō", "Srid", "high", "personal name Thrita"),
    ("Y9.10b", "sāmanąm", "sāmanąm", "Sāmān", "high", "‘of the Sāmas’"),
    ("Y9.10b", "aṣ̌iš", "aṣ̌iš", "tarsagāhīh", "medium", "contextual rendering in this Pahlavi passage"),
    ("Y9.10b", "āiiaptəm", "āiiaptəm", "ābādīh", "high", "‘benefit/prosperity’"),
    ("Y9.10c", "puϑra", "puϑra", "dō pus", "high", "dual ‘two sons’"),
    ("Y9.10c", "zaiiōiϑe", "us.zaiiōiϑe", "ul zād hēnd", "high", "red portion excludes the prefix us.-"),
    ("Y9.10c", "uruuāxšaiiō", "uruuāxšaiiō", "Urwāš", "high", "personal name Urvāxšaya"),
    ("Y9.10c", "kərəsāspasca", "kərəsāspasca", "ud Kirsāsp", "high", "name plus enclitic -ca ‘and’"),
    ("Y9.10d", "t̰kaēšō", "t̰kaēšō", "dādwar", "medium", "contextual rendering; ritual/legal specialist"),
    ("Y9.10e", "uparō", "uparō.kairiiō", "abarkār", "medium", "first member of the compound"),
    ("Y9.10e", "kairiiō", "uparō.kairiiō", "ǰuyān", "low", "TITUS prints ‘abarkār X ǰuyān’; correspondence is uncertain"),
    ("Y9.10e", "gaēsuš", "gaēsuš", "gēswar", "high", "‘long-/curly-haired’"),
    ("Y9.10e", "gaδauuarō", "gaδauuarō", "gadwar", "high", "‘club-bearing’"),
    # Citation/lemma forms supplied by Encyclopaedia Iranica. Orthographic
    # variants of forms already above are not duplicated as separate lexemes.
    ("Y9.8a", "aži", "aži (citation form)", "az", "medium", "Iranica citation form ‘snake/dragon’; MP correspondence is contextual"),
    ("Y9.8a", "Aži Dahāka", "Aži Dahāka (name)", "Az[i]dahāg / Dahāg", "high", "Iranica explicitly gives the Pahlavi forms"),
    ("Y9.8a", "aš.aojaŋhəm", "aš.aojaŋhəm", "adādag ī pad gōhrag", "medium", "not red in the DOCX; Iranica glosses it ‘very strong’; Pahlavi is the contextual Y9.8a rendering"),
    ("Y9.8a", "jan-/γn-", "jan-/γn- (verbal root)", "zan-/zad", "medium", "Iranica identifies the root ‘strike, kill’; zad is the Y9.8a Pahlavi preterite"),
    ("Y9.10b", "Θrita", "Θrita (citation form)", "Srid", "high", "Iranica citation form of the name represented by inflected ϑritō"),
    ("Y9.10c", "Uruuāxšaiia", "Uruuāxšaiia (citation form)", "Urwāš", "high", "Iranica citation form of the name"),
    ("Y9.10c", "Kərəsāspa", "Kərəsāspa (citation form)", "Kirsāsp", "high", "Iranica citation form of the name"),
]

PAHLAVI = {
    "Y9.8a": "kē =š zad az ī dahāg ī sē zafar ī sē kamāl ī šaš aš ī hazār wizōstār adādag ī pad gōhrag",
    "Y9.8b": "ī wasōz dēw druz ī wattar ō gēhānān zyāngār ud druwand",
    "Y9.8c": "kē =š wasōztom druz frāz kirrēnīd gannāg mēnōy abar ō astōmandān gēhān pad margīh ī ān ahlāyīh gēhān",
    "Y9.10b": "Srid ī Sāmān ī sūdxwāstār ... ōy ān tarsagāhīh kird ō ōy mad ābādīh",
    "Y9.10c": "kū az ōy dō pus ul zād hēnd Urwāš ud Kirsāsp",
    "Y9.10d": "dādwar any būd Urwāš kū =š wizīr ud dādwarīh kird",
    "Y9.10e": "ān any abarkār X ǰuyān gēswar ud gadwar Kirsāsp kū =š kār pad gad wēš kird",
}


def cell(ref, value, style=0):
    return f'<c r="{ref}" t="inlineStr" s="{style}"><is><t>{escape(str(value))}</t></is></c>'


headers = ["Passage", "Avestan form", "Full/citation form", "Pahlavi correspondence", "Confidence", "Alignment note", "Corresponding Pahlavi passage", "Source"]
sheet_rows = ['<row r="1">' + ''.join(cell(f"{chr(65+i)}1", h, 1) for i, h in enumerate(headers)) + '</row>']
for number, row in enumerate(ROWS, 2):
    is_iranica = "Iranica" in row[5]
    source = (
        "Encyclopaedia Iranica, AŽDAHĀ i. In Old and Middle Iranian"
        if is_iranica
        else "GitHub.docx (red formatting); TITUS Pahlavi Yasna 9"
    )
    values = list(row) + [PAHLAVI[row[0]], source]
    sheet_rows.append(f'<row r="{number}">' + ''.join(cell(f"{chr(65+i)}{number}", value, 2 if i in {5, 6, 7} else 0) for i, value in enumerate(values)) + '</row>')

sheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <dimension ref="A1:H{len(ROWS)+1}"/>
 <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
 <cols><col min="1" max="1" width="13" customWidth="1"/><col min="2" max="3" width="24" customWidth="1"/><col min="4" max="4" width="25" customWidth="1"/><col min="5" max="5" width="13" customWidth="1"/><col min="6" max="6" width="45" customWidth="1"/><col min="7" max="7" width="90" customWidth="1"/><col min="8" max="8" width="55" customWidth="1"/></cols>
 <sheetData>{''.join(sheet_rows)}</sheetData><autoFilter ref="A1:H{len(ROWS)+1}"/>
</worksheet>'''

parts = {
    "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>''',
    "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
    "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Red Avestan–Pahlavi" sheetId="1" r:id="rId1"/></sheets></workbook>''',
    "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>''',
    "xl/styles.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF7F0000"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf></cellXfs></styleSheet>''',
    "xl/worksheets/sheet1.xml": sheet,
}

with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
    for name, content in parts.items():
        archive.writestr(name, content.encode("utf-8"))

print(f"Wrote {len(ROWS)} red-form alignments to {OUTPUT}")
