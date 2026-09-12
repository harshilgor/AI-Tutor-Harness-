from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import GraphJob, GraphVersion, JobStatus, TopicScope
from .session_models import ActionEvent, LearningSession, LessonArtifact, RunStatus


class Store:
    """Small local persistence adapter.

    SQLite keeps the first slice runnable without external services. Its
    repository interface is intentionally narrow so PostgreSQL can replace it
    without changing API or domain code.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS topic_scopes (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS graph_jobs (
                id TEXT PRIMARY KEY,
                scope_id TEXT NOT NULL REFERENCES topic_scopes(id),
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS graph_versions (
                id TEXT PRIMARY KEY,
                scope_id TEXT NOT NULL REFERENCES topic_scopes(id),
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL REFERENCES graph_versions(id),
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learning_actions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES learning_sessions(id),
                idempotency_key TEXT,
                payload TEXT NOT NULL,
                UNIQUE(session_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS lesson_artifacts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES learning_sessions(id),
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS action_events (
                id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL REFERENCES learning_actions(id),
                sequence INTEGER NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(action_id, sequence)
            );
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def save_scope(self, scope: TopicScope) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO topic_scopes(id, payload) VALUES(?, ?)",
            (scope.id, scope.model_dump_json()),
        )
        self._connection.commit()

    def get_scope(self, scope_id: str) -> TopicScope | None:
        row = self._connection.execute("SELECT payload FROM topic_scopes WHERE id = ?", (scope_id,)).fetchone()
        return TopicScope.model_validate_json(row["payload"]) if row else None

    def save_job(self, job: GraphJob) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO graph_jobs(id, scope_id, payload) VALUES(?, ?, ?)",
            (job.id, job.scope_id, job.model_dump_json()),
        )
        self._connection.commit()

    def get_job(self, job_id: str) -> GraphJob | None:
        row = self._connection.execute("SELECT payload FROM graph_jobs WHERE id = ?", (job_id,)).fetchone()
        return GraphJob.model_validate_json(row["payload"]) if row else None

    def save_graph(self, graph: GraphVersion) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO graph_versions(id, scope_id, payload) VALUES(?, ?, ?)",
            (graph.id, graph.scope_id, graph.model_dump_json()),
        )
        self._connection.commit()

    def get_graph(self, graph_id: str) -> GraphVersion | None:
        row = self._connection.execute("SELECT payload FROM graph_versions WHERE id = ?", (graph_id,)).fetchone()
        return GraphVersion.model_validate_json(row["payload"]) if row else None

    def save_session(self, session: LearningSession) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO learning_sessions(id, graph_id, payload) VALUES(?, ?, ?)",
            (session.id, session.graph_id, session.model_dump_json()),
        )
        self._connection.commit()

    def get_session(self, session_id: str) -> LearningSession | None:
        row = self._connection.execute("SELECT payload FROM learning_sessions WHERE id = ?", (session_id,)).fetchone()
        return LearningSession.model_validate_json(row["payload"]) if row else None

    def save_action(self, action: RunStatus, idempotency_key: str | None = None) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO learning_actions(id, session_id, idempotency_key, payload) VALUES(?, ?, ?, ?)",
            (action.run_id, action.session_id, idempotency_key, action.model_dump_json()),
        )
        self._connection.commit()

    def get_action(self, action_id: str) -> RunStatus | None:
        row = self._connection.execute("SELECT payload FROM learning_actions WHERE id = ?", (action_id,)).fetchone()
        return RunStatus.model_validate_json(row["payload"]) if row else None

    def get_action_by_idempotency(self, session_id: str, idempotency_key: str) -> RunStatus | None:
        row = self._connection.execute(
            "SELECT payload FROM learning_actions WHERE session_id = ? AND idempotency_key = ?",
            (session_id, idempotency_key),
        ).fetchone()
        return RunStatus.model_validate_json(row["payload"]) if row else None

    def save_artifact(self, artifact: LessonArtifact) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO lesson_artifacts(id, session_id, payload) VALUES(?, ?, ?)",
            (artifact.id, artifact.session_id, artifact.model_dump_json()),
        )
        self._connection.commit()

    def get_artifact(self, artifact_id: str) -> LessonArtifact | None:
        row = self._connection.execute("SELECT payload FROM lesson_artifacts WHERE id = ?", (artifact_id,)).fetchone()
        return LessonArtifact.model_validate_json(row["payload"]) if row else None

    def save_event(self, event: ActionEvent) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO action_events(id, action_id, sequence, payload) VALUES(?, ?, ?, ?)",
            (event.id, event.action_id, event.sequence, event.model_dump_json()),
        )
        self._connection.commit()

    def list_events(self, action_id: str) -> list[ActionEvent]:
        rows = self._connection.execute(
            "SELECT payload FROM action_events WHERE action_id = ? ORDER BY sequence ASC", (action_id,)
        ).fetchall()
        return [ActionEvent.model_validate_json(row["payload"]) for row in rows]
