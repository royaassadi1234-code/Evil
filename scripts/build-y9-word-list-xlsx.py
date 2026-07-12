"""Build an Excel list of every Avestan word occurrence in Yasna 9."""

import json
import html
import math
import re
import unicodedata
import urllib.request
import zipfile
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from xml.sax.saxutils import escape


WORKSPACE = Path(__file__).resolve().parent.parent
SOURCE = WORKSPACE / "CABLinguisticCorpus.json"
OUTPUT = WORKSPACE / "Y9-word-list.xlsx"
PY_SOURCE = WORKSPACE / "PY-Pt4.txt"
DICTIONARY_SOURCE = WORKSPACE / "mpcd-workspace-dictionary.json"
PASSAGE_PATTERN = re.compile(r"^Y9\.\d+[a-z]+$")
TITUS_Y9_URL = "https://titus.uni-frankfurt.de/texte/etcs/iran/miran/mpers/avpt/yvrpt/yvrpt010.htm"

# Only direct, high-confidence correspondences in the available PY 9.3 passage.
PAHLAVI_EQUIVALENTS = {
    ("Y9.3a", "aōxta"): "guft",
    ("Y9.3a", "zaraϑuštrō"): "zardušt",
    ("Y9.3a", "nəmō"): "namāz",
    ("Y9.3a", "haōmāi"): "hōm",
    ("Y9.3b", "kasə.ϑβąm"): "kē tō",
    ("Y9.3b", "paōiriiō"): "fradom",
    ("Y9.3b", "haōma"): "hōm",
    ("Y9.3b", "maṣ̌iiō"): "mardōmān",
    ("Y9.3b", "astuuaiϑiiāi"): "astōmandān",
    ("Y9.3b", "hunūta"): "hunīd hē",
    ("Y9.3b", "gaēϑaiiāi"): "gēhān",
    ("Y9.3b", "aṣ̌iš"): "nēkīh",
    ("Y9.3b", "jasat̰"): "mad",
    ("Y9.3b", "āiiaptəm"): "ābādīh",
}


def extract_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(item for item in value if isinstance(item, str))
    return ""


def collect_passages(node, passages):
    if isinstance(node, list):
        for item in node:
            collect_passages(item, passages)
        return
    if not isinstance(node, dict):
        return

    passage = str(node.get("xml:id", ""))
    text = " ".join(filter(None, (extract_text(node.get("#text")), extract_text(node.get("l")))))
    text = " ".join(text.split())
    if PASSAGE_PATTERN.fullmatch(passage) and text:
        passages.append((passage, text))

    for value in node.values():
        if isinstance(value, (dict, list)):
            collect_passages(value, passages)


def extract_words(text):
    words = []
    for token in text.split():
        start = 0
        end = len(token)
        while start < end and unicodedata.category(token[start])[0] not in {"L", "M"}:
            start += 1
        while end > start and unicodedata.category(token[end - 1])[0] not in {"L", "M"}:
            end -= 1
        if start < end:
            words.append(token[start:end])
    return words


