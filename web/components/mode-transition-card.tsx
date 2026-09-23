"use client";

import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { CircleHelp, GraduationCap, Sparkles, X, ArrowRight } from 'lucide-react';
import type { ModeTransitionSuggestion } from '@/lib/api';
import styles from './mode-transition-card.module.css';

interface ModeTransitionCardProps {
  suggestion: ModeTransitionSuggestion;
  onAccept: (suggestion: ModeTransitionSuggestion) => void | Promise<void>;
  onDismiss: (suggestion: ModeTransitionSuggestion) => void | Promise<void>;
  disabled?: boolean;
}

export function ModeTransitionCard({
  suggestion,
  onAccept,
  onDismiss,
  disabled = false,
}: ModeTransitionCardProps) {
  const reduceMotion = useReducedMotion();
  const [dismissed, setDismissed] = useState(false);
  const [busy, setBusy] = useState(false);

  const isLearn = suggestion.targetMode === 'learn';
  const Icon = isLearn ? GraduationCap : CircleHelp;

  const handleAccept = async () => {
    if (busy || disabled) return;
    setBusy(true);
    try {
      await onAccept(suggestion);
    } finally {
      setBusy(false);
    }
  };

  const handleDismiss = async () => {
    if (busy) return;
    setDismissed(true);
    await onDismiss(suggestion);
  };

  if (dismissed) return null;

  return (
    <AnimatePresence>
      <motion.div
        className={`${styles.transitionCard} ${isLearn ? styles.learn : styles.quiz}`}
        role="region"
        aria-label="Mode handoff suggestion"
        initial={reduceMotion ? false : { opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={reduceMotion ? undefined : { opacity: 0, y: -6, scale: 0.98 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}
      >
        <div className={styles.header}>
          <span className={`${styles.iconTile} ${isLearn ? styles.learn : styles.quiz}`}>
            <Icon size={14} />
          </span>
          <strong className={styles.title}>{suggestion.title}</strong>
        </div>
        <p className={styles.description}>{suggestion.description}</p>
        <div className={styles.actions}>
          <button
            type="button"
            className={`${styles.primaryButton} ${isLearn ? styles.learn : styles.quiz}`}
            disabled={disabled || busy}
            onClick={() => void handleAccept()}
          >
            <span>{suggestion.actionLabel}</span>
            <ArrowRight size={13} />
          </button>
          <button
            type="button"
            className={styles.dismissButton}
            disabled={disabled || busy}
            onClick={() => void handleDismiss()}
          >
            {suggestion.dismissLabel || 'Not now'}
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

interface OriginBadgeProps {
  summary: string;
  onDismiss: () => void;
}

export function OriginBadge({ summary, onDismiss }: OriginBadgeProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={styles.originBadge}
      role="status"
      initial={reduceMotion ? false : { opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? undefined : { opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      <Sparkles size={12} />
      <span>{summary}</span>
      <button type="button" aria-label="Dismiss origin note" onClick={onDismiss}>
        <X size={12} />
      </button>
    </motion.div>
  );
}
