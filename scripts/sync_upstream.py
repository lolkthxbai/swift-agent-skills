#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ("SKILL.md", "references", "assets", "agents")


@dataclass(frozen=True)
class Upstream:
    display_name: str
    repository_name: str
    repository_url: str
    source_directory: str
    skill_name: str


UPSTREAMS = (
    Upstream(
        "SwiftUI Pro",
        "SwiftUI-Agent-Skill",
        "https://github.com/twostraws/SwiftUI-Agent-Skill.git",
        "swiftui-pro",
        "swiftui-pro",
    ),
    Upstream(
        "SwiftData Pro",
        "SwiftData-Agent-Skill",
        "https://github.com/twostraws/SwiftData-Agent-Skill.git",
        "swiftdata-pro",
        "swiftdata-pro",
    ),
    Upstream(
        "Swift Concurrency Pro",
        "Swift-Concurrency-Agent-Skill",
        "https://github.com/twostraws/Swift-Concurrency-Agent-Skill.git",
        "swift-concurrency-pro",
        "swift-concurrency-pro",
    ),
    Upstream(
        "Swift Testing Pro",
        "Swift-Testing-Agent-Skill",
        "https://github.com/twostraws/Swift-Testing-Agent-Skill.git",
        "swift-testing-pro",
        "swift-testing-pro",
    ),
)


def run(*arguments: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        arguments,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def tree_digest() -> str:
    digest = hashlib.sha256()
    paths = [ROOT / "skills", ROOT / "licenses", ROOT / "LICENSE", ROOT / "ATTRIBUTION.md"]
    files: list[Path] = []

    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file())

    for path in sorted(files):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())

    return digest.hexdigest()


def reject_symlinks(path: Path) -> None:
    for candidate in path.rglob("*"):
        if candidate.is_symlink():
            raise RuntimeError(f"Refusing to copy upstream symlink: {candidate}")


def replace_directory(source: Path, destination: Path) -> None:
    replacement = destination.with_name(f".{destination.name}.new")
    backup = destination.with_name(f".{destination.name}.backup")

    for transient in (replacement, backup):
        if transient.exists():
            shutil.rmtree(transient)

    shutil.copytree(source, replacement)
    if destination.exists():
        destination.rename(backup)

    try:
        replacement.rename(destination)
    except Exception:
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def write_attribution(commits: dict[str, str]) -> None:
    rows = []
    for upstream in UPSTREAMS:
        repository_url = upstream.repository_url.removesuffix(".git")
        rows.append(
            f"| {upstream.display_name} | [{upstream.repository_name}]({repository_url}) "
            f"| `{commits[upstream.skill_name]}` |"
        )

    content = "\n".join(
        [
            "# Attribution",
            "",
            "Swift Agent Skills is an unofficial Codex plugin bundle containing four agent skills created by Paul Hudson ([@twostraws](https://github.com/twostraws)).",
            "",
            "| Skill | Upstream repository | Bundled commit |",
            "| --- | --- | --- |",
            *rows,
            "",
            "The bundled skills are distributed under the MIT License. A copy of each upstream license is preserved in `licenses/`.",
            "",
            "The canonical skill contents are copied without modification: `SKILL.md`, `references/`, `assets/`, and `agents/openai.yaml`. Repository-level documentation and tool-specific packaging are not included in this Codex bundle.",
            "",
        ]
    )
    (ROOT / "ATTRIBUTION.md").write_text(content, encoding="utf-8")


def bump_plugin_version() -> str:
    manifest_path = ROOT / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", manifest["version"])
    if match is None:
        raise RuntimeError(f"Cannot increment plugin version: {manifest['version']}")

    major, minor, patch = (int(part) for part in match.groups())
    manifest["version"] = f"{major}.{minor}.{patch + 1}"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest["version"]


def main() -> None:
    before = tree_digest()
    commits: dict[str, str] = {}

    with tempfile.TemporaryDirectory(prefix="swift-agent-skills-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        staged_skills = temporary_root / "staged-skills"
        staged_licenses = temporary_root / "staged-licenses"
        staged_skills.mkdir()
        staged_licenses.mkdir()

        for upstream in UPSTREAMS:
            clone = temporary_root / upstream.repository_name
            run("git", "clone", "--quiet", "--depth", "1", upstream.repository_url, str(clone))
            commits[upstream.skill_name] = run("git", "rev-parse", "HEAD", cwd=clone)

            source = clone / upstream.source_directory
            if not source.is_dir():
                raise RuntimeError(f"Missing upstream skill directory: {source}")

            staged_skill = staged_skills / upstream.skill_name
            staged_skill.mkdir()
            for component_name in COMPONENTS:
                component = source / component_name
                if not component.exists():
                    raise RuntimeError(f"Missing upstream component: {component}")
                reject_symlinks(component)
                if component.is_dir():
                    shutil.copytree(component, staged_skill / component_name)
                else:
                    shutil.copy2(component, staged_skill / component_name)

            license_source = clone / "LICENSE"
            if not license_source.is_file():
                raise RuntimeError(f"Missing upstream license: {license_source}")
            shutil.copy2(license_source, staged_licenses / f"{upstream.skill_name}-LICENSE")

        for upstream in UPSTREAMS:
            replace_directory(
                staged_skills / upstream.skill_name,
                ROOT / "skills" / upstream.skill_name,
            )

        licenses_directory = ROOT / "licenses"
        licenses_directory.mkdir(exist_ok=True)
        for upstream in UPSTREAMS:
            shutil.copy2(
                staged_licenses / f"{upstream.skill_name}-LICENSE",
                licenses_directory / f"{upstream.skill_name}-LICENSE",
            )

        shutil.copy2(staged_licenses / "swiftui-pro-LICENSE", ROOT / "LICENSE")
        write_attribution(commits)

    after = tree_digest()
    if before == after:
        print("Upstream skills are already current.")
        return

    version = bump_plugin_version()
    print(f"Synchronized upstream skills and set plugin version to {version}.")


if __name__ == "__main__":
    main()
