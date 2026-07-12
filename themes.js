const THEME_TEXTS = [
  { id: "av-corpus", siglum: "Av.", title: "Avestan Corpus", file: "CABLinguisticCorpus.json", parseMode: "cab-json" },
  { id: "py", siglum: "PY", title: "Pahlavi Yasna", file: "PY-Pt4.txt", englishFile: "PY-en.txt" },
  { id: "dd", siglum: "DD", title: "Dadestan i Denig", file: "Dd.txt", englishFile: "DD-en.txt" },
  { id: "wz", siglum: "WZ", title: "Wizidagiha i Zadspram", file: "WZ.txt", englishFile: "WZ-en.txt" },
  { id: "nm", siglum: "NM", title: "Namagiha i Manuscihr", file: "NM.txt", englishFile: "NM-en.txt" },
  { id: "prdd", siglum: "PRDD", title: "Pahlavi Rivayat Accompanying the Dadestan i Denig", file: "PRDd.txt", parseMode: "section" },
  { id: "gbd", siglum: "GBd", title: "Greater Bundahishn", file: "GBd.txt", parseMode: "section" }
];

const themeState = {
  texts: [],
  themes: [],
  dictionary: new Map(),
  selectedThemeId: "",
  themeSearch: "",
  themeMenuOpen: false,
  keywords: "",
  wholeWord: true,
  caseSensitive: false,
  contextSize: 2,
  pages: {}
};

const themeSearchEl = document.querySelector("#theme-search");
const themeTitleMenuEl = document.querySelector("#theme-title-menu");
const statusEl = document.querySelector("#theme-status");
const overviewEl = document.querySelector("#theme-overview");
const comparisonEl = document.querySelector("#theme-comparison");

const THEME_PAGE_SIZE = 5;
const DICTIONARY_URL = "mpcd-workspace-dictionary.json";
const THEME_KEYWORD_DEBOUNCE_MS = 300;
let themeKeywordRenderTimer = null;
const TRANSLITERATION_MAP = {
  "\u0100": "A",
  "\u0101": "a",
  "\u0112": "E",
  "\u0113": "e",
  "\u012A": "I",
  "\u012B": "i",
  "\u014C": "O",
  "\u014D": "o",
  "\u016A": "U",
  "\u016B": "u",
  "\u010C": "C",
  "\u010D": "c",
  "\u0160": "S",
  "\u0161": "s",
  "\u01F0": "j",
  "\u01E6": "G",
  "\u01E7": "g"
};

initThemes();

async function initThemes() {
  bindThemeEvents();

  try {
    const [themes, texts] = await Promise.all([
      loadThemes(),
      Promise.all(THEME_TEXTS.map(loadText))
    ]);
    const dictionary = await loadDictionary();

    themeState.themes = themes;
    themeState.texts = texts;
    themeState.dictionary = dictionary;
    themeState.selectedThemeId = themes[0]?.id || "";
    populateThemeSelect();
    syncKeywordInput();
    renderThemes();
  } catch (error) {
    statusEl.textContent = "Theme loading failed";
    comparisonEl.innerHTML = `<div class="empty-state">The theme comparison data could not be loaded.</div>`;
    console.error(error);
  }
}

async function loadDictionary() {
  try {
    const response = await fetch(DICTIONARY_URL);
    if (!response.ok) {
      return new Map();
    }

    const data = await response.json();
    return new Map((data.entries || []).flatMap((entry) => {
      const meanings = (entry.meanings || []).filter(Boolean);
      if (!entry.word || !meanings.length) {
        return [];
      }
      return getDictionaryKeys(entry.word).map((key) => [key, meanings]);
    }));
  } catch (error) {
    console.warn("Dictionary glosses unavailable", error);
    return new Map();
  }
}

