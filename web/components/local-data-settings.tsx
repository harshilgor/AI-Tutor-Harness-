"use client";

import { ChangeEvent, useEffect, useRef, useState } from 'react';
import { Download, RefreshCw, ShieldCheck, Trash2, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { learningApi } from '@/lib/api';
import styles from './local-data-settings.module.css';
import { ProviderSettings } from './provider-settings';
import { ReviewNotificationSettings } from './review-notification-settings';

type UpdateStatus = { state: 'idle' | 'checking' | 'downloading' | 'ready' | 'up-to-date' | 'error' | 'unavailable'; currentVersion: string; availableVersion?: string; detail?: string };
type DesktopUpdates = { status: () => Promise<UpdateStatus>; check: () => Promise<UpdateStatus>; install: () => Promise<boolean>; onStatus: (callback: (status: UpdateStatus) => void) => () => void };

function desktopUpdates(): DesktopUpdates | null {
  if (typeof window === 'undefined') return null;
  return (window as Window & { formaDesktop?: { updates?: DesktopUpdates } }).formaDesktop?.updates || null;
}

/** Application updates. Renders nothing outside the desktop shell. */
export function UpdateSection() {
  const [updates] = useState<DesktopUpdates | null>(() => desktopUpdates());
  const [update, setUpdate] = useState<UpdateStatus | null>(null);

  useEffect(() => {
    if (!updates) return;
    void updates.status().then(setUpdate);
    return updates.onStatus(setUpdate);
  }, [updates]);

  if (!updates || !update) return null;

  async function checkForUpdate() { if (updates) setUpdate(await updates.check()); }
  async function installUpdate() { if (updates) await updates.install(); }

  return <section className={styles.update} aria-label="Application updates">
    <div><strong>Open Learn {update.currentVersion}</strong><p>{update.detail || 'Keep Open Learn current with verified GitHub releases.'}</p></div>
    {update.state === 'ready' ? <Button onClick={installUpdate}>Restart and install {update.availableVersion}</Button> : <Button variant="outline" disabled={update.state === 'checking' || update.state === 'downloading'} onClick={checkForUpdate}><RefreshCw size={15} />{update.state === 'checking' ? 'Checking…' : update.state === 'downloading' ? 'Downloading…' : 'Check for updates'}</Button>}
  </section>;
}

function download(base64: string, filename: string, type: string) {
  const raw = atob(base64); const bytes = Uint8Array.from(raw, char => char.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([bytes], { type })); const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
}

/** Export, backup, restore, and deletion for locally stored learner data. */
export function DataActionsSection() {
  const [busy, setBusy] = useState<'export' | 'backup' | 'restore' | 'delete' | null>(null);
  const [message, setMessage] = useState('');
  const restoreInput = useRef<HTMLInputElement>(null);

  async function backupData() {
    setBusy('backup'); setMessage('');
    try { const data = await learningApi.createLocalBackup(); download(data.archiveBase64, `open-learn-backup-${new Date().toISOString().slice(0, 10)}.zip`, 'application/zip'); setMessage('Checksummed local backup downloaded. Provider credentials were not included.'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'The backup could not be created.'); }
    finally { setBusy(null); }
  }

  async function restoreData(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; event.target.value = ''; if (!file) return;
    setBusy('restore'); setMessage('');
    try {
      const base64 = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onerror = () => reject(new Error('The backup could not be read.')); reader.onload = () => resolve(String(reader.result).split(',')[1] ?? ''); reader.readAsDataURL(file); });
      const preflight = await learningApi.preflightLocalBackup(base64);
      if (preflight.requiresReplaceConfirmation && !window.confirm(`This will replace ${preflight.existingRecordCount} local records with ${preflight.recordCount} records from the backup. Create a fresh backup first. Continue?`)) return;
      const restored = await learningApi.restoreLocalBackup(base64, preflight.requiresReplaceConfirmation);
      setMessage(`Restored ${restored.restored} records and ${restored.files} local files. Restart Open Learn to reload restored workspace data.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : 'The backup could not be restored.'); }
    finally { setBusy(null); }
  }

  async function exportData() {
    setBusy('export'); setMessage('');
    try {
      const data = await learningApi.exportLocalData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      const link = document.createElement('a'); link.href = url;
      link.download = `open-learn-data-${new Date().toISOString().slice(0, 10)}.json`; link.click();
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

  return <>
    <div className={styles.callout}><ShieldCheck size={18} /><span>Open Learn keeps your learner data on this device. Provider keys use the desktop operating system’s encrypted credential store.</span></div>
    <div className={styles.actions}>
      <Button variant="outline" disabled={busy !== null} onClick={exportData}><Download size={15} />{busy === 'export' ? 'Preparing export…' : 'Export local data'}</Button>
      <Button variant="outline" disabled={busy !== null} onClick={backupData}><Download size={15} />{busy === 'backup' ? 'Creating backup…' : 'Download backup'}</Button>
      <Button variant="outline" disabled={busy !== null} onClick={() => restoreInput.current?.click()}><Upload size={15} />{busy === 'restore' ? 'Restoring…' : 'Restore backup'}</Button>
      <Button variant="outline" disabled={busy !== null} onClick={deleteData}><Trash2 size={15} />{busy === 'delete' ? 'Deleting…' : 'Delete local data'}</Button>
    </div>
    <input ref={restoreInput} className={styles.file} type="file" accept=".zip,application/zip" onChange={restoreData} />
    {message ? <p className={styles.message} role="status">{message}</p> : null}
  </>;
}

export function LocalDataSettings({ onDone }: { onDone: () => void }) {
  return <div className={styles.body}>
    <ProviderSettings />
    <ReviewNotificationSettings />
    <UpdateSection />
    <DataActionsSection />
    <Button variant="ghost" onClick={onDone}>Back to learning</Button>
  </div>;
}
