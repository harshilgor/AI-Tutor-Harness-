"use client";

import { useEffect, useState } from 'react';
import { KeyRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { learningApi, friendlyServiceError, type ProviderSettingsStatus } from '@/lib/api';

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

  if (!credentials) return <ServerProviderSettings />;

  return <div className="provider-settings">
    <div className="settings-section-title"><KeyRound size={16} /><strong>Model providers</strong></div>
    <p className="settings-help">Keys stay on this device and are passed only to the local tutor service. Leave a field empty to keep its current value.</p>
    <label>OpenRouter API key<input type="password" autoComplete="off" value={openRouterKey} onChange={event => setOpenRouterKey(event.target.value)} placeholder={configured.openRouter ? 'Key saved securely' : 'sk-or-v1-…'} /></label>
    <label>OpenAI API key<input type="password" autoComplete="off" value={openAiKey} onChange={event => setOpenAiKey(event.target.value)} placeholder={configured.openAi ? 'Key saved securely' : 'sk-…'} /></label>
    <div className="settings-actions"><Button disabled={busy || (!openRouterKey.trim() && !openAiKey.trim())} onClick={save}>Save provider keys</Button>{configured.openRouter ? <Button variant="ghost" disabled={busy} onClick={() => remove('OPENROUTER_API_KEY', 'openRouter')}>Remove OpenRouter</Button> : null}{configured.openAi ? <Button variant="ghost" disabled={busy} onClick={() => remove('OPENAI_API_KEY', 'openAi')}>Remove OpenAI</Button> : null}</div>
    {message ? <p className="settings-message" role="status">{message}</p> : null}
  </div>;
}

/**
 * Browser development shell: keys are stored in the local API server's own
 * configuration file. The desktop application keeps using the OS credential
 * store above. A service restart applies a new key.
 */
function ServerProviderSettings() {
  const [status, setStatus] = useState<ProviderSettingsStatus | null>(null);
  const [openRouterKey, setOpenRouterKey] = useState('');
  const [openAiKey, setOpenAiKey] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void learningApi.getProviderSettings().then(setStatus).catch((cause: unknown) => {
        const friendly = friendlyServiceError(cause, 'Provider status');
        setMessage(`${friendly.message} ${friendly.detail}`);
      });
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function save() {
    setBusy(true); setMessage('');
    try {
      let next: ProviderSettingsStatus | null = null;
      if (openRouterKey.trim()) next = await learningApi.saveProviderKey('openrouter', openRouterKey.trim());
      if (openAiKey.trim()) next = await learningApi.saveProviderKey('openai', openAiKey.trim());
      if (next) setStatus(next);
      setOpenRouterKey(''); setOpenAiKey('');
      setMessage('Provider key saved on the tutor service. Restart the service to use it.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Provider key could not be saved.'); }
    finally { setBusy(false); }
  }

  async function remove(provider: 'openrouter' | 'openai') {
    setBusy(true); setMessage('');
    try {
      setStatus(await learningApi.deleteProviderKey(provider));
      setMessage('Provider key removed. Restart the service to return to the deterministic provider.');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Provider key could not be removed.'); }
    finally { setBusy(false); }
  }

  return <div className="provider-settings">
    <div className="settings-section-title"><KeyRound size={16} /><strong>Model providers</strong></div>
    <p className="settings-help">Keys are stored in the local tutor service configuration and never leave this machine. Leave a field empty to keep its current value.</p>
    <label>OpenRouter API key<input type="password" autoComplete="off" value={openRouterKey} onChange={event => setOpenRouterKey(event.target.value)} placeholder={status?.openRouterConfigured ? 'Key saved' : 'sk-or-v1-…'} /></label>
    <label>OpenAI API key<input type="password" autoComplete="off" value={openAiKey} onChange={event => setOpenAiKey(event.target.value)} placeholder={status?.openAiConfigured ? 'Key saved' : 'sk-…'} /></label>
    <div className="settings-actions"><Button disabled={busy || (!openRouterKey.trim() && !openAiKey.trim())} onClick={save}>Save provider keys</Button>{status?.openRouterConfigured ? <Button variant="ghost" disabled={busy} onClick={() => remove('openrouter')}>Remove OpenRouter</Button> : null}{status?.openAiConfigured ? <Button variant="ghost" disabled={busy} onClick={() => remove('openai')}>Remove OpenAI</Button> : null}</div>
    {message ? <p className="settings-message" role="status">{message}</p> : null}
  </div>;
}
