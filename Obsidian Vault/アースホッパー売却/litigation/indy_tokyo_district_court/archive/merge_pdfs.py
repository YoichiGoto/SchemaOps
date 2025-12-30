#!/usr/bin/env python3
"""
表紙PDFと元のPDFを結合するスクリプト
"""
import sys
from pathlib import Path
import PyPDF2

def merge_pdfs(cover_pdf, original_pdf, output_pdf):
    """PDFを結合"""
    merger = PyPDF2.PdfMerger()
    
    # 表紙を追加
    merger.append(str(cover_pdf))
    
    # 元のPDFを追加
    merger.append(str(original_pdf))
    
    # 出力
    merger.write(str(output_pdf))
    merger.close()
    
    print(f"✓ 結合完了: {output_pdf.name}")

def main():
    exhibits = Path(__file__).parent
    
    # 結合するPDFのリスト
    to_merge = [
        ("甲3-2_表紙.pdf", "甲3-2_Colorado_SOS_Entity_Summary.pdf"),
        ("甲4_表紙.pdf", "甲4_2025-11-11_direct_with_indy_message.pdf"),
        ("甲5_表紙.pdf", "甲5_2025-10-08_to_2025-11-25_ghosting_packet.pdf"),
        ("甲7_表紙.pdf", "甲7_MUFG_FX_2025-12-25_screenshot.pdf"),
    ]
    
    for cover_name, original_name in to_merge:
        cover_pdf = exhibits / cover_name
        original_pdf = exhibits / original_name
        temp_pdf = exhibits / f"{original_name}.tmp"
        
        if not cover_pdf.exists():
            print(f"⚠ 表紙が見つかりません: {cover_name}")
            continue
        
        if not original_pdf.exists():
            print(f"⚠ 元のPDFが見つかりません: {original_name}")
            continue
        
        # 結合
        merge_pdfs(cover_pdf, original_pdf, temp_pdf)
        
        # 元のファイルを置き換え
        temp_pdf.replace(original_pdf)
    
    print("\n完了しました。")

if __name__ == "__main__":
    main()

