---
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

Curated wisdom from 17 philosophical traditions, structured for AI training
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

- `wisdom_entries.jsonl` — 77 curated wisdom entries (JSONL)
- `traditions.jsonl` — 17 tradition descriptions (JSONL)
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
