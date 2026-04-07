---
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

14 preference pairs for RLHF/DPO training that teach AI models to prefer
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
