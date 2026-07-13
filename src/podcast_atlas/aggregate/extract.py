from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from .gazetteer import Gazetteer
from .rss_parse import html_to_text

AD_SEPARATORS = [
    "+++++",
    "**********",
]

_LINE_NOISE_MARKERS = [
    "instagram",
    "tiktok",
    "facebook",
    "linktr",
    "campfire",
    "werbepartner",
    "werbung",
    "apple podcasts",
    "podcastplattform panoptikum",
    "rezensiert oder bewertet",
    "hosted on acast",
    "acast.com/privacy",
    "podcasthörer",
    "freundinnen und freunden",
    "kolleginnen und kollegen",
    "nachbarinnen und nachbarn",
]

_TERMINAL_SECTION_HEADINGS = {
    "aus unserer werbung",
    "besprochene folgen",
    "bildnachweis",
    "credits",
    "episodenbild",
    "erwähnte episoden",
    "erwähnte folgen",
    "erwähnte literatur",
    "folgenbild",
    "im buch erwähnte folgen",
    "links",
    "literatur",
    "mitwirkende",
    "museen & ausstellungen",
    "musik",
    "podcasts des monats",
    "quellen",
    "quellen & links",
    "shownotes",
    "team",
    "tools",
    "weiterführende links",
    "werbung",
}

_CREDIT_LINE_RE = re.compile(
    r"^(?:"
    r"autor(?:in)?(?:\s+und\s+producer(?:in)?)?|"
    r"host(?:in)?|moderation|online-veröffentlichung|producer(?:in)?|produktion|"
    r"redaktion|regie|recherche|schnitt|sounddesign|sprecher(?:in)?|"
    r"technische\s+distribution"
    r")\s*:\s*\S+",
    re.IGNORECASE,
)

_TRAILING_BROADCASTER_RE = re.compile(
    r"\s*\((?:dlf\s*nova|dradio\s+wissen|deutschlandradio\s+wissen)\)\s*$",
    re.IGNORECASE,
)

_INLINE_METADATA_RE = re.compile(
    r"(?:"
    r"\bdie\s+passende\s+ausgabe\s+[„“”‚‘’\"']?eine\s+stunde\s+history[„“”‚‘’\"']?\s+läuft\s+am|"
    r"\bursprünglich\s+wurden\s+die\s+sendungen\s+bei\s+deutschlandradio\s+wissen\b|"
    r"\*?affiliate-link\s*:|"
    r"\b(?:hörenswert|lesenswert|sehenswert|wissenswert)\s*:"
    r")",
    re.IGNORECASE,
)

_INLINE_CREDIT_SENTENCE_RE = re.compile(
    r"(?:^|(?<=\s))matthias\s+von\s+hellfeld\s+erzählt\.\s*",
    re.IGNORECASE,
)

_BOILERPLATE_SENTENCE_RE = re.compile(
    r"(?:^|(?<=[.!?])\s+)"
    r"(?:"
    r"wir\s+freuen\s+uns(?:\s+auch)?(?:\s+immer)?,?\s+wenn\s+ihr\s+(?:den\s+podcast|euren\s+freundinnen)|"
    r"(?:abonniert|bewertet|rezensiert)\s+(?:uns|den\s+podcast)|"
    r"folgt\s+uns\s+(?:auf|bei)\s+(?:instagram|facebook|tiktok)|"
    r"mehr\s+informationen\s+(?:findet|gibt)\s+ihr\s+(?:auf|unter)|"
    r"hosted\s+on\s+acast(?:\.|\s+see\s+acast\.com/privacy\s+for\s+more\s+information\.?)?"
    r")"
    r".*?(?=(?:[.!?](?:\s+|$))|$)",
    re.IGNORECASE,
)


