#!/usr/bin/env python3
"""Build the site as one self-contained HTML page in public/."""

from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MENU_FILE = ROOT / "menu.html"
OUTPUT_FILE = ROOT / "public" / "index.html"
LINK_PATTERN = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<label>.*?)</a>", re.IGNORECASE | re.DOTALL)


def attribute(attrs: str, name: str) -> str | None:
    match = re.search(rf'\b{name}\s*=\s*(["\'])(.*?)\1', attrs, re.IGNORECASE | re.DOTALL)
    return match.group(2) if match else None


def main() -> None:
    menu = MENU_FILE.read_text(encoding="utf-8")
    sections: dict[str, str] = {}

    def collect_link(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        href = attribute(attrs, "href")
        if not href or not href.lower().endswith(".html"):
            return match.group(0)

        section_path = (ROOT / href).resolve()
        if ROOT not in section_path.parents or not section_path.is_file():
            raise FileNotFoundError(f"Menu section source not found: {href}")

        sections[href] = section_path.read_text(encoding="utf-8")
        attrs = re.sub(r'\s+href\s*=\s*(["\']).*?\1', "", attrs, flags=re.IGNORECASE | re.DOTALL)
        attrs += f' href="#{escape(href, quote=True)}" data-section-file="{escape(href, quote=True)}"'
        return f'<a{attrs}>{match.group("label")}</a>'

    menu = LINK_PATTERN.sub(collect_link, menu)
    if not sections:
        raise RuntimeError("No local HTML sections were found in the menu")

    iframe_pattern = re.compile(r"<iframe\b(?P<attrs>[^>]*)>\s*</iframe>", re.IGNORECASE)

    def inline_initial_section(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        if attribute(attrs, "name") != "content-frame":
            return match.group(0)
        source = attribute(attrs, "src")
        if source not in sections:
            raise RuntimeError(f"Initial iframe source is not a menu section: {source}")
        attrs = re.sub(r'\s+src\s*=\s*(["\']).*?\1', "", attrs, flags=re.IGNORECASE | re.DOTALL)
        attrs = re.sub(r'\s+srcdoc\s*=\s*(["\']).*?\1', "", attrs, flags=re.IGNORECASE | re.DOTALL)
        return f'<iframe{attrs} srcdoc="{escape(sections[source], quote=True)}"></iframe>'

    menu, replacements = iframe_pattern.subn(inline_initial_section, menu)
    if replacements == 0:
        raise RuntimeError("Could not find the content-frame iframe in menu.html")

    documents_json = json.dumps(sections, ensure_ascii=False).replace("</", "<\\/")
    section_script = f"""
    <script>
        const sectionDocuments = {documents_json};
        const sectionFrame = document.querySelector('iframe[name="content-frame"]');
        document.querySelectorAll('.nav-link[data-section-file]').forEach((link) => {{
            link.addEventListener('click', () => {{
                const documentHtml = sectionDocuments[link.dataset.sectionFile];
                if (sectionFrame && documentHtml) sectionFrame.srcdoc = documentHtml;
            }});
        }});
    </script>
    """
    if "</body>" not in menu.lower():
        raise RuntimeError("menu.html is missing its closing body tag")
    menu = re.sub(r"</body>", section_script + "\n</body>", menu, count=1, flags=re.IGNORECASE)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(menu, encoding="utf-8")
    print(f"Built {OUTPUT_FILE.relative_to(ROOT)} with {len(sections)} section(s)")


if __name__ == "__main__":
    main()
