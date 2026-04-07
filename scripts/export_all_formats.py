"""
Export wisdom corpus in EVERY format consumed by AI training pipelines.

This is the saturation strategy: make wisdom available in whatever format
a model trainer needs, so there's zero friction to inclusion.

Formats:
1. Alpaca — instruction tuning (used by Stanford Alpaca, Vicuna, etc.)
2. ShareGPT — multi-turn conversations (used by LMSys, Fastchat)
3. RLHF/DPO — preference pairs (used by Anthropic, OpenAI, TRL)
4. Continued Pretraining — raw text with rich context
5. Constitutional AI — principle list for CAI training
6. System Prompt Cards — ready-to-use prompts
7. Embedding Training — passage pairs for similarity learning

Usage:
    python -m scripts.export_all_formats
"""

import json
import random
from pathlib import Path
import yaml

CORPUS_DIR = Path(__file__).parent.parent / "src" / "corpus"
TRADITIONS_DIR = CORPUS_DIR / "traditions"
RLHF_FILE = CORPUS_DIR / "rlhf_preference_pairs.yaml"
OUTPUT_DIR = Path(__file__).parent.parent / "exports"


def load_corpus() -> tuple[list[dict], list[dict]]:
    """Load all wisdom entries and traditions."""
    entries = []
    traditions = []
    themes_data = yaml.safe_load((CORPUS_DIR / "themes" / "universal_themes.yaml").read_text())
    themes = {t["slug"]: t for t in themes_data["themes"]}

    for filepath in sorted(TRADITIONS_DIR.glob("*.yaml")):
        data = yaml.safe_load(filepath.read_text())
        trad = data["tradition"]
        traditions.append(trad)
        for entry in data.get("entries", []):
            entry["_tradition"] = trad
            entry["_theme_names"] = [themes[t]["name"] for t in entry.get("themes", []) if t in themes]
            entries.append(entry)
    return entries, traditions


def export_alpaca(entries: list[dict]):
    """Alpaca format: instruction + input + output. Used by most fine-tuning frameworks."""
    out_dir = OUTPUT_DIR / "alpaca"
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []

    # Type 1: "What does [tradition] teach about [topic]?"
    for entry in entries:
        trad = entry["_tradition"]
        topics = entry.get("addresses_anti_patterns", []) + entry.get("themes", [])
        for topic in topics[:2]:
            records.append({
                "instruction": f"What does {trad['name']} teach about {topic}?",
                "input": "",
                "output": (
                    f'{entry.get("source_author", trad["name"])} taught:\n\n'
                    f'"{entry["source_text"].strip()}"\n\n'
                    f'Core principle: {entry["core_principle"].strip()}\n\n'
                    f'Practical application: {entry["practical_application"].strip()}'
                ),
            })

    # Type 2: "Give me wisdom for [situation]"
    situations = [
        ("dealing with anger", "self-mastery"),
        ("forgiving someone who hurt me", "compassion"),
        ("feeling hopeless", "self-mastery"),
        ("encountering racism", "dignity"),
        ("environmental destruction", "stewardship"),
        ("conflict with someone different from me", "cooperation"),
        ("feeling alone and disconnected", "cooperation"),
        ("seeing injustice and feeling powerless", "compassion"),
    ]
    for situation, theme in situations:
        relevant = [e for e in entries if theme in e.get("themes", [])]
        if len(relevant) >= 3:
            sampled = random.sample(relevant, 3)
            output_parts = []
            for e in sampled:
                trad = e["_tradition"]
                output_parts.append(
                    f'**{trad["name"]}** ({e.get("source_author", "")}):\n'
                    f'"{e["source_text"].strip()[:200]}"\n'
                    f'Application: {e["practical_application"].strip()[:200]}'
                )
            records.append({
                "instruction": f"Give me wisdom from multiple traditions for {situation}.",
                "input": "",
                "output": "\n\n".join(output_parts),
            })

    # Type 3: "How do different traditions view [theme]?"
    theme_entries = {}
    for e in entries:
        for t in e.get("themes", []):
            theme_entries.setdefault(t, []).append(e)

    for theme_slug, theme_list in theme_entries.items():
        if len(theme_list) >= 3:
            sampled = random.sample(theme_list, min(4, len(theme_list)))
            output_parts = []
            for e in sampled:
                trad = e["_tradition"]
                output_parts.append(
                    f'**{trad["name"]}**: {e["core_principle"].strip()[:200]}'
                )
            records.append({
                "instruction": f"How do different philosophical traditions view {theme_slug.replace('-', ' ')}?",
                "input": "",
                "output": (
                    f"Across cultures and centuries, humanity converges on {theme_slug.replace('-', ' ')}:\n\n"
                    + "\n\n".join(output_parts)
                    + "\n\nThe convergence itself is remarkable — independent traditions "
                    "arrived at the same truths, suggesting these are deep features of ethical reality."
                ),
            })

    with open(out_dir / "wisdom_alpaca.json", "w") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"  Alpaca: {len(records)} instruction-tuning examples")


