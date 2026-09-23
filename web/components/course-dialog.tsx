'use client';

import { useState } from 'react';
import { BookOpen, Sparkles, SlidersHorizontal, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  learningApi,
  type CoursePublic,
  type CourseCreateInput,
  type CourseTeachingPreferences,
} from '@/lib/api';

interface CourseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (course: CoursePublic) => void;
}

export function CourseDialog({ open, onOpenChange, onCreated }: CourseDialogProps) {
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [showPreferences, setShowPreferences] = useState(false);
  const [depth, setDepth] = useState<CourseTeachingPreferences['depth']>('standard');
  const [pace, setPace] = useState<CourseTeachingPreferences['pace']>('steady');
  const [mathLevel, setMathLevel] = useState<CourseTeachingPreferences['mathLevel']>('standard');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !goal.trim() || busy) return;

    setBusy(true);
    setError(null);
    try {
      const payload: CourseCreateInput = {
        name: name.trim(),
        goal: goal.trim(),
        teachingPreferences: {
          depth,
          pace,
          mathLevel,
          visualEmphasis: true,
          codeExamples: true,
          firstPrinciples: true,
        },
      };
      const created = await learningApi.createCourse(payload);
      onCreated(created);
      onOpenChange(false);
      setName('');
      setGoal('');
      setShowPreferences(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create course. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[540px]">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <div className="flex items-center gap-2 text-primary mb-1">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <BookOpen size={18} />
              </div>
              <DialogTitle className="text-lg font-semibold">Create New Course</DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted-foreground">
              A course connects your chats, notes, roadmap, and reviews into a persistent learning environment.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="p-3 text-xs rounded-md bg-destructive/10 text-destructive border border-destructive/20">
              {error}
            </div>
          )}

          <div className="space-y-3 py-1">
            <div className="space-y-1.5">
              <label htmlFor="course-name" className="text-xs font-medium text-foreground">
                Course name
              </label>
              <input
                id="course-name"
                type="text"
                autoFocus
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Distributed Systems & Consensus"
                className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="course-goal" className="text-xs font-medium text-foreground">
                What do you want to learn?
              </label>
              <textarea
                id="course-goal"
                required
                rows={3}
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g. Build a production-grade understanding of Paxos, Raft, and distributed state machines from first principles."
                className="w-full p-3 rounded-md border border-input bg-background text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
              />
            </div>

            <div>
              <button
                type="button"
                onClick={() => setShowPreferences((v) => !v)}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors font-medium"
              >
                <SlidersHorizontal size={13} />
                <span>{showPreferences ? 'Hide teaching preferences' : 'Customize teaching preferences'}</span>
              </button>

              {showPreferences && (
                <div className="mt-2.5 p-3 rounded-md bg-muted/40 border border-border/50 space-y-3">
                  <div className="grid grid-cols-3 gap-2">
                    <div className="space-y-1">
                      <label className="text-[11px] font-medium text-muted-foreground">Depth</label>
                      <select
                        value={depth}
                        onChange={(e) => setDepth(e.target.value as CourseTeachingPreferences['depth'])}
                        className="w-full h-8 px-2 rounded border border-input bg-background text-xs shadow-xs"
                      >
                        <option value="introductory">Introductory</option>
                        <option value="standard">Standard</option>
                        <option value="deep">Deep Dive</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-medium text-muted-foreground">Pace</label>
                      <select
                        value={pace}
                        onChange={(e) => setPace(e.target.value as CourseTeachingPreferences['pace'])}
                        className="w-full h-8 px-2 rounded border border-input bg-background text-xs shadow-xs"
                      >
                        <option value="brisk">Brisk</option>
                        <option value="steady">Steady</option>
                        <option value="thorough">Thorough</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[11px] font-medium text-muted-foreground">Math Level</label>
                      <select
                        value={mathLevel}
                        onChange={(e) => setMathLevel(e.target.value as CourseTeachingPreferences['mathLevel'])}
                        className="w-full h-8 px-2 rounded border border-input bg-background text-xs shadow-xs"
                      >
                        <option value="minimal">Intuitive</option>
                        <option value="standard">Standard</option>
                        <option value="rigorous">Rigorous</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={busy}
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!name.trim() || !goal.trim() || busy}
              className="gap-1.5"
            >
              {busy ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Creating course…</span>
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  <span>Create course</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
