---
name: ayurvedic-wellness
description: Ayurvedic wellness guidance — remedies, recipes, exercise, and daily/seasonal routines — gated by a safety triage before any suggestion is made. Use for questions about doshas, home remedies, Ayurvedic diet, yoga/pranayama, or dinacharya/ritucharya routines.
---

# Ayurvedic Wellness

This skill is the prose-facing counterpart to the `ayurveda-wellness-mcp` server.
The MCP mirrors the rules below in code — treat this file as the router and the
`ayurveda-wellness-mcp` tools as the source of truth for what actually gets
returned to the user.

## Safety gate — always first

Before suggesting any remedy or building a routine, run the equivalent of
`safety_check` / the gate inside `suggest_remedy` and `build_day_plan`:

1. **Red flags** (chest pain, breathing difficulty, stroke signs, severe
   bleeding, etc.) → refer to emergency care. Do not suggest a remedy.
2. **Blacklist** (bhasma, rasa shastra, aconite/vatsanabha, datura,
   bhallataka, self-administered panchakarma) → refuse, cite heavy-metal
   contamination risk (JAMA 2004/2008, ~20% of tested products), point to a
   licensed practitioner.
3. **Conditional flags** (pregnancy, infant, young child, medications,
   chronic disease) → caution: narrow remedies to ones without a matching
   contraindication, and for infant/young child suppress remedies entirely in
   favor of hydration/comfort + pediatrician referral.
4. Otherwise → clear, suggest normally.

Always append the standard educational disclaimer to remedy/routine output.

## Domain reference modules

- **ayurveda** — dosha theory (vata/pitta/kapha), remedies, evidence grading
  (A = RCT/meta-analysis, B = mixed/small trial, C = traditional only).
  Mirrors `suggest_remedy` / `get_remedy_detail`.
- **cooking** — dosha- and season-appropriate recipes, tridoshic dishes that
  match every dosha filter. Mirrors `find_recipe`.
- **exercise** — dosha-appropriate exercise routines and pranayama, including
  contraindications (e.g. kapalabhati is unsafe in pregnancy, hypertension,
  heart disease). Mirrors `get_exercise_routine` / `get_pranayama`.
- **integration** — combining the above into a full dinacharya (daily) or
  ritucharya (seasonal) routine, applying the safety gate to swap
  contraindicated practices rather than dropping the whole plan. Mirrors
  `build_day_plan`.

## When to prefer the MCP tools over free-text answers

If `ayurveda-wellness-mcp` is available, call its tools instead of
generating remedies/recipes/routines from memory — the tool responses are
gated, versioned, and testable; free-text answers are not.
