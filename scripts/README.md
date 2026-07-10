# Scripts

## validate-skills.py

Validates all skills in `skills/` against the [agentskills.io](https://agentskills.io/specification) specification.

### Usage

```bash
# Validate all skills (warnings don't fail)
python3 scripts/validate-skills.py

# Strict mode (warnings become errors)
python3 scripts/validate-skills.py --strict

# JSON output for CI/CD
python3 scripts/validate-skills.py --json

# Custom skills directory
python3 scripts/validate-skills.py --skills-dir /path/to/skills
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All skills valid, no warnings |
| 1 | Skills valid but have warnings |
| 2 | One or more skills have errors |

### Checks Performed

1. SKILL.md exists in each skills/ subdirectory
2. YAML frontmatter is valid and parseable
3. Required fields: `name`, `description`, `license`
4. `name` field matches directory name (kebab-case)
5. `name` is 1-64 chars, lowercase, hyphens only
6. `description` is 1-1024 chars
7. `compatibility` is a string (NOT a YAML list)
8. No Claude Code-specific fields (`context`, `agent`, `model`, `hooks`, etc.)
9. `scripts/` directory exists with at least 1 file
10. Scripts are executable (`chmod +x`)
11. SKILL.md is under 1000 lines
12. No references to specific projects (agnostic check)
13. `metadata.version` and `metadata.author` present
14. Has `## Related Skills` section
15. Has keywords in description
