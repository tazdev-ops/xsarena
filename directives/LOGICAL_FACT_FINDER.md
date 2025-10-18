# Logical Fact Finder Pack

This pack provides tools for neutral, educational analysis of complex claims using definitions, logic, and evidence.

## Components

### Roles
- `role.logical_fact_finder.md` - Evaluates claims neutrally using definitions, logic, and evidence
- `role.debate_referee_logic.md` - Analyzes arguments with focus on validity and soundness
- `role.bayesian_reasoner.md` - Performs Bayesian analysis with educational focus

### Style Overlays
- `reasoning_overlays.md` - Provides reasoning overlays like steelman-first, evidence-ladder, fallacy-scan, etc.

### Prompt Templates (JSON)
- `claim_definition.json.md` - Defines claims with terms and scope
- `argument_catalog.json.md` - Catalogs arguments for and against
- `argument_evaluation.json.md` - Evaluates argument validity and soundness
- `evidence_registry.json.md` - Registers evidence and its relevance
- `bayesian_update_sheet.json.md` - Performs Bayesian updates
- `falsifiability_matrix.json.md` - Tests hypotheses against predictions
- `reasoned_brief.json.md` - Creates reasoned summaries

## Usage Examples

### Basic Analysis
```
xsarena prompt run -s directives/roles/role.logical_fact_finder.md -t "Question: Does God exist? Frame: classical theism; constraints: neutral, educational"
```

### Argument Catalog
```
xsarena prompt run -s directives/prompt/argument_catalog.json.md -t "Question: Does God exist? Frame: classical theism (omnipotent, omniscient, omnibenevolent)" | jq .
```

### Bayesian Analysis
```
xsarena prompt run -s directives/prompt/bayesian_update_sheet.json.md -t "Hypotheses: {God exists, God does not exist}; Observations: fine-tuning, moral experience, hiddenness, evil" | jq .
```

### Mixed Overlays
```
/prompt.style on steelman-first
/prompt.style on evidence-ladder
/prompt.style on fallacy-scan
```

## Workflow for Complex Questions
1. Define the frame and terms
2. Catalog arguments
3. Evaluate arguments (validity/soundness)
4. Register evidence (optional)
5. Perform Bayesian analysis (optional)
6. Draft a reasoned brief

For more details on the suggested workflow, see the individual template files or the original documentation.
