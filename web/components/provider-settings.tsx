"use client";

import { useEffect, useState } from 'react';
import { KeyRound } from 'lucide-react';
import { Button } from '@/components/ui/button';

type DesktopCredentials = {
  has: (key: string) => Promise<boolean>;
  get: (key: string) => Promise<string | null>;
  set: (key: string, value: string) => Promise<boolean>;
  delete: (key: string) => Promise<boolean>;
};

function desktopCredentials(): DesktopCredentials | null {
  if (typeof window === 'undefined') return null;
  return (window as Window & { formaDesktop?: { credentials?: DesktopCredentials } }).formaDesktop?.credentials || null;
}

export function ProviderSettings() {
  const [credentials] = useState<DesktopCredentials | null>(() => desktopCredentials());
  const [openRouterKey, setOpenRouterKey] = useState('');
  const [openAiKey, setOpenAiKey] = useState('');
  const [configured, setConfigured] = useState({ openRouter: false, openAi: false });
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!credentials) return;
    void Promise.all([credentials.has('OPENROUTER_API_KEY'), credentials.has('OPENAI_API_KEY')]).then(([openRouter, openAi]) => {
      setConfigured({ openRouter: Boolean(openRouter), openAi: Boolean(openAi) });
    });
  }, [credentials]);

  async function save() {
    if (!credentials) return;
    setBusy(true); setMessage('');
    try {
      if (openRouterKey.trim()) await credentials.set('OPENROUTER_API_KEY', openRouterKey.trim());
      if (openAiKey.trim()) await credentials.set('OPENAI_API_KEY', openAiKey.trim());
      setConfigured(current => ({ openRouter: current.openRouter || Boolean(openRouterKey.trim()), openAi: current.openAi || Boolean(openAiKey.trim()) }));
      setOpenRouterKey(''); setOpenAiKey('');
      setMessage('Provider keys saved securely. Restart Forma to use a newly saved key.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Provider keys could not be saved.'); }
    finally { setBusy(false); }
  }

  async function remove(key: 'OPENROUTER_API_KEY' | 'OPENAI_API_KEY', label: 'openRouter' | 'openAi') {
    if (!credentials) return;
    setBusy(true); setMessage('');
    try { await credentials.delete(key); setConfigured(current => ({ ...current, [label]: false })); setMessage('Provider key removed. Restart Forma to return to the deterministic provider.'); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Provider key could not be removed.'); }
    finally { setBusy(false); }
  }

  if (!credentials) return <div className="settings-callout"><KeyRound size={18} /><span>Provider setup is available in the desktop application. The browser development shell uses its existing environment configuration.</span></div>;

  return <div className="provider-settings">
    <div className="settings-section-title"><KeyRound size={16} /><strong>Model providers</strong></div>
    <p className="settings-help">Keys stay on this device and are passed only to the local tutor service. Leave a field empty to keep its current value.</p>
    <label>OpenRouter API key<input type="password" autoComplete="off" value={openRouterKey} onChange={event => setOpenRouterKey(event.target.value)} placeholder={configured.openRouter ? 'Key saved securely' : 'sk-or-v1-…'} /></label>
    <label>OpenAI API key<input type="password" autoComplete="off" value={openAiKey} onChange={event => setOpenAiKey(event.target.value)} placeholder={configured.openAi ? 'Key saved securely' : 'sk-…'} /></label>
    <div className="settings-actions"><Button disabled={busy || (!openRouterKey.trim() && !openAiKey.trim())} onClick={save}>Save provider keys</Button>{configured.openRouter ? <Button variant="ghost" disabled={busy} onClick={() => remove('OPENROUTER_API_KEY', 'openRouter')}>Remove OpenRouter</Button> : null}{configured.openAi ? <Button variant="ghost" disabled={busy} onClick={() => remove('OPENAI_API_KEY', 'openAi')}>Remove OpenAI</Button> : null}</div>
    {message ? <p className="settings-message" role="status">{message}</p> : null}
  </div>;
}
