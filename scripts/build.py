#!/usr/bin/env python3
"""Build the site as one self-contained HTML page in public/."""

from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MENU_FILE = ROOT / "menu.html"
CONTENT_FILE = ROOT / "index.html"
OUTPUT_FILE = ROOT / "public" / "index.html"


def main() -> None:
    menu = MENU_FILE.read_text(encoding="utf-8")
    cheat_sheet = CONTENT_FILE.read_text(encoding="utf-8")

    iframe_pattern = re.compile(r"<iframe\b(?P<attrs>[^>]*)>\s*</iframe>", re.IGNORECASE)

    def inline_content(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        if not re.search(r'\bname\s*=\s*["\']content-frame["\']', attrs, re.IGNORECASE):
            return match.group(0)

        # The source document is embedded as srcdoc so the deployed artifact has
        # no runtime dependency on files outside public/.
        attrs = re.sub(r'\s+src\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', "", attrs, flags=re.IGNORECASE)
        attrs = re.sub(r'\s+srcdoc\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', "", attrs, flags=re.IGNORECASE)
        return f'<iframe{attrs} srcdoc="{escape(cheat_sheet, quote=True)}"></iframe>'

    built_page, replacements = iframe_pattern.subn(inline_content, menu)
    if replacements == 0 or "srcdoc=" not in built_page:
        raise RuntimeError("Could not find the content-frame iframe in menu.html")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(built_page, encoding="utf-8")
    print(f"Built {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