def _remove_inline_boilerplate(text: str) -> str:
    """Remove promotional sentences when feeds flatten them into narrative text."""
    previous = None
    while text != previous:
        previous = text
        text = _BOILERPLATE_SENTENCE_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _heading_key(line: str) -> str:
    """Normalize a standalone Markdown/feed section heading for matching."""
    key = " ".join(line.strip().split())
    key = re.sub(r"^[\s#/|>*_~+\-=–—]+", "", key)
    key = re.sub(r"[\s:>*_~+\-=–—]+$", "", key)
    return key.casefold()


def _is_terminal_section_heading(line: str) -> bool:
    key = _heading_key(line)
    return bool(key) and key in _TERMINAL_SECTION_HEADINGS


def _is_credit_line(line: str) -> bool:
    return bool(_CREDIT_LINE_RE.match(" ".join(line.strip().split())))


def _is_noise_line(line: str) -> bool:
    s = line.strip().casefold()
    if not s:
        return True
    if "http://" in s or "https://" in s or "www." in s:
        return True
    return any(m in s for m in _LINE_NOISE_MARKERS)


def clean_description(raw: str) -> str:
    """Return narrative description text without metadata/footer sections.

    Podcast feeds commonly append bibliography publication years, cross-links,
    image credits, advertising, and production credits. Those sections are not
    episode subject matter and must not feed date/place extraction or clustering.
    """
    txt = html_to_text(raw)
    # drop everything after repeated ad separator blocks
    for sep in AD_SEPARATORS:
        if sep in txt:
            txt = txt.split(sep, 1)[0]
    # Some feeds append schedule, cross-promotion, and affiliate metadata in
    # the same HTML paragraph as the narrative. Truncate at the first explicit
    # marker so publication dates and linked-episode topics cannot leak into
    # extraction or clustering.
    metadata_match = _INLINE_METADATA_RE.search(txt)
    if metadata_match:
        txt = txt[: metadata_match.start()]
    txt = _INLINE_CREDIT_SENTENCE_RE.sub("", txt)
    txt = _remove_inline_boilerplate(txt)
    txt = _TRAILING_BROADCASTER_RE.sub("", txt)
    lines = []
    for line in txt.splitlines():
        s = line.strip()
        # Footer sections in the supported feeds are terminal: once one starts,
        # everything after it is metadata rather than episode narrative.
        if _is_terminal_section_heading(s):
            break
        if _is_noise_line(s):
            continue
        if _is_credit_line(s):
            continue
        lines.append(s)
    return "\n".join(lines).strip()


_SEGMENT_NOISE_EXACT = {
    "aus unserer werbung",
    "literatur",
    "erwähnte folgen",
    "podcasts des monats",
    "links",
    "erwähnte episoden",
    "besprochene folgen",
    "im buch erwähnte folgen",
    "museen & ausstellungen",
    "erwähnte literatur",
    "episodenbild",
    "musik",
    "tools",
}

_SEGMENT_NOISE_MARKERS = [
    "apple podcasts",
    "itunes",
    "podcastplattform panoptikum",
    "podcasthörer",
    "freundinnen und freunden",
    "kolleginnen und kollegen",
    "nachbarinnen und nachbarn",
    "wir haben auch ein buch geschrieben",
    "piper.de/buecher/geschichten-aus-der-geschichte",
    "campfirefm",
    "geschichte.shop",
    "amazon.de/gp/product",
    "werbepartner",
    "linktr.ee/geschichtenausdergeschichte",
]


def _is_noise_segment(block: str) -> bool:
    s = " ".join(block.strip().split()).casefold()
    if not s:
        return True
    if s in _SEGMENT_NOISE_EXACT:
        return True
    return any(marker in s for marker in _SEGMENT_NOISE_MARKERS)


def segment_text(pure: str) -> list[tuple[str, str]]:
    """Return list of (section, segment_text)."""
    segs: list[tuple[str, str]] = []
    # crude headings
    for i, block in enumerate(re.split(r"\n\s*\n", pure)):
        b = block.strip()
        if not b:
            continue
        if _is_terminal_section_heading(b):
            break
        if _is_noise_segment(b):
            continue
        lines = [line.strip() for line in b.splitlines() if line.strip()]
        lines = [line for line in lines if not _is_credit_line(line)]
        b = "\n".join(lines).strip()
        if not b:
            continue
        section = "main"
        if b.lower().startswith("das erwartet") or b.lower().startswith("ihr hört"):
            section = "outline"
        if "folgenbild" in b.lower() and "zeigt" in b.lower():
            section = "caption"
        segs.append((section, b))
    return segs


