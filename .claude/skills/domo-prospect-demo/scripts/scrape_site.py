#!/usr/bin/env python3
"""Scrape a homepage for brand colors, fonts, logo, and text context."""
import argparse
import json
import re
from collections import Counter
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEX_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}\b")
GENERIC_FONT_KEYWORDS = {"inherit", "unset", "initial", "normal", "sans-serif", "serif", "monospace"}


def _is_neutral_color(hex_color, tolerance=15):
    """Grayscale (including near-grayscale) colors read as UI chrome, not brand color."""
    digits = hex_color.lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    r, g, b = int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)
    return max(r, g, b) - min(r, g, b) <= tolerance


def fetch_html(url, timeout=10):
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_title_and_description(soup):
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    description = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        description = meta["content"].strip()
    return title, description


def extract_colors(soup, extra_css=""):
    candidates = Counter()

    theme_meta = soup.find("meta", attrs={"name": "theme-color"})
    theme_color = theme_meta["content"].strip() if theme_meta and theme_meta.get("content") else None

    style_text = " ".join(tag.get_text() for tag in soup.find_all("style"))
    inline_styles = " ".join(tag.get("style", "") for tag in soup.find_all(style=True))
    combined = style_text + " " + inline_styles + " " + extra_css

    for match in HEX_COLOR_RE.findall(combined):
        normalized = match.lower()
        if not _is_neutral_color(normalized):
            candidates[normalized] += 1

    ranked = [color for color, _ in candidates.most_common(8)]
    if theme_color and theme_color.lower() not in ranked:
        ranked.insert(0, theme_color.lower())

    return ranked, theme_color


def extract_fonts(soup, extra_css=""):
    fonts = []
    for link in soup.find_all("link", href=True):
        href = link["href"]
        if "fonts.googleapis.com" in href or "fonts.google.com" in href:
            fonts.append(href)

    style_text = " ".join(tag.get_text() for tag in soup.find_all("style")) + " " + extra_css
    for match in re.findall(r"font-family:\s*([^;{}]+)", style_text):
        name = match.split(",")[0]
        name = re.sub(r"!important", "", name, flags=re.IGNORECASE).strip().strip("'\"")
        if not name or name.lower() in GENERIC_FONT_KEYWORDS or "icon" in name.lower():
            continue
        fonts.append(name)

    seen = []
    for f in fonts:
        if f not in seen:
            seen.append(f)
    return seen[:5]


def extract_logo(soup, base_url):
    for img in soup.find_all("img"):
        class_attr = img.get("class") or []
        haystack = " ".join([
            img.get("alt", ""),
            " ".join(class_attr),
            img.get("id", ""),
            img.get("src", ""),
        ]).lower()
        if "logo" in haystack and img.get("src"):
            return urljoin(base_url, img["src"])

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        return urljoin(base_url, og_image["content"])

    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)
        if "icon" in rel_str.lower() and link.get("href"):
            return urljoin(base_url, link["href"])

    return None


def extract_stylesheet_urls(soup, base_url):
    urls = []
    for link in soup.find_all("link", href=True):
        rel = link.get("rel") or []
        rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)
        if "stylesheet" in rel_str.lower():
            urls.append(urljoin(base_url, link["href"]))
    return urls


def fetch_linked_stylesheets(urls, timeout=10, max_sheets=5):
    css_text = ""
    for url in urls[:max_sheets]:
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            resp.raise_for_status()
            css_text += " " + resp.text
        except requests.RequestException:
            continue
    return css_text


def extract_body_text(soup, max_chars=3000):
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def scrape(url):
    result = {
        "url": url,
        "scrape_ok": False,
        "title": "",
        "meta_description": "",
        "theme_color": None,
        "colors": [],
        "fonts": [],
        "logo_url": None,
        "body_text": "",
        "error": None,
    }
    try:
        html = fetch_html(url)
    except requests.RequestException as exc:
        result["error"] = str(exc)
        return result

    soup = BeautifulSoup(html, "html.parser")
    title, description = extract_title_and_description(soup)

    stylesheet_urls = extract_stylesheet_urls(soup, url)
    extra_css = fetch_linked_stylesheets(stylesheet_urls)

    colors, theme_color = extract_colors(soup, extra_css)

    result.update({
        "scrape_ok": True,
        "title": title,
        "meta_description": description,
        "theme_color": theme_color,
        "colors": colors,
        "fonts": extract_fonts(soup, extra_css),
        "logo_url": extract_logo(soup, url),
        "body_text": extract_body_text(soup),
    })
    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape a homepage for brand style + context.")
    parser.add_argument("url", help="Homepage URL to scrape")
    args = parser.parse_args()
    print(json.dumps(scrape(args.url), indent=2))


if __name__ == "__main__":
    main()
