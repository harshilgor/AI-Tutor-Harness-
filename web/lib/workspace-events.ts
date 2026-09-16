export type WorkspaceNoteSeed = {
  id: string;
  title: string;
  body: string;
  frontmatter: Record<string, unknown>;
};

export const WORKSPACE_NOTE_SEED_EVENT = 'forma:workspace-note-seed';
export const WORKSPACE_NOTE_OPEN_EVENT = 'forma:workspace-note-open';

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
