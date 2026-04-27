#!/usr/bin/env bash
# Validates agent .md files for required YAML frontmatter fields and recommended sections.
# Also validates SKILL.md files for required frontmatter keys (including the v0.4
# `team_pattern` enum), `<!-- @ref _shared/*.md -->` resolution, teammate name
# resolution, parallel-panel `dedup_decisions` taxonomy, and global agent-name
# uniqueness.
# Usage: ./scripts/lint-agents.sh [path/to/agents/dir]
#   Defaults to plugins/tk-agent-team/agents/

set -euo pipefail

AGENTS_DIR="${1:-plugins/tk-agent-team/agents}"
SKILLS_DIR="${SKILLS_DIR:-plugins/tk-agent-team/skills}"
SHARED_DIR="${SKILLS_DIR}/_shared"
REQUIRED_FIELDS=("name" "description" "tools" "color" "emoji" "vibe")
RECOMMENDED_SECTIONS=("Memory protocol" "Core mission" "Critical rules" "Workflow process" "Communication style" "Success metrics")
SKILL_REQUIRED_FIELDS=("name" "description")
KNOWN_FAMILY_SLUGS=("orchestrator" "planner" "tester" "researcher" "debugger" "docs-writer" "reviewer" "developer" "curator" "design" "framework" "engineering" "marketing")

# Six-pattern catalog from _shared/team-protocol.md, plus the special `solo|pair`
# value used by /work (mode-routed skill — only accepted exception).
TEAM_PATTERN_CATALOG=("solo" "pair" "parallel-panel" "pipeline" "staged-team" "feature-team" "solo|pair")

errors=0
warnings=0
checked=0
skills_checked=0

# Per-check counters for the summary line.
team_pattern_ok=0
team_pattern_missing=0
ref_ok=0
ref_unresolved=0
teammate_ok=0
teammate_unresolved=0
name_unique_count=0
name_duplicate_count=0
panel_dedup_ok=0
panel_dedup_missing=0

# Globals populated during scan.
ALL_AGENT_NAMES_FILE=""

cleanup() {
  if [[ -n "$ALL_AGENT_NAMES_FILE" && -f "$ALL_AGENT_NAMES_FILE" ]]; then
    rm -f "$ALL_AGENT_NAMES_FILE"
  fi
}
trap cleanup EXIT

# Returns 0 if file's first non-blank line is `---` (i.e., has YAML frontmatter).
has_frontmatter() {
  local file="$1"
  local first_line
  first_line=$(awk 'NF{print; exit}' "$file")
  [[ "$first_line" == "---" ]]
}

# Extract a single field's value from a frontmatter block. Strips quotes.
extract_frontmatter_field() {
  local file="$1"
  local field="$2"
  awk -v f="$field" '
    /^---$/ { found++; next }
    found==1 {
      if ($0 ~ "^"f":") {
        sub("^"f":[[:space:]]*", "")
        gsub(/^["\x27]|["\x27]$/, "")
        print
        exit
      }
    }
    found==2 { exit }
  ' "$file"
}

# Returns 0 if value is in the team-pattern catalog.
is_valid_team_pattern() {
  local value="$1"
  local p
  for p in "${TEAM_PATTERN_CATALOG[@]}"; do
    [[ "$value" == "$p" ]] && return 0
  done
  return 1
}

