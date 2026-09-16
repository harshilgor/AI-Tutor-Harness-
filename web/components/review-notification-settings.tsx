"use client";

import { useEffect, useState } from 'react';
import { Bell } from 'lucide-react';

type DesktopPreferences = { reviewNotifications: boolean };
type PreferenceBridge = { get: () => Promise<DesktopPreferences>; set: (value: DesktopPreferences) => Promise<DesktopPreferences> };

function bridge(): PreferenceBridge | null {
  if (typeof window === 'undefined') return null;
  return (window as Window & { formaDesktop?: { preferences?: PreferenceBridge } }).formaDesktop?.preferences || null;
}

export function ReviewNotificationSettings() {
  const [preferences] = useState<PreferenceBridge | null>(() => bridge());
  const [enabled, setEnabled] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => { if (preferences) void preferences.get().then(value => { setEnabled(value.reviewNotifications); setReady(true); }); }, [preferences]);
  if (!preferences) return null;

  async function toggle() {
    if (!preferences) return;
    const value = !enabled; setEnabled(value);
    try { await preferences.set({ reviewNotifications: value }); } catch { setEnabled(!value); }
  }

  return <div className="notification-settings">
    <div><Bell size={17} /><span><strong>Review reminders</strong><small>Notify me on this device when a scheduled review is due.</small></span></div>
    <button type="button" role="switch" aria-checked={enabled} disabled={!ready} className={enabled ? 'enabled' : ''} onClick={toggle}><span />{enabled ? 'On' : 'Off'}</button>
  </div>;
}
