from __future__ import annotations

from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/yoichigoto/Documents/Obsidian Vault/アースホッパー売却")
EXHIBITS = ROOT / "litigation/indy_tokyo_district_court/exhibits"


def md_to_plain_text(md: str) -> str:
    # Minimal cleanup: strip markdown code fences, keep text as-is.
    lines: list[str] = []
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            lines.append(line)
        else:
            # Remove leading markdown bullets/headers minimally
            lines.append(line.replace("\t", "    "))
    return "\n".join(lines).strip() + "\n"


def text_to_multipage_pdf(title: str, body: str, out_pdf: Path) -> None:
    # A4 portrait-ish
    width, height = 1240, 1754
    margin_x, margin_y = 70, 70
    line_h = 28

    font = ImageFont.load_default()

    # Wrap long lines to fit width (roughly)
    wrap_width = 95
    wrapped_lines: list[str] = [title, ""]
    for raw in body.splitlines():
        if raw.strip() == "":
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.wrap(raw, width=wrap_width, break_long_words=False) or [""])

    lines_per_page = (height - 2 * margin_y) // line_h
    pages: list[Image.Image] = []

    for start in range(0, len(wrapped_lines), lines_per_page):
        chunk = wrapped_lines[start : start + lines_per_page]
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        x, y = margin_x, margin_y
        for line in chunk:
            draw.text((x, y), line, fill="black", font=font)
            y += line_h
        pages.append(img)

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(out_pdf, save_all=True, append_images=pages[1:])


def main() -> None:
    # 注意: 甲1（MOU）と甲2（NOTICE OF CLAIM）は原本PDFを使用するため、ここでは生成しません
    mapping = [
        (
            "甲3号証（写し）\n被告送達先・登録情報メモ（日本語）",
            ROOT / "litigation/indy_tokyo_district_court/07_defendant_address_memo_ja.md",
            EXHIBITS / "甲3_defendant_address_memo_ja.pdf",
        ),
        (
            "甲6号証（写し）\n損害計算書（USD→JPY換算）",
            ROOT / "litigation/indy_tokyo_district_court/03_damage_calculation.md",
            EXHIBITS / "甲6_damage_calculation_USDJPY.pdf",
        ),
        (
            "甲9号証（写し）\n稼働時間明細（MOU締結後）— 100時間",
            ROOT / "litigation/indy_tokyo_district_court/09_timesheet_100h.md",
            EXHIBITS / "甲9_timesheet_100h.pdf",
        ),
        (
            "甲10号証（写し）\n陳述書（後藤 陽一）",
            ROOT / "litigation/indy_tokyo_district_court/08_statement_goto.md",
            EXHIBITS / "甲10_statement_goto.pdf",
        ),
    ]

    for title, src, out_pdf in mapping:
        md = src.read_text(encoding="utf-8")
        plain = md_to_plain_text(md)
        text_to_multipage_pdf(title, plain, out_pdf)

    print("Created text exhibits:")
    for _, _, out_pdf in mapping:
        print(f"- {out_pdf}")


if __name__ == "__main__":
    main()




