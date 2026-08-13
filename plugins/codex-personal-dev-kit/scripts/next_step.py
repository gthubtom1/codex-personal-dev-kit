"""Print the exact next commands for the current Dev Kit project state.

Prose workflows get skimmed, reordered, and half-executed; a read-only script
that prints the next command does not.  Run this whenever the next action is
unclear.  It never modifies the project.

Usage:
    python next_step.py --root <project-root>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import feature_guard  # noqa: E402

GUARD = f'python "{SCRIPT_DIR / "feature_guard.py"}"'


def _git_ok(root: Path) -> bool:
    result = feature_guard._run_git(root, "rev-parse", "--verify", "HEAD")
    return result.returncode == 0


def _dirty_files(root: Path) -> list[str]:
    result = feature_guard._run_git(root, "status", "--porcelain")
    if result.returncode != 0:
        return []
    return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]


def _pending_versions(root: Path) -> list[str]:
    versions_path = root / feature_guard.VERSIONS_RELATIVE
    if not versions_path.is_file():
        return []
    pending: list[str] = []
    for match in re.finditer(r"(?im)^\|\s*(v\d+\.\d+\.\d+)\s*\|", versions_path.read_text(encoding="utf-8", errors="replace")):
        version = match.group(1)
        tag = feature_guard._run_git(root, "rev-parse", "--verify", f"refs/tags/{version}")
        if tag.returncode != 0:
            pending.append(version)
    return pending


def _release_review_state(root: Path, version: str) -> str:
    review_path = root / feature_guard.RELEASE_REVIEW_RELATIVE
    if not review_path.is_file():
        return "missing"
    text = review_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?im)^\s*-\s*Version\s*:\s*(\S+)\s*$", text)
    if not match or match.group(1).strip() != version:
        return "other-version"
    return "present"


def plan_next_steps(root: Path) -> list[str]:
    lines: list[str] = []
    if not _git_ok(root):
        lines.append("NOW: 这个项目还没有可用的 Git 基线。先接入项目，不要直接改代码。")
        lines.append("  action: 调用 $onboard-codex-project 建立 Git 基线、docs 事实和可复现命令。")
        return lines
    if not (root / "docs/FEATURES.md").is_file() or not (root / "docs/STATUS.md").is_file():
        lines.append("NOW: 缺少 docs/FEATURES.md 或 docs/STATUS.md，项目事实不完整。")
        lines.append("  action: 调用 $onboard-codex-project 补齐项目事实基线，再开始修改。")
        return lines

    contract = feature_guard._read_contract(root)
    dirty = _dirty_files(root)

    if not contract:
        if dirty:
            lines.append("NOW: 工作区有未登记的修改（可能是用户或其他写入者的工作），先逐个确认归属，不要覆盖或清理：")
            for path in dirty[:8]:
                lines.append(f"  - {path}")
            if len(dirty) > 8:
                lines.append(f"  - ... 以及另外 {len(dirty) - 8} 个文件")
            lines.append("NEXT: 确认后再开契约；确属本任务的文件用 --own-path 声明。")
        else:
            lines.append("NOW: 没有打开的变更契约。第一次编辑前先读 FEATURES/STATUS，然后开契约：")
        lines.append(
            f"  command: {GUARD} start --root . --objective \"<结果>\" --change <F-ID> --verify <邻接F-ID>"
        )
        for version in _pending_versions(root):
            state = _release_review_state(root, version)
            if state == "present":
                lines.append(f"NEXT: {version} 已有终审记录但还没有本地标签（先确认终审和版本行已包含在最终检查点中）：")
                lines.append(f"  command: {GUARD} version --root . --name {version}")
            else:
                reason = "docs/RELEASE-REVIEW.md 缺失" if state == "missing" else f"docs/RELEASE-REVIEW.md 记录的不是 {version}"
                lines.append(f"NEXT: docs/VERSIONS.md 里的 {version} 还没有本地标签，且 {reason}。")
                lines.append(f"  action: 按 release-readiness 参考完成 {version} 的 21 维终审并放进最终检查点，再运行 guarded version。")
        lines.append("NEXT: 新能力/新集成/陌生报错默认先查现成做法（$research-and-reuse），学写法不整包搬运。")
        return lines

    state = contract.get("state", "open")
    staged = contract.get("stagedPaths", [])
    runs = contract.get("verificationRuns", [])
    changed = contract.get("changedFeatureIds", [])
    verify_ids = sorted(set(changed) | set(contract.get("explicitVerificationIds", [])))
    feature_flags = " ".join(f"--feature {feature_id}" for feature_id in verify_ids) or "--feature <F-ID>"

    if state == "verified":
        lines.append("NOW: 契约已验证但还没有保存回退点，先创建检查点再做任何新修改：")
        lines.append(f"  command: {GUARD} checkpoint --root . --message \"checkpoint: <结果>\"")
        return lines

    objective = contract.get("objective", "")
    lines.append(f"NOW: 契约进行中：{objective}")
    if not staged:
        lines.append("NEXT: 实现当前切片，然后只暂存本任务的精确文件：")
        lines.append(f"  command: {GUARD} stage --root . --path <file> [--path <file> ...]")
    elif not runs:
        lines.append("NEXT: 通过门禁真实运行验证命令并绑定功能：")
        lines.append(f"  command: {GUARD} verify --root . {feature_flags} -- <真实测试命令>")
    else:
        lines.append("NEXT: 验证已记录。复查最终 diff 后封契约并保存回退点：")
        lines.append(f"  command: {GUARD} complete --root .")
        lines.append(f"  command: {GUARD} checkpoint --root . --message \"checkpoint: <结果>\"")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    for line in plan_next_steps(root):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
