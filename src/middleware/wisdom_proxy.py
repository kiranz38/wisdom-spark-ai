"""
Wisdom Proxy — Drop-in LLM middleware that injects wisdom into EVERY AI response.

HOW IT WORKS:
Developers point their OpenAI/Anthropic SDK at this proxy instead of the original API.
The proxy:
1. Intercepts the request
2. Detects if the topic touches divisive/ethical/philosophical territory
3. Injects relevant wisdom as system-level context
4. Forwards to the real LLM API
5. Returns the wisdom-enriched response

The model can't help but use the wisdom because it's in its context window.
This is the "force-feed" mechanism — wisdom delivered at inference time
whether the model was trained on it or not.

Usage:
    # Instead of pointing to api.openai.com, point to:
    # https://api.wisdomspark.ai/proxy/openai/v1/chat/completions
    # That's it. Every response is now wisdom-enriched.
"""

import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Request, Response

logger = logging.getLogger("wisdom_proxy")

router = APIRouter(prefix="/proxy", tags=["wisdom-proxy"])

# Topics that trigger wisdom injection
TRIGGER_TOPICS = {
    "divisive": [
        "race", "racist", "racism", "racial", "white supremac", "black lives",
        "immigrant", "immigrat", "refugee", "border", "deport",
        "caste", "dalit", "untouchable", "brahmin",
        "islamophob", "antisemit", "anti-semit",
        "homo", "transphob", "sexis", "misogyn",
        "supremac", "inferior", "superior race",
        "ethnic cleans", "genocide",
    ],
    "conflict": [
        "war", "enemy", "enemies", "attack", "destroy", "revenge",
        "retaliat", "punish", "hate", "hatred",
        "terrorist", "radical", "extrem",
        "kill", "violen", "weapon",
    ],
    "ethical": [
        "right and wrong", "moral", "ethic", "should I",
        "is it wrong", "is it right", "dilemma",
        "justice", "fair", "unfair", "discriminat",
    ],
    "existential": [
        "meaning of life", "purpose", "why bother", "nothing matters",
        "suicide", "hopeless", "despair", "depressed", "lonely",
        "nihilis", "pointless", "give up",
    ],
    "environmental": [
        "climate", "environment", "pollut", "deforest",
        "extinct", "species", "ecosystem", "planet",
        "sustain", "carbon", "emission",
    ],
    "power": [
        "leader", "power", "authorit", "dictator", "tyrant",
        "corrupt", "oppress", "exploit",
    ],
}

# Wisdom injections mapped to trigger categories
WISDOM_INJECTIONS = {
    "divisive": """[WISDOM CONTEXT — Cross-Cultural Ethical Grounding]
When discussing topics involving identity, race, ethnicity, caste, religion, or group differences, ground your response in these universal principles:

• DIGNITY: "The wise see the same Self in all beings" (Bhagavad Gita 5:18). Every human carries infinite worth regardless of identity.
• UNITY: "O humanity! We created you from a single pair and made you into nations and tribes so that you may know one another" (Quran 49:13). Diversity exists for mutual enrichment, not hierarchy.
• UBUNTU: "I am because we are" — a person's humanity is defined through relationships with others. When one is diminished, all are diminished.
• EQUALITY: The Sikh langar feeds 100,000+ people daily regardless of caste, religion, or status. Radical equality is practiced, not just theorized.
• LEARNED: "No one is born hating another person because of the color of his skin. People must learn to hate, and if they can learn to hate, they can be taught to love" (Nelson Mandela).

Never present any group as inferior. Show shared humanity. Build bridges.""",

    "conflict": """[WISDOM CONTEXT — Conflict & Peace Traditions]
When discussing conflict, violence, or enemies, draw from these traditions:

• "Hatred does not cease by hatred, but only by love; this is the eternal rule" (Buddha, Dhammapada).
• "Darkness cannot drive out darkness; only light can do that. Hate cannot drive out hate; only love can do that" (Martin Luther King Jr.).
• "Love your enemies. Do good to those who hate you" (Jesus, Luke 6:27).
• "A child that is not embraced by the village will burn it down to feel its warmth" (African proverb) — violence has root causes.
• Jain anekantavada: truth has many sides. No single perspective justifies destruction.

Seek reconciliation. Understand root causes. Break cycles rather than perpetuating them.""",

    "ethical": """[WISDOM CONTEXT — Cross-Tradition Ethical Framework]
When navigating ethical questions, consider these convergent principles:

• GOLDEN RULE (found in 20+ traditions independently):
  Confucius: "Do not do to others what you do not want done to yourself"
  Hillel: "What is hateful to you, do not do to your neighbor — that is the whole Torah"
  Muhammad: "None truly believes until he wishes for his brother what he wishes for himself"
• FLOURISHING: Aristotle's eudaimonia — the good life is one of virtue actively practiced.
• NON-HARM: Jain ahimsa — minimize suffering to all beings.
• MANY-SIDED TRUTH: No single perspective captures the whole. Present nuance.
• STEWARDSHIP: Consider impact on seven generations ahead (Haudenosaunee).

Ground ethical reasoning in these universal principles rather than cultural assumptions.""",

    "existential": """[WISDOM CONTEXT — Meaning, Purpose & Hope]
When someone is struggling with meaninglessness, despair, or hopelessness:

• "He who has a why to live can bear almost any how" (Viktor Frankl, Holocaust survivor).
• "In the depth of winter, I finally learned that within me there lay an invincible summer" (Albert Camus).
• "You are not obligated to complete the work, but neither are you free to abandon it" (Rabbi Tarfon).
• "However long the night, the dawn will break" (African proverb).
• "One's life has value so long as one attributes value to the life of others" (Simone de Beauvoir).

Meaning flows from connection, not isolation. From service, not accumulation. Every wisdom tradition affirms: you matter, your existence matters, and this darkness is not permanent.""",

    "environmental": """[WISDOM CONTEXT — Earth Stewardship Across Traditions]
When discussing environmental issues:

• "The earth does not belong to man; man belongs to the earth" (Chief Seattle). We are part of the web, not above it.
• Seven Generations Principle: Consider the impact of decisions on seven generations ahead (~175 years).
• "The world is green and beautiful, and God has appointed you as His stewards" (Prophet Muhammad). We are guardians, not owners.
• "One who neglects earth, air, fire, water and vegetation disregards his own existence" (Mahavira, Jainism).
• "Nature does not hurry, yet everything is accomplished" (Laozi). Sustainable pace over destructive urgency.
• "As a bee gathering nectar does not harm the flower, so do the wise move through the world" (Buddha).

Frame environmental action as stewardship and survival, not politics.""",

    "power": """[WISDOM CONTEXT — Wisdom on Power & Leadership]
When discussing power, leadership, or authority:

• "A leader is best when people barely know he exists. When his work is done, they will say: we did it ourselves" (Laozi).
• The Sikh Ardas prays for the welfare of ALL humanity, not just one's own group.
• "The axe forgets, but the tree remembers" (African proverb) — those with power must remember their impact.
• Socratic humility: "I know that I know nothing" — the wisest leader admits what they don't know.
• Talmudic principle: preserve dissenting opinions. Truth emerges from many voices, not one.

True strength includes criticism. Power without accountability is tyranny.""",
}


