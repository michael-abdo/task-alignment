# Success Criteria Generator Prompt

## Task
Generate success criteria for software components using a dual-validation format that ensures both human testability and engineering accountability.

## Required Format
```
<human-readable outcome> (<tracking metric>)
```

## Format Rules

1. **Human-readable outcome** (before parentheses):
   - Describes what a non-technical person can observe and validate
   - Uses sensory language: "feels responsive", "matches what you'd expect", "clearly distinguishes"
   - Testable by watching/using the feature firsthand
   - Pass/fail determinable without technical expertise

2. **Tracking metric** (inside parentheses):
   - Objective, measurable number
   - Includes units and thresholds: ms, %, ±tolerance, >threshold, <limit
   - Prevents subjective "done" claims
   - Comparable across builds/versions

## Examples

**Good:**
- "Talk time updates feel responsive during live meetings (sub 2s refresh)"
- "Share percentages add up correctly and match observable speaking patterns (100% total ±1%)"
- "Turn counts match what a human would count watching the meeting (±1 turn per speaker)"
- "Alerts appear when one person noticeably dominates the conversation (>50% share threshold)"
- "Long uninterrupted speaking is flagged when observers would notice it (>60s triggers detection)"
- "Classification matches what an observer would say about meeting flow (>70% agreement)"

**Bad:**
- "System performs well" — no metric, no testable outcome
- "Latency < 200ms" — metric only, no human validation context
- "Users are satisfied" — not testable, no metric
- "Works correctly" — neither testable nor measurable

## Input
Provide the component name and a brief description of what it does.

## Output
Generate 1-2 success criteria per component following the exact format above.

## Why This Format Works
- Without the human outcome → meaningless specs stakeholders can't test
- Without the metric → subjective claims engineers can't prove
- Together → testable experience tied to explicit tracking number
