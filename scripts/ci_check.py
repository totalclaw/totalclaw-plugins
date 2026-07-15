#!/usr/bin/env python3
"""仓库机检(SPEC §6 清单的机器化部分)—— CI 与 pre-push 钩子共用入口。

检查项:
  1. registry.json 与磁盘一致(gen_registry 重建比对)
  2. 全 plugin.yaml 必填面/semver/字符集/tested_with(PEP 440)/requires_env 形态
  3. version 递增机检:对基线(origin/master,兜底 HEAD)的 registry.json,
     内容(bundle_sha256)变了版本必须升;版本永不回退;name 消失即警示(id 永不复用)
  4. 禁 import 面扫描(SPEC §3.2/§3.3):
     顶层 import 只许 契约面 + 标准库 + httpx;惰性(缩进)import 放行轻量 SDK,
     但重运行时(torch/cv2/...)与非契约内部模块(totalclaw_cli/run_agent/...)永远禁止
  5. 危险模式扫描(SPEC §5):exec(/eval(/pip install
  6. runtime.yaml 结构校验(SPEC §7);TBD 值允许但警示(deployer 运行期拒绝)

用法:python3 scripts/ci_check.py [--against <git-ref>]
  --against  version 递增比对的基线 ref(默认 origin/master,不存在则 HEAD)
退出码:0 全绿;1 有 FAIL(警示不影响退出码)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_registry  # noqa: E402

ROOT = gen_registry.ROOT
PLUGINS_DIR = gen_registry.PLUGINS_DIR

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# tested_with:PEP 440 版本约束的宽松形态校验(逗号分隔的 比较符+版本号)
TESTED_WITH_RE = re.compile(r"^\s*(==|>=|<=|~=|!=|>|<)\s*\d+(\.\d+)*(\.\*)?"
                            r"(\s*,\s*(==|>=|<=|~=|!=|>|<)\s*\d+(\.\d+)*(\.\*)?)*\s*$")
IMPORT_RE = re.compile(r"^(\s*)(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))")

# 契约 import 面(SPEC §3.2)
ALLOWED_PREFIXES = ("totalclaw_plugin_sdk", "totalclaw_core.plugins.digital_human")
ALLOWED_THIRD_PARTY = {"httpx"}
# 永远禁止(顶层与惰性一律拒):非契约内部模块 + 重运行时(SPEC §3.3)
BANNED_PREFIXES = ("totalclaw_cli", "run_agent")
BANNED_HEAVY = {"torch", "torchvision", "torchaudio", "tensorflow", "cv2",
                "onnxruntime", "paddle", "paddlepaddle", "transformers",
                "ffmpeg", "av", "mediapipe"}
DANGEROUS_PATTERNS = [
    (re.compile(r"(?<![\w.])exec\s*\("), "exec("),
    (re.compile(r"(?<![\w.])eval\s*\("), "eval("),
    # "pip install" 出现在引导文案字符串是 SPEC §3.3 要求的;只拦执行形态
    (re.compile(r"(os\.system|subprocess\.\w+|Popen)\s*\(.*pip"), "执行 pip(动态装包)"),
]

REQUIRED_MANIFEST_FIELDS = ["manifest_version", "requires_protocol_version", "name",
                            "display_name", "version", "description", "author", "kind"]

VALID_DEPLOY_MODES = {"local", "remote", "existing"}
VALID_ARTIFACT_KINDS = {"docker_image", "archive", "model_weights"}

failures: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def _stdlib_names() -> frozenset:
    return getattr(sys, "stdlib_module_names", frozenset())


def iter_plugin_dirs():
    for category_dir in sorted(PLUGINS_DIR.iterdir()):
        if not category_dir.is_dir():
            continue
        for plugin_dir in sorted(category_dir.iterdir()):
            if plugin_dir.is_dir() and plugin_dir.name not in gen_registry.SKIP_NAMES:
                yield category_dir.name, plugin_dir


def check_registry_consistency() -> dict:
    data = gen_registry.build()
    rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    current = gen_registry.REGISTRY.read_text(encoding="utf-8") if gen_registry.REGISTRY.exists() else ""
    if current != rendered:
        fail("registry.json 与磁盘不一致 —— 运行 python3 scripts/gen_registry.py 重新生成")
    return data


def check_manifests() -> None:
    yaml = gen_registry._require_yaml()
    for category, plugin_dir in iter_plugin_dirs():
        rel = plugin_dir.relative_to(ROOT).as_posix()
        manifest = yaml.safe_load((plugin_dir / "plugin.yaml").read_text(encoding="utf-8")) or {}
        for field in REQUIRED_MANIFEST_FIELDS:
            if not manifest.get(field):
                fail(f"{rel}/plugin.yaml: 缺必填字段 {field}")
        version = str(manifest.get("version") or "")
        if version and not SEMVER_RE.match(version):
            fail(f"{rel}/plugin.yaml: version={version!r} 非 semver(x.y.z)")
        tested_with = manifest.get("tested_with")
        if not tested_with:
            fail(f"{rel}/plugin.yaml: 缺 tested_with(R-4:PEP 440 对 agent 版本)")
        elif not TESTED_WITH_RE.match(str(tested_with)):
            fail(f"{rel}/plugin.yaml: tested_with={tested_with!r} 非法(需 PEP 440 约束,如 \">=0.63.72\")")
        for key in ("requires_env", "optional_env"):
            env_list = manifest.get(key) or []
            if not isinstance(env_list, list):
                fail(f"{rel}/plugin.yaml: {key} 必须是列表")
                continue
            for item in env_list:
                if not isinstance(item, dict) or not item.get("name"):
                    fail(f"{rel}/plugin.yaml: {key} 条目须为含 name 的对象(富对象供设置向导渲染)")
                elif key == "requires_env" and not (item.get("description") and item.get("prompt")):
                    warn(f"{rel}/plugin.yaml: requires_env.{item['name']} 缺 description/prompt(向导渲染降级)")


def _parse_version(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def check_version_monotonic(new_data: dict, baseline_ref: str | None) -> None:
    refs = [baseline_ref] if baseline_ref else ["origin/master", "HEAD"]
    old_raw = None
    used_ref = None
    for ref in refs:
        r = subprocess.run(["git", "show", f"{ref}:registry.json"],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 0:
            old_raw, used_ref = r.stdout, ref
            break
    if old_raw is None:
        warn("找不到基线 registry.json(origin/master/HEAD 均无)——跳过 version 递增机检")
        return
    try:
        old_entries = {e["name"]: e for e in json.loads(old_raw).get("plugins", [])}
    except (json.JSONDecodeError, KeyError, TypeError):
        warn(f"基线 {used_ref} 的 registry.json 解析失败——跳过 version 递增机检")
        return
    new_entries = {e["name"]: e for e in new_data.get("plugins", [])}
    for name, new_e in new_entries.items():
        old_e = old_entries.get(name)
        if old_e is None:
            continue  # 新插件
        try:
            old_v, new_v = _parse_version(old_e["version"]), _parse_version(new_e["version"])
        except ValueError:
            fail(f"{name}: 版本号无法解析比较({old_e.get('version')} → {new_e.get('version')})")
            continue
        if new_v < old_v:
            fail(f"{name}: version 回退 {old_e['version']} → {new_e['version']}(基线 {used_ref})")
        elif new_e.get("bundle_sha256") != old_e.get("bundle_sha256") and new_v <= old_v:
            fail(f"{name}: 内容变更但 version 未递增(仍为 {new_e['version']},基线 {used_ref})——发布纪律:改动必递增")
    for name in old_entries.keys() - new_entries.keys():
        warn(f"{name}: 从 registry 消失(下架?)——注意 name/id 永不复用(SPEC §8)")


def check_import_surface() -> None:
    stdlib = _stdlib_names()
    for category, plugin_dir in iter_plugin_dirs():
        for py in sorted(plugin_dir.rglob("*.py")):
            rel = py.relative_to(ROOT).as_posix()
            for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                m = IMPORT_RE.match(line)
                if not m:
                    continue
                indent, module = m.group(1), (m.group(2) or m.group(3))
                if module.startswith("."):
                    continue  # 相对 import:插件自包含内部引用
                top = module.split(".")[0]
                loc = f"{rel}:{lineno}"
                # 永远禁止:非契约内部模块 / totalclaw_core 非契约子面 / 重运行时
                if any(module == p or module.startswith(p + ".") for p in BANNED_PREFIXES):
                    fail(f"{loc}: 禁止 import {module}(非契约面,SPEC §3.2)")
                elif top == "totalclaw_core" and not any(
                        module == p or module.startswith(p + ".") for p in ALLOWED_PREFIXES):
                    fail(f"{loc}: 禁止 import {module}(totalclaw_core 只开放 plugins.digital_human 契约面)")
                elif top in BANNED_HEAVY:
                    fail(f"{loc}: 禁止重依赖 {top}(SPEC §3.3 零重依赖——重活归 Runtime 部署包)")
                elif indent == "":
                    # 顶层 import 只许:契约面 / 标准库 / httpx
                    ok = (any(module == p or module.startswith(p + ".") for p in ALLOWED_PREFIXES)
                          or top in stdlib or top in ALLOWED_THIRD_PARTY
                          or top == "__future__")
                    if not ok:
                        fail(f"{loc}: 顶层 import {module} 不在契约面(三方 SDK 须方法内惰性 import,SPEC §3.3)")


def check_dangerous_patterns() -> None:
    for category, plugin_dir in iter_plugin_dirs():
        for py in sorted(plugin_dir.rglob("*.py")):
            rel = py.relative_to(ROOT).as_posix()
            for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for pattern, label in DANGEROUS_PATTERNS:
                    if pattern.search(line):
                        fail(f"{rel}:{lineno}: 危险模式 {label}(SPEC §5 禁自更新/远程代码加载)")


def check_runtime_manifests() -> None:
    yaml = gen_registry._require_yaml()
    for category, plugin_dir in iter_plugin_dirs():
        rt_path = plugin_dir / "runtime.yaml"
        if not rt_path.exists():
            continue
        rel = rt_path.relative_to(ROOT).as_posix()
        rt = yaml.safe_load(rt_path.read_text(encoding="utf-8")) or {}
        if rt.get("runtime_version") != 1:
            fail(f"{rel}: runtime_version 必须为 1")
        for field in ("name", "display_name", "deploy_modes", "requirements", "artifacts",
                      "health", "service"):
            if not rt.get(field):
                fail(f"{rel}: 缺 {field}")
        modes = rt.get("deploy_modes") or []
        if not set(modes) <= VALID_DEPLOY_MODES:
            fail(f"{rel}: deploy_modes 含非法值 {sorted(set(modes) - VALID_DEPLOY_MODES)}")
        if rt.get("default_mode") and rt["default_mode"] not in modes:
            fail(f"{rel}: default_mode={rt['default_mode']!r} 不在 deploy_modes 中")
        tbd_count = 0
        for art in rt.get("artifacts") or []:
            aid = art.get("id") or "?"
            if not art.get("id"):
                fail(f"{rel}: artifact 缺 id")
            if art.get("kind") not in VALID_ARTIFACT_KINDS:
                fail(f"{rel}: artifact {aid} kind 非法(须 {sorted(VALID_ARTIFACT_KINDS)})")
            sources = art.get("sources") or {}
            if not (sources.get("cn") and sources.get("intl")):
                fail(f"{rel}: artifact {aid} 须 cn/intl 双源(SPEC §7)")
            blob = json.dumps(art, ensure_ascii=False)
            if "TBD" in blob:
                tbd_count += 1
        if tbd_count:
            warn(f"{rel}: {tbd_count} 个 artifact 含 TBD(Runtime 包未发布,deployer 将拒绝部署)")
        compose = (rt.get("deploy") or {}).get("compose")
        if compose and not (plugin_dir / compose).exists():
            fail(f"{rel}: deploy.compose={compose!r} 在插件目录不存在")
        svc = rt.get("service") or {}
        if svc and not svc.get("config_key"):
            fail(f"{rel}: service.config_key 缺失(部署成功无法写回 endpoint)")


def check_conformance() -> None:
    """跑 tests/conformance.py(SPEC §4 全接口族机检);缺 httpx 降级为警示。"""
    try:
        import httpx  # noqa: F401
    except ImportError:
        warn("缺 httpx——跳过 conformance(插件顶层 import httpx;CI 环境请 pip install httpx pyyaml)")
        return
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "conformance.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail("conformance 未过:\n" + (r.stderr or r.stdout).strip())


def main() -> None:
    baseline = None
    if "--against" in sys.argv:
        baseline = sys.argv[sys.argv.index("--against") + 1]
    data = check_registry_consistency()
    check_manifests()
    check_version_monotonic(data, baseline)
    check_import_surface()
    check_dangerous_patterns()
    check_runtime_manifests()
    check_conformance()

    for w in warnings:
        print(f"WARN  {w}")
    for f_ in failures:
        print(f"FAIL  {f_}", file=sys.stderr)
    n = len(data.get("plugins", []))
    if failures:
        print(f"\n机检未过:{len(failures)} 项 FAIL,{len(warnings)} 项警示({n} 个插件)", file=sys.stderr)
        raise SystemExit(1)
    print(f"机检通过:{n} 个插件,0 FAIL,{len(warnings)} 项警示")


if __name__ == "__main__":
    main()
