"""M-PRUNE-01: context is a token budget, not a fixed image count or a 20000-character cut."""
from __future__ import annotations

from app.context import (
    IMAGE_TOKENS,
    clip_text,
    context_token_budget,
    message_tokens,
    prune_messages,
    recon_token_budget,
    usage_delta,
)


def test_clip_text_follows_the_token_budget() -> None:
    clipped = clip_text("x" * 1000, 100)
    assert len(clipped) <= 200
    assert clipped.endswith("[clipped to the token budget]")
    assert clip_text("short", 100) == "short"


def test_prune_keeps_the_newest_image_that_fits() -> None:
    messages = [
        {"role": "user", "content": [{"type": "image", "source": {"data": "old"}}, {"type": "text", "text": "one"}]},
        {"role": "user", "content": [{"type": "image", "source": {"data": "new"}}, {"type": "text", "text": "two"}]},
    ]
    estimate = prune_messages(messages, IMAGE_TOKENS + 40)
    assert messages[0]["content"][0]["type"] == "text"
    assert messages[1]["content"][0]["type"] == "image"
    assert estimate <= IMAGE_TOKENS + 40
    assert message_tokens(messages) == estimate


def test_usage_delta_reads_both_provider_shapes() -> None:
    assert usage_delta({"prompt_tokens": 10, "completion_tokens": 4}) == {
        "prompt_tokens": 10, "completion_tokens": 4}
    assert usage_delta(None) == {}

    class _Usage:
        input_tokens = 3
        output_tokens = 1

    assert usage_delta(_Usage()) == {"prompt_tokens": 3, "completion_tokens": 1}


def test_budgets_have_defaults(monkeypatch) -> None:
    monkeypatch.delenv("SAQR_CONTEXT_TOKENS", raising=False)
    monkeypatch.delenv("SAQR_RECON_TOKENS", raising=False)
    assert context_token_budget() == 24000
    assert recon_token_budget() == 8000
    monkeypatch.setenv("SAQR_RECON_TOKENS", "nope")
    assert recon_token_budget() == 8000
