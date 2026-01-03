#!/usr/bin/env python3
"""
PDFにページ番号を追加するスクリプト
各ページのフッター右端に「現在のページ/総ページ数」の形式でページ番号を追加します。
"""

import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("エラー: PyMuPDFが必要です。以下のコマンドでインストールしてください:")
    print("  pip install pymupdf")
    sys.exit(1)


def add_page_numbers(pdf_path: Path, output_path: Path = None) -> None:
    """
    PDFファイルにページ番号を追加します。
    
    Args:
        pdf_path: 入力PDFファイルのパス
        output_path: 出力PDFファイルのパス（Noneの場合は元のファイルを上書き）
    """
    if output_path is None:
        output_path = pdf_path
    
    print(f"PDFファイルを読み込んでいます: {pdf_path}")
    
    # PDFを開く
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    print(f"総ページ数: {total_pages}")
    print(f"ページ番号を追加しています...")
    
    # 各ページにページ番号を追加
    for page_num in range(total_pages):
        page = doc[page_num]
        
        # ページサイズを取得
        rect = page.rect
        
        # ページ番号テキスト（例: "2/5"）
        page_text = f"{page_num + 1}/{total_pages}"
        
        # フッター右端に配置（マージンを考慮）
        # 右端から約20mm、下端から約10mmの位置
        # テキストの幅を考慮して右揃えにする
        fontsize = 10
        text_width = fitz.get_text_length(page_text, fontsize=fontsize, fontname="helv")
        
        # 右端からマージンを引いた位置
        x_pos = rect.width - 20 - text_width  # 右端から20ポイント（約7mm）+ テキスト幅
        y_pos = rect.height - 20  # 下端から20ポイント（約7mm）
        
        # テキストを挿入
        page.insert_text(
            (x_pos, y_pos),  # 座標
            page_text,
            fontsize=fontsize,
            color=(0, 0, 0)  # 黒色
        )
    
    # PDFを一時ファイルに保存してから移動
    import tempfile
    import shutil
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_path = Path(tmp_file.name)
    
    print(f"PDFファイルに保存しています: {output_path}")
    doc.save(str(tmp_path))
    doc.close()
    
    # 一時ファイルを最終的な出力先に移動
    shutil.move(str(tmp_path), str(output_path))
    
    print(f"完了: {output_path}")


def main():
    if len(sys.argv) < 2:
        print("使用方法: python add_page_numbers.py <PDFファイル1> [PDFファイル2] ...")
        sys.exit(1)
    
    for pdf_path_str in sys.argv[1:]:
        pdf_path = Path(pdf_path_str)
        
        if not pdf_path.exists():
            print(f"エラー: PDFファイルが見つかりません: {pdf_path}")
            continue
        
        # バックアップを作成
        backup_path = pdf_path.with_suffix('.pdf.bak')
        print(f"バックアップを作成しています: {backup_path}")
        import shutil
        shutil.copy2(pdf_path, backup_path)
        
        # ページ番号を追加
        add_page_numbers(pdf_path)


if __name__ == "__main__":
    main()