check_agent() {
  local file="$1"
  local basename
  basename=$(basename "$file")

  # Skip template, README, and schema docs.
  if [[ "$basename" == _* ]] || [[ "$basename" == "README.md" ]] || [[ "$basename" == *.schema.md ]]; then
    return
  fi

  # Skip any *.md in agents/ that lacks YAML frontmatter (non-agent docs).
  if ! has_frontmatter "$file"; then
    if [[ "${LINT_AGENTS_DEBUG:-}" == "1" ]]; then
      echo "  DEBUG  skipping $file (no YAML frontmatter — not an agent file)" >&2
    fi
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

  # Capture name for global uniqueness check
  local name_value
  name_value=$(extract_frontmatter_field "$file" "name")
  if [[ -n "$name_value" ]]; then
    printf '%s\t%s\n' "$name_value" "$file" >> "$ALL_AGENT_NAMES_FILE"
  fi

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

# Returns 0 if any agent file's frontmatter `name:` matches the given value.
agent_name_exists() {
  local target="$1"
  [[ -f "$ALL_AGENT_NAMES_FILE" ]] || return 1
  awk -F'\t' -v t="$target" '$1 == t { found=1; exit } END { exit !found }' "$ALL_AGENT_NAMES_FILE"
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

  # ---- Check 1: team_pattern frontmatter ----
  local team_pattern_value
  team_pattern_value=$(extract_frontmatter_field "$file" "team_pattern")
  if [[ -z "$team_pattern_value" ]]; then
    echo "  ERROR  missing required field 'team_pattern' (one of: ${TEAM_PATTERN_CATALOG[*]})" >&2
    ((file_errors++)) || true
    ((team_pattern_missing++)) || true
  elif ! is_valid_team_pattern "$team_pattern_value"; then
    echo "  ERROR  invalid team_pattern '${team_pattern_value}' (must be one of: ${TEAM_PATTERN_CATALOG[*]})" >&2
    ((file_errors++)) || true
    ((team_pattern_missing++)) || true
  else
    ((team_pattern_ok++)) || true
  fi

  # feature-team requires `### Why feature-team` justification.
  if [[ "$team_pattern_value" == "feature-team" ]]; then
    if ! grep -qE '^### Why feature-team' "$file"; then
      echo "  WARN   team_pattern: feature-team but missing '### Why feature-team' justification section" >&2
      ((file_warnings++)) || true
    fi
  fi

  # Body content for the remaining checks.
  local body
  body=$(awk '/^---$/{found++; next} found>=2{print}' "$file")

  # ---- Check 2: <!-- @ref _shared/*.md --> resolution ----
  local refs
  refs=$(echo "$body" | grep -oE '<!-- @ref _shared/[A-Za-z0-9._/-]+(#[A-Za-z0-9._-]+)? -->' || true)
  if [[ -n "$refs" ]]; then
    while IFS= read -r ref; do
      [[ -z "$ref" ]] && continue
      # Extract the filename (strip optional #anchor).
      local target
      target=$(echo "$ref" | sed -E 's|<!-- @ref _shared/||; s| -->$||; s|#.*$||')
      if [[ -f "${SHARED_DIR}/${target}" ]]; then
        ((ref_ok++)) || true
      else
        echo "  ERROR  unresolved @ref _shared/${target} (no such file at ${SHARED_DIR}/${target})" >&2
        ((file_errors++)) || true
        ((ref_unresolved++)) || true
      fi
    done <<< "$refs"
  fi

  # ---- Check 3: teammate name resolution ----
  # Look for `name: "<value>"` references in the body, common shapes:
  #   Agent({..., name: "reviewer-architecture", ...})
  #   `Agent({name: "developer-backend", ...})`
  # We extract `name:` plus the quoted value, dedupe, and skip placeholders containing `<`.
  local teammate_names
  teammate_names=$(echo "$body" | grep -oE 'name:[[:space:]]*"[A-Za-z0-9_.<>/-]+"' | sed -E 's|^name:[[:space:]]*"||; s|"$||' | sort -u || true)
  if [[ -n "$teammate_names" ]]; then
    while IFS= read -r tname; do
      [[ -z "$tname" ]] && continue
      # Skip placeholders like reviewer-<lens>
      [[ "$tname" == *"<"* ]] && continue
      # Skip values that look like skill names (e.g., name: "review" in frontmatter — already excluded by body extraction).
      if agent_name_exists "$tname"; then
        ((teammate_ok++)) || true
      else
        echo "  WARN   teammate name '${tname}' has no matching agent (no agents/**/*.md with frontmatter 'name: ${tname}')" >&2
        ((file_warnings++)) || true
        ((teammate_unresolved++)) || true
      fi
    done <<< "$teammate_names"
  fi

  # Legacy known-family-slug warning (preserve existing behavior).
  for slug in "${KNOWN_FAMILY_SLUGS[@]}"; do
    if echo "$body" | grep -qE "(^|[^a-z0-9-])${slug}([^a-z0-9-]|$)"; then
      if ! agent_exists "$slug"; then
        echo "  WARN   references agent '${slug}' but no ${AGENTS_DIR}/${slug}.md or ${AGENTS_DIR}/${slug}/ exists" >&2
        ((file_warnings++)) || true
      fi
    fi
  done

  # ---- Check 6: parallel-panel skills should use `section: "dedup_decisions"` ----
  if [[ "$team_pattern_value" == "parallel-panel" ]]; then
    if echo "$body" | grep -qE 'section:[[:space:]]*"dedup_decisions"'; then
      ((panel_dedup_ok++)) || true
    else
      echo "  WARN   team_pattern: parallel-panel but no 'section: \"dedup_decisions\"' usage found (canonical per _shared/team-protocol.md#team-memory-section-taxonomy)" >&2
      ((file_warnings++)) || true
      ((panel_dedup_missing++)) || true
    fi
  fi

  if [[ $file_errors -gt 0 ]] || [[ $file_warnings -gt 0 ]]; then
    echo "$file"
    ((errors += file_errors)) || true
    ((warnings += file_warnings)) || true
  fi
}

# ---- Check 5: agent-name uniqueness across all agent files ----
check_name_uniqueness() {
  [[ -f "$ALL_AGENT_NAMES_FILE" ]] || return 0
  local total
  total=$(wc -l < "$ALL_AGENT_NAMES_FILE" | tr -d ' ')
  local dupes
  dupes=$(awk -F'\t' '{print $1}' "$ALL_AGENT_NAMES_FILE" | sort | uniq -d || true)
  if [[ -z "$dupes" ]]; then
    name_unique_count=$total
    name_duplicate_count=0
    return 0
  fi
  while IFS= read -r dup; do
    [[ -z "$dup" ]] && continue
    echo "" >&2
    echo "  ERROR  duplicate agent name '${dup}' across:" >&2
    awk -F'\t' -v d="$dup" '$1 == d { print "         - " $2 }' "$ALL_AGENT_NAMES_FILE" >&2
    ((errors++)) || true
    ((name_duplicate_count++)) || true
  done <<< "$dupes"
  name_unique_count=$((total - name_duplicate_count))
}

ALL_AGENT_NAMES_FILE=$(mktemp -t lint-agents.XXXXXX)
: > "$ALL_AGENT_NAMES_FILE"

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

# Run name-uniqueness check after every agent file has been scanned.
check_name_uniqueness

echo ""
echo "Results: $checked agent file(s) checked, $skills_checked skill file(s) checked, $errors error(s), $warnings warning(s)"
echo "  - SKILL team_pattern: ${team_pattern_ok}/${team_pattern_missing} (ok/missing)"
echo "  - SKILL @ref resolution: ${ref_ok}/${ref_unresolved} (ok/unresolved)"
echo "  - SKILL teammate resolution: ${teammate_ok}/${teammate_unresolved} (ok/unresolved)"
echo "  - Agent name uniqueness: ${name_unique_count}/${name_duplicate_count} (ok/duplicates)"
echo "  - parallel-panel dedup_decisions: ${panel_dedup_ok}/${panel_dedup_missing} (ok/missing)"

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
