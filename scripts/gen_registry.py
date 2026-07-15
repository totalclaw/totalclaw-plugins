#!/usr/bin/env python3
"""生成 registry.json —— 本仓唯一的索引生成入口。

遍历 plugins/<category>/<name>/,读取每个 plugin.yaml,计算逐文件 sha256 与
bundle_hash(排序遍历的确定性摘要,与 agent 侧 bundle_content_hash 同构),
输出市场兼容(schema_version=1)的 registry.json。

用法:python scripts/gen_registry.py [--check]
  --check  只校验现有 registry.json 是否与磁盘一致(CI 用),不一致退出码 1
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
REGISTRY = ROOT / "registry.json"
REPO_RAW_BASE = "https://gitee.com/jlzdyx/totalclaw-plugins/raw/master"
REPO_GIT = "https://gitee.com/jlzdyx/totalclaw-plugins.git"
SKIP_NAMES = {"_TEMPLATE"}
SKIP_FILES = {".DS_Store"}


def _require_yaml():
    try:
        import yaml  # type: ignore
        return yaml
    except ImportError:
        print("需要 PyYAML:pip install pyyaml", file=sys.stderr)
        raise SystemExit(2)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _bundle_hash(files: "list[dict]") -> str:
    """排序遍历的确定性 bundle 摘要:sha256(rel + ':' + file_sha256 换行拼接)。"""
    h = hashlib.sha256()
    for f in sorted(files, key=lambda x: x["path"]):
        h.update(f"{f['path']}:{f['sha256']}\n".encode("utf-8"))
    return h.hexdigest()


def _collect_plugin(plugin_dir: Path, category: str) -> dict:
    yaml = _require_yaml()
    manifest_path = plugin_dir / "plugin.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    name = str(manifest.get("name") or "").strip()
    if not name:
        raise SystemExit(f"{manifest_path}: plugin.yaml 缺 name")
    if name != plugin_dir.name:
        raise SystemExit(f"{manifest_path}: name={name!r} 与目录名 {plugin_dir.name!r} 不一致")
    if manifest.get("manifest_version") != 1:
        raise SystemExit(f"{manifest_path}: manifest_version 必须为 1")
    if not manifest.get("version"):
        raise SystemExit(f"{manifest_path}: 缺 version")

    rel_root = plugin_dir.relative_to(ROOT).as_posix()
    files = []
    for p in sorted(plugin_dir.rglob("*")):
        if not p.is_file() or p.name in SKIP_FILES:
            continue
        rel = p.relative_to(plugin_dir).as_posix()
        files.append({"path": rel, "sha256": _sha256(p), "size": p.stat().st_size})
    if not files:
        raise SystemExit(f"{plugin_dir}: 空插件目录")

    entry = {
        # ── 市场 schema v1 兼容字段(agent 既有 resolve/install 消费) ──
        "name": name,
        "display_name": manifest.get("display_name") or name,
        "description": manifest.get("description") or "",
        "version": str(manifest["version"]),
        "author": manifest.get("author") or "",
        "verified": True,  # 官方仓内置即 verified;第三方 PR 由维护者审后置位
        # tested_with 由插件自声明(PEP 440,对 agent 版本软检查)
        **({"tested_with": manifest["tested_with"]} if manifest.get("tested_with") else {}),
        # ── 单仓多插件扩展字段(新下载器 plugin_hub 消费;legacy 解析器忽略) ──
        "category": category,
        "path": rel_root,
        "raw_base": f"{REPO_RAW_BASE}/{rel_root}",
        "git_sparse": {"repo": REPO_GIT, "subdir": rel_root},
        "files": files,
        "bundle_sha256": _bundle_hash(files),
        "kind": manifest.get("kind") or "backend",
        "requires_env": manifest.get("requires_env") or [],
    }
    return entry


def build() -> dict:
    entries = []
    for category_dir in sorted(PLUGINS_DIR.iterdir()):
        if not category_dir.is_dir():
            continue
        for plugin_dir in sorted(category_dir.iterdir()):
            if not plugin_dir.is_dir() or plugin_dir.name in SKIP_NAMES:
                continue
            if not (plugin_dir / "plugin.yaml").exists():
                raise SystemExit(f"{plugin_dir}: 缺 plugin.yaml")
            entries.append(_collect_plugin(plugin_dir, category_dir.name))
    names = [e["name"] for e in entries]
    if len(names) != len(set(names)):
        raise SystemExit(f"插件 name 重复:{sorted(n for n in names if names.count(n) > 1)}")
    return {
        "schema_version": 1,
        "registry": "totalclaw-plugins",
        "source": REPO_GIT,
        "plugins": entries,
    }


def main() -> None:
    data = build()
    rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if "--check" in sys.argv:
        current = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else ""
        if current != rendered:
            print("registry.json 与磁盘不一致 — 运行 python scripts/gen_registry.py 重新生成", file=sys.stderr)
            raise SystemExit(1)
        print(f"registry.json 一致({len(data['plugins'])} 个插件)")
        return
    REGISTRY.write_text(rendered, encoding="utf-8")
    print(f"registry.json 已生成:{len(data['plugins'])} 个插件")


if __name__ == "__main__":
    main()
