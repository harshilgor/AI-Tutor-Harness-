"use client";

import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { ArrowLeft, Bell, CircleHelp, Database, Gauge, KeyRound, Moon, Settings2, Sun } from 'lucide-react';
import { ProviderSettings } from './provider-settings';
import { UsageSettings } from './usage-settings';
import { ReviewNotificationSettings } from './review-notification-settings';
import { DataActionsSection, UpdateSection } from './local-data-settings';
import styles from './settings-page.module.css';

export type SettingsCategory = 'general' | 'usage' | 'api-keys' | 'notifications' | 'data' | 'about';

const CATEGORIES: { id: SettingsCategory; label: string; icon: typeof Settings2 }[] = [
  { id: 'general', label: 'General', icon: Settings2 },
  { id: 'usage', label: 'Usage', icon: Gauge },
  { id: 'api-keys', label: 'API keys', icon: KeyRound },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'data', label: 'Data & privacy', icon: Database },
  { id: 'about', label: 'About', icon: CircleHelp },
];

function hasDesktopPreferences(): boolean {
  if (typeof window === 'undefined') return false;
  return Boolean((window as Window & { formaDesktop?: { preferences?: unknown } }).formaDesktop?.preferences);
}

/**
 * Full-page settings destination. Categories map one-to-one onto real,
 * already-supported product surfaces; add a category by extending
 * CATEGORIES and rendering its section below. No placeholder settings.
 */
export function SettingsPage({ category, onCategoryChange, onBack }: {
  category: SettingsCategory;
  onCategoryChange: (category: SettingsCategory) => void;
  onBack: () => void;
}) {
  const [desktop, setDesktop] = useState(false);
  const { theme, setTheme } = useTheme();
  const selectedTheme = theme ?? 'light';
  useEffect(() => {
    const timer = window.setTimeout(() => setDesktop(hasDesktopPreferences()), 0);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className={styles.page}>
      <nav className={styles.nav} aria-label="Settings categories">
        <button type="button" className={styles.back} onClick={onBack}>
          <ArrowLeft size={15} />Back to app
        </button>
        {CATEGORIES.map(item => (
          <button
            key={item.id}
            type="button"
            aria-current={category === item.id ? 'page' : undefined}
            className={styles.navItem + (category === item.id ? ' ' + styles.active : '')}
            onClick={() => onCategoryChange(item.id)}
          >
            <item.icon size={16} />{item.label}
          </button>
        ))}
      </nav>
      <div className={styles.content}>
        <div className={styles.inner}>
          {category === 'general' ? (
            <section aria-label="General settings">
              <h1>General</h1>
              <p className={styles.lede}>Choose how Open Learn looks on this device.</p>
              <div className={styles.card}>
                <h2 className={styles.preferenceTitle}>Appearance</h2>
                <p className={styles.preferenceHelp}>Set a theme for the workspace. Your choice is saved in this browser.</p>
                <div className={styles.themeChoices} role="group" aria-label="Color theme">
                  <button type="button" aria-pressed={selectedTheme === 'light'} className={styles.themeChoice + (selectedTheme === 'light' ? ' ' + styles.themeChoiceActive : '')} onClick={() => setTheme('light')}>
                    <Sun size={17} />Light
                  </button>
                  <button type="button" aria-pressed={selectedTheme === 'dark'} className={styles.themeChoice + (selectedTheme === 'dark' ? ' ' + styles.themeChoiceActive : '')} onClick={() => setTheme('dark')}>
                    <Moon size={17} />Dark
                  </button>
                </div>
              </div>
              <div className={styles.group}>
                <UpdateSection />
                {!desktop ? <p className={styles.muted}>Update checks are available in the desktop app.</p> : null}
              </div>
            </section>
          ) : null}
          {category === 'usage' ? (
            <section aria-label="Usage settings">
              <h1>Usage</h1>
              <p className={styles.lede}>Tokens and generations used on this device, measured from provider-reported usage where available.</p>
              <div className={styles.group}>
                <div className={styles.card}>
                  <UsageSettings />
                </div>
              </div>
            </section>
          ) : null}
          {category === 'api-keys' ? (
            <section aria-label="API key settings">
              <h1>API keys</h1>
              <p className={styles.lede}>Connect a model provider for AI-powered lessons and quizzes. Keys stay in this device’s encrypted credential store.</p>
              <div className={styles.group}>
                <div className={styles.card}>
                  <ProviderSettings />
                </div>
              </div>
            </section>
          ) : null}
          {category === 'notifications' ? (
            <section aria-label="Notification settings">
              <h1>Notifications</h1>
              <p className={styles.lede}>Reminders that help you return to scheduled reviews.</p>
              <div className={styles.card}>
                <ReviewNotificationSettings />
                {!desktop ? <p className={styles.muted}>Review reminders are available in the desktop app. Notifications stay on this device.</p> : null}
              </div>
            </section>
          ) : null}
          {category === 'data' ? (
            <section aria-label="Data and privacy settings">
              <h1>Data &amp; privacy</h1>
              <p className={styles.lede}>Your lessons, notes, and review state stay on this device. Export or remove them at any time.</p>
              <div className={styles.card}>
                <DataActionsSection />
              </div>
            </section>
          ) : null}
          {category === 'about' ? (
            <section aria-label="About Open Learn">
              <h1>About</h1>
              <p className={styles.lede}>A local-first learning environment for guided study, practice, and review.</p>
              <div className={styles.card}>
                <div className={styles.aboutRow}><strong>Open Learn</strong><span>Personal · On this device</span></div>
                <p className={styles.muted}>Lessons, notes, quiz attempts, and review schedules are stored locally. Provider keys live in the desktop operating system’s encrypted credential store and are never exported with backups.</p>
              </div>
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
