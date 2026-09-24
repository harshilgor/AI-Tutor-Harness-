"use client";

import { useEffect, useMemo, useState } from 'react';
import { learningApi } from '@/lib/api';
import { Visualization } from './visualization';
import styles from './visualization.module.css';

type Reference = { lessonId: string; visualizationId: string; title?: string };
function references(body: string): Reference[] {
  const found: Reference[] = [];
  for (const match of body.matchAll(/```visualization-ref\s*\n([^\n]+)\n```/g)) {
    try {
      const value = JSON.parse(match[1]) as Reference;
      if (/^lesson_[A-Za-z0-9_-]+$/.test(value.lessonId) && /^[A-Za-z0-9_-]+$/.test(value.visualizationId)
        && !found.some(item => item.lessonId === value.lessonId && item.visualizationId === value.visualizationId)) found.push(value);
    } catch { /* A learner may edit Markdown freely. */ }
  }
  return found.slice(0, 12);
}

export function NoteVisualReferences({ body }: { body: string }) {
  const refs = useMemo(() => references(body), [body]);
  const [loaded, setLoaded] = useState<Record<string, unknown>>({});
  useEffect(() => {
    let active = true;
    for (const reference of refs) {
      const key = `${reference.lessonId}:${reference.visualizationId}`;
      void learningApi.getLessonVisualization(reference.lessonId, reference.visualizationId)
        .then(value => { if (active) setLoaded(old => ({ ...old, [key]: value })); })
        .catch(() => { if (active) setLoaded(old => ({ ...old, [key]: null })); });
    }
    return () => { active = false; };
  }, [refs]);
  if (!refs.length) return null;
  return <div className={styles.noteVisuals} aria-label="Lesson visuals saved with this note">
    <strong>Lesson visuals</strong>
    {refs.map(reference => {
      const key = `${reference.lessonId}:${reference.visualizationId}`;
      return <details key={key}><summary>{reference.title || 'Open visualization'}</summary>
        {loaded[key] ? <Visualization value={loaded[key]} lessonId={reference.lessonId}/> : <p>Visualization unavailable or loading.</p>}
      </details>;
    })}
  </div>;
}
