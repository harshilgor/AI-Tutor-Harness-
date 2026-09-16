export type WorkspaceNoteSeed = {
  id: string;
  title: string;
  body: string;
  frontmatter: Record<string, unknown>;
};

export const WORKSPACE_NOTE_SEED_EVENT = 'forma:workspace-note-seed';

/**
 * An explicit, local UI boundary between a lesson and the learner-owned vault.
 * The note panel decides whether an unsaved editor can be replaced.
 */
export function openWorkspaceNoteDraft(input: Omit<WorkspaceNoteSeed, 'id'>): void {
  window.dispatchEvent(new CustomEvent<WorkspaceNoteSeed>(WORKSPACE_NOTE_SEED_EVENT, {
    detail: { ...input, id: crypto.randomUUID() },
  }));
}
