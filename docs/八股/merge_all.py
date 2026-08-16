# -*- coding: utf-8 -*-
"""把 docs/八股/ 下所有拆分文档按序聚合回完整的 docs/八股.md。

- 只聚合本目录下的 .md 文件（00-基础.md、01-第X部分...md）
- 按文件名中的序号（00、01、02...）升序拼接，顺序可逆
- 拆分/聚合往返应逐字节一致（diff 为空）
- 维护方式：平时只改 八股/ 下的各分部文件，需要完整单文件时运行本脚本

用法：
    python merge_all.py            # 输出回 docs/八股.md（覆盖旧完整版）
    python merge_all.py out.md     # 输出到自定义路径
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.normpath(os.path.join(HERE, os.pardir, "八股.md"))

def collect_md_files(directory):
    files = []
    for name in os.listdir(directory):
        # 只聚合拆分的分部文档；AGENTS.md 是目录说明（有独立用途），工具脚本是 .py，均排除
        if name.endswith(".md") and name != "AGENTS.md":
            files.append(name)
    def sort_key(name):
        m = re.match(r"^(\d+)-", name)
        return (int(m.group(1)) if m else 9999, name)
    return sorted(files, key=sort_key)

def merge(out_path):
    files = collect_md_files(HERE)
    if not files:
        raise SystemExit("八股/ 目录下没有 .md 文件可聚合")
    print("聚合顺序：")
    parts = []
    for f in files:
        with open(os.path.join(HERE, f), encoding="utf-8-sig") as fh:
            content = fh.read()
        parts.append(content)
        print(f"  + {f} ({len(content.splitlines())} 行)")
    merged = "".join(parts)
    # 统一写入 UTF-8（无 BOM），避免个别文件带 BOM 污染完整版
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write(merged)
    print(f"\n聚合完成 → {out_path}（{len(merged.splitlines())} 行）")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    merge(out)