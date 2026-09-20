"""Optional provider contract check: RUN_LIVE_PROVIDER_TESTS=true pytest -m live_provider."""
import asyncio
import os

import pytest

from backend.app.model_provider import configured_lesson_provider


@pytest.mark.live_provider
def test_configured_provider_emits_stream_text():
    if os.getenv("RUN_LIVE_PROVIDER_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_LIVE_PROVIDER_TESTS=true to spend a real provider request.")
    provider = configured_lesson_provider()
    if provider is None:
        pytest.skip("No model provider is configured.")

    async def collect():
        chunks = []
        async with asyncio.timeout(60):
            async for chunk in provider.stream_text("Reply with exactly: provider stream works", 40):
                chunks.append(chunk)
        return "".join(chunks)

    assert asyncio.run(collect()).strip()
