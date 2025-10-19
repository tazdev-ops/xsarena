# Role Launcher System

## Purpose
Quickly switch between different expert roles for different types of analysis and content creation.

## Available Roles
- Socratic Cross-Examiner: /systemfile directives/role.socratic.md
- Steelman + Synthesis Mediator: /systemfile directives/role.steelman.md
- Policy Drafter (Plain English): /systemfile directives/role.policy_drafter.md
- Risk Officer (Five Whys): /systemfile directives/role.risk_officer.md
- Glossary Surgeon: /systemfile directives/role.glossary_surgeon.md
- Narrative Flow Editor: /systemfile directives/role.narrative_editor.md
- Red-Team (Defensive): /systemfile directives/role.red_team.md

## Quick Usage Pattern
1. Set defaults: /style.nobs on; /style.narrative on
2. Set length: /out.minchars 1400-2200 (for short forms) or 4200-5200 (for chapter sections)
3. Load role: /systemfile directives/role.[role_name].md
4. Apply: /next "Your topic/task here"

## Toggles You Can Layer On Any Role
- Tone: mild | medium | hot (amount of edge; still no personal attacks)
- Focus: logic | rhetoric | incentives | outcomes (pick 2-3)
- Scope: personal habits | community standards | public policy
- Length: short (900-1400) | medium (1800-2400) | deep (3000+)
- Bilingual: EN/FA pairs ON/OFF (same structure both sides)

## JSON Mode (for pipelines)
Add: "Return strict JSON only with fields: {section1:…, section2:…}" to any role for structured output.
