# -*- coding: utf-8 -*-
"""
word.py — 词库工具脚本
用途：解析 mom_1000_words.docx，导出为 words.txt（单词\t释义 格式）
      方便通过 App 侧栏的"词库导入"功能上传到 Google Sheets

使用方法：
    python word.py
输出：同目录下的 words.txt
"""
import os
import docx


def parse_docx_to_txt(docx_path: str, output_path: str):
    if not os.path.exists(docx_path):
        print(f"❌ 找不到文件：{docx_path}")
        return

    doc = docx.Document(docx_path)
    results = []

    for para in doc.paragraphs:
        line = para.text.strip()
        if not line:
            continue

        # 支持多种分隔符：制表符、中文全角空格、逗号、冒号、普通空格
        for sep in ["\t", "，", "　", ",", "：", ":", "  "]:
            if sep in line:
                parts = line.split(sep, 1)
                word = parts[0].strip()
                meaning = parts[1].strip() if len(parts) > 1 else ""
                if word:
                    results.append((word, meaning))
                break
        else:
            # 没有找到分隔符，整行作为单词，释义留空
            results.append((line, ""))

    if not results:
        print("⚠️  未解析到任何内容，请检查文档格式。")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        for word, meaning in results:
            f.write(f"{word}\t{meaning}\n")

    print(f"✅ 导出完成！共 {len(results)} 条 → {output_path}")
    print("   现在可以在 App 侧栏上传 words.txt 导入词库。")


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    docx_file = os.path.join(base, "mom_1000_words.docx")
    txt_file = os.path.join(base, "words.txt")
    parse_docx_to_txt(docx_file, txt_file)
