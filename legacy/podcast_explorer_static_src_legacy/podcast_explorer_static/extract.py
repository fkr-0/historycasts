from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from .rss_parse import html_to_text
from .gazetteer import Gazetteer


AD_SEPARATORS = [
    "+++++",
    "**********",
]


def clean_description(raw: str) -> str:
    """Remove ad/footer boilerplate and convert HTML to text."""
    txt = html_to_text(raw)
    # drop everything after repeated ad separator blocks
    for sep in AD_SEPARATORS:
        if sep in txt:
            txt = txt.split(sep, 1)[0]
    # remove obvious social media/footer lines
    drop_markers = [
        "instagram",
        "tiktok",
        "facebook",
        "wenn euch",
        "abonniert",
        "noch mehr",
        "deutschlandfunk app",
        "campfire",
        "werbepartner",
        "werbung",
    ]
    lines = []
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        if any(m in s.lower() for m in drop_markers):
            continue
        lines.append(s)
    return "\n".join(lines).strip()


def segment_text(pure: str) -> list[tuple[str, str]]:
    """Return list of (section, segment_text)."""
    segs: list[tuple[str, str]] = []
    # crude headings
    for i, block in enumerate(re.split(r"\n\s*\n", pure)):
        b = block.strip()
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
_YEAR = re.compile(r"\b(1\d{3}|20\d{2})\b")
_YEAR_RANGE = re.compile(r"\b(\d{3,4})\s*[–-]\s*(\d{2,4})\b")
_CENTURY = re.compile(r"\b(\d{1,2})\.\s*Jahrhundert\b", re.IGNORECASE)

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
    if section == "caption":
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
        ey = int(ye) if len(ye) == 4 else int(str(sy)[:2] + ye)
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
}


def rake_phrases(text: str, *, max_phrases: int = 25) -> list[tuple[str, float]]:
    # split on punctuation
    tokens = re.split(r"[^A-Za-zÄÖÜäöüß0-9]+", text.lower())
    phrases: list[list[str]] = []
    cur: list[str] = []
    for t in tokens:
        if not t or t in _STOP_DE or len(t) <= 2:
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
        score = 0.0
        for w in ph:
            score += (deg.get(w, 0) + freq.get(w, 1)) / float(freq.get(w, 1))
        scores[phrase] = max(scores.get(phrase, 0.0), score)

    items = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return items[:max_phrases]
