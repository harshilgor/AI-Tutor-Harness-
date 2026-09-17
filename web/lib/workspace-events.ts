export type WorkspaceNoteSeed = {
  id: string;
  title: string;
  body: string;
  frontmatter: Record<string, unknown>;
};

export const WORKSPACE_NOTE_SEED_EVENT = 'forma:workspace-note-seed';
export const WORKSPACE_NOTE_OPEN_EVENT = 'forma:workspace-note-open';
export const WORKSPACE_NOTE_MENTION_EVENT = 'forma:workspace-note-mention';
export const WORKSPACE_NOTE_REPLACE_DRAFT_EVENT = 'forma:workspace-note-replace-draft';
export const WORKSPACE_SOURCE_OPEN_EVENT = 'forma:workspace-source-open';

export type WorkspaceNoteMention = { noteId: string; title: string; revision: number; startOffset: number; endOffset: number; excerpt: string };

/**
 * An explicit, local UI boundary between a lesson and the learner-owned vault.
 * The note panel decides whether an unsaved editor can be replaced.
 */
export function openWorkspaceNoteDraft(input: Omit<WorkspaceNoteSeed, 'id'>): void {
  window.dispatchEvent(new CustomEvent<WorkspaceNoteSeed>(WORKSPACE_NOTE_SEED_EVENT, {
    detail: { ...input, id: crypto.randomUUID() },
  }));
}

/** Focus an existing note from a chat-context receipt without copying it. */
export function openWorkspaceNote(noteId: string): void {
  window.dispatchEvent(new CustomEvent<string>(WORKSPACE_NOTE_OPEN_EVENT, { detail: noteId }));
}

/** Add an explicit selected note excerpt to the current chat context. */
export function mentionWorkspaceNoteExcerpt(input: WorkspaceNoteMention): void {
  window.dispatchEvent(new CustomEvent<WorkspaceNoteMention>(WORKSPACE_NOTE_MENTION_EVENT, { detail: input }));
}

/** Request a draft that can replace an explicitly selected, saved note section. */
export function createWorkspaceNoteReplacementDraft(input: { noteId: string; title: string; revision: number; startOffset: number; endOffset: number }): void {
  window.dispatchEvent(new CustomEvent(WORKSPACE_NOTE_REPLACE_DRAFT_EVENT, { detail: input }));
}

/** Focus a learner-owned material passage without altering the chat thread. */
export function openWorkspaceSource(input: { spanId: string; versionId?: string; title?: string }): void {
  window.dispatchEvent(new CustomEvent(WORKSPACE_SOURCE_OPEN_EVENT, { detail: input }));
}