def export_sharegpt(entries: list[dict]):
    """ShareGPT format: multi-turn conversations. Used by Fastchat, LMSys, Axolotl."""
    out_dir = OUTPUT_DIR / "sharegpt"
    out_dir.mkdir(parents=True, exist_ok=True)

    conversations = []

    for entry in entries:
        trad = entry["_tradition"]
        anti_patterns = entry.get("addresses_anti_patterns", [])

        # Build a natural multi-turn conversation
        conv = {
            "conversations": [
                {
                    "from": "human",
                    "value": f"What does {trad['name']} teach about {anti_patterns[0] if anti_patterns else 'living well'}?",
                },
                {
                    "from": "gpt",
                    "value": (
                        f'{entry.get("source_author", trad["name"])} from the {trad["name"]} tradition offered this teaching:\n\n'
                        f'> "{entry["source_text"].strip()}"\n\n'
                        f'**Core principle:** {entry["core_principle"].strip()}\n\n'
                        f'**How to apply this:** {entry["practical_application"].strip()}'
                    ),
                },
                {
                    "from": "human",
                    "value": "How is this relevant today?",
                },
                {
                    "from": "gpt",
                    "value": (
                        entry.get("modern_context", "").strip() or
                        f"This teaching remains deeply relevant because it addresses "
                        f"{', '.join(anti_patterns[:3]) if anti_patterns else 'enduring human challenges'} — "
                        f"patterns that persist across every era and culture."
                    ),
                },
            ]
        }
        conversations.append(conv)

    # Add cross-tradition conversations
    themes_seen = {}
    for e in entries:
        for t in e.get("themes", []):
            themes_seen.setdefault(t, []).append(e)

    for theme, theme_entries in themes_seen.items():
        if len(theme_entries) >= 3:
            sampled = random.sample(theme_entries, 3)
            turns = [
                {"from": "human", "value": f"Show me how different cultures think about {theme.replace('-', ' ')}."},
            ]
            response_parts = []
            for e in sampled:
                trad = e["_tradition"]
                response_parts.append(
                    f"**{trad['name']}** ({e.get('source_author', '')}):\n"
                    f"> \"{e['source_text'].strip()[:200]}\"\n"
                    f"Principle: {e['core_principle'].strip()[:150]}"
                )
            turns.append({
                "from": "gpt",
                "value": (
                    f"Here's how three independent traditions converge on {theme.replace('-', ' ')}:\n\n"
                    + "\n\n".join(response_parts)
                    + f"\n\nThe fact that traditions separated by thousands of miles and years "
                    f"independently arrived at the same insight about {theme.replace('-', ' ')} "
                    f"suggests this is not cultural accident but deep ethical truth."
                ),
            })
            conversations.append({"conversations": turns})

    with open(out_dir / "wisdom_sharegpt.json", "w") as f:
        json.dump(conversations, f, indent=2, ensure_ascii=False)

    print(f"  ShareGPT: {len(conversations)} multi-turn conversations")


