#!/usr/bin/env python3
"""Validate agent skills against agentskills.io specification.

Checks:
1. SKILL.md exists in each skills/ subdirectory
2. YAML frontmatter is valid and parseable
3. Required fields: name, description, license
4. name field matches directory name (kebab-case)
5. name is 1-64 chars, lowercase, hyphens only
6. description is 1-1024 chars
7. compatibility is a string (NOT a YAML list)
8. No Claude Code-specific fields (context, agent, model, hooks, paths,
   disable-model-invocation, user-invocable, disallowed-tools, effort,
   argument-hint, arguments, shell)
9. scripts/ directory exists with at least 1 file
10. scripts are executable (chmod +x)
11. SKILL.md is under 1000 lines
12. No references to specific projects (check for "munin" case-insensitive)
13. metadata.version and metadata.author present
14. Has "## Related Skills" section
15. Has keywords in description

Exit codes:
  0 = all skills valid
  1 = one or more skills have warnings
  2 = one or more skills have errors

Usage:
  python3 scripts/validate-skills.py [--strict] [--json]
  --strict: warnings become errors
  --json: output as JSON instead of human-readable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Parse YAML frontmatter from SKILL.md content.

    Returns (frontmatter_dict, body_text) or (None, content) if no frontmatter.
    """
    if not content.startswith("---\n"):
        return None, content

    # Find the closing ---
    lines = content.split("\n")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None, content

    yaml_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1:])

    # Minimal YAML parser for our frontmatter structure
    fm: dict = {}
    current_key: str | None = None
    current_subkey: str | None = None
    in_list = False
    in_multiline = False
    multiline_buffer: list[str] = []

    for line in yaml_text.split("\n"):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue

        # Multiline string (folded > or literal |)
        if in_multiline:
            if line.startswith(" ") or line.startswith("\t") or not stripped:
                multiline_buffer.append(line.strip())
                continue
            else:
                # End of multiline
                if current_key:
                    fm[current_key] = " ".join(multiline_buffer)
                in_multiline = False
                multiline_buffer = []

        # Sub-key / sub-list (indented lines) — must be checked BEFORE top-level
        # list items to avoid treating `metadata:\n  tags:\n    - amd` as a
        # top-level list under `metadata`.
        if line.startswith("  ") and current_key:
            sub_match = re.match(r"^\s+([a-zA-Z_]+):\s*(.*)", line)
            if sub_match:
                sub_key = sub_match.group(1)
                sub_value = sub_match.group(2).strip().strip('"').strip("'")
                if current_key not in fm or not isinstance(fm[current_key], dict):
                    fm[current_key] = {}
                fm[current_key][sub_key] = sub_value
                current_subkey = sub_key
            # Sub-list items (tags)
            elif stripped.startswith("- ") and current_subkey:
                item_value = stripped[2:].strip().strip('"').strip("'")
                if isinstance(fm.get(current_key, {}).get(current_subkey), list):
                    fm[current_key][current_subkey].append(item_value)
                else:
                    fm[current_key][current_subkey] = [item_value]
            continue

        # Check for key: value (top-level)
        match = re.match(r"^([a-zA-Z_-]+):\s*(.*)", line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()

            # Flush previous multiline
            if in_multiline and current_key:
                fm[current_key] = " ".join(multiline_buffer)
                in_multiline = False
                multiline_buffer = []

            current_key = key
            current_subkey = None
            in_list = False

            if value == ">" or value == "|":
                in_multiline = True
                multiline_buffer = []
            elif value:
                fm[key] = value
            # If no value, could be a list or dict — wait for next lines
            continue

        # Top-level list item
        if stripped.startswith("- ") and current_key:
            if not in_list:
                in_list = True
                fm[current_key] = []
            item_value = stripped[2:].strip().strip('"').strip("'")
            if isinstance(fm.get(current_key), list):
                fm[current_key].append(item_value)
            continue

    # Flush remaining multiline
    if in_multiline and current_key:
        fm[current_key] = " ".join(multiline_buffer)

    return fm, body


# Claude Code-specific fields that reduce portability
CLAUDE_CODE_FIELDS = {
    "context", "agent", "model", "hooks", "paths",
    "disable-model-invocation", "user-invocable",
    "disallowed-tools", "effort", "argument-hint",
    "arguments", "shell",
}

# Required fields
REQUIRED_FIELDS = ["name", "description", "license"]

# Project names to avoid (agnostic check)
FORBIDDEN_PROJECT_NAMES = ["munin"]


class SkillValidator:
    """Validates a single skill directory against agentskills.io spec."""

    def __init__(self, skill_dir: Path, strict: bool = False):
        self.skill_dir = skill_dir
        self.skill_name = skill_dir.name
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """Run all validations. Returns True if no errors."""
        skill_md = self.skill_dir / "SKILL.md"

        # 1. SKILL.md exists
        if not skill_md.exists():
            self.errors.append(f"SKILL.md not found in {self.skill_name}/")
            return False

        content = skill_md.read_text(encoding="utf-8")

        # 2. Parse frontmatter
        fm, body = parse_frontmatter(content)
        if fm is None:
            self.errors.append("No YAML frontmatter found (must start with ---)")
            return False

        # 3. Required fields
        for field in REQUIRED_FIELDS:
            if field not in fm:
                self.errors.append(f"Missing required field: '{field}'")

        # 4. name matches directory
        if "name" in fm:
            name = str(fm["name"])
            if name != self.skill_name:
                self.errors.append(
                    f"name field '{name}' does not match directory name '{self.skill_name}'"
                )
            # kebab-case check
            if not re.match(r"^[a-z][a-z0-9-]*[a-z0-9]$", name):
                self.errors.append(
                    f"name '{name}' is not valid kebab-case "
                    "(lowercase, hyphens, no leading/trailing hyphen)"
                )
            # Length check
            if len(name) > 64:
                self.errors.append(f"name '{name}' exceeds 64 characters")

        # 5. description length
        if "description" in fm:
            desc = str(fm["description"])
            if len(desc) < 10:
                self.errors.append("description is too short (minimum 10 chars)")
            if len(desc) > 1024:
                self.errors.append(
                    f"description exceeds 1024 characters ({len(desc)} chars)"
                )
            # Keywords check
            if "keyword" not in desc.lower():
                self.warnings.append(
                    "description does not contain 'Keywords:' section "
                    "(recommended for agent matching)"
                )

        # 6. compatibility is string, not list
        if "compatibility" in fm:
            compat = fm["compatibility"]
            if isinstance(compat, list):
                self.errors.append(
                    "compatibility field is a YAML list — must be a string "
                    "(agentskills.io spec)"
                )
            elif isinstance(compat, str) and len(compat) > 500:
                self.errors.append(
                    f"compatibility exceeds 500 characters ({len(compat)} chars)"
                )

        # 7. No Claude Code-specific fields
        for field in CLAUDE_CODE_FIELDS:
            if field in fm:
                self.warnings.append(
                    f"Field '{field}' is Claude Code-specific and reduces "
                    f"cross-agent portability"
                )

        # 8. metadata present
        if "metadata" not in fm:
            self.warnings.append("metadata field is missing (recommended)")
        else:
            meta = fm["metadata"]
            if not isinstance(meta, dict):
                self.warnings.append("metadata is not a valid object")
            else:
                if "version" not in meta:
                    self.warnings.append("metadata.version is missing")
                if "author" not in meta:
                    self.warnings.append("metadata.author is missing")

        # 9. scripts/ directory
        scripts_dir = self.skill_dir / "scripts"
        if not scripts_dir.exists():
            self.warnings.append("scripts/ directory not found (recommended)")
        elif not any(scripts_dir.iterdir()):
            self.warnings.append("scripts/ directory is empty")
        else:
            # 10. scripts executable
            for script in scripts_dir.iterdir():
                if script.is_file() and not script.stat().st_mode & 0o111:
                    self.warnings.append(
                        f"Script {script.name} is not executable (chmod +x)"
                    )

        # 11. SKILL.md under 1000 lines
        line_count = len(content.split("\n"))
        if line_count > 1000:
            self.warnings.append(
                f"SKILL.md has {line_count} lines (recommended max 1000, "
                f"use references/ for deep content)"
            )

        # 12. No forbidden project names
        for name in FORBIDDEN_PROJECT_NAMES:
            if name.lower() in content.lower():
                self.errors.append(
                    f"Reference to '{name}' found — skills must be project-agnostic"
                )

        # 13. Related Skills section
        if "## Related Skills" not in body:
            self.warnings.append(
                "No '## Related Skills' section found (recommended for discovery)"
            )

        # Apply strict mode
        if self.strict:
            self.errors.extend(self.warnings)
            self.warnings = []

        return len(self.errors) == 0

    def report(self) -> str:
        """Generate human-readable report."""
        lines = [f"  {self.skill_name}/"]
        if not self.errors and not self.warnings:
            lines.append("    ✅ All checks passed")
        for err in self.errors:
            lines.append(f"    ❌ ERROR: {err}")
        for warn in self.warnings:
            lines.append(f"    ⚠️  WARN:  {warn}")
        return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate agent skills against agentskills.io specification"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--skills-dir", default="skills",
        help="Path to skills/ directory (default: skills)"
    )
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    if not skills_dir.exists():
        print(f"❌ Skills directory not found: {skills_dir}")
        return 2

    # Find all skill directories
    skill_dirs = sorted([
        d for d in skills_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])

    if not skill_dirs:
        print(f"❌ No skill directories found in {skills_dir}")
        return 2

    validators = []
    for skill_dir in skill_dirs:
        v = SkillValidator(skill_dir, strict=args.strict)
        v.validate()
        validators.append(v)

    # Collect results
    total = len(validators)
    passed = sum(1 for v in validators if not v.errors and not v.warnings)
    warned = sum(1 for v in validators if not v.errors and v.warnings)
    errored = sum(1 for v in validators if v.errors)

    if args.json:
        results = {
            "total": total,
            "passed": passed,
            "warnings": warned,
            "errors": errored,
            "skills": []
        }
        for v in validators:
            results["skills"].append({
                "name": v.skill_name,
                "errors": v.errors,
                "warnings": v.warnings,
            })
        print(json.dumps(results, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  AMD ROCm Skills — Validation Report")
        print(f"{'='*60}\n")
        for v in validators:
            print(v.report())
        print(f"\n{'='*60}")
        print(f"  Total: {total} | ✅ Passed: {passed} | "
              f"⚠️  Warnings: {warned} | ❌ Errors: {errored}")
        print(f"{'='*60}\n")

    if errored > 0:
        return 2
    elif warned > 0 and args.strict:
        return 2
    elif warned > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