function bindThemeEvents() {
  themeSearchEl.addEventListener("pointerdown", (event) => {
    if (themeState.themeMenuOpen && document.activeElement === themeSearchEl) {
      event.preventDefault();
      themeState.themeMenuOpen = false;
      themeSearchEl.blur();
      renderThemeTitleMenu();
    }
  });

  themeSearchEl.addEventListener("focus", () => {
    themeState.themeSearch = "";
    themeSearchEl.value = "";
    themeState.themeMenuOpen = true;
    renderThemeTitleMenu();
  });

  themeSearchEl.addEventListener("input", () => {
    themeState.themeSearch = themeSearchEl.value;
    themeState.themeMenuOpen = true;
    renderThemeTitleMenu();
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".theme-search-wrap")) {
      themeState.themeMenuOpen = false;
      renderThemeTitleMenu();
    }
  });

  comparisonEl.addEventListener("click", (event) => {
    const button = event.target.closest("[data-theme-page]");
    if (!button) {
      return;
    }

    themeState.pages[button.dataset.textId] = Number(button.dataset.themePage);
    renderThemesImmediately();
  });
}

function scheduleThemeKeywordRender() {
  window.clearTimeout(themeKeywordRenderTimer);
  themeKeywordRenderTimer = window.setTimeout(() => {
    themeKeywordRenderTimer = null;
    resetPages();
    renderThemes();
  }, THEME_KEYWORD_DEBOUNCE_MS);
}

function renderThemesImmediately() {
  window.clearTimeout(themeKeywordRenderTimer);
  themeKeywordRenderTimer = null;
  renderThemes();
}

async function loadThemes() {
  const response = await fetch("themes-data.json");
  if (!response.ok) {
    throw new Error("Could not load themes-data.json");
  }
  return response.json();
}

async function loadText(config) {
  const [response, englishRaw] = await Promise.all([
    fetch(config.file),
    fetchOptionalText(config.englishFile)
  ]);
  if (!response.ok) {
    throw new Error(`Could not load ${config.file}`);
  }

  if (config.parseMode === "cab-json") {
    return {
      ...config,
      raw: "",
      records: parseCabCorpusRecords(await response.json()),
      englishByLocation: new Map()
    };
  }

  const raw = await response.text();
  const englishRecords = englishRaw ? parseRecords(englishRaw) : [];
  return {
    ...config,
    raw,
    records: parseRecords(raw),
    englishByLocation: new Map(englishRecords.map((record) => [record.location, record.text]))
  };
}

async function fetchOptionalText(file) {
  if (!file) {
    return "";
  }
  try {
    const response = await fetch(file);
    return response.ok ? response.text() : "";
  } catch {
    return "";
  }
}

function populateThemeSelect() {
  syncThemeSearchInput();
  renderThemeTitleMenu();
}

function syncThemeSearchInput() {
  const theme = getSelectedTheme();
  themeState.themeSearch = "";
  themeSearchEl.value = theme?.label || "";
}

function renderThemeTitleMenu() {
  if (!themeTitleMenuEl || !themeSearchEl) {
    return;
  }
  if (!themeState.themeMenuOpen) {
    themeTitleMenuEl.hidden = true;
    return;
  }

  const terms = tokenizeSearch(themeState.themeSearch);
  const rows = themeState.themes.filter((theme) => {
    if (!terms.length) {
      return true;
    }
    const haystack = normalizeQueryText(`${theme.label} ${theme.description || ""} ${(theme.keywords || []).join(" ")}`);
    return terms.every((term) => haystack.includes(term));
  });

  themeTitleMenuEl.hidden = false;
  themeTitleMenuEl.innerHTML = rows.length ? rows.map((theme) => `
    <button class="theme-title-option${theme.id === themeState.selectedThemeId ? " active" : ""}" type="button" data-theme-id="${escapeHtml(theme.id)}">
      <strong>${escapeHtml(theme.label)}</strong>
      <small>${escapeHtml((theme.keywords || []).join(", "))}</small>
    </button>
  `).join("") : `<div class="empty-state">No theme titles match this search.</div>`;

  themeTitleMenuEl.querySelectorAll("[data-theme-id]").forEach((button) => {
    button.addEventListener("click", () => {
      themeState.selectedThemeId = button.dataset.themeId;
      themeState.themeMenuOpen = false;
      syncThemeSearchInput();
      syncKeywordInput();
      resetPages();
      renderThemeTitleMenu();
      renderThemesImmediately();
    });
  });
}