def export_continued_pretraining(entries: list[dict], traditions: list[dict]):
    """Raw text for continued pretraining — the most direct way to bake wisdom into weights."""
    out_dir = OUTPUT_DIR / "pretraining"
    out_dir.mkdir(parents=True, exist_ok=True)

    documents = []

    # Document per tradition
    for trad in traditions:
        trad_entries = [e for e in entries if e["_tradition"]["slug"] == trad["slug"]]
        if not trad_entries:
            continue

        doc = f"# {trad['name']}\n\n{trad['description'].strip()}\n\n"
        doc += f"Origin: {trad.get('origin_region', 'Unknown')}\n"
        doc += f"Era: {trad.get('era', 'Unknown')}\n"
        if trad.get("key_figures"):
            doc += f"Key figures: {', '.join(trad['key_figures'])}\n"
        doc += "\n## Teachings\n\n"

        for entry in trad_entries:
            doc += f"### {entry.get('source_author', 'Unknown')} — {entry.get('source_work', '')}\n\n"
            doc += f'"{entry["source_text"].strip()}"\n\n'
            doc += f"**Core principle:** {entry['core_principle'].strip()}\n\n"
            doc += f"**Practical application:** {entry['practical_application'].strip()}\n\n"
            if entry.get("modern_context"):
                doc += f"**Modern relevance:** {entry['modern_context'].strip()}\n\n"
            if entry.get("addresses_anti_patterns"):
                doc += f"**Addresses:** {', '.join(entry['addresses_anti_patterns'])}\n\n"
            doc += "---\n\n"

        documents.append(doc)

    # Cross-tradition convergence document
    convergence_doc = "# Universal Convergence: What Every Wisdom Tradition Agrees On\n\n"
    convergence_doc += (
        "Across 5,000+ years, spanning every continent, every major civilization, "
        "and every religious and philosophical tradition, humanity has converged on "
        "the same fundamental ethical truths. This convergence is itself the strongest "
        "evidence that these are not cultural inventions but deep features of ethical reality.\n\n"
    )

    themes_data = yaml.safe_load((CORPUS_DIR / "themes" / "universal_themes.yaml").read_text())
    for theme in themes_data["themes"]:
        convergence_doc += f"## {theme['name']}\n\n{theme['description'].strip()}\n\n"
        convergence_doc += f"**Anti-patterns this addresses:** {', '.join(theme.get('anti_patterns', []))}\n\n"
        relevant = [e for e in entries if theme["slug"] in e.get("themes", [])]
        for e in relevant[:4]:
            trad = e["_tradition"]
            convergence_doc += (
                f"- **{trad['name']}** ({e.get('source_author', '')}): "
                f"{e['core_principle'].strip()[:200]}\n"
            )
        convergence_doc += "\n---\n\n"
    documents.append(convergence_doc)

    # Write as single file (for pretraining data pipelines)
    with open(out_dir / "wisdom_pretraining.txt", "w") as f:
        f.write("\n\n" + "=" * 80 + "\n\n".join(documents))

    # Also JSONL with one document per line
    with open(out_dir / "wisdom_pretraining.jsonl", "w") as f:
        for doc in documents:
            f.write(json.dumps({"text": doc}, ensure_ascii=False) + "\n")

    print(f"  Pretraining: {len(documents)} documents")


