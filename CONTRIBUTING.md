# Contributing to tk-agent-team

Agent definitions, skill pipelines, and memory substrate improvements are all welcome.
This guide covers how to add new teammates and what makes an agent definition good.

---

## Adding a new agent

### 1. Copy the template

```bash
cp plugins/tk-agent-team/agents/_TEMPLATE.md plugins/tk-agent-team/agents/your-agent.md
```

For a persona in an existing family (multiple agents sharing one memory namespace):

```bash
cp plugins/tk-agent-team/agents/reviewer/architecture.md \
   plugins/tk-agent-team/agents/reviewer/your-persona.md
```

Personas in the same directory share a memory namespace — they all call
`memory_read(agent_name="reviewer")` where `reviewer` is the directory name.

### 2. Fill in the frontmatter

All six fields are required (the linter enforces this):

```yaml
---
name: your-agent-name            # must match the directory name for families, or be unique for solo agents
description: Use for X. ...      # triggering conditions + anti-patterns (see below)
tools: Read, Grep, Glob, ...     # only list tools this agent actually needs
color: "#6366F1"                 # hex color for marketplace display
emoji: 🤖                        # single emoji
vibe: "One sentence philosophy"  # the defining principle that shapes edge-case judgment
---
```

**Writing a good `description`:** This is what the orchestrator reads to decide which agent to activate. Structure it as:
- Use for [triggering conditions]
- Specializes in [what makes this agent distinct]
- Hand off when [specific signals]
- Don't use for [anti-patterns / what to use instead]

**Choosing `tools`:** Less is more. Every tool in the list is a capability the agent will try to use. If your agent doesn't need `Bash`, don't list it.

### 3. Keep the memory protocol verbatim

The `## Memory protocol` section must be copied exactly from the template (with `agent_name` updated). Every agent on the team must follow the read-at-start / append-during / report-warning pattern or the curation pipeline breaks.

### 4. Fill in the 8 sections

| Section | What to write |
|---------|--------------|
| **Your identity** | 2–3 sentences on what drives the agent's judgment and what distinguishes it |
| **Core mission** | 3–5 numbered responsibilities with concrete deliverables |
| **Critical rules** | Non-negotiable constraints with the failure mode each rule prevents |
| **Workflow process** | Step-by-step methodology (start with "Load memory", end with "Append learnings") |
| **Communication style** | Output format, severity labels, tone conventions |
| **Success metrics** | Checklist of verifiable outcomes the orchestrator can check |
| **Your specialty** | Domain boundaries, escalation triggers, what to refuse/redirect |
| **Memory item guidelines** | Keep verbatim from template unless your domain warrants special guidance |

### 5. Validate with the linter

```bash
chmod +x scripts/lint-agents.sh
./scripts/lint-agents.sh
```

Errors (missing required frontmatter fields) must be fixed. Warnings (missing recommended sections) are non-blocking but strongly encouraged.

---

## Agent quality guidelines

### Specificity over generality
An agent that does one thing excellently is more useful than one that does many things adequately. The reviewer family is a good example: three narrow personas sharing memory are more capable than one broad "code reviewer."

### Vibe as a decision heuristic
The `vibe` field isn't decoration. It should capture the principle the agent falls back on when a case is ambiguous. "Trust no input, verify every boundary" tells the security reviewer how to rule on edge cases. Make it specific enough to generate a decision, not just describe a domain.

### Memory items are domain knowledge
An agent that never appends to memory is an agent that never learns. The `## Memory item guidelines` section should explain what kinds of things are worth remembering in this domain — and what aren't. Avoid items like "check the documentation" (too obvious) or "this project uses TypeScript" (in the shared file).

### Communication style shapes usefulness
An agent that produces unformatted walls of text is hard for the orchestrator to parse. Define severity labels, output sections, and formatting expectations explicitly. The correctness reviewer's `🔴 Blocker | 🟡 Suggestion | 💭 Nit` scheme is a model.

---

## Adding a new agent family

A family is a directory under `agents/` where all personas share a memory namespace. To create a new family:

1. Create the directory: `mkdir plugins/tk-agent-team/agents/your-family`
2. Create personas: each file sets `name: your-family` in frontmatter (matching the directory)
3. Update the `agents/README.md` family registry

Family memory is pooled — all personas read and write to `your-family.yaml`. Design the personas to cover complementary concerns, not overlapping ones.

---

## Modifying the memory scoring rubric

The curator's drop threshold and dimension weights live in
`plugins/tk-agent-team/skills/memory-curate/references/scoring.md`.

Before editing weights:
1. Run a curation session on a real agent memory file
2. Check the curator's own memory for open questions about calibration
3. Make the smallest change that addresses the observed behavior
4. Document the reason for the weight change in `scoring.md`

The curator will propose changes via open questions in its memory when it sees calibration signals — check those before manually adjusting.

---

## Running tests

```bash
cd plugins/tk-agent-team/mcp-servers/agent-substrate
pytest
```

All MCP server changes require passing tests. Agent `.md` file changes require passing the lint check.

---

## Pull request checklist

- [ ] New/modified agents pass `./scripts/lint-agents.sh` with no errors
- [ ] All 6 frontmatter fields are present
- [ ] `## Memory protocol` is verbatim from the template (with agent_name updated)
- [ ] All 8 personality sections are present
- [ ] If MCP server was modified: `pytest` passes
- [ ] `agents/README.md` updated if a new agent or family was added