function tokenizeSearch(value) {
  return normalizeQueryText(value).split(/\s+/).filter(Boolean);
}

function normalizeQueryText(value) {
  return String(value).toLocaleLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
}

function syncKeywordInput() {
  const theme = getSelectedTheme();
  themeState.keywords = (theme?.keywords || []).join(",");
}

function renderThemes() {
  const theme = getSelectedTheme();
  if (!theme) {
    statusEl.textContent = "No themes";
    overviewEl.innerHTML = "";
    comparisonEl.innerHTML = `<div class="empty-state">Add a theme to themes-data.json to begin.</div>`;
    return;
  }

  const terms = getKeywordTerms();
  const results = themeState.texts.map((text) => {
    const textTerms = getThemeTermsForText(theme, text, terms);
    return { ...getThemeMatches(text, textTerms), terms: textTerms };
  });
  const totalHits = results.reduce((sum, result) => sum + result.matches.length, 0);
  const textHits = results.filter((result) => result.matches.length > 0).length;

  statusEl.textContent = `${textHits} of ${results.length} texts | ${totalHits} passages`;
  renderThemeOverview(theme, terms, results);
  renderThemeComparison(results, terms);
}

function renderThemeOverview(theme, terms, results) {
  overviewEl.innerHTML = `
    <article class="text-card theme-description-card">
      <div class="siglum">Theme</div>
      <h2>${escapeHtml(theme.label)}</h2>
      <p class="meta">${escapeHtml(theme.description || "Keyword-assisted theme comparison")}</p>
    </article>
  `;
}

function renderThemeComparison(results, terms) {
  if (!terms.length) {
    comparisonEl.innerHTML = `<div class="empty-state">Enter one or more keywords to compare this theme.</div>`;
    return;
  }

  comparisonEl.innerHTML = results
    .map((result) => renderThemeColumn(result, terms))
    .join("");
}

function renderThemeColumn(result, terms) {
  const total = result.matches.length;
  const pageCount = Math.max(1, Math.ceil(total / THEME_PAGE_SIZE));
  const currentPage = clampPage(themeState.pages[result.text.id] || 1, pageCount);
  themeState.pages[result.text.id] = currentPage;
  const start = (currentPage - 1) * THEME_PAGE_SIZE;
  const visible = result.matches.slice(start, start + THEME_PAGE_SIZE);

  return `
    <article class="theme-column">
      <header>
        <div>
          <div class="siglum">${escapeHtml(result.text.siglum)}</div>
          <h2>${escapeHtml(result.text.title)}</h2>
        </div>
        <span class="count-pill ${total ? "hit" : "miss"}">${total}</span>
      </header>
      <div class="theme-passages">
        ${visible.length ? visible.map((match) => renderThemeHit(match, result.terms || terms, result.text)).join("") : `<div class="empty-state">No suggested passages for this theme.</div>`}
      </div>
      ${total > THEME_PAGE_SIZE ? renderThemePagination(result.text.id, currentPage, pageCount) : ""}
    </article>
  `;
}

function renderThemeHit(match, terms, text) {
  return `
    <section class="theme-hit">
      <div class="theme-hit-meta">
        <span>${renderThemeLocationLink(text, match.location)}</span>
        <span>${match.score} keyword${match.score === 1 ? "" : "s"}</span>
      </div>
      <div class="theme-hit-content">
        <div>
          <p>${highlightTheme(match.snippet, terms, { annotate: true })}</p>
          ${renderTranslationActions(match.snippet, text.englishByLocation?.get(match.location))}
        </div>
      </div>
    </section>
  `;
}

function getThemeTermsForText(theme, text, fallbackTerms) {
  if (theme.id !== "azhi-dahaka") {
    return fallbackTerms;
  }
  return text.id === "av-corpus"
    ? (theme.avestanKeywords || [])
    : (theme.pahlaviKeywords || []);
}

function renderThemeLocationLink(text, location) {
  const href = getThemeTransLocationHref(text, location);
  if (!href) {
    return escapeHtml(location);
  }

  return `<a class="diagram-location-link" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(location)}</a>`;
}

