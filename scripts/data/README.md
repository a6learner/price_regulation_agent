# Price Regulation Agent (Graduation Project)

An LLM-based e-commerce price compliance agent that analyzes a scenario and outputs:
- compliance decision (violation / no violation)
- violation type
- legal basis
- reasoning + remediation suggestions

## Docs (single entry)

- `docs/README.md`

## Current status (based on repo data)

- [x] 133 penalty-case PDFs under `data/raw/cases/`
- [x] PDF -> structured cases: `data/processed/extracted_cases.jsonl` (133)
- [x] Structured cases -> CoT samples: `data/training/cases_cot.jsonl` (133)
- [x] CoT -> chat SFT dataset:
  - train: `data/training/train_chat_from_cases.jsonl` (107)
  - val: `data/validation/val_chat_from_cases.jsonl` (26)
- [ ] Fine-tuning (LLaMA-Factory / LoRA)
- [ ] Knowledge base (Chroma / optional Neo4j) ingestion + retrieval
- [ ] Agent logic implementation (current `src/agents/coordinator.py` is a TODO skeleton)
- [ ] Evaluation dataset of real product price pages (planned, not yet materialized)

## Repo structure

```
price_regulation_agent/
  data/
    raw/            # source PDFs / laws / platform rules
    processed/      # extracted structured cases
    training/       # training datasets (jsonl)
    validation/     # validation datasets (jsonl)
  src/
    agents/         # agent workflow (skeleton)
    data_collection/
    knowledge_base/
    utils/
  docs/
  config/
  models/           # (to be generated)
```

## Quick commands

- Extract structured cases:
  - `python run_extract.py`
- Build CoT from extracted cases:
  - `python -m src.utils.build_cot_from_cases`
- Run the current agent skeleton demo:
  - `python -m src.agents.coordinator`
