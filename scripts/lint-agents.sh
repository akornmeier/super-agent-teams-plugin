#!/usr/bin/env bash
# Validates agent .md files for required YAML frontmatter fields and recommended sections.
# Also validates SKILL.md files for required frontmatter keys and warns on references to
# non-existent agents.
# Usage: ./scripts/lint-agents.sh [path/to/agents/dir]
#   Defaults to plugins/tk-agent-team/agents/

set -euo pipefail

AGENTS_DIR="${1:-plugins/tk-agent-team/agents}"
SKILLS_DIR="${SKILLS_DIR:-plugins/tk-agent-team/skills}"
REQUIRED_FIELDS=("name" "description" "tools" "color" "emoji" "vibe")
RECOMMENDED_SECTIONS=("Memory protocol" "Core mission" "Critical rules" "Workflow process" "Communication style" "Success metrics")
SKILL_REQUIRED_FIELDS=("name" "description")
KNOWN_FAMILY_SLUGS=("orchestrator" "planner" "tester" "researcher" "debugger" "docs-writer" "reviewer" "developer" "curator" "design" "framework" "engineering" "marketing")

errors=0
warnings=0
checked=0
skills_checked=0

check_agent() {
  local file="$1"
  local basename
  basename=$(basename "$file")

  # Skip template and non-agent files
  if [[ "$basename" == _* ]] || [[ "$basename" == "README.md" ]]; then
    return
  fi

  ((checked++)) || true
  local file_errors=0
  local file_warnings=0

  # Extract frontmatter block (between first two --- lines)
  local frontmatter
  frontmatter=$(awk '/^---$/{found++; next} found==1{print} found==2{exit}' "$file")

  # Check required fields
  for field in "${REQUIRED_FIELDS[@]}"; do
    if ! echo "$frontmatter" | grep -q "^${field}:"; then
      echo "  ERROR  missing required field '${field}'" >&2
      ((file_errors++)) || true
    fi
  done

  # Check recommended sections
  for section in "${RECOMMENDED_SECTIONS[@]}"; do
    if ! grep -q "## ${section}" "$file"; then
      echo "  WARN   missing recommended section '## ${section}'" >&2
      ((file_warnings++)) || true
    fi
  done

  if [[ $file_errors -gt 0 ]] || [[ $file_warnings -gt 0 ]]; then
    echo "$file"
    ((errors += file_errors)) || true
    ((warnings += file_warnings)) || true
  fi
}

# Returns 0 if an agent file exists for the given slug (either agents/<slug>.md or agents/<slug>/).
agent_exists() {
  local slug="$1"
  if [[ -f "${AGENTS_DIR}/${slug}.md" ]] || [[ -d "${AGENTS_DIR}/${slug}" ]]; then
    return 0
  fi
  return 1
}

check_skill() {
  local file="$1"

  ((skills_checked++)) || true
  local file_errors=0
  local file_warnings=0

  # Extract frontmatter block
  local frontmatter
  frontmatter=$(awk '/^---$/{found++; next} found==1{print} found==2{exit}' "$file")

  for field in "${SKILL_REQUIRED_FIELDS[@]}"; do
    if ! echo "$frontmatter" | grep -q "^${field}:"; then
      echo "  ERROR  missing required field '${field}'" >&2
      ((file_errors++)) || true
    fi
  done

  # Warn on references to known family slugs that have no corresponding agent file.
  # Scan the whole body; we accept false positives for warnings.
  local body
  body=$(awk '/^---$/{found++; next} found>=2{print}' "$file")

  for slug in "${KNOWN_FAMILY_SLUGS[@]}"; do
    if echo "$body" | grep -qE "(^|[^a-z0-9-])${slug}([^a-z0-9-]|$)"; then
      if ! agent_exists "$slug"; then
        echo "  WARN   references agent '${slug}' but no ${AGENTS_DIR}/${slug}.md or ${AGENTS_DIR}/${slug}/ exists" >&2
        ((file_warnings++)) || true
      fi
    fi
  done

  if [[ $file_errors -gt 0 ]] || [[ $file_warnings -gt 0 ]]; then
    echo "$file"
    ((errors += file_errors)) || true
    ((warnings += file_warnings)) || true
  fi
}

echo "Linting agent files in: $AGENTS_DIR"
echo ""

while IFS= read -r -d '' file; do
  check_agent "$file"
done < <(find "$AGENTS_DIR" -name "*.md" -not -name "_*" -not -name "README.md" -print0 | sort -z)

# Skill validation: only runs if SKILL.md files exist under SKILLS_DIR.
if [[ -d "$SKILLS_DIR" ]]; then
  skill_files=()
  while IFS= read -r -d '' f; do
    skill_files+=("$f")
  done < <(find "$SKILLS_DIR" -name "SKILL.md" -print0 2>/dev/null | sort -z)

  if [[ ${#skill_files[@]} -gt 0 ]]; then
    echo ""
    echo "Linting skill files in: $SKILLS_DIR"
    echo ""
    for f in "${skill_files[@]}"; do
      check_skill "$f"
    done
  fi
fi

echo ""
echo "Results: $checked agent file(s) checked, $skills_checked skill file(s) checked, $errors error(s), $warnings warning(s)"

if [[ $errors -gt 0 ]]; then
  echo "FAIL — fix errors before merging"
  exit 1
elif [[ $warnings -gt 0 ]]; then
  echo "PASS with warnings — recommended sections missing or soft references unresolved (non-blocking)"
  exit 0
else
  echo "PASS"
  exit 0
fi
