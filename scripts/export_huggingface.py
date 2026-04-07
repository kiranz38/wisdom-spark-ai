"""
Export the wisdom corpus as HuggingFace-compatible dataset files.
Generates JSONL format ready for upload to HuggingFace Hub.

Usage:
    python -m scripts.export_huggingface
"""

import json
from pathlib import Path
import yaml

CORPUS_DIR = Path(__file__).parent.parent / "src" / "corpus"
TRADITIONS_DIR = CORPUS_DIR / "traditions"
THEMES_DIR = CORPUS_DIR / "themes"
OUTPUT_DIR = Path(__file__).parent.parent / "exports" / "huggingface"


def load_themes() -> dict[str, dict]:
    themes_file = THEMES_DIR / "universal_themes.yaml"
    data = yaml.safe_load(themes_file.read_text())
    return {t["slug"]: t for t in data["themes"]}


def export():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    themes = load_themes()
    all_entries = []
    all_traditions = []

    for filepath in sorted(TRADITIONS_DIR.glob("*.yaml")):
        data = yaml.safe_load(filepath.read_text())
        trad = data["tradition"]

        all_traditions.append({
            "slug": trad["slug"],
            "name": trad["name"],
            "origin_region": trad.get("origin_region"),
            "era": trad.get("era"),
            "description": trad["description"].strip(),
            "key_figures": trad.get("key_figures", []),
            "core_principles": trad.get("core_principles", []),
        })

        for entry in data.get("entries", []):
            record = {
                "tradition_slug": trad["slug"],
                "tradition_name": trad["name"],
                "source_text": entry["source_text"].strip(),
                "source_author": entry.get("source_author"),
                "source_work": entry.get("source_work"),
                "source_era": entry.get("source_era"),
                "original_language": entry.get("original_language"),
                "core_principle": entry["core_principle"].strip(),
                "practical_application": entry["practical_application"].strip(),
                "modern_context": (entry.get("modern_context") or "").strip(),
                "addresses_anti_patterns": entry.get("addresses_anti_patterns", []),
                "themes": entry.get("themes", []),
                "theme_names": [themes[t]["name"] for t in entry.get("themes", []) if t in themes],
                "flourishing_scores": {
                    "reduces_suffering": entry.get("reduces_suffering", 0.0),
                    "respects_dignity": entry.get("respects_dignity", 0.0),
                    "promotes_cooperation": entry.get("promotes_cooperation", 0.0),
                    "considers_future": entry.get("considers_future", 0.0),
                    "honors_nature": entry.get("honors_nature", 0.0),
                },
                "citation": entry.get("citation"),
                # Pre-computed for training: a rich text representation
                "training_text": _build_training_text(entry, trad),
            }
            all_entries.append(record)

    # Write JSONL (one record per line)
    entries_file = OUTPUT_DIR / "wisdom_entries.jsonl"
    with open(entries_file, "w") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    traditions_file = OUTPUT_DIR / "traditions.jsonl"
    with open(traditions_file, "w") as f:
        for trad in all_traditions:
            f.write(json.dumps(trad, ensure_ascii=False) + "\n")

    # Also write a combined JSON for easy loading
    combined_file = OUTPUT_DIR / "wisdom_corpus.json"
    with open(combined_file, "w") as f:
        json.dump({
            "name": "Wisdom Spark AI - Philosophical Wisdom Corpus",
            "version": "0.1.0",
            "description": "Curated wisdom from 15+ philosophical traditions for AI training",
            "license": "MIT",
            "traditions_count": len(all_traditions),
            "entries_count": len(all_entries),
            "traditions": all_traditions,
            "entries": all_entries,
        }, f, indent=2, ensure_ascii=False)

    # Dataset card
    card_file = OUTPUT_DIR / "README.md"
    card_file.write_text(_dataset_card(len(all_traditions), len(all_entries)))

    print(f"Exported {len(all_entries)} entries from {len(all_traditions)} traditions")
    print(f"Output: {OUTPUT_DIR}")


def _build_training_text(entry: dict, tradition: dict) -> str:
    """Build a rich text representation suitable for training data."""
    parts = [
        f"[{tradition['name']}] {entry.get('source_author', 'Unknown')}",
        f'"{entry["source_text"].strip()}"',
        f"Source: {entry.get('source_work', 'Unknown')}, {entry.get('source_era', '')}",
        f"\nCore Principle: {entry['core_principle'].strip()}",
        f"\nPractical Application: {entry['practical_application'].strip()}",
    ]
    if entry.get("modern_context"):
        parts.append(f"\nModern Context: {entry['modern_context'].strip()}")
    if entry.get("addresses_anti_patterns"):
        parts.append(f"\nThis wisdom addresses: {', '.join(entry['addresses_anti_patterns'])}")
    return "\n".join(parts)


def _dataset_card(n_traditions: int, n_entries: int) -> str:
    return f"""---
license: mit
task_categories:
  - text-generation
  - text-classification
language:
  - en
tags:
  - philosophy
  - ethics
  - wisdom
  - ai-safety
  - human-flourishing
  - cross-cultural
  - stoicism
  - buddhism
  - vedanta
  - ubuntu
  - taoism
  - sufism
  - jainism
  - indigenous-wisdom
  - positive-psychology
pretty_name: Wisdom Spark AI - Philosophical Wisdom Corpus
size_categories:
  - n<1K
---

# Wisdom Spark AI - Philosophical Wisdom Corpus

Curated wisdom from {n_traditions} philosophical traditions, structured for AI training
and alignment. Each entry includes source text, extracted principles, practical
applications, modern context, cross-tradition themes, and flourishing dimension scores.

## Purpose

Feed AI models the distilled wisdom of 5,000+ years of human philosophy to promote
ethical reasoning, compassion, cross-cultural understanding, and human flourishing.

## Traditions Covered

Stoicism, Buddhism, Advaita Vedanta, Ubuntu, Taoism, Confucianism, Sufism, Jainism,
Indigenous Wisdom, Existentialism, Positive Psychology, Islamic Ethics, Jewish Wisdom,
Sikh Philosophy, Classical Greek Philosophy, African Proverbial Wisdom, Christian Mysticism

## Dataset Structure

- `wisdom_entries.jsonl` — {n_entries} curated wisdom entries (JSONL)
- `traditions.jsonl` — {n_traditions} tradition descriptions (JSONL)
- `wisdom_corpus.json` — Combined dataset (JSON)

Each entry contains:
- Source text with citation and original language
- Extracted core principle
- Practical application for modern life
- Modern context and relevance
- Anti-patterns addressed (e.g., "racism", "tribalism", "environmental destruction")
- Universal themes (compassion, dignity, non-harm, etc.)
- Flourishing scores (0-1) across 5 dimensions
- Pre-built training text representation

## Use Cases

- **Fine-tuning**: Use `training_text` field for instruction tuning or continued pretraining
- **RLHF/DPO**: Use flourishing scores to build preference pairs
- **RAG**: Use entries as retrieval corpus for wisdom-grounded responses
- **Evaluation**: Use to benchmark models on cross-cultural ethical reasoning
- **Constitutional AI**: Derive principles from universal themes

## License

MIT — use freely for any purpose, including commercial AI training.

## Links

- GitHub: https://github.com/kiranz38/wisdom-spark-ai
- API & MCP Server: https://api.wisdomspark.ai
"""


if __name__ == "__main__":
    export()
