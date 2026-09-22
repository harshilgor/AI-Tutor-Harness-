"use client";

import { useEffect, useRef, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { learningApi, type NextActionRecommendation, type RecommendationSet } from '@/lib/api';
import styles from './next-action-cards.module.css';

type LocalAction = {
  id: string;
  label: string;
  kind: 'learn' | 'ask' | 'quiz' | 'review' | 'check';
  item?: NextActionRecommendation;
};

function suggestionLabel(item: NextActionRecommendation): string {
  const concept = item.conceptTitle?.trim();
  if (item.pedagogicalAction === 'repair') return concept ? `Try a different approach to ${concept}` : 'Try a different explanation';
  if (item.pedagogicalAction === 'check') return concept ? `Check ${concept}` : 'Check your understanding';
  if (item.actionKind === 'learn') return concept ? `Continue with ${concept}` : (item.title || 'Continue learning');
  if (item.actionKind === 'ask') return concept ? `Ask about ${concept}` : (item.title || 'Ask a follow-up');
  if (item.actionKind === 'quiz') return concept ? `Quiz yourself on ${concept}` : (item.title || 'Quiz this concept');
  if (item.actionKind === 'review') return concept ? `Review ${concept}` : (item.title || 'Review concepts');
  return item.title || 'Continue';
}

export function NextActionCards({ sessionId, enabled, refreshKey, onLearn, onAsk, onQuiz, onReview, onCheck }: {
  sessionId: string; enabled: boolean; refreshKey?: string | number;
  onLearn: (item?: NextActionRecommendation) => void | Promise<void>;
  onAsk: (item: NextActionRecommendation) => void | Promise<void>;
  onQuiz: (item?: NextActionRecommendation) => void | Promise<void>;
  onReview: (item?: NextActionRecommendation) => void | Promise<void>;
  onCheck: () => void;
}) {
  const [set, setSet] = useState<RecommendationSet | null>(null);
  const loaded = useRef<string | null>(null);

  useEffect(() => {
    const requestKey = `${sessionId}:${refreshKey ?? ''}`;
    if (!enabled || loaded.current === requestKey) return;
    let active = true;
    void learningApi.getRecommendations(sessionId).then(next => {
      if (active) { setSet(next); loaded.current = requestKey; }
    }).catch(() => undefined);
    return () => { active = false; };
  }, [enabled, refreshKey, sessionId]);

  useEffect(() => {
    if (!set?.recommendations.length) return;
    for (const item of set.recommendations.slice(0, 3)) {
      void learningApi.recordRecommendationInteraction(item.id, 'impression', 'local', `${set.id}:${item.id}:impression`).catch(() => undefined);
    }
  }, [set]);

  const actions: LocalAction[] = [];
  const primary = set?.recommendations[0];
  if (primary) {
    const kind = primary.pedagogicalAction === 'check' ? 'check' : primary.actionKind;
    actions.push({ id: primary.id, label: suggestionLabel(primary), kind, item: primary });
  } else {
    actions.push({ id: 'continue', label: 'Continue learning', kind: 'learn' });
  }

  const kinds = new Set(actions.map(action => action.kind));
  if (!kinds.has('check')) actions.push({ id: 'check', label: 'Check understanding', kind: 'check' });
  if (!kinds.has('quiz')) actions.push({ id: 'quiz', label: 'Quiz this concept', kind: 'quiz' });
  if (!kinds.has('review')) actions.push({ id: 'review', label: 'Review concepts', kind: 'review' });

  async function select(action: LocalAction) {
    if (action.item) {
      void learningApi.recordRecommendationInteraction(action.item.id, 'selection').catch(() => undefined);
    }
    try {
      if (action.kind === 'check') { onCheck(); return; }
      if (action.kind === 'learn') { await onLearn(action.item); return; }
      if (action.kind === 'ask' && action.item) { await onAsk(action.item); return; }
      if (action.kind === 'quiz') { await onQuiz(action.item); return; }
      if (action.kind === 'review') { await onReview(action.item); return; }
    } catch {
      if (action.item) void learningApi.recordRecommendationInteraction(action.item.id, 'failure').catch(() => undefined);
    }
  }

  return (
    <div className={styles.list} aria-label="Suggested next steps">
      {actions.map(action => (
        <button
          key={action.id}
          type="button"
          className={styles.action}
          disabled={!enabled}
          onClick={() => void select(action)}
        >
          <span>{action.label}</span>
          <ArrowRight size={14} />
        </button>
      ))}
      {primary?.rationale ? <details className={styles.why}>
        <summary>Why this next?</summary>
        <p>{primary.rationale}</p>
      </details> : null}
    </div>
  );
}
