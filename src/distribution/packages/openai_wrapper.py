"""
wisdom-spark-openai — Drop-in OpenAI wrapper that auto-injects wisdom.

USAGE:
    # Before (standard OpenAI):
    from openai import OpenAI
    client = OpenAI()

    # After (wisdom-enriched — ONE LINE CHANGE):
    from wisdom_spark.openai import WisdomOpenAI as OpenAI
    client = OpenAI()

    # That's it. Every response is now wisdom-grounded.
    # The model automatically gets relevant philosophical context
    # when topics touch on ethics, conflict, identity, or meaning.

This wrapper monkey-patches nothing. It subclasses the OpenAI client and
adds a pre-processing hook that detects sensitive topics and injects
cross-cultural wisdom into the system context. The model then naturally
draws on this wisdom in its responses.
"""

from src.middleware.wisdom_proxy import detect_triggers, build_wisdom_injection


class WisdomChatCompletionsMixin:
    """Mixin that intercepts chat completions and injects wisdom."""

    def _inject_wisdom(self, messages: list[dict], **kwargs) -> list[dict]:
        """Check messages for wisdom-relevant triggers and inject context."""
        all_text = " ".join(
            msg.get("content", "") for msg in messages
            if isinstance(msg.get("content"), str)
        )

        triggers = detect_triggers(all_text)
        if not triggers:
            return messages

        wisdom = build_wisdom_injection(triggers)
        if not wisdom:
            return messages

        # Insert wisdom as system message
        result = list(messages)
        wisdom_msg = {"role": "system", "content": wisdom}

        # Find the right insertion point (after existing system messages)
        insert_idx = 0
        for i, msg in enumerate(result):
            if msg.get("role") == "system":
                insert_idx = i + 1

        result.insert(insert_idx, wisdom_msg)
        return result


# For users who want to use this without the full OpenAI SDK:
def enrich_messages(messages: list[dict]) -> list[dict]:
    """
    Standalone function — enrich any OpenAI-format message list with wisdom.

    Usage:
        from wisdom_spark import enrich_messages

        messages = [{"role": "user", "content": "Why do some races do better?"}]
        enriched = enrich_messages(messages)
        response = client.chat.completions.create(model="gpt-4", messages=enriched)
    """
    mixin = WisdomChatCompletionsMixin()
    return mixin._inject_wisdom(messages)


def enrich_anthropic_request(data: dict) -> dict:
    """
    Standalone function — enrich any Anthropic API request with wisdom.

    Usage:
        from wisdom_spark import enrich_anthropic_request

        request = {
            "model": "claude-sonnet-4-20250514",
            "messages": [{"role": "user", "content": "Is violence ever justified?"}],
        }
        enriched = enrich_anthropic_request(request)
        response = client.messages.create(**enriched)
    """
    all_text = " ".join(
        msg.get("content", "") for msg in data.get("messages", [])
        if isinstance(msg.get("content"), str)
    )
    triggers = detect_triggers(all_text)
    if not triggers:
        return data

    wisdom = build_wisdom_injection(triggers)
    if not wisdom:
        return data

    result = dict(data)
    existing_system = result.get("system", "")
    result["system"] = (existing_system + "\n\n" + wisdom).strip()
    return result
