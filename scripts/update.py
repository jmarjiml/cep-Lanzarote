#!/usr/bin/env python3
"""Genera carteles.json desde fuentes públicas del blog CEP Lanzarote.
No requiere API privada, cookies ni permisos de WordPress.
Por seguridad, las entradas sin fecha de cierre explícita no se muestran automáticamente.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, date, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www3.gobiernodecanarias.org/medusa/edublog/cprofeslanzarote/"
FEED = urljoin(BASE, "feed/")
TZ = ZoneInfo("Atlantic/Canary")
MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
          "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
          "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
MONTHS_RE = "|".join(MONTHS)
NUMERIC = re.compile(r"(?<!\d)(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(20\d{2})(?!\d)")
TEXTUAL = re.compile(r"(?<!\d)(\d{1,2})\s+de\s+(" + MONTHS_RE + r")(?:\s+de(?:l)?\s+(20\d{2}))?", re.I)
HEADINGS = re.compile(r"inscripci[oó]n|plazo de (?:inscripci[oó]n|presentaci[oó]n|solicitud)|presentaci[oó]n de (?:solicitudes|trabajos)|matr[ií]cula|solicitudes", re.I)
CLOSE_WORDS = re.compile(r"hasta|finaliz|cierre|l[ií]mite|termina|último d[ií]a|última fecha|\bal\b|fin del plazo", re.I)
INVITE_WORDS = re.compile(r"inscr[ií]b|inscripci[oó]n|solicitud|presentaci[oó]n de (?:trabajos|art[ií]culos)", re.I)
SESSION_WORDS = re.compile(r"calendario|sesiones|ponencia|horario|celebraci[oó]n|fecha de realizaci[oó]n", re.I)

S = requests.Session()
S.headers.update({"User-Agent": "CEP-Lanzarote-Carteleria/1.0 (+blog public RSS)", "Accept": "text/html,application/rss+xml,application/xml"})


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def get(url: str) -> requests.Response:
    response = S.get(url, timeout=25)
    response.raise_for_status()
    return response


def normal(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def parse_dates(s: str, default_year: int | None = None) -> list[tuple[date, int, int]]:
    """(fecha, inicio, fin) para elegir la ÚLTIMA fecha de un rango de inscripción."""
    results = []
    for m in NUMERIC.finditer(s):
        try:
            results.append((date(int(m[3]), int(m[2]), int(m[1])), m.start(), m.end()))
        except ValueError:
            pass
    for m in TEXTUAL.finditer(s):
        year = int(m[3]) if m[3] else default_year
        if year:
            try:
                results.append((date(year, MONTHS[m[2].lower()], int(m[1])), m.start(), m.end()))
            except ValueError:
                pass
    # Para rangos «del 4 de noviembre al 29 de enero de 2027», el primer año
    # se infiere por cercanía a la fecha final; no afecta a la fecha de cierre.
    return sorted(results, key=lambda x: x[1])


def extract_deadline(html: str, published: date) -> tuple[date | None, str]:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "nav", "footer", "form"]):
        node.decompose()
    # Examinar bloques de texto, no toda la publicación (evita confundir
    # el calendario del curso con el plazo de inscripción).
    nodes = soup.find_all(["h2", "h3", "h4", "h5", "p", "li", "div"])
    lines = []
    for node in nodes:
        # Preferir bloques terminales para evitar duplicados del div contenedor.
        if node.name == "div" and node.find(["p", "h2", "h3", "h4", "li"]):
            continue
        txt = normal(node.get_text(" ", strip=True))
        if txt and txt not in lines and len(txt) < 700:
            lines.append(txt)
    candidates = []
    for i, line in enumerate(lines):
        is_heading = HEADINGS.search(line)
        context = line
        if is_heading and len(line) < 95:
            context += " " + " ".join(lines[i + 1:i + 3])[:350]
        if not (HEADINGS.search(context) or (INVITE_WORDS.search(context) and CLOSE_WORDS.search(context))):
            continue
        if SESSION_WORDS.search(line[:35]) and not HEADINGS.search(line):
            continue
        dates = parse_dates(context, published.year)
        if not dates:
            continue
        # La fecha final de un rango es la mayor en orden textual.
        # Evitar fecha sola cuando se trata de «inscripciones desde ...».
        if len(dates) == 1 and not CLOSE_WORDS.search(context):
            continue
        chosen = dates[-1][0]
        # Una fecha sin año se hereda de publicación, salvo fechas anteriores
        # por cambio de año (noviembre -> enero).
        if len(dates) == 1 and chosen < published and chosen.month < published.month and chosen.year == published.year and chosen.month <= 3 and published.month >= 10:
            chosen = chosen.replace(year=chosen.year + 1)
        candidates.append((chosen, context[:230]))
    if not candidates:
        return None, "No se ha encontrado una fecha límite explícita"
    # No abrir una entrada por un plazo que quizá ya venció cuando otra fecha
    # cercana se refiere a otro trámite; primera referencia fuerte prima.
    return candidates[0]


def image_for(html: str, page: BeautifulSoup, url: str) -> str | None:
    containers = page.select("article .entry-content, article .et_pb_post_content, .et_post_meta_wrapper, article, main")
    selected = containers[0] if containers else page
    options = []
    for im in selected.select("img"):
        src = im.get("data-src") or im.get("data-lazy-src") or im.get("src")
        if not src or src.startswith("data:"):
            continue
        alt = (im.get("alt") or "").lower()
        candidate = urljoin(url, src)
        if any(x in candidate.lower() for x in ("avatar", "logo", "gravatar", "emoji", "icon-")):
            continue
        try:
            w, h = int(im.get("width", "0")), int(im.get("height", "0"))
        except ValueError:
            w, h = 0, 0
        if w and w < 200 or h and h < 200:
            continue
        score = (30 if re.search(r"cartel|curso|convocatoria|jameos|formaci[oó]n", alt) else 0) + (10 if w >= 600 else 0)
        options.append((score, candidate))
    if options:
        options.sort(key=lambda x: -x[0])
        return options[0][1]
    # Puede haber imagen en el RSS aunque no en el cuerpo de la noticia.
    feed_soup = BeautifulSoup(html, "html.parser")
    for im in feed_soup.find_all("img"):
        src = im.get("src")
        if src and not src.startswith("data:"):
            return urljoin(url, src)
    meta = page.find("meta", property="og:image")
    if meta and meta.get("content"):
        src = urljoin(url, meta["content"])
        if "logo" not in src.lower():
            return src
    return None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    overrides = read_json(ROOT / "config.json")
    manual = overrides.get("manual", {})
    excluded = set(overrides.get("exclude", []))
    now = datetime.now(TZ)
    today = now.date()
    post_limit = int(overrides.get("max_posts", 65))
    feed_pages = int(overrides.get("feed_pages", 7))
    found = {}
    errors = []
    feed_success = False
    for pg in range(1, feed_pages + 1):
        feed_url = FEED if pg == 1 else FEED + f"?paged={pg}"
        try:
            raw = get(feed_url).content
            xml = ET.fromstring(raw)
        except Exception as exc:
            errors.append(f"RSS página {pg}: {exc}")
            if pg == 1:
                logging.error(errors[-1])
                return 1  # No publicar una lista vacía por caída de RSS
            break
        feed_success = True
        items = xml.findall("./channel/item")
        if not items:
            break
        added = 0
        for item in items:
            link = (item.findtext("link") or "").strip()
            if not link or link in found or link in excluded:
                continue
            title = normal(BeautifulSoup(item.findtext("title") or "", "html.parser").get_text())
            raw_date = item.findtext("pubDate") or ""
            try:
                published = parsedate_to_datetime(raw_date).date()
            except Exception:
                published = today
            if published > today or published < today - timedelta(days=190):
                continue
            content = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or item.findtext("description") or ""
            found[link] = (title, published, content)
            added += 1
            if len(found) >= post_limit:
                break
        if len(found) >= post_limit or (pg > 1 and added == 0):
            break
    entries = []
    ambiguous = []
    for url, (title, published, feed_html) in found.items():
        opt = manual.get(url, {})
        if opt.get("exclude"):
            continue
        try:
            if "close" in opt:
                deadline = date.fromisoformat(opt["close"])
                reason = "Fecha verificada manualmente"
            else:
                # El contenido RSS suele ser completo; inspeccionamos la página
                # para obtener el cartel de mayor calidad.
                deadline, reason = extract_deadline(feed_html, published)
            if deadline is not None and deadline < today:
                continue
            page = BeautifulSoup(get(url).text, "html.parser")
            article = page.select_one("article .entry-content, article .et_pb_post_content, article") or page
            if "close" not in opt:
                page_date, page_reason = extract_deadline(str(article), published)
                if page_date is not None:
                    deadline, reason = page_date, page_reason
            if deadline is None:
                ambiguous.append({"title": title, "url": url, "reason": reason})
                continue
            if deadline < today:
                continue
            img = opt.get("image") or image_for(feed_html, page, url)
            if not img or urlparse(img).scheme not in ("http", "https"):
                ambiguous.append({"title": title, "url": url, "reason": "No se encontró cartel válido"})
                continue
            entries.append({"title": title, "url": url, "image": img,
                            "close": deadline.isoformat(), "published": published.isoformat()})
        except Exception as exc:
            errors.append(f"Entrada {url}: {exc}")
            logging.warning(errors[-1])
    entries.sort(key=lambda x: x["published"], reverse=True)
    out = ROOT / "site" / "carteles.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"updated": now.isoformat(), "entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "site" / "revision.json").write_text(json.dumps({"pending_review": ambiguous, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("RSS OK: %s entradas; %s abiertas; %s para revisar", len(found), len(entries), len(ambiguous))
    return 0 if feed_success else 1


if __name__ == "__main__":
    sys.exit(main())
