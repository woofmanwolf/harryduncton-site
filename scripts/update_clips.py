#!/usr/bin/env python3
"""Daily clips updater for harryduncton.com.

Reads data/feeds.json (RSS/Atom feeds such as a Google Alert for your name),
merges what it finds with data/manual.json and previously found clips, then
rewrites the "Latest work" list inside index.html.

Items from trusted outlets (allow_domains) go straight on the site. Anything
else lands in data/review.json for you to check by hand, so a stray mention
on a random blog never appears on your homepage.

Standard library only: nothing to install.
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INDEX = ROOT / "index.html"
FOUND = DATA / "found.json"
REVIEW = DATA / "review.json"
START, END = "<!--CLIPS:START-->", "<!--CLIPS:END-->"

OUTLET_NAMES = {
    "gardenersworld.com": "BBC Gardeners' World Magazine",
    "t3.com": "T3",
    "trustedreviews.com": "Trusted Reviews",
    "granddesignsmagazine.com": "Grand Designs Magazine",
    "stuff.tv": "Stuff",
    "bbc.co.uk": "BBC",
    "theguardian.com": "The Guardian",
    "telegraph.co.uk": "The Telegraph",
    "independent.co.uk": "The Independent",
    "thetimes.com": "The Times",
    "rfs.org.uk": "Royal Forestry Society",
}
TYPE_LABELS = {"review": "Review", "guide": "Buying guide",
               "feature": "Feature", "broadcast": "Radio"}
ROBOT_WORDS = ("robot", "robotic", "automower", "landroid", "navimow",
               "mammotion", "luba")


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def domain_of(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def norm_key(url):
    p = urllib.parse.urlparse(url)
    return (domain_of(url) + p.path.rstrip("/")).lower()


def unwrap_google(url):
    """Google Alert links point at google.com/url?url=REAL_LINK."""
    p = urllib.parse.urlparse(url)
    if p.netloc.endswith("google.com") and p.path == "/url":
        q = urllib.parse.parse_qs(p.query)
        for key in ("url", "q"):
            if q.get(key):
                return q[key][0]
    return url


def clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_date(text):
    if not text:
        return None
    try:
        return parsedate_to_datetime(text).date().isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def classify(title):
    t = title.lower()
    if "review" in t:
        kind = "review"
    elif re.search(r"\bbest\b", t):
        kind = "guide"
    else:
        kind = "feature"
    topics = ["robot"] if any(w in t for w in ROBOT_WORDS) else []
    return kind, topics


def tidy_title(title):
    """Drop the ' | T3' style site suffix publishers add."""
    return re.split(r"\s+[|–—-]\s+(?=[^|]{0,40}$)", title)[0].strip()


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "harryduncton.com clips updater (once daily)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def read_feed(raw):
    """Yield (title, link, date, summary) from RSS or Atom."""
    root = ET.fromstring(raw)
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    for item in root.iter("item"):
        yield (item.findtext("title", ""), item.findtext("link", ""),
               item.findtext("pubDate") or item.findtext("date"),
               item.findtext("description", "") + " " + item.findtext("creator", ""))
    for entry in root.iter("entry"):
        link = ""
        for l in entry.findall("link"):
            if l.get("rel", "alternate") == "alternate":
                link = l.get("href", "")
        author = " ".join(a.findtext("name", "") for a in entry.findall("author"))
        yield (entry.findtext("title", ""), link,
               entry.findtext("published") or entry.findtext("updated"),
               (entry.findtext("content", "") or entry.findtext("summary", "")) + " " + author)


def gather(config):
    name = config.get("name", "").lower()
    surname = name.split()[-1] if name else ""
    allow = config.get("allow_domains", [])
    trusted, unsure = [], []
    for feed in config.get("feeds", []):
        url = feed.get("url", "")
        if not url.startswith(("http", "file:")):
            continue
        try:
            items = list(read_feed(fetch(url)))
        except Exception as exc:  # one bad feed must not stop the rest
            print(f"Skipped feed {url}: {exc}", file=sys.stderr)
            continue
        for title, link, date, summary in items:
            title, link = tidy_title(clean(title)), unwrap_google(link.strip())
            if not title or not link.startswith("http"):
                continue
            if not feed.get("byline_only") and surname not in (title + " " + clean(summary)).lower():
                continue
            if "/author/" in link or domain_of(link).endswith("harryduncton.com"):
                continue
            kind, topics = classify(title)
            dom = domain_of(link)
            clip = {"title": title, "url": link,
                    "outlet": feed.get("outlet") or OUTLET_NAMES.get(dom, dom),
                    "type": kind, "topics": topics, "date": parse_date(date),
                    "source": "feed"}
            if any(dom == d or dom.endswith("." + d) for d in allow):
                trusted.append(clip)
            else:
                unsure.append(clip)
    return trusted, unsure


def merge(manual, found, new):
    """Manual wins over feed copies of the same link; found clips are kept."""
    by_key = {}
    for clip in found + new:
        by_key.setdefault(norm_key(clip["url"]), clip)
    manual_keys = {norm_key(c["url"]) for c in manual}
    feed_only = [c for k, c in by_key.items() if k not in manual_keys]
    return feed_only, manual + feed_only


def ordered(clips):
    dated = sorted([c for c in clips if c.get("date")], key=lambda c: c["date"], reverse=True)
    return dated + [c for c in clips if not c.get("date")]


def card(clip):
    esc = lambda s: html.escape(s or "", quote=True)
    meta = TYPE_LABELS.get(clip.get("type"), "Article")
    if clip.get("date"):
        meta += " · " + datetime.fromisoformat(clip["date"]).strftime("%b %Y")
    elif clip.get("type") == "guide":
        meta += " · updated regularly"
    return (f'<li class="clip" data-type="{esc(clip.get("type"))}" '
            f'data-topics="{esc(" ".join(clip.get("topics", [])))}">'
            f'<a href="{esc(clip["url"])}" target="_blank" rel="noopener">'
            f'<span class="clip-outlet">{esc(clip.get("outlet"))}</span>'
            f'<span class="clip-title">{esc(clip["title"])}</span>'
            f'<span class="clip-meta">{esc(meta)}</span></a></li>')


def write_index(clips):
    page = INDEX.read_text(encoding="utf-8")
    if START not in page or END not in page:
        sys.exit("index.html is missing the CLIPS markers")
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y")
    block = (f'{START}\n<ul class="clips" id="clips" data-updated="{stamp}">\n'
             + "\n".join(card(c) for c in ordered(clips)) + f"\n</ul>\n{END}")
    new_page = re.sub(re.escape(START) + ".*?" + re.escape(END),
                      lambda _: block, page, flags=re.S)
    # Only rewrite when the clip list itself changed, so the date stamp alone
    # never triggers a commit.
    strip = lambda s: re.sub(r'data-updated="[^"]*"', "", s)
    if strip(new_page) != strip(page):
        INDEX.write_text(new_page, encoding="utf-8")
        return True
    return False


def main():
    config = load(DATA / "feeds.json", {})
    manual = load(DATA / "manual.json", {}).get("clips", [])
    found = load(FOUND, [])
    trusted, unsure = gather(config)
    found, all_clips = merge(manual, found, trusted)
    FOUND.write_text(json.dumps(found, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    review = load(REVIEW, [])
    seen = {norm_key(c["url"]) for c in review + all_clips}
    review += [c for c in unsure if norm_key(c["url"]) not in seen]
    REVIEW.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    changed = write_index(all_clips)
    print(f"{len(all_clips)} clips on site ({len(trusted)} from feeds today), "
          f"{len(review)} waiting in review.json. index.html "
          f"{'updated' if changed else 'unchanged'}.")


if __name__ == "__main__":
    main()
