"use client";

import { useRef, useState } from 'react';
import { ArrowUp, FileText, Paperclip, X, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import styles from './learn-chat.module.css';
import type { Gear } from '@/lib/api';

export type ChatAttachment = { id: string; name: string; file: File; versionId?: string; materialId?: string };

export function ChatComposer({ value, onChange, attachments, onAttachmentsChange, onSubmit, busy, followup, gear, onGearChange }: {
  value: string; onChange: (value: string) => void; attachments: ChatAttachment[];
  onAttachmentsChange: (items: ChatAttachment[]) => void; onSubmit: () => void; busy: boolean; followup: boolean; gear: Gear; onGearChange: (gear: Gear) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const dragDepth = useRef(0);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  function add(files: File[]) {
    const accepted: ChatAttachment[] = [];
    const rejected: string[] = [];
    for (const file of files) {
      if (!/\.(pdf|txt|md|png|jpe?g|webp|gif)$/i.test(file.name) || !file.size || file.size > 50 * 1024 * 1024) { rejected.push(file.name); continue; }
      if (!attachments.some(item => item.name === file.name && item.file.size === file.size) && !accepted.some(item => item.name === file.name && item.file.size === file.size)) accepted.push({ id: crypto.randomUUID(), name: file.name, file });
    }
    onAttachmentsChange([...attachments, ...accepted]);
    setError(rejected.length ? `Couldn't attach ${rejected.join(', ')}. Use PDF, TXT, Markdown, PNG, JPG, WEBP, or GIF files up to 50 MB.` : '');
  }
  const hasLink = /https?:\/\/\S+/i.test(value);
  return <form className={`${followup ? styles.followupComposer : styles.composer} ${styles.chatComposer} ${dragging ? styles.dragging : ''}`}
    onSubmit={event => { event.preventDefault(); onSubmit(); }}
    onDragEnter={event => { if (!busy && event.dataTransfer.types.includes('Files')) { event.preventDefault(); dragDepth.current++; setDragging(true); } }}
    onDragOver={event => { if (event.dataTransfer.types.some(type => ['Files', 'text/uri-list'].includes(type))) { event.preventDefault(); event.dataTransfer.dropEffect = busy ? 'none' : 'copy'; } }}
    onDragLeave={event => { event.preventDefault(); if (--dragDepth.current <= 0) { dragDepth.current = 0; setDragging(false); } }}
    onDrop={event => { if (event.dataTransfer.files.length) { event.preventDefault(); if (!busy) add(Array.from(event.dataTransfer.files)); } else { const link = event.dataTransfer.getData('text/uri-list').split('\n').find(line => /^https?:\/\//i.test(line)); if (link) { event.preventDefault(); if (!busy) onChange(`${value}${value ? '\n' : ''}${link}`.slice(0, 4000)); } } dragDepth.current = 0; setDragging(false); }}>
    {dragging && <div className={styles.dropOverlay}><Upload size={26} /><strong>Drop your files here</strong><span>Books, notes, and anything you’re learning from</span></div>}
    {attachments.length > 0 && <div className={styles.attachments} aria-label="Chat attachments">{attachments.map(item => <div className={styles.attachment} key={item.id}><FileText size={21} /><div><strong title={item.name}>{item.name}</strong><span>{item.versionId ? 'In this conversation' : `${item.name.split('.').at(-1)?.toUpperCase()} · ${(item.file.size / 1024 / 1024).toFixed(1)} MB`}</span></div><button type="button" disabled={busy} aria-label={`Remove ${item.name} from this conversation`} onClick={() => onAttachmentsChange(attachments.filter(other => other.id !== item.id))}><X size={14} /></button></div>)}</div>}
    <label htmlFor="chat-message" className="sr-only">Message your tutor</label>
    <textarea id="chat-message" disabled={busy} value={value} maxLength={4000} placeholder={followup ? 'Ask a follow-up…' : 'Ask anything, or drop in a book…'} rows={followup ? 2 : 3} onChange={event => onChange(event.target.value)}
      onPaste={event => { if (event.clipboardData.files.length) { event.preventDefault(); add(Array.from(event.clipboardData.files)); } }}
      onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); onSubmit(); } }} />
    <input ref={input} type="file" hidden multiple accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp,.gif" onChange={event => { add(Array.from(event.target.files || [])); event.target.value = ''; }} />
    <div className={styles.composerBottom}><div className={styles.composerTools}><Button type="button" variant="ghost" size="icon" disabled={busy} aria-label="Attach files" title="Attach PDF, text, Markdown, or images" onClick={() => input.current?.click()}><Paperclip size={19} /></Button><span>{attachments.length ? 'Ask about your attachments' : 'Files, books, notes, or a link'}</span><span className={styles.thinkingLabel}>Thinking</span><div className={styles.gearToggle} role="group" aria-label="Thinking depth">{(['Quick', 'Guided', 'Deep'] as Gear[]).map(option => <button type="button" key={option} className={gear === option ? styles.gearActive : ''} onClick={() => onGearChange(option)}>{option}</button>)}</div></div><Button size="icon" type="submit" disabled={busy || (!value.trim() && !attachments.length)} aria-label="Send message"><ArrowUp size={20} /></Button></div>
    {hasLink && <p className={styles.composerNote}>Links are shared as references. To teach from a page’s contents, attach the file or paste its text.</p>}
    {error && <p className={styles.error} role="alert">{error}</p>}
  </form>;
}
