#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
India Code Legislation Downloader
=================================

Downloads legislations from India Code (https://www.indiacode.nic.in) and
saves them as UTF-8 text in this layout:

    <OUTPUT_PATH>/
        <Legislation Name>/
            Section_001 - <Section title>.txt
            Section_002 - <Section title>.txt
            ...

Every legislation gets its own folder, and every section is its own .txt file
holding that section's text.

EDIT THE TWO SETTINGS BELOW (OUTPUT_PATH and LEGISLATIONS), then run:

    python download_legislation.py

See README.md for full instructions.
"""

# =============================================================================
# 1) OUTPUT PATH  --  WHERE THE DOWNLOADED FOLDERS WILL BE SAVED
# =============================================================================
# Put the full path of the folder you want between the quotes.
# Keep the letter r in front of the quotes (it makes Windows paths work).
#
#   Windows example : OUTPUT_PATH = r"C:\Users\Karthik\Documents\Legislations"
#   Mac/Linux example: OUTPUT_PATH = r"/Users/karthik/Documents/Legislations"
#
# If you leave it empty (""), a folder named "downloaded_legislations" is
# created next to this script.

OUTPUT_PATH = r""


# =============================================================================
# 2) LEGISLATIONS TO DOWNLOAD  --  REPLACE THESE NAMES WITH THE ONES YOU NEED
# =============================================================================
# Each line is one legislation. Change the name inside the quotes to any
# other Act. Add or remove lines as you like (keep the comma at the end).
#
# Option A - just the name (the script searches India Code for it):
#       {"name": "The Indian Contract Act, 1872"},
#
# Option B - name + India Code link (most reliable; use this if the search
#            picks the wrong Act). Open the Act on indiacode.nic.in in your
#            browser and copy the address bar link, e.g.
#            https://www.indiacode.nic.in/handle/123456789/XXXX
#       {"name": "The Indian Contract Act, 1872",
#        "url":  "https://www.indiacode.nic.in/handle/123456789/XXXX"},
#
# The "name" is also used as the folder name.

LEGISLATIONS = [
    {"name": "The Indian Contract Act, 1872"},
    {"name": "The Specific Relief Act, 1963"},
    {"name": "The Limitation Act, 1963"},
]


# =============================================================================
# 3) OPTIONAL SETTINGS  (you normally don't need to touch these)
# =============================================================================
BASE_URL = "https://www.indiacode.nic.in"
DELAY_BETWEEN_REQUESTS = 1.0   # seconds; be polite to the government server
REQUEST_TIMEOUT = 60           # seconds per request
MAX_RETRIES = 4                # retries per request on network errors
VERIFY_SSL = True              # set to False ONLY if you get SSL certificate errors
SKIP_EXISTING_FILES = True     # re-running continues where it stopped
INCLUDE_FOOTNOTES = True       # add the section's footnotes at the end of each file


# =============================================================================
# ------------------------  NO NEED TO EDIT BELOW  ----------------------------
# =============================================================================

import json
import os
import re
import sys
import time
import unicodedata
from urllib.parse import parse_qs, urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing packages. Please run:  pip install -r requirements.txt")
    sys.exit(1)

if not VERIFY_SSL:
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

session = requests.Session()
session.headers.update(HEADERS)


# ----------------------------------------------------------------------------
# Networking
# ----------------------------------------------------------------------------
def fetch(url, params=None, ajax=False):
    """GET a URL with retries. Returns a requests.Response."""
    headers = {"X-Requested-With": "XMLHttpRequest"} if ajax else None
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, headers=headers,
                               timeout=REQUEST_TIMEOUT, verify=VERIFY_SSL)
            resp.raise_for_status()
            time.sleep(DELAY_BETWEEN_REQUESTS)
            return resp
        except requests.RequestException as exc:
            last_error = exc
            wait = 2 ** attempt
            print(f"      ! request failed ({exc.__class__.__name__}), "
                  f"retry {attempt}/{MAX_RETRIES} in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Could not download {url}: {last_error}")


# ----------------------------------------------------------------------------
# Text helpers
# ----------------------------------------------------------------------------
def safe_filename(text, max_len=120):
    """Make a string safe to use as a file/folder name on Windows/Mac/Linux."""
    text = unicodedata.normalize("NFC", text or "")
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", text)
    text = re.sub(r"\s+", " ", text).strip().rstrip(". ")
    if len(text) > max_len:
        text = text[:max_len].rstrip(". ")
    return text or "untitled"


def html_to_text(html):
    """Convert a fragment of HTML into clean plain text, keeping paragraphs."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li", "tr", "h1", "h2", "h3",
                                "h4", "h5", "h6", "table", "blockquote"]):
        block.insert_before("\n")
        block.insert_after("\n")
    text = soup.get_text()
    text = text.replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


