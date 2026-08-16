# -*- coding: utf-8 -*-
"""拆分 docs/八股.md 为 docs/八股/ 下的多个文档（按 ## 一级部分拆分）。

- 文件头（# 基础 + ---）单独保留在 00-基础.md
- 每个 "## 第X部分 · 名称" 独立为一个文件，文件名 = 01-第X部分 · 名称.md
- 内容 100% 保留原文（含每条目缩进、注释行），只做切分不重写
- 配合 merge_all.py 可将 八股/ 下所有文件按序聚合回完整 八股.md
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, os.pardir, "八股.md"))
DST_DIR = HERE
PART_RE = re.compile(r"^(## 第[一二三四五六七八九十]+部分[^\n]*)")

def split():
    with open(SRC, encoding="utf-8") as f:
        lines = f.readlines()
    # 定位所有一级部分标题行
    part_idx = []  # (index, title)
    for i, line in enumerate(lines):
        m = PART_RE.match(line.rstrip("\n"))
        if m:
            part_idx.append((i, m.group(1).strip()))
    if not part_idx:
        raise SystemExit("未找到 '## 第X部分' 一级标题，无法拆分")

    # 文件头：0 到第一个部分标题前的所有行（含 00-基础 与分隔线）
    header_lines = lines[:part_idx[0][0]]
    os.makedirs(DST_DIR, exist_ok=True)
    seen = set()
    with open(os.path.join(DST_DIR, "00-基础.md"), "w", encoding="utf-8") as f:
        f.writelines(header_lines)
    seen.add("00-基础.md")

    # 每个部分：从当前部分标题到下一个部分标题前
    for j, (start_idx, title) in enumerate(part_idx):
        end_idx = part_idx[j + 1][0] if j + 1 < len(part_idx) else len(lines)
        part_lines = lines[start_idx:end_idx]
        # 从标题提取 "第X部分 · 干净名称" 用于文件名
        m2 = re.match(r"## 第([一二三四五六七八九十]+)部分\s*[·\-\s]*(.*)", title)
        zh_num = m2.group(1) if m2 else str(j + 1)
        rest = m2.group(2).strip() if m2 and m2.group(2).strip() else ""
        base = f"{j + 1:02d}-第{zh_num}部分" + (f" · {rest}" if rest else "")
        # 去除 Windows 不允许的字符
        fname = re.sub(r'[\\/:*?"<>|]', "-", base) + ".md"
        n = 2
        while fname in seen:
            fname = re.sub(r"\.md$", "", base) + f"-{n}.md"
            n += 1
        seen.add(fname)
        with open(os.path.join(DST_DIR, fname), "w", encoding="utf-8") as f:
            f.writelines(part_lines)
        print(f"{fname}: {len(part_lines)} 行  ({title})")

    print(f"\n拆分完成 → {DST_DIR}")
    print(f"共 {len(part_idx)} 个部分 + 00-基础.md")

if __name__ == "__main__":
    split()