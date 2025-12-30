#!/usr/bin/env python3
"""
甲号証PDFに表紙を追加するスクリプト
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import io

EXHIBITS = Path(__file__).parent

# 表紙が必要な証拠のリスト
EXHIBITS_NEEDING_COVER = {
    "甲3-2_Colorado_SOS_Entity_Summary.pdf": {
        "number": "甲3-2号証（写し）",
        "title": "Colorado州 Business Database\n（Entity Summary / Registered Agent情報）",
        "date": "2025年12月25日（取得日）",
        "author": "Colorado Secretary of State"
    },
    "甲4_2025-11-11_direct_with_indy_message.pdf": {
        "number": "甲4号証（写し）",
        "title": "11/11合意メッセージ\n（取引ストラクチャー承認）",
        "date": "2025年11月11日",
        "author": "Erik Mogensen（被告代表者）"
    },
    "甲5_2025-10-08_to_2025-11-25_ghosting_packet.pdf": {
        "number": "甲5号証（写し）",
        "title": "ゴースティングの連絡履歴\n（通話ログ・メッセージ）",
        "date": "2025年10月8日〜11月25日",
        "author": "株式会社Pioneerwork → Erik Mogensen"
    },
    "甲7_MUFG_FX_2025-12-25_screenshot.pdf": {
        "number": "甲7号証（写し）",
        "title": "為替相場（TTM算定根拠）\nスクリーンショット",
        "date": "2025年12月25日（取得日）",
        "author": "三菱UFJリサーチ&コンサルティング"
    }
}


def create_cover_page(info: dict) -> bytes:
    """
    表紙PDFを作成
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # フォント設定（日本語対応）
    try:
        # macOSのヒラギノフォントを試す
        pdfmetrics.registerFont(TTFont('Japanese', '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc', subfontIndex=0))
        font_name = 'Japanese'
    except:
        try:
            # 別のフォントを試す
            pdfmetrics.registerFont(TTFont('Japanese', '/System/Library/Fonts/Hiragino Sans GB.ttc', subfontIndex=0))
            font_name = 'Japanese'
        except:
            # フォールバック
            font_name = 'Helvetica'
    
    # 証拠番号（大きく、中央上部）
    c.setFont(font_name, 24)
    c.drawCentredString(width / 2, height - 100*mm, info["number"])
    
    # タイトル（中央）
    c.setFont(font_name, 16)
    y_position = height / 2 + 20*mm
    for line in info["title"].split('\n'):
        c.drawCentredString(width / 2, y_position, line)
        y_position -= 8*mm
    
    # 日付
    c.setFont(font_name, 12)
    c.drawCentredString(width / 2, height / 2 - 20*mm, f"作成日：{info['date']}")
    
    # 作成者
    c.drawCentredString(width / 2, height / 2 - 30*mm, f"作成者：{info['author']}")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def add_cover_to_pdf(original_pdf_path: Path, cover_info: dict):
    """
    既存のPDFに表紙を追加
    """
    # 表紙PDF作成
    cover_pdf_bytes = create_cover_page(cover_info)
    cover_pdf = PyPDF2.PdfReader(io.BytesIO(cover_pdf_bytes))
    
    # 元のPDF読み込み
    original_pdf = PyPDF2.PdfReader(str(original_pdf_path))
    
    # 新しいPDF作成
    output_pdf = PyPDF2.PdfWriter()
    
    # 表紙を追加
    output_pdf.add_page(cover_pdf.pages[0])
    
    # 元のページを追加
    for page in original_pdf.pages:
        output_pdf.add_page(page)
    
    # 一時ファイルに保存
    temp_path = original_pdf_path.with_suffix('.tmp.pdf')
    with open(temp_path, 'wb') as f:
        output_pdf.write(f)
    
    # 元のファイルを置き換え
    temp_path.replace(original_pdf_path)
    print(f"✓ 表紙を追加しました: {original_pdf_path.name}")


def main():
    """
    メイン処理
    """
    print("甲号証PDFに表紙を追加します...")
    print()
    
    for filename, info in EXHIBITS_NEEDING_COVER.items():
        pdf_path = EXHIBITS / filename
        if pdf_path.exists():
            add_cover_to_pdf(pdf_path, info)
        else:
            print(f"⚠ ファイルが見つかりません: {filename}")
    
    print()
    print("完了しました。")


if __name__ == "__main__":
    main()