# ----------------------------------------------------------------------------
# Step 1: find the Act page on India Code
# ----------------------------------------------------------------------------
HANDLE_RE = re.compile(r"/handle/123456789/\d+")


def find_act_url(name):
    """Search India Code for an Act by name and return its /handle/ URL."""
    print(f"    Searching India Code for: {name}")
    resp = fetch(f"{BASE_URL}/simple-search", params={"query": name})
    soup = BeautifulSoup(resp.text, "html.parser")

    wanted = norm(name)
    wanted_year = re.findall(r"(1[6-9]\d\d|20\d\d)", name)
    candidates = []
    for a in soup.find_all("a", href=True):
        m = HANDLE_RE.search(a["href"])
        title = a.get_text(" ", strip=True)
        if not m or not title:
            continue
        t = norm(title)
        score = 0
        if t == wanted:
            score += 100
        if wanted in t or t in wanted:
            score += 50
        score += len(set(t.split()) & set(wanted.split()))
        if wanted_year and wanted_year[0] in title:
            score += 20
        candidates.append((score, title, urljoin(BASE_URL, m.group(0))))

    if not candidates:
        return None
    candidates.sort(key=lambda c: -c[0])
    best = candidates[0]
    print(f"    Best match: {best[1]}  ->  {best[2]}")
    return best[2]


