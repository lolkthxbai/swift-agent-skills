#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAMS = {
    "swiftui-pro": ("SwiftUI Pro", "https://github.com/twostraws/SwiftUI-Agent-Skill"),
    "swiftdata-pro": ("SwiftData Pro", "https://github.com/twostraws/SwiftData-Agent-Skill"),
    "swift-concurrency-pro": (
        "Swift Concurrency Pro",
        "https://github.com/twostraws/Swift-Concurrency-Agent-Skill",
    ),
    "swift-testing-pro": (
        "Swift Testing Pro",
        "https://github.com/twostraws/Swift-Testing-Agent-Skill",
    ),
}


def frontmatter_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\n\"']+)", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else None


def validate() -> list[str]:
    errors: list[str] = []
    manifest_path = ROOT / ".codex-plugin" / "plugin.json"

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"Invalid plugin manifest: {error}"]

    if manifest.get("name") != "swift-agent-skills":
        errors.append("Plugin manifest name must be swift-agent-skills.")
    if re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", manifest.get("version", "")) is None:
        errors.append("Plugin version must use semantic versioning.")
    if manifest.get("skills") != "./skills/":
        errors.append("Plugin manifest must point skills to ./skills/.")
    if "Paul Hudson" not in manifest.get("author", {}).get("name", ""):
        errors.append("Plugin manifest must credit Paul Hudson as the skill author.")
    if manifest.get("license") != "MIT":
        errors.append("Plugin manifest license must be MIT.")
    if "[TODO:" in manifest_path.read_text(encoding="utf-8"):
        errors.append("Plugin manifest contains a TODO placeholder.")

    skill_root = ROOT / "skills"
    actual_skills = {path.name for path in skill_root.iterdir() if path.is_dir() and not path.name.startswith(".")}
    if actual_skills != set(UPSTREAMS):
        errors.append(f"Unexpected skill directories: {sorted(actual_skills ^ set(UPSTREAMS))}")

    root_license = (ROOT / "LICENSE").read_bytes() if (ROOT / "LICENSE").is_file() else b""
    if b"MIT License" not in root_license or b"Copyright (c) 2026 Paul Hudson" not in root_license:
        errors.append("Root LICENSE does not preserve Paul Hudson's MIT notice.")

    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").is_file() else ""
    attribution = (ROOT / "ATTRIBUTION.md").read_text(encoding="utf-8") if (ROOT / "ATTRIBUTION.md").is_file() else ""

    for skill_name, (display_name, repository_url) in UPSTREAMS.items():
        skill_directory = skill_root / skill_name
        skill_file = skill_directory / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"Missing {skill_name}/SKILL.md.")
            continue

        text = skill_file.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            errors.append(f"Invalid frontmatter in {skill_name}/SKILL.md.")
            continue

        frontmatter = parts[1]
        if frontmatter_value(frontmatter, "name") != skill_name:
            errors.append(f"Skill name mismatch for {skill_name}.")
        if frontmatter_value(frontmatter, "license") != "MIT":
            errors.append(f"{skill_name} must retain its MIT license metadata.")
        if not re.search(r"^\s+author:\s*Paul Hudson\s*$", frontmatter, re.MULTILINE):
            errors.append(f"{skill_name} must retain Paul Hudson author metadata.")

        references = set(re.findall(r"references/([A-Za-z0-9._-]+\.md)", text))
        actual_references = {
            path.name for path in (skill_directory / "references").glob("*.md")
        }
        missing_references = references - actual_references
        if missing_references:
            errors.append(f"{skill_name} is missing references: {sorted(missing_references)}")

        openai_metadata = skill_directory / "agents" / "openai.yaml"
        if not openai_metadata.is_file():
            errors.append(f"Missing OpenAI metadata for {skill_name}.")
        else:
            metadata_text = openai_metadata.read_text(encoding="utf-8")
            for relative_path in re.findall(r"(?:icon_small|icon_large):\s*[\"']([^\"']+)", metadata_text):
                if not (skill_directory / relative_path).is_file():
                    errors.append(f"Missing metadata asset for {skill_name}: {relative_path}")

        for candidate in skill_directory.rglob("*"):
            if candidate.is_symlink():
                errors.append(f"Symlinks are not allowed in bundled skills: {candidate.relative_to(ROOT)}")

        license_copy = ROOT / "licenses" / f"{skill_name}-LICENSE"
        if not license_copy.is_file() or license_copy.read_bytes() != root_license:
            errors.append(f"License copy is missing or changed for {skill_name}.")
        if display_name not in readme or repository_url not in readme:
            errors.append(f"README must describe and link {display_name}.")
        if repository_url not in attribution:
            errors.append(f"Attribution must link {display_name} upstream.")

    if len(re.findall(r"`[0-9a-f]{40}`", attribution)) != len(UPSTREAMS):
        errors.append("Attribution must record one 40-character commit hash per upstream skill.")

    return errors


def main() -> None:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Bundle validation passed.")


if __name__ == "__main__":
    main()
