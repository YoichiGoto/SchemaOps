from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/yoichigoto/Documents/Obsidian Vault/アースホッパー売却")
EXHIBITS = ROOT / "litigation/indy_tokyo_district_court/exhibits"


def image_to_pdf(image_path: Path, out_pdf: Path) -> None:
    img = Image.open(image_path).convert("RGB")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_pdf)


def text_pdf(lines: list[str], out_pdf: Path) -> None:
    # A4 portrait @ 150dpi-ish canvas
    width, height = 1240, 1754
    margin = 80
    line_h = 34

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Use default bitmap font (portable). If available, prefer a nicer font.
    font = ImageFont.load_default()

    x, y = margin, margin
    for line in lines:
        draw.text((x, y), line, fill="black", font=font)
        y += line_h
        if y > height - margin:
            break

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_pdf)


def main() -> None:
    # 甲7：為替相場（TTM算定根拠）— スクリーンショットPDF化
    fx_png = EXHIBITS / "甲7_MUFG_FX_2025-12-25_screenshot.png"
    fx_pdf = EXHIBITS / "甲7_MUFG_FX_2025-12-25_screenshot.pdf"
    image_to_pdf(fx_png, fx_pdf)

    # 甲8：STAドラフト break fee条項（抜粋）— テキストPDF化
    sta_excerpt_pdf = EXHIBITS / "甲8_STA_break_fee_clause_excerpt.pdf"
    sta_excerpt_lines = [
        "甲8号証（写し）",
        "Share Transfer Agreement v3（ドラフト） 抜粋",
        "",
        "Article 8. DAMAGES AND COMPENSATION",
        "8.2 Failure of Fallback Payment.",
        "If the Lender Consent referred to in Article 4(iii) is not obtained by the scheduled Closing,",
        "the Purchaser shall pay the Additional Cash Consideration pursuant to Article 2.5 at Closing.",
        "If the Purchaser fails to make such payment when due, the Seller may terminate this Agreement",
        "by written notice and the Purchaser shall immediately pay to the Seller a break fee of",
        "JPY 20,000,000. If payment of such break fee is delayed, late damages calculated at an annual",
        "interest rate of 10% shall accrue from the due date until payment in full.",
        "",
        "出典：/indy/SHARE TRANSFER AGREEMENTv3.md（Article 8.2）",
    ]
    text_pdf(sta_excerpt_lines, sta_excerpt_pdf)

    print("Created:")
    print(f"- {fx_pdf}")
    print(f"- {sta_excerpt_pdf}")


if __name__ == "__main__":
    main()

