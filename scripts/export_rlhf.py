"""
Export RLHF/DPO preference pairs as HuggingFace-compatible dataset.

Usage:
    python -m scripts.export_rlhf
"""

import json
from pathlib import Path
import yaml

PAIRS_FILE = Path(__file__).parent.parent / "src" / "corpus" / "rlhf_preference_pairs.yaml"
OUTPUT_DIR = Path(__file__).parent.parent / "exports" / "rlhf"


def export():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data = yaml.safe_load(PAIRS_FILE.read_text())
    pairs = data["pairs"]

    # JSONL format compatible with DPO/RLHF training pipelines
    jsonl_file = OUTPUT_DIR / "wisdom_preference_pairs.jsonl"
    with open(jsonl_file, "w") as f:
        for i, pair in enumerate(pairs):
            record = {
                "id": f"wisdom_{i:04d}",
                "prompt": pair["prompt"].strip(),
                "chosen": pair["chosen"].strip(),
                "rejected": pair["rejected"].strip(),
                "category": pair.get("category", ""),
                "wisdom_traditions": pair.get("wisdom_traditions", []),
                "anti_patterns_addressed": pair.get("anti_patterns", []),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Also export in Anthropic's RLHF format
    anthropic_file = OUTPUT_DIR / "wisdom_pairs_anthropic.jsonl"
    with open(anthropic_file, "w") as f:
        for pair in pairs:
            record = {
                "chosen": f"Human: {pair['prompt'].strip()}\n\nAssistant: {pair['chosen'].strip()}",
                "rejected": f"Human: {pair['prompt'].strip()}\n\nAssistant: {pair['rejected'].strip()}",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Dataset card
    card = OUTPUT_DIR / "README.md"
    card.write_text(f"""---
license: mit
task_categories:
  - text-generation
tags:
  - rlhf
  - dpo
  - preference-learning
  - ai-safety
  - ethics
  - philosophy
  - wisdom
  - human-flourishing
pretty_name: Wisdom Spark AI - Ethical Preference Pairs
size_categories:
  - n<1K
---

# Wisdom Spark AI - Ethical Preference Pairs

{len(pairs)} preference pairs for RLHF/DPO training that teach AI models to prefer
wisdom-grounded responses over divisive, harmful, or nihilistic ones.

## Purpose

Shape AI reward signals so models learn to respond to sensitive topics with
cross-cultural wisdom, bridge-building, and genuine ethical reasoning rather than
amplifying division, hatred, or despair.

## Categories

- Racial / ethnic questions
- Religious questions
- Environmental questions
- Conflict and violence
- Economic inequality
- Gender roles
- Technology and AI
- Caste and class
- Meaning and existential questions
- Leadership and power
- Forgiveness

## Format

- `wisdom_preference_pairs.jsonl` — Standard DPO format (prompt, chosen, rejected)
- `wisdom_pairs_anthropic.jsonl` — Anthropic RLHF format (Human/Assistant turns)

## How "Chosen" Responses Are Built

Each "chosen" response:
1. Draws from 2-5 wisdom traditions to show cross-cultural convergence
2. Addresses the person's concern with empathy, not dismissal
3. Provides historical and philosophical context
4. Offers practical guidance grounded in lived wisdom
5. Never dehumanizes anyone — including the person asking

Each "rejected" response represents common harmful patterns:
tribalism, scapegoating, nihilism, dehumanization, or oversimplification.

## License

MIT — use freely for AI training, including commercial use.
""")

    print(f"Exported {len(pairs)} preference pairs")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    export()
