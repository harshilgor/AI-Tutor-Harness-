"""Explicit, bounded note context for Ask and Learn.

This service is intentionally separate from retrieval.  It resolves only note
IDs the learner selected, preserves the visible excerpt receipt, and never
searches or silently adds other vault content.
"""

from __future__ import annotations

from .storage import Store
from .session_models import NoteContextInput
from .workspace_note_models import (
    WorkspaceNoteContextEntry,
    WorkspaceNoteContextManifest,
)
from .workspace_note_service import WorkspaceNoteError, WorkspaceNoteService


MAX_NOTE_CONTEXT_CHARACTERS = 6_000
MAX_MANIFEST_CHARACTERS = 12_000


class WorkspaceNoteContextService:
    def __init__(self, store: Store):
        self.notes = WorkspaceNoteService(store)

    def resolve(self, learner_id: str, request: NoteContextInput | None) -> WorkspaceNoteContextManifest:
        if request is None:
            return WorkspaceNoteContextManifest(notes=[], total_characters=0)
        entries: list[WorkspaceNoteContextEntry] = []
        total = 0
        for selection in request.notes:
            note = self.notes.get(learner_id, selection.note_id)
            if selection.expected_revision is not None and selection.expected_revision != note.revision:
                raise WorkspaceNoteError("note_revision_conflict", "A mentioned note changed; review the selected text before sending.", 409)
            body = note.body
            if selection.start_offset is None:
                start, end = 0, len(body)
            else:
                start, end = selection.start_offset, selection.end_offset
                assert end is not None  # enforced by the request contract
                if end > len(body):
                    raise WorkspaceNoteError("invalid_note_excerpt", "The selected note range is outside the current note.", 422)
            excerpt = body[start:end]
            if not excerpt.strip():
                raise WorkspaceNoteError("empty_note_excerpt", "Select a non-empty note excerpt before sending.", 422)
            if len(excerpt) > MAX_NOTE_CONTEXT_CHARACTERS:
                raise WorkspaceNoteError("note_excerpt_too_large", f"Select at most {MAX_NOTE_CONTEXT_CHARACTERS} characters from one note.", 422)
            total += len(excerpt)
            if total > MAX_MANIFEST_CHARACTERS:
                raise WorkspaceNoteError("note_context_too_large", f"Select at most {MAX_MANIFEST_CHARACTERS} note characters in one request.", 422)
            entries.append(WorkspaceNoteContextEntry(
                note_id=note.id, title=note.title, revision=note.revision,
                start_offset=selection.start_offset, end_offset=selection.end_offset,
                text=excerpt,
            ))
        return WorkspaceNoteContextManifest(notes=entries, total_characters=total)