def fetch_titus_y9_passages():
    """Return the Middle Persian translation keyed to the local Y9 verse IDs."""
    request = urllib.request.Request(TITUS_Y9_URL, headers={"User-Agent": "DARC-Y9-alignment/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        source = response.read().decode("utf-8")

    anchor_pattern = re.compile(
        r'<a\s+name="Avesta-PT_Y_9_(\d+)_([a-z]+)"[^>]*>', re.IGNORECASE
    )
    span_pattern = re.compile(r'<span\s+id=miphts[^>]*>(.*?)</span>', re.IGNORECASE | re.DOTALL)
    anchors = list(anchor_pattern.finditer(source))
    passages = {}
    occurrences = Counter()
    for index, anchor in enumerate(anchors):
        paragraph, verse = anchor.groups()
        key = f"Y9.{int(paragraph)}{verse.lower()}"
        occurrences[key] += 1

        # TITUS has an evident numbering typo after Y 9.6: its second 9.4a-c is Y 9.7a-c.
        if key in {"Y9.4a", "Y9.4b", "Y9.4c"} and occurrences[key] == 2:
            key = key.replace("Y9.4", "Y9.7")

        end = anchors[index + 1].start() if index + 1 < len(anchors) else len(source)
        span = span_pattern.search(source, anchor.end(), end)
        if not span:
            continue
        text = re.sub(r"<[^>]+>", " ", span.group(1))
        passages[key] = " ".join(html.unescape(text).split())
    return passages


def fold(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return value.replace("ϑ", "t").replace("θ", "t").replace("ŋ", "n").replace("δ", "d").replace("γ", "g").replace("š", "s").replace("ž", "z")


def user_family_equivalent(word):
    key = fold(word)
    families = (
        ("haōm", "hōm", "haōm", "Haoma"),
        ("ϑraētaōn", "Thraētaōna", "ϑraētaōn", "Thraētaōna"),
        ("ažīm", "az; az ī dahāg", "ažīm", "serpent; serpent Dahāg"),
        ("dahāk", "az; az ī dahāg", "dahāk", "Dahāg"),
        ("druj", "druz", "druj", "lie, evil, demonic force"),
        ("aŋhrō", "gannāg", "aŋhrō", "evil"),
        ("maińiiuš", "mēnōy", "maińiiuš", "spirit"),
        ("aŋra", "Ahreman (Ahriman)", "aŋra mainiiu", "Evil Spirit"),
        ("mainiiu", "mēnōg", "mainiiu", "spiritual world/spirit"),
        ("ahura", "Ohrmazd", "ahura mazdā", "Wise Lord"),
        ("mazdā", "Ohrmazd", "ahura mazdā", "Wise Lord"),
        ("daēv", "dēw", "daēva", "demon"),
        ("aṣ̌a", "ard / ahlāyīh", "aša (arta)", "truth, righteousness"),
        ("vohu", "Wahman", "vohu manah", "Good Mind"),
        ("manah", "mēnōg / man", "manah", "mind"),
        ("xšaϑra", "Šahrewar", "xšaθra vairya", "Desirable Dominion"),
        ("spənta", "Spandarmad", "spənta ārmaiti", "Holy Devotion"),
        ("ārmaiti", "Spandarmad", "spənta ārmaiti", "Holy Devotion"),
        ("haurvat", "Hordād", "haurvatāt", "Wholeness"),
        ("amərət", "Amurdād", "amərətāt", "Immortality"),
        ("sraoša", "Srōš", "sraoša", "Obedience, divine being"),
        ("rašn", "Rašn", "rašnū", "Justice"),
        ("miϑra", "Mihr", "miθra", "Mithra"),
        ("ātar", "Ādur (Ātaxš)", "ātar", "Fire"),
        ("apąm", "Burz ī Apām Napāt", "apąm napāt", "Son of the Waters"),
        ("napāt", "Burz ī Apām Napāt", "apąm napāt", "Son of the Waters"),
        ("vərəϑraγn", "Wahrām", "vərəθraγna", "Victory deity"),
        ("tištri", "Tištar", "tištriia", "Sirius deity"),
        ("arədvī", "Ardwīsūr Anāhīd", "arədvī sūrā anāhitā", "Anahita"),
        ("anāhit", "Ardwīsūr Anāhīd", "anāhitā", "Anahita"),
        ("yazat", "yazd", "yazata", "worthy of worship"),
        ("fravaš", "fravahr / fravard", "fravaši", "guardian spirit"),
        ("urvan", "ruwān", "urvan", "soul"),
        ("daēn", "dēn", "daēnā", "religion, conscience"),
        ("baod", "bōy / bōd", "baodah", "knowledge, understanding"),
        ("gaēϑ", "gēhān", "gaēϑ", "material world"),
        ("gētī", "gētīg", "gētī", "material existence"),
        ("astvat", "astōmand", "astvat", "corporeal"),
        ("astuuat", "astōmand", "astvat", "corporeal"),
        ("frašō.kərə", "frašgird", "frašō.kərəti", "Final Renovation"),
        ("saoš", "Sōšāns", "saošiiant", "Savior"),
        ("yima", "Jam", "yima", "Yima/Jamshid"),
        ("zaraϑuštr", "Zardušt", "zarathuštra", "Zoroaster"),
        ("vištāsp", "Wištāsp", "kavi vištāspa", "Vishtaspa"),
        ("xrafstr", "xrafstar", "xrafstra", "noxious creature"),
        ("nasu", "nasā", "nasu", "corpse pollution"),
        ("pairik", "parīg", "pairika", "fairy/demoness"),
        ("karapan", "karb", "karapan", "heretical priest"),
        ("maga", "mag", "maga", "magus"),
        ("māϑra", "mānthr / mānthrag", "māθra", "sacred utterance"),
        ("yasna", "yazišn", "yasna", "worship, sacrifice"),
        ("barəsman", "barsom", "barəsman", "ritual bundle of twigs"),
        ("gəuš", "gōspand", "gəuš", "cattle"),
        ("puϑr", "pus", "puϑr", "son"),
        ("druuaṇt", "druwand", "druuaṇt", "possessing the Lie; wicked"),
    )
    if key == "yo" or key.startswith("yoi"):
        return "kē =š", "yō", "who, which"
    for source, equivalent, family, meaning in families:
        if key.startswith(fold(source)):
            return equivalent, family, meaning
    return None


def collect_yasna_sections(node, sections):
    if isinstance(node, list):
        for item in node:
            collect_yasna_sections(item, sections)
        return
    if not isinstance(node, dict):
        return
    passage = str(node.get("xml:id", ""))
    match = re.fullmatch(r"Y(\d+\.\d+)[a-z]+", passage)
    text = " ".join(filter(None, (extract_text(node.get("#text")), extract_text(node.get("l")))))
    if match and text:
        sections[match.group(1)].extend(extract_words(text))
    for value in node.values():
        if isinstance(value, (dict, list)):
            collect_yasna_sections(value, sections)


def build_inferred_lexicon(corpus, py_text):
    av_sections = defaultdict(list)
    collect_yasna_sections(corpus.get("text", []), av_sections)
    py_sections = defaultdict(list)
    for line in py_text.splitlines():
        columns = line.split("\t")
        if len(columns) < 3:
            continue
        match = re.fullmatch(r"PY\s+(\d+\.\d+)", columns[1].strip())
        if match and not match.group(1).startswith("9."):
            py_sections[match.group(1)].extend(extract_words(columns[2]))

    dictionary = json.loads(DICTIONARY_SOURCE.read_text(encoding="utf-8"))
    lemma_by_fold = {fold(entry["word"]): entry["word"] for entry in dictionary.get("entries", []) if entry.get("word")}
    av_count = Counter()
    mp_count = Counter()
    cooccurrence = defaultdict(Counter)
    for section in set(av_sections) & set(py_sections):
        av_set = set(av_sections[section])
        mp_lemmas = {lemma_by_fold.get(fold(word)) for word in py_sections[section]}
        mp_set = {lemma for lemma in mp_lemmas if lemma}
        if not av_set or not mp_set:
            continue
        av_count.update(av_set)
        mp_count.update(mp_set)
        for av_word in av_set:
            cooccurrence[av_word].update(mp_set)

    inferred = {}
    for av_word, candidates in cooccurrence.items():
        ranked = []
        for lemma, shared in candidates.items():
            association = shared / math.sqrt(av_count[av_word] * mp_count[lemma])
            similarity = SequenceMatcher(None, fold(av_word), fold(lemma)).ratio()
            score = association + 0.25 * similarity
            ranked.append((score, shared, similarity, lemma))
        ranked.sort(reverse=True)
        if not ranked:
            continue
        score, shared, similarity, lemma = ranked[0]
        margin = score - (ranked[1][0] if len(ranked) > 1 else 0)
        confidence = "medium" if shared >= 3 and margin >= 0.08 else "low"
        inferred[av_word] = (lemma, confidence, shared, score)
    return inferred, len(set(av_sections) & set(py_sections))


def inline_cell(reference, value, style=None):
    style_attr = f' s="{style}"' if style is not None else ""
    return f'<c r="{reference}" t="inlineStr"{style_attr}><is><t>{escape(str(value))}</t></is></c>'


def number_cell(reference, value):
    return f'<c r="{reference}"><v>{value}</v></c>'


def build_sheet(rows):
    sheet_rows = [
        '<row r="1">'
        + inline_cell("A1", "Sequence", 1)
        + inline_cell("B1", "Passage", 1)
        + inline_cell("C1", "Avestan word", 1)
        + inline_cell("D1", "Pahlavi equivalent", 1)
        + inline_cell("E1", "Meaning", 1)
        + inline_cell("F1", "Confidence", 1)
        + inline_cell("G1", "Method", 1)
        + inline_cell("H1", "Corresponding Pahlavi passage", 1)
        + "</row>"
    ]
    for excel_row, (sequence, passage, word, pahlavi, meaning, confidence, method, py_passage) in enumerate(rows, 2):
        sheet_rows.append(
            f'<row r="{excel_row}">'
            + number_cell(f"A{excel_row}", sequence)
            + inline_cell(f"B{excel_row}", passage)
            + inline_cell(f"C{excel_row}", word)
            + inline_cell(f"D{excel_row}", pahlavi)
            + inline_cell(f"E{excel_row}", meaning)
            + inline_cell(f"F{excel_row}", confidence)
            + inline_cell(f"G{excel_row}", method)
            + inline_cell(f"H{excel_row}", py_passage)
            + "</row>"
        )
    final_row = len(rows) + 1
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:H{final_row}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols><col min="1" max="1" width="12" customWidth="1"/><col min="2" max="2" width="16" customWidth="1"/><col min="3" max="4" width="28" customWidth="1"/><col min="5" max="5" width="32" customWidth="1"/><col min="6" max="7" width="18" customWidth="1"/><col min="8" max="8" width="80" customWidth="1"/></cols>
  <sheetData>{''.join(sheet_rows)}</sheetData>
  <autoFilter ref="A1:H{final_row}"/>
</worksheet>'''


def write_workbook(rows):
    parts = {
        "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>''',
        "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''',
        "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Yasna 9 words" sheetId="1" r:id="rId1"/></sheets>
</workbook>''',
        "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''',
        "xl/styles.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>
</styleSheet>''',
        "xl/worksheets/sheet1.xml": build_sheet(rows),
    }
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content.encode("utf-8"))


corpus = json.loads(SOURCE.read_text(encoding="utf-8"))
py_text = PY_SOURCE.read_text(encoding="utf-8")
inferred, training_sections = build_inferred_lexicon(corpus, py_text)
titus_passages = fetch_titus_y9_passages()
py_93_lines = []
for line in py_text.splitlines():
    columns = line.split("\t")
    if len(columns) >= 3 and columns[1].strip() == "PY 9.3":
        py_93_lines.append(columns[2].strip())
py_93 = " ".join(py_93_lines)
passages = []
collect_passages(corpus.get("text", []), passages)
rows = []
for passage, text in passages:
    for word in extract_words(text):
        word = unicodedata.normalize("NFC", word)
        direct = PAHLAVI_EQUIVALENTS.get((passage, word))
        guess = inferred.get(word)
        user_supplied = user_family_equivalent(word)
        pahlavi = user_supplied[0] if user_supplied else direct or (guess[0] if guess else "")
        meaning = user_supplied[2] if user_supplied else ""
        confidence = "user-specified" if user_supplied else "high" if direct else (guess[1] if guess else "")
        method = f"user-specified {user_supplied[1]} family" if user_supplied else "direct PY 9.3 alignment" if direct else (f"cross-section inference ({guess[2]} shared sections)" if guess else "")
        corresponding_passage = titus_passages.get(passage, py_93 if passage in {"Y9.3a", "Y9.3b"} else "")
        rows.append((len(rows) + 1, passage, word, pahlavi, meaning, confidence, method, corresponding_passage))
write_workbook(rows)
filled = sum(bool(row[3]) for row in rows)
aligned = len({row[1] for row in rows if row[7]})
print(
    f"Wrote {len(rows)} word occurrences ({filled} supplied equivalents; "
    f"{aligned} TITUS passages; {training_sections} aligned training sections) to {OUTPUT}"
)