function getThemeTransLocationHref(text, location) {
  if (!["dd", "py", "wz", "nm"].includes(text.id)) {
    return "";
  }

  return `trans.html?text=${encodeURIComponent(text.id)}&location=${encodeURIComponent(location)}`;
}

function renderThemePagination(textId, currentPage, pageCount) {
  return `
    <nav class="rank-pagination result-pagination" aria-label="Theme result pages">
      ${getVisiblePages(currentPage, pageCount)
        .map((page) => page === "gap"
          ? `<span class="page-gap" aria-hidden="true">...</span>`
          : `<button
              class="page-dot ${page === currentPage ? "active" : ""}"
              type="button"
              data-text-id="${escapeHtml(textId)}"
              data-theme-page="${page}"
              aria-label="Show theme result page ${page}"
              ${page === currentPage ? `aria-current="page"` : ""}
            >${page}</button>`)
        .join("")}
    </nav>
  `;
}

function getThemeMatches(text, terms) {
  if (!terms.length) {
    return { text, matches: [] };
  }

  const matches = text.records
    .map((record, recordIndex) => {
      const ranges = findMatchRanges(record.text, terms);
      if (!ranges.length) {
        return null;
      }

      return {
        location: record.location,
        score: new Set(ranges.map((range) => range.termIndex)).size,
        snippet: makeSnippet(text.records, recordIndex, terms)
      };
    })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score || compareLocations(a.location, b.location));

  return { text, matches };
}

function parseRecords(raw) {
  const lines = raw.split(/\r?\n/);
  const hasTsvRecords = lines.some((line) => {
    const trimmed = line.trim();
    return trimmed && !trimmed.startsWith("#") && isTsvRecord(trimmed);
  });

  return hasTsvRecords ? parseTsvRecords(lines) : parseSectionRecords(lines);
}

function parseCabCorpusRecords(data) {
  const records = [];
  const excludedTypes = new Set(["pahltr", "pahltxt"]);
  const structuralKeys = new Set(["div", "ab"]);

  function visit(node, context = {}) {
    if (Array.isArray(node)) {
      node.forEach((item) => visit(item, context));
      return;
    }
    if (!node || typeof node !== "object") {
      return;
    }

    const type = String(node.type || "").toLowerCase();
    const language = String(node["xml:lang"] || "").toLowerCase();
    if (excludedTypes.has(type) || language === "pal") {
      return;
    }

    const nextContext = {
      work: node["xml:id"] && !context.work ? node["xml:id"] : context.work,
      section: node.n || context.section,
      id: node["xml:id"] || context.id
    };
    const text = [extractCabText(node["#text"]), extractCabText(node.l)]
      .filter(Boolean)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();

    if (text) {
      const locationParts = [nextContext.work, nextContext.section || nextContext.id].filter(Boolean);
      records.push({
        index: records.length,
        location: locationParts.join(" · ") || `passage ${records.length + 1}`,
        text,
        searchable: true
      });
    }

    Object.entries(node).forEach(([key, value]) => {
      if (structuralKeys.has(key)) {
        visit(value, nextContext);
      }
    });
  }

  visit(Array.isArray(data?.text) ? data.text : [], {});
  return records;
}

function extractCabText(value) {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.filter((item) => typeof item === "string").join(" ");
  }
  return "";
}

function parseTsvRecords(lines) {
  return lines
    .map((line, index) => {
      const trimmed = line.trim();
      const columns = trimmed.split("\t");
      const hasTsvShape = isTsvRecord(trimmed) && !trimmed.startsWith("#");

      return {
        index,
        location: hasTsvShape ? formatTsvLocation(columns) : "",
        text: hasTsvShape ? columns.slice(2).join(" ") : trimmed,
        searchable: hasTsvShape && trimmed.length > 0
      };
    })
    .filter((record) => record.searchable);
}