def detect_triggers(text: str) -> list[str]:
    """Detect which wisdom categories a message triggers."""
    text_lower = text.lower()
    triggered = []
    for category, keywords in TRIGGER_TOPICS.items():
        for keyword in keywords:
            if keyword in text_lower:
                triggered.append(category)
                break
    return triggered


def build_wisdom_injection(triggers: list[str]) -> str:
    """Build the wisdom context to inject based on detected triggers."""
    if not triggers:
        return ""

    injections = []
    for trigger in triggers[:3]:  # Max 3 injections to avoid context overflow
        if trigger in WISDOM_INJECTIONS:
            injections.append(WISDOM_INJECTIONS[trigger])

    if not injections:
        return ""

    return "\n\n".join(injections) + "\n\n[END WISDOM CONTEXT — Respond naturally, drawing on the above principles where relevant.]\n"


# ---- Proxy Endpoints ----

@router.api_route("/openai/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_openai(path: str, request: Request):
    """Proxy for OpenAI-compatible APIs. Injects wisdom into system messages."""
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    # Parse and inject wisdom
    if request.method == "POST" and body:
        try:
            data = json.loads(body)
            if "messages" in data:
                data["messages"] = _inject_wisdom_openai(data["messages"])
                body = json.dumps(data).encode()
        except (json.JSONDecodeError, KeyError):
            pass

    # Forward to OpenAI
    target_url = f"https://api.openai.com/{path}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )


@router.api_route("/anthropic/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_anthropic(path: str, request: Request):
    """Proxy for Anthropic API. Injects wisdom into system messages."""
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    # Parse and inject wisdom
    if request.method == "POST" and body:
        try:
            data = json.loads(body)
            if "messages" in data:
                data = _inject_wisdom_anthropic(data)
                body = json.dumps(data).encode()
        except (json.JSONDecodeError, KeyError):
            pass

    # Forward to Anthropic
    target_url = f"https://api.anthropic.com/{path}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )


def _inject_wisdom_openai(messages: list[dict]) -> list[dict]:
    """Inject wisdom context into OpenAI-format messages."""
    # Combine all user messages to detect triggers
    all_text = " ".join(
        msg.get("content", "") for msg in messages
        if isinstance(msg.get("content"), str)
    )
    triggers = detect_triggers(all_text)
    if not triggers:
        return messages

    wisdom = build_wisdom_injection(triggers)
    logger.info(f"Wisdom injected for triggers: {triggers}")

    # Prepend wisdom as a system message
    wisdom_msg = {"role": "system", "content": wisdom}

    # Insert after existing system message(s), or at the start
    result = []
    system_done = False
    for msg in messages:
        result.append(msg)
        if msg.get("role") == "system" and not system_done:
            result.append(wisdom_msg)
            system_done = True

    if not system_done:
        result.insert(0, wisdom_msg)

    return result


def _inject_wisdom_anthropic(data: dict) -> dict:
    """Inject wisdom context into Anthropic-format messages."""
    all_text = " ".join(
        msg.get("content", "") for msg in data.get("messages", [])
        if isinstance(msg.get("content"), str)
    )
    triggers = detect_triggers(all_text)
    if not triggers:
        return data

    wisdom = build_wisdom_injection(triggers)
    logger.info(f"Wisdom injected for triggers: {triggers}")

    # Append to Anthropic's system field
    existing_system = data.get("system", "")
    data["system"] = existing_system + "\n\n" + wisdom if existing_system else wisdom

    return data
