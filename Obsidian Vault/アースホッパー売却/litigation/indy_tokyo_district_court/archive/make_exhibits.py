from __future__ import annotations

from pathlib import Path

from PIL import Image
from pypdf import PdfWriter, PdfReader


ROOT = Path("/Users/yoichigoto/Documents/Obsidian Vault/アースホッパー売却")
OUT_DIR = ROOT / "litigation/indy_tokyo_district_court/exhibits"


def pngs_to_pdf(png_paths: list[Path], out_pdf: Path) -> None:
    images = []
    for p in png_paths:
        img = Image.open(p).convert("RGB")
        images.append(img)

    if not images:
        raise ValueError("No images to write.")

    first, rest = images[0], images[1:]
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    first.save(out_pdf, save_all=True, append_images=rest)


def merge_pdfs(pdf_paths: list[Path], out_pdf: Path) -> None:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for p in pdf_paths:
        reader = PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)
    with open(out_pdf, "wb") as f:
        writer.write(f)


def main() -> None:
    # 甲4：Plan B提案画像 ＋ 11/11合意メッセージ
    kou4_pngs = [
        ROOT / "indy/WhatsApp Chat - Erik Mogensen (1)/00000027-PHOTO-2025-11-07-21-32-33.jpg",  # 提案ストラクチャー
        ROOT / "indy/screenshots/IMG_0520.PNG"  # Yes回答
    ]
    kou4_pdf = OUT_DIR / "甲4_2025-11-11_direct_with_indy_message.pdf"
    pngs_to_pdf(kou4_pngs, kou4_pdf)

    # 甲5：ゴースティングの経緯（WhatsApp + 通話履歴）
    kou5_pngs = [
        ROOT / "indy/screenshots/IMG_0515.PNG",      # 10/8頃のやりとり・不応答
        ROOT / "indy/screenshots/IMG_0514.PNG",      # 10/14 "Will reach out tomorrow"
        ROOT / "indy/screenshots/IMG_0517.PNG",      # 11/7 "I am ready to have a call"
        ROOT / "indy/screenshots/IMG_0374 2.PNG",    # 11/7〜11/13 通話履歴
        ROOT / "indy/screenshots/IMG_0519.PNG",      # 11/10 "updated numbers asap"
        ROOT / "indy/screenshots/IMG_0372 2.PNG",    # 11/13以降の完全無視（通話履歴）
    ]
    kou5_pdf = OUT_DIR / "甲5_2025-10-08_to_2025-11-25_ghosting_packet.pdf"
    pngs_to_pdf(kou5_pngs, kou5_pdf)

    # 甲3-2（Colorado SOS）は既にPDF保存済みなので、exhibitsにコピー版を作成
    kou3_2_src = ROOT / "litigation/indy_tokyo_district_court/Colorado Secretary of State - Summary.pdf"
    kou3_2_pdf = OUT_DIR / "甲3-2_Colorado_SOS_Entity_Summary.pdf"
    merge_pdfs([kou3_2_src], kou3_2_pdf)

    print("Created:")
    print(f"- {kou4_pdf}")
    print(f"- {kou5_pdf}")
    print(f"- {kou3_2_pdf}")


if __name__ == "__main__":
    main()