# -------------------- Time extraction --------------------


@dataclass(frozen=True)
class Span:
    start: Optional[dt.date]
    end: Optional[dt.date]
    precision: str
    qualifier: str
    source_text: str
    score: float
    review_flag: Optional[str] = None


_DATE_DMY = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_DATE_DMY_TIME = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})\b")
# Three- and four-digit CE years. The word boundaries intentionally avoid
# matching feed identifiers such as ``GAG544`` where the digits touch letters.
_YEAR = re.compile(r"\b([1-9]\d{2,3})\b")
_YEAR_RANGE = re.compile(r"\b(\d{3,4})\s*[–-]\s*(\d{2,4})\b")
_CENTURY = re.compile(r"\b(\d{1,2})\.\s*Jahrhundert(?:s)?\b", re.IGNORECASE)

# lexical cues
_CUE_STRONG = ["im jahr", "im jahre", "während", "zur zeit", "zu dieser zeit"]
_CUE_MED = [
    "im november",
    "im dezember",
    "im februar",
    "im mai",
    "im juni",
    "im juli",
    "im august",
    "im september",
    "im oktober",
    "im märz",
    "im april",
]


def _mk_date(y: int, m: int = 1, d: int = 1) -> Optional[dt.date]:
    try:
        return dt.date(y, m, d)
    except Exception:
        return None


def _expand_year_range_end(start_year: int, end_raw: int, end_digits: int) -> int:
    if end_digits >= len(str(start_year)):
        return end_raw

    factor = 10**end_digits
    prefix = start_year // factor
    candidate = prefix * factor + end_raw
    if candidate < start_year:
        candidate += factor
    return candidate


def extract_spans(segment: str, section: str) -> list[Span]:
    spans: list[Span] = []
    low = segment.lower()

    cue_boost = 1.0
    if any(c in low for c in _CUE_STRONG):
        cue_boost *= 1.35
    if any(c in low for c in _CUE_MED):
        cue_boost *= 1.10

    section_weight = 1.0
    review_flag = None
    if section == "title":
        # Titles are compact editorial summaries and usually carry less
        # incidental chronology than show notes.
        section_weight *= 1.35
    elif section == "caption":
        section_weight *= 0.18
        if "folgenbild" in low and "zeigt" in low:
            section_weight *= 0.35
            review_flag = "caption-folgenbild"
        if "portr" in low and "jahr" in low:
            section_weight *= 0.22
            review_flag = "caption-portrait-year"

    # exact d.m.y hh:mm
    for d, m, y, hh, mm in _DATE_DMY_TIME.findall(segment):
        dd = _mk_date(int(y), int(m), int(d))
        if dd:
            spans.append(
                Span(
                    dd,
                    dd,
                    "minute",
                    "exact",
                    f"{d}.{m}.{y} {hh}:{mm}",
                    10.0 * cue_boost * section_weight,
                    review_flag,
                )
            )

    # exact d.m.y
    for d, m, y in _DATE_DMY.findall(segment):
        dd = _mk_date(int(y), int(m), int(d))
        if dd:
            spans.append(
                Span(
                    dd,
                    dd,
                    "day",
                    "exact",
                    f"{d}.{m}.{y}",
                    9.0 * cue_boost * section_weight,
                    review_flag,
                )
            )

    # year ranges
    for ys, ye in _YEAR_RANGE.findall(segment):
        sy = int(ys)
        ey_raw = int(ye)
        ey = _expand_year_range_end(sy, ey_raw, len(ye))
        s = _mk_date(sy, 1, 1)
        e = _mk_date(ey, 12, 31)
        if s and e:
            spans.append(
                Span(
                    s,
                    e,
                    "year",
                    "range",
                    f"{ys}-{ye}",
                    7.0 * cue_boost * section_weight,
                    review_flag,
                )
            )

    # centuries
    for c in _CENTURY.findall(segment):
        cc = int(c)
        s = _mk_date((cc - 1) * 100 + 1, 1, 1)
        e = _mk_date(cc * 100, 12, 31)
        if s and e:
            spans.append(
                Span(
                    s,
                    e,
                    "century",
                    "range",
                    f"{c}. Jahrhundert",
                    5.0 * cue_boost * section_weight,
                    review_flag,
                )
            )

    # single years
    for y in _YEAR.findall(segment):
        yy = int(y)
        s = _mk_date(yy, 1, 1)
        e = _mk_date(yy, 12, 31)
        if s and e:
            base = 6.0
            # penalize lone years in captions even further
            if section == "caption":
                base *= 0.25
            spans.append(
                Span(s, e, "year", "year", y, base * cue_boost * section_weight, review_flag)
            )

    # dedupe by (start,end,precision,qualifier)
    uniq: dict[tuple, Span] = {}
    for sp in spans:
        key = (sp.start, sp.end, sp.precision, sp.qualifier, sp.source_text)
        if key not in uniq or sp.score > uniq[key].score:
            uniq[key] = sp
    return sorted(uniq.values(), key=lambda s: s.score, reverse=True)