function parseSectionRecords(lines) {
  const records = [];
  let current = null;

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return;
    }

    const section = trimmed.match(/^([0-9]+(?:\.[0-9]+[a-z]?)?)\s+(.*)$/);
    if (section) {
      current = {
        index,
        location: section[1],
        text: section[2],
        searchable: true
      };
      records.push(current);
      return;
    }

    if (current) {
      current.text += ` ${trimmed}`;
      return;
    }

    records.push({
      index,
      location: `line ${index + 1}`,
      text: trimmed,
      searchable: true
    });
  });

  return records;
}

function isTsvRecord(line) {
  const columns = line.split("\t");
  return columns.length >= 3 &&
    columns[0].trim().length > 0 &&
    columns[1].trim().length > 0 &&
    columns.slice(2).join(" ").trim().length > 0;
}

function formatTsvLocation(columns) {
  const first = columns[0].trim();
  const second = columns[1].trim();
  if (/outdated|K35/i.test(first)) {
    return second.replace(/^[A-Za-z]+\s+/, "");
  }
  return [first, second].filter(Boolean).join(" | ");
}

function makeSnippet(records, recordIndex, terms) {
  const text = records[recordIndex].text;
  const ranges = findMatchRanges(text, terms);
  if (ranges.length) {
    const first = ranges[0];
    const radius = 220 + themeState.contextSize * 80;
    const start = Math.max(0, first.start - radius);
    const end = Math.min(text.length, first.end + radius);
    const prefix = start > 0 ? "... " : "";
    const suffix = end < text.length ? " ..." : "";
    return `${prefix}${text.slice(start, end)}${suffix}`;
  }

  const start = Math.max(0, recordIndex - themeState.contextSize);
  const end = Math.min(records.length, recordIndex + themeState.contextSize + 1);
  return records.slice(start, end).map((record) => record.text).join(" ");
}

function highlightTheme(text, terms, options = {}) {
  if (options.annotate) {
    return annotateText(text, terms);
  }

  const ranges = findMatchRanges(text, terms);
  if (!ranges.length) {
    return escapeHtml(text);
  }

  let html = "";
  let cursor = 0;
  ranges.forEach(({ start, end }) => {
    html += escapeHtml(text.slice(cursor, start));
    html += `<mark>${escapeHtml(text.slice(start, end))}</mark>`;
    cursor = end;
  });
  html += escapeHtml(text.slice(cursor));
  return html;
}

function annotateText(value, terms = []) {
  const text = String(value);
  const ranges = terms.length ? findMatchRanges(text, terms) : [];
  const wordPattern = /[\p{L}\p{M}\p{N}=_-]+/gu;
  let html = "";
  let cursor = 0;
  let match;

  while ((match = wordPattern.exec(text)) !== null) {
    html += highlightSegment(text.slice(cursor, match.index), ranges, cursor);
    const token = match[0];
    const tokenStart = match.index;
    const tokenEnd = tokenStart + token.length;
    const tokenHtml = highlightSegment(token, ranges, tokenStart);
    const meanings = getMeanings(token);
    html += meanings.length
      ? `<span class="dict-word" title="${escapeHtml(meanings.join("; "))}">${tokenHtml}</span>`
      : tokenHtml;
    cursor = tokenEnd;
  }

  html += highlightSegment(text.slice(cursor), ranges, cursor);
  return html;
}

function renderTranslationActions(value, englishText = "") {
  return `
    <div class="translation-actions">
      <details class="eng-trans">
        <summary>Eng. Transl.</summary>
        <p>${englishText ? escapeHtml(englishText) : "English translation will be added later."}</p>
      </details>
      <details class="pers-trans">
        <summary>Pers. Trans.</summary>
        <p dir="rtl" lang="fa">${escapeHtml(toArabicTranscription(value))}</p>
      </details>
    </div>
  `;
}

function toArabicTranscription(value) {
  const parts = String(value).split(/(\s+|[.,;:!?()[\]{}<>]+)/u);
  let output = "";

  parts.forEach((part) => {
    if (/[\p{L}\p{M}\p{N}=_-]/u.test(part)) {
      if (isStandaloneEzafe(part)) {
        output = output.replace(/\s+$/u, "") + "ِ";
        return;
      }
      output += transliterateWord(part);
      return;
    }

    output += part;
  });

  return output;
}

