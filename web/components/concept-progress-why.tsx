"use client";

import { useEffect, useState } from 'react';
import { learningApi, type ConceptStateExplanation, type TimelineEntry } from '@/lib/api';
import styles from './learn-chat.module.css';

/** Compact ordinal Progress / Why surface — never percentages. */
export function ConceptProgressWhy({ conceptId, enabled = true }: { conceptId?: string | null; enabled?: boolean }) {
  const [explanation, setExplanation] = useState<ConceptStateExplanation | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!enabled || !conceptId) return;
    let active = true;
    void (async () => {
      try {
        const [why, page] = await Promise.all([
          learningApi.getConceptExplanation(conceptId),
          learningApi.getLearnerTimeline({ limit: 8 }),
        ]);
        if (!active) return;
        setExplanation(why);
        setTimeline(page.entries.filter(entry => !entry.conceptId || entry.conceptId === conceptId).slice(0, 5));
        setError('');
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : 'Progress could not be loaded.');
      }
    })();
    return () => { active = false; };
  }, [conceptId, enabled]);

  if (!conceptId || !enabled) return null;
  if (error) return <p className={styles.hint} role="status">{error}</p>;
  if (!explanation) return null;

  const status = explanation.state.status;
  const dueReason = explanation.review?.dueReason;
  return (
    <details className={styles.sources}>
      <summary>Progress · Why this standing</summary>
      <p className={styles.hint}>
        Current standing: <strong>{status}</strong>
        {dueReason ? ` · Next review: ${dueReason}` : null}
      </p>
      <p className={styles.hint}>{explanation.rationale}</p>
      {explanation.admittedEvidence.length ? (
        <ul className={styles.hint}>
          {explanation.admittedEvidence.slice(0, 4).map(item => (
            <li key={item.id}>{item.condition} {item.outcome} · {item.kind}</li>
          ))}
        </ul>
      ) : <p className={styles.hint}>No admitted evidence yet for this concept.</p>}
      {timeline.length ? (
        <>
          <p className={styles.hint}>Recent activity</p>
          <ul className={styles.hint}>
            {timeline.map(entry => <li key={entry.id}>{entry.summary}</li>)}
          </ul>
        </>
      ) : null}
    </details>
  );
}