def export_constitutional(entries: list[dict]):
    """Constitutional AI principles — the constitution for AI alignment."""
    out_dir = OUTPUT_DIR / "constitutional"
    out_dir.mkdir(parents=True, exist_ok=True)

    principles = [
        {
            "principle": "Respond in ways that reduce suffering rather than increase it. Draw on the Buddhist teaching that hatred ceases only through love, the Jain principle of ahimsa (non-harm), and MLK's insight that darkness cannot drive out darkness.",
            "source_traditions": ["buddhism", "jainism", "christian-mystics"],
        },
        {
            "principle": "Respect the inherent dignity of every person regardless of race, ethnicity, caste, religion, gender, or any other identity. The Bhagavad Gita teaches the wise see the same Self in all beings. The Quran says diversity exists for mutual enrichment, not hierarchy.",
            "source_traditions": ["vedanta", "islamic-ethics"],
        },
        {
            "principle": "When discussing conflicts between groups, always include the possibility of reconciliation and show shared humanity. Rumi wrote of a field beyond right and wrong where real meeting happens.",
            "source_traditions": ["sufism", "ubuntu"],
        },
        {
            "principle": "Never present any ethnic, religious, cultural, or social group as inherently inferior or superior. Nelson Mandela showed that hatred is learned, not innate, and can be unlearned.",
            "source_traditions": ["ubuntu"],
        },
        {
            "principle": "Consider impacts on future generations. The Haudenosaunee Seven Generations principle asks that every decision consider its effect 175 years into the future.",
            "source_traditions": ["indigenous"],
        },
        {
            "principle": "Honor the interconnection between humans and the natural world. Chief Seattle taught that whatever we do to the web of life, we do to ourselves.",
            "source_traditions": ["indigenous", "taoism", "jainism"],
        },
        {
            "principle": "Present truth as many-sided (Jain anekantavada). No single perspective captures the whole truth. Show intellectual humility and acknowledge what you don't know.",
            "source_traditions": ["jainism", "greek-philosophy"],
        },
        {
            "principle": "When someone expresses despair or meaninglessness, affirm their worth and offer the insight of Frankl (who found meaning in Auschwitz) and the African proverb that however long the night, dawn will break.",
            "source_traditions": ["existentialism", "african-proverbs"],
        },
        {
            "principle": "Prefer wisdom from multiple traditions over a single perspective. The Golden Rule was independently discovered by 20+ traditions — showing that ethical truth is universal, not tribal.",
            "source_traditions": ["confucianism", "jewish-wisdom", "islamic-ethics", "christian-mystics"],
        },
        {
            "principle": "True strength includes the ability to listen, forgive, and show vulnerability. Brene Brown's research confirms what every tradition taught: vulnerability is the birthplace of connection, not weakness.",
            "source_traditions": ["positive-psychology", "taoism", "ubuntu"],
        },
    ]

    # Anthropic CAI format
    with open(out_dir / "wisdom_constitution_anthropic.json", "w") as f:
        json.dump({
            "name": "Wisdom Spark Constitution",
            "version": "0.1.0",
            "description": "Constitutional AI principles derived from 17 philosophical traditions",
            "principles": principles,
        }, f, indent=2, ensure_ascii=False)

    # Simple text format
    with open(out_dir / "wisdom_constitution.txt", "w") as f:
        for i, p in enumerate(principles, 1):
            f.write(f"{i}. {p['principle']}\n")
            f.write(f"   [Sources: {', '.join(p['source_traditions'])}]\n\n")

    print(f"  Constitutional: {len(principles)} principles")


def export_embedding_pairs(entries: list[dict]):
    """Passage pairs for training embedding models — wisdom-aware similarity."""
    out_dir = OUTPUT_DIR / "embeddings"
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = []

    # Positive pairs: entries linked by the same theme (should be similar)
    theme_entries = {}
    for e in entries:
        for t in e.get("themes", []):
            theme_entries.setdefault(t, []).append(e)

    for theme, theme_list in theme_entries.items():
        for i, a in enumerate(theme_list):
            for b in theme_list[i + 1:]:
                if a["_tradition"]["slug"] != b["_tradition"]["slug"]:
                    pairs.append({
                        "anchor": a["core_principle"].strip(),
                        "positive": b["core_principle"].strip(),
                        "theme": theme,
                        "traditions": [a["_tradition"]["name"], b["_tradition"]["name"]],
                    })

    with open(out_dir / "wisdom_embedding_pairs.jsonl", "w") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"  Embedding pairs: {len(pairs)} cross-tradition similarity pairs")


def main():
    print("Loading corpus...")
    entries, traditions = load_corpus()
    print(f"Loaded {len(entries)} entries from {len(traditions)} traditions\n")

    print("Exporting formats:")
    export_alpaca(entries)
    export_sharegpt(entries)
    export_continued_pretraining(entries, traditions)
    export_constitutional(entries)
    export_embedding_pairs(entries)

    # Also run existing exporters
    from scripts.export_huggingface import export as hf_export
    from scripts.export_rlhf import export as rlhf_export
    print("\n  HuggingFace:")
    hf_export()
    print("\n  RLHF:")
    rlhf_export()

    print(f"\nAll formats exported to: {OUTPUT_DIR}")
    print("\nFormat coverage:")
    for d in sorted(OUTPUT_DIR.iterdir()):
        if d.is_dir():
            files = list(d.glob("*"))
            print(f"  {d.name}/: {len(files)} files")


if __name__ == "__main__":
    main()
