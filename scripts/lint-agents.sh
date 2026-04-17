#!/usr/bin/env bash
# Validates agent .md files for required YAML frontmatter fields and recommended sections.
# Usage: ./scripts/lint-agents.sh [path/to/agents/dir]
#   Defaults to plugins/tk-agent-team/agents/

set -euo pipefail

AGENTS_DIR="${1:-plugins/tk-agent-team/agents}"
REQUIRED_FIELDS=("name" "description" "tools" "color" "emoji" "vibe")
RECOMMENDED_SECTIONS=("Memory protocol" "Core mission" "Critical rules" "Workflow process" "Communication style" "Success metrics")

errors=0
warnings=0
checked=0

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

export -f check_agent

echo "Linting agent files in: $AGENTS_DIR"
echo ""

while IFS= read -r -d '' file; do
  check_agent "$file"
done < <(find "$AGENTS_DIR" -name "*.md" -not -name "_*" -not -name "README.md" -print0 | sort -z)

echo ""
echo "Results: $checked file(s) checked, $errors error(s), $warnings warning(s)"

if [[ $errors -gt 0 ]]; then
  echo "FAIL — fix errors before merging"
  exit 1
elif [[ $warnings -gt 0 ]]; then
  echo "PASS with warnings — recommended sections missing (non-blocking)"
  exit 0
else
  echo "PASS"
  exit 0
fi