def best_span(spans: Iterable[Span]) -> Optional[Span]:
    spans = list(spans)
    if not spans:
        return None
    return sorted(spans, key=lambda s: s.score, reverse=True)[0]


# -------------------- Place extraction --------------------

_PLACE_HINT = re.compile(r"\b(in|bei|nach|aus|von|auf)\s+([A-ZÄÖÜ][\wÄÖÜäöüß\-]+)")


def guess_place_candidates(text: str) -> list[str]:
    cands: list[str] = []
    for _, name in _PLACE_HINT.findall(text):
        cands.append(name.strip(".,;:()[]\"'"))
    # also add strong proper nouns from patterns like "Westsahara" etc
    for w in re.findall(r"\b[A-ZÄÖÜ][a-zäöüß]{3,}\b", text):
        if w not in cands:
            cands.append(w)
    return cands[:30]


def extract_places(segment: str, gaz: Gazetteer) -> list[tuple[str, str, float, float, float]]:
    """Return list of (canonical, kind, lat, lon, radius)."""
    out = []
    for cand in guess_place_candidates(segment):
        e = gaz.lookup(cand)
        if e:
            out.append((e.canonical_name, e.kind, e.lat, e.lon, e.radius_km))
    # dedupe by canonical
    seen = set()
    ded = []
    for row in out:
        if row[0] not in seen:
            ded.append(row)
            seen.add(row[0])
    return ded


# -------------------- Entity extraction --------------------

_PERSON = re.compile(
    r"\b([A-ZÄÖÜ][a-zäöüß]+(?:\s+(?:von|der|de|del|da|di))?\s+[A-ZÄÖÜ][a-zäöüß]+)\b"
)
_ORG = re.compile(
    r"\b([A-ZÄÖÜ][\wÄÖÜäöüß\- ]{2,}\b(?:GmbH|AG|Universität|University|Institut|Stiftung|Bundestag|KPdSU|CDU|CSU|NSDAP|KPD|SPD))\b"
)
_EVENT = re.compile(
    r"\b(Schlacht\s+von\s+[A-ZÄÖÜ][\wÄÖÜäöüß\-]+|Revolution\s+[A-ZÄÖÜ][\wÄÖÜäöüß\-]+|Gründung\s+der\s+[A-ZÄÖÜ][\wÄÖÜäöüß\-]+|Attentat\s+auf\s+[A-ZÄÖÜ][\wÄÖÜäöüß\-]+|Parteitag\s+der\s+[A-ZÄÖÜ][\wÄÖÜäöüß\-]+)\b"
)


