#!/usr/bin/env python3
"""Runtime 工件 digest/sha256 回填工具(R-10~R-13 的发布收尾步)。

把 runtime.yaml 里指定 artifact 的 TBD 源/摘要换成真值,保持其余内容原样
(文本级替换,不重排 YAML);回填后提醒跑 gen_registry.py(runtime.yaml 变更
= 插件内容变更 = 版本必须递增,ci_check 会强制)。

用法:
  python3 scripts/backfill_runtime_digest.py <插件名> --artifact <id> \
      --cn <cn 源(镜像 ref@sha256:... 或 URL)> --intl <intl 源> \
      [--sha256 <archive 工件的 sha256>] [--size-mb <n>]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin", help="插件名,如 dh-duix-local")
    parser.add_argument("--artifact", required=True, help="runtime.yaml 里的 artifact id")
    parser.add_argument("--cn", required=True, help="cn 源(digest/URL)")
    parser.add_argument("--intl", required=True, help="intl 源(digest/URL)")
    parser.add_argument("--sha256", default="", help="archive/model_weights 工件的 sha256")
    parser.add_argument("--size-mb", default="", help="工件体积 MB")
    args = parser.parse_args()

    hits = list((ROOT / "plugins").glob(f"*/{args.plugin}/runtime.yaml"))
    if not hits:
        sys.exit(f"找不到 plugins/*/{args.plugin}/runtime.yaml")
    path = hits[0]
    text = path.read_text(encoding="utf-8")

    # 定位该 artifact 块(- id: <artifact> 到下一个 "- id:" 或顶层键)
    pattern = re.compile(
        rf"(- id: {re.escape(args.artifact)}\n(?:    .*\n|      .*\n)*)", re.M)
    m = pattern.search(text)
    if not m:
        sys.exit(f"{path}: 找不到 artifact id={args.artifact}")
    block = m.group(1)
    if "TBD" not in block and "sha256" in block:
        print(f"注意:{args.artifact} 似已回填过,将覆盖旧值")

    new_block = block
    new_block = re.sub(r'cn:\s*\[.*\]', f'cn:   ["{args.cn}"]', new_block)
    new_block = re.sub(r'intl:\s*\[.*\]', f'intl: ["{args.intl}"]', new_block)
    if args.sha256:
        if re.search(r"sha256:", new_block):
            new_block = re.sub(r'sha256: .*', f'sha256: "{args.sha256}"', new_block)
        else:
            new_block = new_block.replace(
                f"- id: {args.artifact}\n",
                f"- id: {args.artifact}\n    sha256: \"{args.sha256}\"\n", 1)
    if args.size_mb:
        new_block = re.sub(r"size_mb: .*", f"size_mb: {args.size_mb}", new_block)

    text = text.replace(block, new_block, 1)
    path.write_text(text, encoding="utf-8")
    remaining_tbd = text.count("TBD")
    print(f"已回填 {path}:artifact={args.artifact}")
    print(f"剩余 TBD:{remaining_tbd} 处" + ("(全部清零,deployer 可部署)" if not remaining_tbd else ""))
    print("下一步:递增该插件 plugin.yaml version → python3 scripts/gen_registry.py → 同 commit 提交")


if __name__ == "__main__":
    main()
