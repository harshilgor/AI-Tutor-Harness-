"use client";

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { ArrowRight, BookOpen, CircleHelp, ClipboardCheck, RotateCcw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { learningApi, type NextActionRecommendation, type RecommendationSet } from '@/lib/api';
import styles from './next-action-cards.module.css';

const icons = { learn: BookOpen, ask: CircleHelp, quiz: ClipboardCheck, review: RotateCcw };

export function NextActionCards({ sessionId, enabled, onLearn, onAsk, onQuiz, onReview }: {
  sessionId: string; enabled: boolean;
  onLearn: (item: NextActionRecommendation) => void | Promise<void>;
  onAsk: (item: NextActionRecommendation) => void | Promise<void>;
  onQuiz: (item: NextActionRecommendation) => void | Promise<void>;
  onReview: (item: NextActionRecommendation) => void | Promise<void>;
}) {
  const reduceMotion = useReducedMotion();
  const [set, setSet] = useState<RecommendationSet | null>(null);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState(false);
  const loaded = useRef<string | null>(null);
  useEffect(() => {
    if (!enabled || loaded.current === sessionId) return;
    let active = true;
    void learningApi.getRecommendations(sessionId).then(next => { if (active) { setSet(next); loaded.current = sessionId; } }).catch(() => undefined);
    return () => { active = false; };
  }, [enabled, sessionId]);
  useEffect(() => {
    if (!set) return;
    for (const item of set.recommendations) {
      void learningApi.recordRecommendationInteraction(item.id, 'impression', 'local', `${set.id}:${item.id}:impression`).catch(() => undefined);
    }
  }, [set]);
  if (!set) return null;
  const visible = set.recommendations.filter(item => !dismissed.has(item.id));
  if (!visible.length) return null;
  function interaction(id: string, eventType: 'selection' | 'dismissal' | 'failure') {
    void learningApi.recordRecommendationInteraction(id, eventType).catch(() => undefined);
  }
  async function select(item: NextActionRecommendation) {
    interaction(item.id, 'selection');
    try {
      await ({ learn: onLearn, ask: onAsk, quiz: onQuiz, review: onReview }[item.actionKind])(item);
    } catch { interaction(item.id, 'failure'); }
  }
  return <section className={styles.section} aria-label="Suggested next actions">
    <div className={styles.heading}><div><span>WHAT NEXT</span><h2>Choose your next step</h2></div><Button variant="ghost" size="sm" onClick={() => setExpanded(value => !value)}>{expanded ? 'Fewer details' : 'Why these?'}</Button></div>
    <div className={styles.cards}><AnimatePresence initial={false}>{visible.map((item, index) => {
      const Icon = icons[item.actionKind];
      return <motion.article className={styles.card} key={item.id} layout={!reduceMotion} initial={reduceMotion ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={reduceMotion ? undefined : { opacity: 0, scale: 0.96 }} transition={{ duration: 0.18, delay: reduceMotion ? 0 : index * 0.05, ease: 'easeOut' }}>
        <div className={styles.cardTop}><Icon size={17} /><button type="button" aria-label={`Dismiss ${item.title}`} onClick={() => { setDismissed(current => new Set(current).add(item.id)); interaction(item.id, 'dismissal'); }}><X size={15} /></button></div>
        <h3>{item.title}</h3><p>{item.rationale}</p>
        {expanded ? <dl><div><dt>Concept</dt><dd>{item.conceptTitle}</dd></div><div><dt>Time</dt><dd>About {item.effortMinutes} min</dd></div><div><dt>Policy</dt><dd>{set.policyVersion}</dd></div></dl> : <small>{item.conceptTitle} · about {item.effortMinutes} min</small>}
        <Button size="sm" variant="outline" onClick={() => void select(item)}>{item.actionKind === 'ask' ? 'Ask a question' : item.actionKind === 'quiz' ? 'Open quiz' : item.actionKind === 'review' ? 'Start review' : 'Continue learning'}<ArrowRight size={14} /></Button>
      </motion.article>;
    })}</AnimatePresence></div>
  </section>;
}


