#!/usr/bin/env bash
# Converts agent .md files from tk-agent-team format to other tool formats.
# Supports: cursor (.mdc), aider (AGENTS.md), combined AGENTS.md
#
# Usage:
#   ./scripts/convert.sh cursor   # outputs to .cursor/rules/
#   ./scripts/convert.sh aider    # outputs AGENTS.md at repo root
#   ./scripts/convert.sh all      # runs all formats
#
# Source of truth: plugins/tk-agent-team/agents/**/*.md
# All conversions strip the memory protocol section (Claude Code-specific MCP tooling).

set -euo pipefail

AGENTS_DIR="${AGENTS_DIR:-plugins/tk-agent-team/agents}"
OUTPUT_CURSOR=".cursor/rules"
OUTPUT_AIDER="AGENTS.md"

usage() {
  echo "Usage: $0 [cursor|aider|all]"
  exit 1
}

# Extract frontmatter value: extract_field <file> <field>
extract_field() {
  local file="$1"
  local field="$2"
  awk "/^---$/{found++; next} found==1{print} found==2{exit}" "$file" \
    | grep "^${field}:" \
    | sed "s/^${field}: *//" \
    | tr -d '"'
}

# Extract body (everything after the second ---)
extract_body() {
  local file="$1"
  awk '/^---$/{found++; next} found>=2{print}' "$file"
}

# Strip sections that are Claude Code-specific (memory protocol, memory item guidelines)
strip_mcp_sections() {
  awk '
    /^## Memory protocol/ { skip=1 }
    /^## Memory item guidelines/ { skip=1 }
    /^## / && !/^## Memory protocol/ && !/^## Memory item guidelines/ { skip=0 }
    !skip { print }
  '
}

convert_cursor() {
  echo "Converting to Cursor format → $OUTPUT_CURSOR/"
  mkdir -p "$OUTPUT_CURSOR"

  while IFS= read -r -d '' file; do
    local basename
    basename=$(basename "$file" .md)
    local dir
    dir=$(basename "$(dirname "$file")")

    # Skip template and README
    [[ "$basename" == _* ]] && continue
    [[ "$basename" == "README" ]] && continue

    local name
    name=$(extract_field "$file" "name")
    local description
    description=$(extract_field "$file" "description")
    local emoji
    emoji=$(extract_field "$file" "emoji")

    # Derive output filename: family-persona or just name
    local outname
    if [[ "$dir" != "agents" ]]; then
      outname="${dir}-${basename}"
    else
      outname="$basename"
    fi

    local outfile="$OUTPUT_CURSOR/agent-${outname}.mdc"

    {
      echo "---"
      echo "description: $description"
      echo "globs:"
      echo "alwaysApply: false"
      echo "---"
      echo ""
      echo "# $emoji $name"
      echo ""
      extract_body "$file" | strip_mcp_sections
    } > "$outfile"

    echo "  wrote $outfile"
  done < <(find "$AGENTS_DIR" -name "*.md" -print0 | sort -z)

  echo "  Cursor conversion complete."
}

convert_aider() {
  echo "Converting to Aider format → $OUTPUT_AIDER"

  {
    echo "# Agent Team — Conventions and Specialist Roles"
    echo ""
    echo "This file describes the specialist agents available in this project and their domains."
    echo "Reference these roles when asking for focused reviews or domain-specific help."
    echo ""
    echo "---"
    echo ""

    while IFS= read -r -d '' file; do
      local basename
      basename=$(basename "$file" .md)

      [[ "$basename" == _* ]] && continue
      [[ "$basename" == "README" ]] && continue

      local name
      name=$(extract_field "$file" "name")
      local description
      description=$(extract_field "$file" "description")
      local emoji
      emoji=$(extract_field "$file" "emoji")

      echo "## $emoji $name"
      echo ""
      echo "$description"
      echo ""
      extract_body "$file" | strip_mcp_sections
      echo ""
      echo "---"
      echo ""
    done < <(find "$AGENTS_DIR" -name "*.md" -print0 | sort -z)
  } > "$OUTPUT_AIDER"

  echo "  wrote $OUTPUT_AIDER"
  echo "  Aider conversion complete."
}

case "${1:-}" in
  cursor) convert_cursor ;;
  aider)  convert_aider ;;
  all)
    convert_cursor
    convert_aider
    ;;
  *) usage ;;
esac
