"use client";

import { useState } from 'react';
import { Download, ShieldCheck, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { learningApi } from '@/lib/api';
import styles from './local-data-settings.module.css';
import { ProviderSettings } from './provider-settings';
import { ReviewNotificationSettings } from './review-notification-settings';

export function LocalDataSettings({ onDone }: { onDone: () => void }) {
  const [busy, setBusy] = useState<'export' | 'delete' | null>(null);
  const [message, setMessage] = useState('');

  async function exportData() {
    setBusy('export'); setMessage('');
    try {
      const data = await learningApi.exportLocalData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      const link = document.createElement('a'); link.href = url;
      link.download = `forma-learning-data-${new Date().toISOString().slice(0, 10)}.json`; link.click();
      URL.revokeObjectURL(url); setMessage('Your local learning data was downloaded.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'The export could not be created.'); }
    finally { setBusy(null); }
  }

  async function deleteData() {
    if (!window.confirm('Delete all local learner data, lessons, quizzes, and imported materials? This cannot be undone.')) return;
    setBusy('delete'); setMessage('');
    try { await learningApi.deleteLocalData(); localStorage.clear(); setMessage('All local learning data was deleted.'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'The local data could not be deleted.'); }
    finally { setBusy(null); }
  }

  return <div className={styles.body}>
    <ProviderSettings />
    <ReviewNotificationSettings />
    <div className={styles.callout}><ShieldCheck size={18} /><span>Forma keeps your learner data on this device. Provider keys use the desktop operating system’s encrypted credential store.</span></div>
    <div className={styles.actions}>
      <Button variant="outline" disabled={busy !== null} onClick={exportData}><Download size={15} />{busy === 'export' ? 'Preparing export…' : 'Export local data'}</Button>
      <Button variant="outline" disabled={busy !== null} onClick={deleteData}><Trash2 size={15} />{busy === 'delete' ? 'Deleting…' : 'Delete local data'}</Button>
    </div>
    {message ? <p className={styles.message} role="status">{message}</p> : null}
    <Button variant="ghost" onClick={onDone}>Back to learning</Button>
  </div>;
}
