# Public Opinion & Survey Methods Pack

This pack provides roles, overlays, and strict-JSON templates for designing, fielding, auditing, and analyzing surveys (including experiments and panels). Educational, non-partisan, and privacy-aware.

## How to Use

- Save files under `directives/(roles|prompt.*|style.*).md`.
- Try:
  - `xsarena prompt run -s directives/roles/role.survey_designer.md -t "Topic: trust in institutions; audience: adults; constraints: mobile-first, 8 minutes"`
  - `xsarena prompt run -s directives/prompt.survey_instrument.json.md -t "Build an instrument on job transitions for adults 18+; 7–9 minutes" | jq .`
- Mix overlays in cockpit: `/prompt.style on measurement-error-lens; /prompt.style on mode-effects-guard`

## Components

### A) Roles (Survey-Facing Personas)

- `role.survey_designer.md` - Create practical, defensible survey plans
- `role.questionnaire_architect.md` - Design questionnaires with mobile-first approach
- `role.sampling_statistician.md` - Design sampling plans
- `role.weighting_benchmarker.md` - Create weighting & benchmarking plans
- `role.panel_ops_manager.md` - Manage panels with privacy-forward approach
- `role.mode_effects_analyst.md` - Analyze mode effects
- `role.cognitive_interviewer.md` - Create cognitive interview guides
- `role.survey_experiment_lead.md` - Design survey experiments
- `role.nonresponse_strategist.md` - Reduce nonresponse bias

### B) Overlays (Toggleable Method Lenses)

- `style.survey_overlays.md` - Contains multiple overlays:
  - `measurement-error-lens`
  - `mode-effects-guard`
  - `social-desirability-shield`
  - `randomization-integrity`
  - `benchmark-first`
  - `preregister`
  - `privacy-minimums`
  - `field-control`

### C) Strict-JSON Templates (Scriptable Structures)

- `prompt.question_bank_survey.json.md` - Question Bank template
- `prompt.survey_instrument.json.md` - Survey Instrument template
- `prompt.sampling_plan.json.md` - Sampling Plan template
- `prompt.weighting_plan.json.md` - Weighting Plan template
- `prompt.benchmark_audit.json.md` - Benchmark Audit template
- `prompt.response_rate_report.json.md` - Response Rate Report template
- `prompt.panel_health.json.md` - Panel Health template
- `prompt.cognitive_interview_script.json.md` - Cognitive Interview Script template
- `prompt.randomized_experiment_survey.json.md` - Survey Experiment template
- `prompt.cleaning_rules.json.md` - Cleaning Rules template
- `prompt.codebook.json.md` - Codebook template
- `prompt.crosstab_spec.json.md` - Crosstab Specification template

## Ready-to-try Combos

- Fast instrument: `role.questionnaire_architect + overlays: measurement-error-lens, field-control`
- Experiment on survey: `role.survey_experiment_lead + overlays: randomization-integrity, preregister`
- Weighting + audit: `role.weighting_benchmarker + overlays: benchmark-first`
- Nonresponse reduction: `role.nonresponse_strategist + overlays: privacy-minimums, mode-effects-guard`
- Panel operations: `role.panel_ops_manager + overlays: field-control, privacy-minimums`

## Scope & Safety

- Educational; non-medical; non-therapeutic; non-partisan; avoids targeted persuasion.
- Privacy-forward: no PII; redact free text; minimize data collection.
- JSON templates are strict—great for scripting and dashboards.
- Overlays are additive and composable; they don't change core code.
