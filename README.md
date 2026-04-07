# Wisdom Spark AI

**An open wisdom repository and MCP server feeding AI the distilled wisdom of humanity's philosophical traditions.**

AI models are trained on internet-scale data that includes tribalism, misinformation, and divisive content. Wisdom Spark AI provides the antidote: a curated, structured, machine-readable corpus of humanity's deepest wisdom — from Stoicism to Buddhism, Vedanta to Ubuntu, Taoism to Indigenous knowledge systems — exposed via REST API and MCP server for any AI system to consume.

## The Idea

The antidote to AI toxicity isn't better filters — it's better food. Feed AI the distilled wisdom of 5,000+ years of human beings figuring out how to live well together, and the outputs change fundamentally.

## What's Inside

### 10 Philosophical Traditions

| Tradition | Origin | Key Insight |
|---|---|---|
| **Stoicism** | Greece/Rome | Virtue, self-mastery, shared rational nature |
| **Buddhism** | India/East Asia | Compassion, interdependence, non-attachment |
| **Advaita Vedanta** | India | Non-duality — the same self dwells in all beings |
| **Ubuntu** | Southern Africa | "I am because we are" — communal personhood |
| **Taoism** | China | Harmony with nature, gentle persistence |
| **Confucianism** | China | Social harmony, the Golden Rule, moral cultivation |
| **Sufism** | Middle East/Persia | Divine love, dissolving barriers between self and other |
| **Jainism** | India | Radical non-violence, many-sidedness of truth |
| **Indigenous Wisdom** | Global | Land as kin, Seven Generations thinking, reciprocity |
| **Positive Psychology** | Modern | Scientific validation of ancient wisdom on flourishing |

### 7 Universal Themes

Compassion, Non-Harm (Ahimsa), Human Dignity, Environmental Stewardship, Cooperation, The Golden Rule, Self-Mastery

### 10 MCP Tools

1. `get_wisdom` — Retrieve by topic, tradition, or theme
2. `check_ethical_alignment` — Score text against flourishing dimensions
3. `reframe_divisive_content` — Wisdom-based reframing of harmful content
4. `get_cross_cultural_perspective` — Same topic, multiple traditions
5. `flourishing_score` — 5-dimension scoring (suffering, dignity, cooperation, future, nature)
6. `find_common_ground` — Show convergence across traditions
7. `get_practice` — Actionable exercises for life situations
8. `historical_lesson` — Wisdom about recurring human patterns
9. `list_traditions` — Browse all traditions
10. `list_themes` — Browse universal themes

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL + pgvector
- **MCP Server**: Streamable HTTP transport via FastMCP
- **Embeddings**: OpenAI-compatible API for semantic search
- **Deployment**: Render / Docker

## Getting Started

```bash
# Clone
git clone https://github.com/kiranz38/wisdom-spark-ai.git
cd wisdom-spark-ai

# Setup
cp .env.example .env  # Edit with your database credentials
pip install -e ".[dev]"
pip install pyyaml

# Create database (requires PostgreSQL with pgvector extension)
createdb wisdom_spark
psql wisdom_spark -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Seed the wisdom corpus
python -m scripts.seed_corpus

# Generate embeddings (requires OpenAI API key in .env)
python -m scripts.generate_embeddings

# Run
uvicorn src.app:app --reload
```

**API**: http://localhost:8000/docs
**MCP**: http://localhost:8000/mcp/

## API Endpoints

```
GET  /v1/wisdom/                          — List wisdom (filter by topic, tradition, theme)
POST /v1/wisdom/search                    — Semantic search
GET  /v1/wisdom/{id}                      — Get single entry
GET  /v1/wisdom/{id}/cross-references     — Cross-tradition connections
GET  /v1/wisdom/perspectives/{topic}      — Multi-tradition perspectives
POST /v1/wisdom/flourishing-score         — Score text against flourishing dimensions
GET  /v1/wisdom/traditions/list           — List all traditions
GET  /v1/wisdom/themes/list               — List universal themes
GET  /health                              — Health check
```

## Philosophy

1. **Inclusive, not prescriptive** — No single tradition is "right." The tapestry speaks.
2. **Practical, not academic** — Every piece maps to real situations.
3. **Bridge-building** — Always show common ground. The convergences are powerful.
4. **Life-affirming** — Every output increases respect for life.
5. **Anti-fragile** — The system models what it teaches: openness, humility, growth.

## Contributing

We welcome contributions of wisdom from traditions not yet represented, corrections to existing entries, and code improvements. Every entry needs:

- Source text with citation
- Core principle extracted
- Practical application for modern life
- Cross-references to similar ideas in other traditions
- Flourishing dimension scores

## License

MIT
