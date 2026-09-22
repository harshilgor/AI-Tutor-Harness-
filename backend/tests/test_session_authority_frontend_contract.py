"""Frontend-contract checks for session authority helpers used by restore/routing."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = (ROOT / "web" / "lib" / "learning-workflows.ts").read_text(encoding="utf-8")
LEARN_CHAT = (ROOT / "web" / "components" / "learn-chat.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "web" / "components" / "learning-workspace.tsx").read_text(encoding="utf-8")
ROUTE = (ROOT / "web" / "app" / "s" / "[sessionId]" / "page.tsx").read_text(encoding="utf-8")


def test_session_authority_helpers_are_exported():
    for symbol in (
        "getSessionSnapshot",
        "restoreSessionAuthority",
        "sessionPath",
        "sessionIdFromPath",
        "resolveSessionHint",
        "navigateToSession",
        "isStaleSessionConflict",
    ):
        assert symbol in WORKFLOWS


def test_learn_chat_restores_snapshot_first_and_reconciles_replay_expired():
    assert "restoreSessionAuthority" in LEARN_CHAT
    assert "REPLAY_EXPIRED" in LEARN_CHAT
    assert "isStaleSessionConflict" in LEARN_CHAT
    assert "navigateToSession" in LEARN_CHAT


def test_workspace_uses_stable_session_routes():
    assert "initialSessionId" in WORKSPACE
    assert "navigateToSession" in WORKSPACE
    assert "popstate" in WORKSPACE
    assert "initialSessionId" in ROUTE
    assert "/s/" in WORKFLOWS