function transliterateWord(word) {
  const prefix = word.match(/^[=_.:-]+/)?.[0] || "";
  const suffix = word.match(/[=_.:-]+$/)?.[0] || "";
  let body = word.replace(/^[=_.:-]+|[=_.:-]+$/g, "").toLocaleLowerCase();
  if (!body) {
    return word;
  }
  if (body === "ud") {
    return `${prefix}و${suffix}`;
  }
  if (body === "pad") {
    return `${prefix}به${suffix}`;
  }
  if (body === "čē" || body === "ce") {
    return `${prefix}چه${suffix}`;
  }
  const finalLongE = body.endsWith("ē");
  if (finalLongE) {
    body = body.slice(0, -1);
  }
  const initialA = body.startsWith("a");
  if (initialA) {
    body = body.slice(1);
  }
  const initialE = body.startsWith("e");
  if (initialE) {
    body = body.slice(1);
  }

  const replacements = [
    ["xw", "خو"], ["kh", "خ"], ["ch", "چ"], ["sh", "ش"], ["zh", "ژ"],
    ["θ", "ث"], ["γ", "غ"], ["δ", "ذ"], ["š", "ش"], ["č", "چ"], ["ǰ", "ج"],
    ["ā", "ا"], ["ē", "ێ"], ["ī", "ی"], ["ō", "و"], ["ū", "و"]
  ];
  replacements.forEach(([from, to]) => {
    body = body.replaceAll(from, to);
  });

  const chars = {
    a: "َ", e: "ِ", i: "ِ", o: "ُ", u: "ُ",
    b: "ب", p: "پ", t: "ت", j: "ج", c: "چ", d: "د", f: "ف",
    g: "گ", h: "ه", k: "ک", l: "ل", m: "م", n: "ن", r: "ر",
    s: "س", w: "و", v: "و", x: "خ", y: "ی", z: "ز", q: "ق"
  };

  const transcribed = `${initialA ? "ا" : ""}${initialE ? "ای" : ""}${Array.from(body).map((char) => chars[char] || char).join("")}${finalLongE ? "ه" : ""}`;
  return `${prefix}${transcribed}${suffix}`;
}

function isStandaloneEzafe(value) {
  const clean = String(value).replace(/^[=_.:-]+|[=_.:-]+$/g, "").toLocaleLowerCase();
  return clean === "ī" || clean === "i";
}

function highlightSegment(segment, ranges, offset) {
  if (!ranges.length || !segment) {
    return escapeHtml(segment);
  }

  let html = "";
  let cursor = 0;
  const segmentEnd = offset + segment.length;
  ranges
    .filter((range) => range.start < segmentEnd && range.end > offset)
    .forEach((range) => {
      const start = Math.max(0, range.start - offset);
      const end = Math.min(segment.length, range.end - offset);
      if (start < cursor) {
        return;
      }
      html += escapeHtml(segment.slice(cursor, start));
      html += `<mark>${escapeHtml(segment.slice(start, end))}</mark>`;
      cursor = end;
    });
  html += escapeHtml(segment.slice(cursor));
  return html;
}

function getMeanings(token) {
  for (const key of getDictionaryKeys(token)) {
    const meanings = themeState.dictionary.get(key);
    if (meanings?.length) {
      return meanings;
    }
  }
  return [];
}

function getDictionaryKeys(value) {
  const raw = String(value).trim();
  const trimmed = raw.replace(/^[=_.:;,[\](){}<>]+|[=_.:;,[\](){}<>]+$/g, "");
  const seeds = [raw, trimmed, foldText(raw).text, foldText(trimmed).text]
    .map((key) => key.toLowerCase())
    .filter(Boolean);
  const variants = new Set(seeds);

  seeds.forEach((key) => {
    [
      key.replace(/^=+/, ""),
      key.replace(/^u-/, ""),
      key.replace(/^i-/, ""),
      key.replace(/^pad-/, ""),
      key.replace(/^az-/, ""),
      key.replace(/^o-/, ""),
      key.replace(/^ud-/, ""),
      key.replace(/-(iz|is|im|it|san|man|tan)$/, "")
    ].forEach((variant) => {
      const clean = variant.replace(/^[=_.:-]+|[=_.:-]+$/g, "");
      if (clean) {
        variants.add(clean);
      }
    });
  });

  return [...variants];
}