def extract_entities(segment: str) -> list[tuple[str, str, float, str]]:
    out: list[tuple[str, str, float, str]] = []

    for m in _EVENT.finditer(segment):
        s = m.group(1).strip()
        out.append((s, "event", 0.85, s))

    for m in _ORG.finditer(segment):
        s = " ".join(m.group(1).split())
        out.append((s, "org", 0.80, s))

    for m in _PERSON.finditer(segment):
        s = " ".join(m.group(1).split())
        # avoid capturing obvious org-like patterns
        if any(x in s for x in ["Universität", "University", "Institut", "Stiftung"]):
            continue
        out.append((s, "person", 0.65, s))

    # dedupe
    seen = set()
    ded = []
    for name, kind, conf, src in out:
        key = (name, kind)
        if key not in seen:
            ded.append((name, kind, conf, src))
            seen.add(key)
    return ded


# -------------------- Keywords (RAKE-like, tiny) --------------------

_STOP_DE = {
    "der",
    "die",
    "das",
    "und",
    "oder",
    "aber",
    "wenn",
    "weil",
    "dass",
    "ist",
    "sind",
    "war",
    "waren",
    "eine",
    "ein",
    "einer",
    "eines",
    "einem",
    "im",
    "in",
    "am",
    "an",
    "auf",
    "aus",
    "bei",
    "mit",
    "von",
    "zu",
    "für",
    "über",
    "um",
    "als",
    "auch",
    "noch",
    "mehr",
    "nicht",
    "wir",
    "ihr",
    "euch",
    "uns",
    "diese",
    "dieser",
    "dieses",
    "podcast",
    "podcasts",
    "apple",
    "itunes",
    "instagram",
    "acast",
    "privacy",
    "hosted",
    "www",
    "http",
    "https",
    "com",
    "org",
    "net",
    "rezensiert",
    "bewertet",
    "folge",
    "folgen",
    "feedback",
    "themenvorschlag",
    "quellen",
}

_NOISE_TOKEN_RE = re.compile(r"^(?:gag\d+|feedgag\d+)$")
_NOISE_PHRASE_MARKERS = [
    "apple podcasts",
    "podcastplattform panoptikum",
    "acast",
    "privacy",
    "hosted on",
    "podcasthörer",
    "freuen uns wenn",
    "immer dies möglich",
    "uns empfehlen",
    "uns erzählt",
    "du hast",
    "themenvorschlag",
    "quellen",
    "instagram",
]


def _is_noise_phrase(phrase: str) -> bool:
    p = phrase.casefold()
    if any(m in p for m in _NOISE_PHRASE_MARKERS):
        return True
    if "http" in p or "www" in p:
        return True
    toks = p.split()
    if toks and all(_NOISE_TOKEN_RE.match(t) for t in toks):
        return True
    return False


def rake_phrases(text: str, *, max_phrases: int = 25) -> list[tuple[str, float]]:
    # split on punctuation
    tokens = re.split(r"[^A-Za-zÄÖÜäöüß0-9]+", text.lower())
    phrases: list[list[str]] = []
    cur: list[str] = []
    for t in tokens:
        if not t or t in _STOP_DE or len(t) <= 2 or _NOISE_TOKEN_RE.match(t):
            if cur:
                phrases.append(cur)
                cur = []
            continue
        cur.append(t)
    if cur:
        phrases.append(cur)

    # word frequency & degree
    freq: dict[str, int] = {}
    deg: dict[str, int] = {}
    for ph in phrases:
        unique = ph
        d = len(unique)
        for w in unique:
            freq[w] = freq.get(w, 0) + 1
            deg[w] = deg.get(w, 0) + (d - 1)

    scores: dict[str, float] = {}
    for ph in phrases:
        if len(ph) > 5:
            continue
        phrase = " ".join(ph)
        if _is_noise_phrase(phrase):
            continue
        score = 0.0
        for w in ph:
            score += (deg.get(w, 0) + freq.get(w, 1)) / float(freq.get(w, 1))
        scores[phrase] = max(scores.get(phrase, 0.0), score)

    items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return items[:max_phrases]