# ----------------------------------------------------------------------------
# Step 2: list all sections of the Act
# ----------------------------------------------------------------------------
def list_sections(act_url):
    """
    Return a list of dicts: {actid, section_id, number, title, url}
    by reading the section links ("show-data?actid=...&sectionId=...")
    on the Act's India Code page.
    """
    url = act_url
    if "view_type" not in url:
        url += ("&" if "?" in url else "?") + "view_type=browse"
    resp = fetch(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    sections, seen = [], set()
    for a in soup.find_all("a", href=True):
        # HTML parsers read "&sectionId" as the entity "&sect;" (the § sign),
        # so undo that before reading the link parameters.
        href = a["href"].replace("\u00a7ion", "&section")
        if "show-data" not in href or "sectionId" not in href:
            continue
        full = urljoin(BASE_URL + "/", href)
        qs = parse_qs(urlparse(full).query)
        actid = (qs.get("actid") or [""])[0]
        sec_id = (qs.get("sectionId") or [""])[0]
        if not sec_id or sec_id in seen:
            continue
        seen.add(sec_id)

        number = (qs.get("sectionno") or [""])[0].strip()
        order = (qs.get("orderno") or [""])[0].strip()
        title = a.get_text(" ", strip=True)
        if not title:
            # India Code sometimes puts the heading in a neighbouring element
            parent = a.find_parent(["li", "tr", "div"])
            title = parent.get_text(" ", strip=True) if parent else ""
        sections.append({
            "actid": actid,
            "section_id": sec_id,
            "number": number,
            "order": order,
            "title": title,
            "url": full,
        })

    # keep India Code's order (orderno) when it is available
    if sections and all(s["order"].isdigit() for s in sections):
        sections.sort(key=lambda s: int(s["order"]))

    act_title = ""
    h = soup.find(["h1", "h2", "h3"])
    if h:
        act_title = h.get_text(" ", strip=True)
    return sections, act_title, soup


# ----------------------------------------------------------------------------
# Step 3: download the text of one section
# ----------------------------------------------------------------------------
def get_section_text(sec):
    """
    India Code loads each section's text through the endpoint
    /SectionPageContent?actid=...&sectionID=...  which returns JSON
    {"content": "<html>", "footnote": "<html>"}. If that fails we fall back to
    reading the section's show-data page directly.
    """
    content_html, footnote_html = "", ""
    try:
        resp = fetch(f"{BASE_URL}/SectionPageContent",
                     params={"actid": sec["actid"], "sectionID": sec["section_id"]},
                     ajax=True)
        data = json.loads(resp.text)
        content_html = data.get("content") or ""
        footnote_html = data.get("footnote") or ""
    except (RuntimeError, ValueError):
        pass

    if not content_html.strip():
        resp = fetch(sec["url"])
        soup = BeautifulSoup(resp.text, "html.parser")
        box = (soup.find(id=re.compile(r"(section|sec).*content", re.I))
               or soup.find(class_=re.compile(r"(section|sec).*content|actContent", re.I))
               or soup.find("div", class_=re.compile(r"panel-body|tab-content", re.I)))
        content_html = str(box) if box else ""

    text = html_to_text(content_html)
    if INCLUDE_FOOTNOTES:
        foot = html_to_text(footnote_html)
        if foot:
            text += "\n\n----- Footnotes -----\n" + foot
    return text


# ----------------------------------------------------------------------------
# Step 4: save everything
# ----------------------------------------------------------------------------
def section_filename(index, sec, width):
    label = sec["number"] or str(index)
    title = sec["title"]
    # avoid "Section 1 - 1. Short title" duplication
    title = re.sub(r"^\s*(section\s*)?" + re.escape(label) + r"\s*[.:\-]?\s*",
                   "", title, flags=re.I)
    num = str(index).zfill(width)
    name = f"Section_{num} - Sec {label}"
    if title:
        name += f" - {title}"
    return safe_filename(name, 150) + ".txt"


def download_legislation(item, out_root):
    name = item["name"].strip()
    print("\n" + "=" * 78)
    print(f"  LEGISLATION: {name}")
    print("=" * 78)

    act_url = (item.get("url") or "").strip() or find_act_url(name)
    if not act_url:
        print("    X Could not find this Act on India Code. Add its link as "
              '"url" in LEGISLATIONS (see README).')
        return False

    print(f"    Act page: {act_url}")
    sections, act_title, _ = list_sections(act_url)
    if not sections:
        print("    X No sections found on the Act page. The Act may only be\n"
              "      available as a PDF on India Code, or the link is wrong.")
        return False

    folder = os.path.join(out_root, safe_filename(name))
    os.makedirs(folder, exist_ok=True)
    print(f"    Found {len(sections)} sections. Saving to: {folder}")

    width = max(3, len(str(len(sections))))
    ok = failed = 0
    for i, sec in enumerate(sections, 1):
        fname = section_filename(i, sec, width)
        path = os.path.join(folder, fname)
        if SKIP_EXISTING_FILES and os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"    [{i}/{len(sections)}] exists, skipping: {fname}")
            ok += 1
            continue
        try:
            text = get_section_text(sec)
            header = f"{name}\n"
            header += f"Section {sec['number']}" if sec["number"] else f"Section {i}"
            if sec["title"]:
                header += f": {sec['title']}"
            header += f"\nSource: {sec['url']}\n\n"
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(header + (text or "[No text returned by India Code]") + "\n")
            print(f"    [{i}/{len(sections)}] saved: {fname}")
            ok += 1
        except Exception as exc:  # keep going with the next section
            print(f"    [{i}/{len(sections)}] FAILED: {fname}  ({exc})")
            failed += 1

    print(f"    Done: {ok} saved, {failed} failed.")
    return failed == 0


def main():
    out_root = OUTPUT_PATH.strip() or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "downloaded_legislations")
    out_root = os.path.abspath(os.path.expanduser(out_root))
    os.makedirs(out_root, exist_ok=True)
    print(f"Output folder: {out_root}")
    print(f"Legislations to download: {len(LEGISLATIONS)}")

    results = {}
    for item in LEGISLATIONS:
        try:
            results[item["name"]] = download_legislation(item, out_root)
        except Exception as exc:
            print(f"    X Error: {exc}")
            results[item["name"]] = False

    print("\n" + "=" * 78)
    print("  SUMMARY")
    print("=" * 78)
    for name, good in results.items():
        print(f"  [{'OK' if good else 'PROBLEM'}]  {name}")
    print(f"\nFiles are in: {out_root}")


if __name__ == "__main__":
    main()
