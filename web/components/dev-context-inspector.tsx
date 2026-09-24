"use client";

import { useState } from 'react';
import { request } from '@/lib/api';

type ContextInspection = {
  generationId: string;
  conversationId: string;
  courseId?: string | null;
  mode: string;
  provider: string;
  model: string;
  contextVersion?: string | null;
  providerInputSha256?: string | null;
  providerInputFingerprintKind?: string | null;
  providerInputSerialization?: string | null;
  providerInputStored?: boolean;
  blockDecisions?: { kind: string; source: string; priority: number; required?: boolean; relevanceScore?: number; estimatedTokens: number; sourceIds: string[]; revisions?: string[]; contentSha256: string }[];
  omissionReasons?: { kind: string; source?: string; reason: string; sourceIds?: string[]; omittedSourceIds?: string[]; omittedCount?: number; omittedItemCount?: number; estimatedTokens?: number; remainingTokens?: number; relevanceScore?: number; turnIndexes?: number[] }[];
  included: string[];
  omitted: string[];
  estimatedTokensByBlock: Record<string, number>;
  recentMessageCount?: number | null;
  recentEstimatedTokens?: number | null;
  estimatedInputTokens?: number | null;
  inputBudgetTokens?: number | null;
  exactPromptTokens?: number | null;
  summaryUsed?: boolean | null;
  compactionTriggered?: boolean | null;
};

/** Enabled only in a local development build and guarded again by the API. */
export function DevContextInspector({ generationId }: { generationId: string }) {
  const [inspection, setInspection] = useState<ContextInspection | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);

  if (process.env.NEXT_PUBLIC_AI_TUTOR_DEV_CONTEXT_INSPECTOR !== '1') return null;

  async function inspect() {
    if (open) { setOpen(false); return; }
    setOpen(true);
    if (inspection) return;
    try {
      setInspection(await request<ContextInspection>(`/v1/generations/${encodeURIComponent(generationId)}/context`));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Context metadata is unavailable.');
    }
  }

  return <div className="mt-3 border-t border-border pt-2 text-xs text-muted-foreground">
    <button type="button" onClick={() => void inspect()} aria-expanded={open} className="underline underline-offset-2">Context details</button>
    {open && error && <p role="alert">{error}</p>}
    {open && !inspection && !error && <p>Loading context metadata…</p>}
    {open && inspection && <div className="mt-2 space-y-1">
      <p>Model: {inspection.provider}/{inspection.model} · Mode: {inspection.mode}</p>
      <p>Input: {inspection.exactPromptTokens ?? inspection.estimatedInputTokens ?? 'unknown'} tokens
        {inspection.exactPromptTokens == null ? ' estimated' : ' exact'} · Budget: {inspection.inputBudgetTokens ?? 'unknown'}</p>
      <p>Recent messages: {inspection.recentMessageCount ?? 0} · Summary: {inspection.summaryUsed ? 'included' : 'omitted'}</p>
      <p>Included: {inspection.included.join(', ') || 'none'}</p>
      <p>Omitted: {inspection.omitted.join(', ') || 'none'}</p>
      <p>Context version / provider input SHA-256: {inspection.contextVersion ?? inspection.providerInputSha256 ?? 'unknown'}</p>
      <p>Fingerprint: {inspection.providerInputFingerprintKind ?? 'legacy'} · Serialization: {inspection.providerInputSerialization ?? 'unknown'} · Raw input retained: {inspection.providerInputStored ? 'yes' : 'no'}</p>
      <ul className="list-disc pl-4">
        {inspection.blockDecisions?.map((block, index) => <li key={`${block.kind}-${index}`}>
          {block.kind} from {block.source}: ~{block.estimatedTokens} tokens, priority {block.priority}, relevance {block.relevanceScore ?? 'n/a'}
          {block.sourceIds.length ? ` · ${block.sourceIds.join(', ')}` : ''}
          {block.revisions?.length ? ` · revisions ${block.revisions.join(', ')}` : ''}
          {` · content SHA-256 ${block.contentSha256}`}
        </li>)}
      </ul>
      {!!inspection.omissionReasons?.length && <ul className="list-disc pl-4">{inspection.omissionReasons.map((item, index) => <li key={`${item.kind}-${index}`}>
        Omitted {item.kind} from {item.source ?? 'conversation'}: {item.reason}
        {item.omittedCount != null ? ` · ${item.omittedCount} turns (indexes ${item.turnIndexes?.join(', ') ?? ''})` : ''}
        {item.omittedItemCount != null ? ` · ${item.omittedItemCount} items` : ''}
        {(item.omittedSourceIds?.length ?? 0) ? ` · source IDs ${item.omittedSourceIds!.join(', ')}` : ''}
        {(item.sourceIds?.length ?? 0) ? ` · source IDs ${item.sourceIds!.join(', ')}` : ''}
        {item.estimatedTokens != null ? ` · ~${item.estimatedTokens} tokens; ${item.remainingTokens ?? 0} remained` : ''}
        {item.relevanceScore != null ? ` · relevance ${item.relevanceScore}` : ''}
      </li>)}</ul>}
      <ul className="list-disc pl-4">
        {Object.entries(inspection.estimatedTokensByBlock).map(([kind, tokens]) => <li key={kind}>{kind}: ~{tokens} tokens</li>)}
      </ul>
    </div>}
  </div>;
}
