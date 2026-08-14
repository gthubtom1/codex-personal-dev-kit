"""Print the exact next commands for the current Dev Kit project state.

Prose workflows get skimmed, reordered, and half-executed; a read-only script
that prints the next command does not.  Run this whenever the next action is
unclear.  It never modifies the project.

Every run also prints the objective shapes that require looking up existing
practice before writing anything, so that decision never rests on how confident
the agent happens to feel.

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

SEARCH_TRIGGERS = (
    "要实现新能力、新集成、新算法，或对接不熟悉的 API / 标准",
    "碰到陌生报错",
    "发现自己正要凭印象给出关键结论",
    "没有思路，或在两个方案之间摇摆",
    "正准备向用户提问——先查完再问，用户该看到的是有证据的推荐方案，不是问题",
)

SEARCH_BLIND_SPOT = (
    "SEARCH: 反过来，「我们这套东西现在是什么状态」（某函数的实际行为、测试到底过没过、"
    "文件现在长什么样）搜不出来，搜索只会给出自信的错误结论——那类问题只能去跑、去读源码和 git。"
)


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


def _search_first_reminder() -> list[str]:
    """Print the search triggers on every run, in every state.

    "Do I need to look this up" is the judgment an agent is worst at: it skips
    the search exactly when it feels certain, which is when it is most likely to
    be inventing.  So the triggers are observable shapes rather than a prompt to
    self-assess, and they are not gated on which branch of the guide ran.
    """
    lines = ["SEARCH: 命中下面任一形状就先查现成做法再动手，按形状判断，不按自己有没有把握判断："]
    lines.extend(f"  - {trigger}" for trigger in SEARCH_TRIGGERS)
    lines.append("  action: 调用 $research-and-reuse 查官方文档与同类实现；学写法，不整包搬运。")
    lines.append(SEARCH_BLIND_SPOT)
    return lines


def plan_next_steps(root: Path) -> list[str]:
    return _plan_guarded_steps(root) + _search_first_reminder()


def _plan_guarded_steps(root: Path) -> list[str]:
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
        return lines

    if contract.get("state") != "open":
        lines.append("NOW: 契约已验证但还没有保存回退点，先创建检查点再做任何新修改：")
        lines.append(f"  command: {GUARD} checkpoint --root . --message \"checkpoint: <结果>\"")
        return lines

    lines.append(f"NOW: 契约进行中：{contract.get('objective', '')}")
    if not contract.get("stagedPaths"):
        lines.append("NEXT: 实现当前切片，然后只暂存本任务的精确文件：")
        lines.append(f"  command: {GUARD} stage --root . --path <file> [--path <file> ...]")
        return lines

    gate, blockers = feature_guard.completion_blockers(root, contract)
    if not blockers:
        lines.append("NEXT: 验证已记录。复查最终 diff 后封契约并保存回退点：")
        lines.append(f"  command: {GUARD} complete --root .")
        lines.append(f"  command: {GUARD} checkpoint --root . --message \"checkpoint: <结果>\"")
        return lines

    verify_ids = feature_guard.required_verification_ids(root, contract) or sorted(
        set(contract.get("changedFeatureIds", [])) | set(contract.get("explicitVerificationIds", []))
    )
    feature_flags = " ".join(f"--feature {feature_id}" for feature_id in verify_ids) or "--feature <F-ID>"
    verify_command = f"  command: {GUARD} verify --root . {feature_flags} -- <真实测试命令>"

    lines.append("NEXT: complete 现在会拒绝，理由与门禁完全一致。逐条修掉再继续：")
    for blocker in blockers:
        for text in blocker.splitlines():
            lines.append(f"  - {text.strip()}")
    if gate == "verification":
        lines.append(verify_command)
    elif gate == "snapshot":
        lines.append(f"  command: {GUARD} stage --root . --path <file> [--path <file> ...]")
        lines.append(verify_command)
    else:
        lines.append("  action: 先修正上面的项目事实，再重新运行验证并封契约：")
        lines.append(f"  command: {GUARD} complete --root .")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--mode", choices=("full", "light"), default="full")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    if args.mode == "light":
        print("LIGHT: 轻量模式——先开个草稿仓库（随时能回到上一版），然后边做边改、跑起来演示，收尾说人话。不做契约/门禁/终审仪式。")
        return 0
    for line in plan_next_steps(root):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
