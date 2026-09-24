"use client";

import type { VisualizationSpec } from '@/lib/visualization-spec';
import styles from './visualization.module.css';

export function TimelineRenderer({ spec }: { spec: VisualizationSpec }) {
  const events = [...spec.events].sort((a, b) => a.order - b.order);
  return <ol className={styles.timeline} aria-label={spec.title}>
    {events.map((event, i) => <li key={i} className={event.emphasis ? styles.timelineEmphasis : undefined}>
      <span className={styles.timelineDate}>{event.date}</span>
      <div><strong>{event.title}</strong>{event.category && <small>{event.category}</small>}
        {event.description && <p>{event.description}</p>}</div>
    </li>)}
  </ol>;
}