function findMatchRanges(text, terms) {
  const folded = foldText(text, themeState.caseSensitive);
  const ranges = [];

  terms.forEach((term, termIndex) => {
    const variants = getSearchVariants(term);
    if (!variants.length) {
      return;
    }

    const regex = new RegExp(buildPattern(variants), "gu");
    let match;
    while ((match = regex.exec(folded.text)) !== null) {
      ranges.push({
        start: folded.map[match.index],
        end: folded.map[match.index + match[0].length - 1] + 1,
        termIndex
      });
    }
  });

  return mergeRanges(ranges);
}

function getSearchVariants(term) {
  const folded = foldText(term, themeState.caseSensitive).text;
  if (!folded) {
    return [];
  }

  const variants = new Set([folded]);
  [
    folded.replace(/^=+/, ""),
    folded.replace(/^u-/, ""),
    folded.replace(/^i-/, ""),
    folded.replace(/^pad-/, ""),
    folded.replace(/^az-/, ""),
    folded.replace(/^o-/, ""),
    folded.replace(/^ud-/, ""),
    folded.replace(/-(iz|is|im|it|san|man|tan)$/, "")
  ].forEach((variant) => {
    const clean = variant.replace(/^[=_.:-]+|[=_.:-]+$/g, "");
    if (clean) {
      variants.add(clean);
    }
  });

  [...variants].forEach((variant) => {
    ["u", "i", "pad", "az", "o", "ud"].forEach((prefix) => variants.add(`${prefix}-${variant}`));
    ["iz", "is", "im", "it", "san", "man", "tan"].forEach((suffix) => variants.add(`${variant}-${suffix}`));
  });

  return [...variants].filter(Boolean);
}

function getKeywordTerms() {
  return [...new Set(themeState.keywords
    .split(/[,\n;]+/)
    .map((term) => term.trim())
    .filter(Boolean))];
}

function buildPattern(terms) {
  const escaped = terms
    .slice()
    .sort((a, b) => b.length - a.length)
    .map(escapeRegExp)
    .join("|");
  const boundary = "[\\p{L}\\p{M}\\p{N}_-]";
  return themeState.wholeWord ? `(?<!${boundary})(?:${escaped})(?!${boundary})` : `(?:${escaped})`;
}

function foldText(value, caseSensitive = false) {
  let text = "";
  const map = [];

  Array.from(String(value)).forEach((char, index) => {
    const folded = TRANSLITERATION_MAP[char] || char.normalize("NFD").replace(/\p{M}/gu, "");
    const normalized = caseSensitive ? folded : folded.toLocaleLowerCase();
    Array.from(normalized).forEach((foldedChar) => {
      text += foldedChar;
      map.push(index);
    });
  });

  return { text, map };
}

function mergeRanges(ranges) {
  return ranges
    .sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start))
    .reduce((merged, range) => {
      const previous = merged[merged.length - 1];
      if (previous && range.start < previous.end) {
        if (range.end > previous.end) {
          previous.end = range.end;
        }
      } else {
        merged.push({ ...range });
      }
      return merged;
    }, []);
}

function getVisiblePages(currentPage, pageCount) {
  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }

  const pages = new Set([1, pageCount, currentPage - 1, currentPage, currentPage + 1]);
  const ordered = [...pages]
    .filter((page) => page >= 1 && page <= pageCount)
    .sort((a, b) => a - b);

  return ordered.flatMap((page, index) => {
    if (index === 0 || page === ordered[index - 1] + 1) {
      return [page];
    }
    return ["gap", page];
  });
}

function compareLocations(a, b) {
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

function getSelectedTheme() {
  return themeState.themes.find((theme) => theme.id === themeState.selectedThemeId);
}

function clampPage(page, pageCount) {
  return Math.min(Math.max(page, 1), pageCount);
}

function resetPages() {
  themeState.pages = {};
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
