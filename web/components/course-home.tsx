'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  BookMarked,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Circle,
  Eye,
  FileText,
  FileUp,
  Loader2,
  MessageSquare,
  MoreVertical,
  Play,
  Plus,
  RotateCcw,
  Sparkles,
  Trash2,
  TrendingUp,
  Wand2,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  learningApi,
  type CoursePublic,
  type CourseRoadmapNode,
  type CourseMaterial,
  type ChatSessionSummary,
  type WorkspaceNoteSummary,
} from '@/lib/api';
import { cn } from '@/lib/utils';

interface CourseHomeProps {
  courseId: string;
  onOpenSession: (sessionId: string) => void;
  onNewSession: (topic?: string) => void;
  onOpenNote?: (noteId: string) => void;
  onStartReview?: () => void;
  onDeleted?: () => void;
}

export function CourseHome({
  courseId,
  onOpenSession,
  onNewSession,
  onOpenNote,
  onStartReview,
  onDeleted,
}: CourseHomeProps) {
  const [course, setCourse] = useState<CoursePublic | null>(null);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [notes, setNotes] = useState<WorkspaceNoteSummary[]>([]);
  const [materials, setMaterials] = useState<CourseMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingNodeId, setUpdatingNodeId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Progression & Tailoring states
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluationFeedback, setEvaluationFeedback] = useState<string | null>(null);
  const [showTailorDialog, setShowTailorDialog] = useState(false);
  const [tailorPrompt, setTailorPrompt] = useState('');
  const [isTailoring, setIsTailoring] = useState(false);

  // Adding milestone inline
  const [activeAddPhase, setActiveAddPhase] = useState<string | null>(null);
  const [newMilestoneTitle, setNewMilestoneTitle] = useState('');
  const [isAddingMilestone, setIsAddingMilestone] = useState(false);

  // Materials & Reference Library states
  const [showAddMaterialDialog, setShowAddMaterialDialog] = useState(false);
  const [materialMode, setMaterialMode] = useState<'upload' | 'text'>('upload');
  const [materialRole, setMaterialRole] = useState<'reference' | 'textbook' | 'lecture_notes'>('reference');
  const [textTitle, setTextTitle] = useState('');
  const [textBody, setTextBody] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isAddingMaterial, setIsAddingMaterial] = useState(false);
  const [inspectingMaterial, setInspectingMaterial] = useState<CourseMaterial | null>(null);
  const [passages, setPassages] = useState<Array<{ id?: string; spanId?: string; title?: string; pageIndex: number; text: string }> | null>(null);
  const [loadingPassages, setLoadingPassages] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [courseData, sessionsData, notesData, materialsData] = await Promise.all([
        learningApi.getCourse(courseId),
        learningApi.listCourseSessions(courseId),
        learningApi.listCourseNotes(courseId),
        learningApi.listCourseMaterials(courseId),
      ]);
      setCourse(courseData);
      setSessions(sessionsData.sessions);
      setNotes(notesData.notes);
      setMaterials(materialsData.materials);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load course details.');
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadData();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadData]);

  const handleToggleNodeStatus = async (node: CourseRoadmapNode) => {
    if (!course || updatingNodeId) return;
    const nextStatus: CourseRoadmapNode['status'] =
      node.status === 'completed'
        ? 'planned'
        : node.status === 'in_progress'
        ? 'completed'
        : node.status === 'needs_review'
        ? 'in_progress'
        : 'in_progress';

    setUpdatingNodeId(node.id);
    try {
      const updatedNode = await learningApi.updateRoadmapNode(course.id, node.id, nextStatus);
      setCourse((prev) => {
        if (!prev) return null;
        const newRoadmap = prev.roadmap.map((n) => (n.id === node.id ? updatedNode : n));
        const completedCount = newRoadmap.filter((n) => n.status === 'completed').length;
        const progress = Math.round((completedCount / (newRoadmap.length || 1)) * 100);
        return {
          ...prev,
          roadmap: newRoadmap,
          summary: {
            ...prev.summary,
            roadmapProgress: progress,
          },
        };
      });
    } catch {
      // Ignore or retry
    } finally {
      setUpdatingNodeId(null);
    }
  };

  const handleStartMilestone = async (node: CourseRoadmapNode) => {
    if (!course) return;
    if (node.status === 'planned') {
      void learningApi.updateRoadmapNode(course.id, node.id, 'in_progress').then((updated) => {
        setCourse((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            roadmap: prev.roadmap.map((n) => (n.id === node.id ? updated : n)),
          };
        });
      });
    }
    onNewSession(`Let's study ${node.title} in the context of ${course.name}.`);
  };

  const handleEvaluateProgression = async () => {
    if (!course || isEvaluating) return;
    setIsEvaluating(true);
    setEvaluationFeedback(null);
    try {
      const result = await learningApi.evaluateCourseProgression(course.id);
      setCourse((prev) => {
        if (!prev) return null;
        const progress = Math.round((result.completedCount / (result.totalCount || 1)) * 100);
        return {
          ...prev,
          roadmap: result.roadmap,
          summary: {
            ...prev.summary,
            roadmapProgress: progress,
            dueReviewCount: result.dueReviewCount,
          },
        };
      });
      setEvaluationFeedback(
        result.nodesUpdated > 0
          ? `Progress synced: ${result.nodesUpdated} milestone${result.nodesUpdated === 1 ? '' : 's'} updated.`
          : 'All milestones are up to date with your learning evidence.'
      );
    } catch (err: unknown) {
      setEvaluationFeedback(err instanceof Error ? err.message : 'Failed to evaluate progression.');
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleTailorCurriculum = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!course || isTailoring) return;
    setIsTailoring(true);
    try {
      const newRoadmap = await learningApi.generateCourseRoadmap(course.id, {
        prompt: tailorPrompt.trim() || undefined,
        replaceExisting: true,
      });
      setCourse((prev) => {
        if (!prev) return null;
        const completedCount = newRoadmap.filter((n) => n.status === 'completed').length;
        const progress = Math.round((completedCount / (newRoadmap.length || 1)) * 100);
        return {
          ...prev,
          roadmap: newRoadmap,
          summary: {
            ...prev.summary,
            roadmapProgress: progress,
          },
        };
      });
      setShowTailorDialog(false);
      setTailorPrompt('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to tailor curriculum.');
    } finally {
      setIsTailoring(false);
    }
  };

  const handleAddMilestone = async (phase: string) => {
    if (!course || !newMilestoneTitle.trim() || isAddingMilestone) return;
    setIsAddingMilestone(true);
    try {
      const created = await learningApi.addRoadmapNode(course.id, {
        title: newMilestoneTitle.trim(),
        phase,
      });
      setCourse((prev) => {
        if (!prev) return null;
        const newRoadmap = [...prev.roadmap, created];
        const completedCount = newRoadmap.filter((n) => n.status === 'completed').length;
        const progress = Math.round((completedCount / (newRoadmap.length || 1)) * 100);
        return {
          ...prev,
          roadmap: newRoadmap,
          summary: {
            ...prev.summary,
            roadmapProgress: progress,
          },
        };
      });
      setNewMilestoneTitle('');
      setActiveAddPhase(null);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to add milestone.');
    } finally {
      setIsAddingMilestone(false);
    }
  };

  const handleDeleteMilestone = async (nodeId: string) => {
    if (!course) return;
    try {
      await learningApi.deleteRoadmapNode(course.id, nodeId);
      setCourse((prev) => {
        if (!prev) return null;
        const newRoadmap = prev.roadmap.filter((n) => n.id !== nodeId);
        const completedCount = newRoadmap.filter((n) => n.status === 'completed').length;
        const progress = Math.round((completedCount / (newRoadmap.length || 1)) * 100);
        return {
          ...prev,
          roadmap: newRoadmap,
          summary: {
            ...prev.summary,
            roadmapProgress: progress,
          },
        };
      });
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete milestone.');
    }
  };

  const handleMoveMilestone = async (nodeId: string, direction: 'up' | 'down') => {
    if (!course) return;
    const index = course.roadmap.findIndex((n) => n.id === nodeId);
    if (index === -1) return;
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= course.roadmap.length) return;

    const newIds = course.roadmap.map((n) => n.id);
    const temp = newIds[index];
    newIds[index] = newIds[targetIndex];
    newIds[targetIndex] = temp;

    try {
      const reordered = await learningApi.reorderRoadmapNodes(course.id, newIds);
      setCourse((prev) => (prev ? { ...prev, roadmap: reordered } : null));
    } catch {
      // Revert silently
    }
  };

  const handleAddMaterial = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!course || isAddingMaterial) return;
    setIsAddingMaterial(true);
    try {
      if (materialMode === 'upload') {
        if (!uploadFile) throw new Error('Please select a file to upload.');
        const created = await learningApi.uploadCourseMaterial(course.id, uploadFile, materialRole);
        setMaterials((prev) => [created, ...prev]);
      } else {
        if (!textTitle.trim() || !textBody.trim()) throw new Error('Please enter title and content.');
        const created = await learningApi.addCourseTextMaterial(course.id, {
          title: textTitle.trim(),
          text: textBody.trim(),
          role: materialRole,
        });
        setMaterials((prev) => [created, ...prev]);
      }
      setCourse((prev) =>
        prev
          ? {
              ...prev,
              summary: {
                ...prev.summary,
                materialCount: (prev.summary.materialCount || 0) + 1,
              },
            }
          : null
      );
      setShowAddMaterialDialog(false);
      setUploadFile(null);
      setTextTitle('');
      setTextBody('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to add material.');
    } finally {
      setIsAddingMaterial(false);
    }
  };

  const handleDeleteMaterial = async (matId: string) => {
    if (!course) return;
    try {
      await learningApi.detachCourseMaterial(course.id, matId);
      setMaterials((prev) => prev.filter((m) => m.id !== matId));
      setCourse((prev) =>
        prev
          ? {
              ...prev,
              summary: {
                ...prev.summary,
                materialCount: Math.max(0, (prev.summary.materialCount || 1) - 1),
              },
            }
          : null
      );
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to detach material.');
    }
  };

  const handleInspectMaterial = async (mat: CourseMaterial) => {
    setInspectingMaterial(mat);
    setLoadingPassages(true);
    try {
      const data = await learningApi.getMaterialBlocks(mat.versionId);
      setPassages(data.blocks);
    } catch {
      setPassages([]);
    } finally {
      setLoadingPassages(false);
    }
  };

  const handleDeleteCourse = async () => {
    if (!course || isDeleting) return;
    if (!confirm(`Are you sure you want to delete "${course.name}"? Existing chats and notes will not be deleted, but will be detached from this course.`)) {
      return;
    }
    setIsDeleting(true);
    try {
      await learningApi.deleteCourse(course.id);
      onDeleted?.();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete course.');
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-muted-foreground gap-3">
        <Loader2 size={24} className="animate-spin text-primary" />
        <p className="text-xs">Loading course environment…</p>
      </div>
    );
  }

  if (error || !course) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-md mx-auto gap-3">
        <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
          <BookOpen size={24} />
        </div>
        <h3 className="text-sm font-semibold">Course not found</h3>
        <p className="text-xs text-muted-foreground">{error || 'This course may have been removed or is unavailable.'}</p>
        <Button size="sm" variant="outline" onClick={() => void loadData()}>
          Try again
        </Button>
      </div>
    );
  }

  // Find next active node to recommend
  const nextNode =
    course.roadmap.find((n) => n.status === 'in_progress') ||
    course.roadmap.find((n) => n.status === 'needs_review') ||
    course.roadmap.find((n) => n.status === 'planned');

  // Group roadmap nodes by phase
  const phases = Array.from(new Set(course.roadmap.map((n) => n.phase)));

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium uppercase tracking-wider">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Active Course</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">{course.name}</h1>
              <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">{course.goal}</p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => onNewSession()}
                className="gap-1.5 shadow-xs"
              >
                <Plus size={14} />
                <span>New chat</span>
              </Button>
              <div className="relative">
                <Button
                  size="icon"
                  variant="outline"
                  className="h-8 w-8"
                  onClick={() => setShowSettings((v) => !v)}
                  title="Course options"
                >
                  <MoreVertical size={15} />
                </Button>
                {showSettings && (
                  <div className="absolute right-0 mt-1 w-44 rounded-md border border-border bg-popover p-1 shadow-md z-20">
                    <button
                      type="button"
                      disabled={isDeleting}
                      onClick={handleDeleteCourse}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-destructive hover:bg-destructive/10 rounded-sm transition-colors text-left"
                    >
                      <Trash2 size={13} />
                      <span>Delete course</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Progress Overview Bar */}
          <div className="p-4 rounded-xl border border-border/70 bg-card/60 shadow-xs space-y-3">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 font-medium">
                <TrendingUp size={15} className="text-primary" />
                <span>Curriculum Progress</span>
              </div>
              <span className="font-semibold text-foreground">{course.summary.roadmapProgress}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-500 rounded-full"
                style={{ width: `${course.summary.roadmapProgress}%` }}
              />
            </div>
            <div className="flex items-center gap-6 pt-1 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <MessageSquare size={13} />
                <span>{sessions.length} {sessions.length === 1 ? 'chat' : 'chats'}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <FileText size={13} />
                <span>{notes.length} {notes.length === 1 ? 'living note' : 'living notes'}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <BookMarked size={13} />
                <span>{materials.length} {materials.length === 1 ? 'material' : 'materials'}</span>
              </div>
              {course.summary.dueReviewCount > 0 && (
                <button
                  type="button"
                  onClick={onStartReview}
                  className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 hover:underline font-medium ml-auto"
                >
                  <RotateCcw size={13} />
                  <span>{course.summary.dueReviewCount} reviews due</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Due Reviews Prominent Banner */}
        {course.summary.dueReviewCount > 0 && (
          <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
                <RotateCcw size={18} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-foreground">
                  {course.summary.dueReviewCount} concept {course.summary.dueReviewCount === 1 ? 'review is' : 'reviews are'} due
                </h4>
                <p className="text-xs text-muted-foreground">
                  Strengthen concepts linked to this course to maintain high recall and complete milestones.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              onClick={onStartReview}
              className="gap-1.5 shrink-0 bg-amber-600 hover:bg-amber-700 text-white"
            >
              <RotateCcw size={13} />
              <span>Review Course Concepts</span>
            </Button>
          </div>
        )}

        {/* Continue Learning Callout */}
        {nextNode && (
          <div className="p-5 rounded-xl border border-primary/20 bg-gradient-to-r from-primary/5 via-primary/2 to-transparent flex items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-primary font-medium">
                <Sparkles size={13} />
                <span>{nextNode.status === 'needs_review' ? 'Needs Review' : 'Next Recommended Milestone'}</span>
              </div>
              <h3 className="text-base font-semibold text-foreground">{nextNode.title}</h3>
              <p className="text-xs text-muted-foreground">Phase: {nextNode.phase}</p>
            </div>
            <Button
              size="sm"
              onClick={() => handleStartMilestone(nextNode)}
              className="gap-1.5 shrink-0"
            >
              <Play size={13} />
              <span>Study with Tutor</span>
            </Button>
          </div>
        )}

        {/* Roadmap & Curriculum */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-foreground">Curriculum Roadmap</h2>
              <p className="text-xs text-muted-foreground">
                {course.roadmap.filter((n) => n.status === 'completed').length} of {course.roadmap.length} completed
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={isEvaluating}
                onClick={handleEvaluateProgression}
                className="gap-1.5 text-xs h-8"
                title="Synchronize milestone progression with your demonstrated concepts"
              >
                <Sparkles size={13} className={isEvaluating ? 'animate-spin text-primary' : ''} />
                <span>{isEvaluating ? 'Checking…' : 'Check Progression'}</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowTailorDialog(true)}
                className="gap-1.5 text-xs h-8"
              >
                <Wand2 size={13} />
                <span>Tailor Curriculum</span>
              </Button>
            </div>
          </div>

          {evaluationFeedback && (
            <div className="p-3 rounded-lg border border-primary/20 bg-primary/5 text-xs text-foreground flex items-center justify-between gap-2">
              <span>{evaluationFeedback}</span>
              <button
                type="button"
                onClick={() => setEvaluationFeedback(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={14} />
              </button>
            </div>
          )}

          {/* Tailor Curriculum Dialog */}
          {showTailorDialog && (
            <form
              onSubmit={handleTailorCurriculum}
              className="p-4 rounded-xl border border-border/80 bg-card shadow-sm space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wand2 size={15} className="text-primary" />
                  <h3 className="text-sm font-semibold">Tailor Curriculum with AI</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowTailorDialog(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X size={14} />
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                Provide instructions on what to focus on or modify (e.g. &ldquo;Focus heavily on practical projects and code examples&rdquo;, &ldquo;Add a capstone project&rdquo;, &ldquo;Make math explanations rigorous&rdquo;).
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={tailorPrompt}
                  onChange={(e) => setTailorPrompt(e.target.value)}
                  placeholder="E.g. Focus on building projects, add advanced algorithms..."
                  className="flex-1 h-8 rounded-md border border-input bg-background px-3 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
                <Button size="sm" type="submit" disabled={isTailoring} className="h-8 gap-1 text-xs">
                  {isTailoring ? <Loader2 size={13} className="animate-spin" /> : <Wand2 size={13} />}
                  <span>{isTailoring ? 'Regenerating…' : 'Regenerate'}</span>
                </Button>
              </div>
            </form>
          )}

          <div className="space-y-6">
            {phases.map((phase) => {
              const phaseNodes = course.roadmap.filter((n) => n.phase === phase);
              return (
                <div key={phase} className="space-y-2.5">
                  <div className="flex items-center justify-between px-1">
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {phase}
                    </h3>
                    <button
                      type="button"
                      onClick={() => {
                        setActiveAddPhase(activeAddPhase === phase ? null : phase);
                        setNewMilestoneTitle('');
                      }}
                      className="text-[11px] text-primary hover:underline font-medium flex items-center gap-1"
                    >
                      <Plus size={11} />
                      <span>Add milestone</span>
                    </button>
                  </div>

                  {activeAddPhase === phase && (
                    <div className="flex gap-2 p-2.5 rounded-lg border border-dashed border-primary/40 bg-primary/2">
                      <input
                        type="text"
                        autoFocus
                        value={newMilestoneTitle}
                        onChange={(e) => setNewMilestoneTitle(e.target.value)}
                        placeholder="Milestone title..."
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            void handleAddMilestone(phase);
                          } else if (e.key === 'Escape') {
                            setActiveAddPhase(null);
                          }
                        }}
                        className="flex-1 h-7 rounded border border-input bg-background px-2.5 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      />
                      <Button
                        size="sm"
                        disabled={!newMilestoneTitle.trim() || isAddingMilestone}
                        onClick={() => void handleAddMilestone(phase)}
                        className="h-7 text-xs px-2.5"
                      >
                        Add
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setActiveAddPhase(null)}
                        className="h-7 text-xs px-2"
                      >
                        Cancel
                      </Button>
                    </div>
                  )}

                  <div className="grid gap-2">
                    {phaseNodes.map((node) => {
                      const isCompleted = node.status === 'completed';
                      const isInProgress = node.status === 'in_progress';
                      const isNeedsReview = node.status === 'needs_review';
                      const isUpdating = updatingNodeId === node.id;

                      return (
                        <div
                          key={node.id}
                          className={cn(
                            'group flex items-center justify-between p-3 rounded-lg border transition-all',
                            isCompleted
                              ? 'bg-muted/20 border-border/50 text-muted-foreground'
                              : isNeedsReview
                              ? 'bg-amber-500/5 border-amber-500/30 text-foreground'
                              : isInProgress
                              ? 'bg-primary/5 border-primary/30 text-foreground shadow-xs'
                              : 'bg-card border-border/70 hover:border-border text-foreground'
                          )}
                        >
                          <div className="flex items-center gap-3 min-w-0 flex-1">
                            <button
                              type="button"
                              disabled={isUpdating}
                              onClick={() => handleToggleNodeStatus(node)}
                              className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
                              title={
                                isCompleted
                                  ? 'Mark planned'
                                  : isNeedsReview
                                  ? 'Start review / mark in progress'
                                  : isInProgress
                                  ? 'Mark completed'
                                  : 'Mark in progress'
                              }
                            >
                              {isCompleted ? (
                                <CheckCircle2 size={18} className="text-emerald-500" />
                              ) : isNeedsReview ? (
                                <AlertCircle size={18} className="text-amber-500" />
                              ) : isInProgress ? (
                                <div className="w-4.5 h-4.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                              ) : (
                                <Circle size={18} />
                              )}
                            </button>
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <span
                                className={cn(
                                  'text-sm font-medium truncate',
                                  isCompleted && 'line-through text-muted-foreground'
                                )}
                              >
                                {node.title}
                              </span>
                              {isNeedsReview && (
                                <span className="text-[10px] uppercase tracking-wider font-semibold text-amber-600 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded shrink-0">
                                  Needs review
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
                            <div className="hidden group-hover:flex items-center gap-0.5 mr-1">
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-6 w-6 text-muted-foreground"
                                onClick={() => handleMoveMilestone(node.id, 'up')}
                                title="Move up"
                              >
                                <ArrowUp size={12} />
                              </Button>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-6 w-6 text-muted-foreground"
                                onClick={() => handleMoveMilestone(node.id, 'down')}
                                title="Move down"
                              >
                                <ArrowDown size={12} />
                              </Button>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-6 w-6 text-muted-foreground hover:text-destructive"
                                onClick={() => handleDeleteMilestone(node.id)}
                                title="Delete milestone"
                              >
                                <Trash2 size={12} />
                              </Button>
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 text-xs px-2 gap-1 text-muted-foreground hover:text-foreground"
                              onClick={() => handleStartMilestone(node)}
                            >
                              <span>Study</span>
                              <ChevronRight size={13} />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Course Materials & Reference Library */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <BookMarked size={16} className="text-primary" />
                <span>Reference Library & Materials</span>
              </h2>
              <p className="text-xs text-muted-foreground">
                Documents in this library are automatically retrieved and cited by the tutor during study sessions.
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAddMaterialDialog(true)}
              className="gap-1.5 text-xs h-8"
            >
              <Plus size={13} />
              <span>Add material</span>
            </Button>
          </div>

          {showAddMaterialDialog && (
            <form
              onSubmit={handleAddMaterial}
              className="p-4 rounded-xl border border-border/80 bg-card shadow-sm space-y-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Add Course Reference Material</h3>
                <button
                  type="button"
                  onClick={() => setShowAddMaterialDialog(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X size={14} />
                </button>
              </div>

              <div className="flex gap-2 border-b border-border pb-2">
                <button
                  type="button"
                  onClick={() => setMaterialMode('upload')}
                  className={cn(
                    'px-3 py-1 rounded text-xs font-medium transition-colors',
                    materialMode === 'upload' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'
                  )}
                >
                  Upload File (PDF / Markdown / Text)
                </button>
                <button
                  type="button"
                  onClick={() => setMaterialMode('text')}
                  className={cn(
                    'px-3 py-1 rounded text-xs font-medium transition-colors',
                    materialMode === 'text' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'
                  )}
                >
                  Paste Text / Notes
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <label className="text-xs font-medium text-muted-foreground w-16">Role:</label>
                  <select
                    value={materialRole}
                    onChange={(e) => setMaterialRole(e.target.value as 'reference' | 'textbook' | 'lecture_notes')}
                    className="h-8 rounded-md border border-input bg-background px-2 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="reference">Reference Document</option>
                    <option value="textbook">Textbook / Chapter</option>
                    <option value="lecture_notes">Lecture Notes</option>
                  </select>
                </div>

                {materialMode === 'upload' ? (
                  <div className="space-y-2">
                    <input
                      type="file"
                      accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="text-xs file:mr-2 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                    />
                    <p className="text-[11px] text-muted-foreground">Supported: PDF, Markdown, UTF-8 text, and diagrams up to 50 MB.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={textTitle}
                      onChange={(e) => setTextTitle(e.target.value)}
                      placeholder="Material title (e.g. Chapter 4 Key Theorems)..."
                      className="w-full h-8 rounded-md border border-input bg-background px-3 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                    <textarea
                      value={textBody}
                      onChange={(e) => setTextBody(e.target.value)}
                      rows={4}
                      placeholder="Paste reference text or lecture notes here..."
                      className="w-full rounded-md border border-input bg-background p-3 text-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-1">
                <Button
                  size="sm"
                  type="button"
                  variant="outline"
                  onClick={() => setShowAddMaterialDialog(false)}
                  className="h-8 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  type="submit"
                  disabled={isAddingMaterial || (materialMode === 'upload' ? !uploadFile : !textTitle.trim())}
                  className="h-8 text-xs gap-1.5"
                >
                  {isAddingMaterial ? <Loader2 size={13} className="animate-spin" /> : <FileUp size={13} />}
                  <span>{isAddingMaterial ? 'Adding…' : 'Add Material'}</span>
                </Button>
              </div>
            </form>
          )}

          {materials.length === 0 ? (
            <div className="p-6 rounded-lg border border-dashed border-border/80 text-center space-y-2">
              <p className="text-xs text-muted-foreground">No reference materials attached to this course yet.</p>
              <Button size="sm" variant="outline" onClick={() => setShowAddMaterialDialog(true)} className="gap-1.5 text-xs">
                <FileUp size={13} />
                <span>Add first material</span>
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {materials.map((m) => (
                <div
                  key={m.id}
                  className="p-3 rounded-lg border border-border/70 bg-card hover:border-border transition-all flex items-start justify-between gap-3 group"
                >
                  <div className="min-w-0 flex-1 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-foreground truncate">
                        {m.title}
                      </span>
                      <span className="text-[10px] uppercase font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded shrink-0">
                        {m.role.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground flex items-center gap-2">
                      <span>{(m.byteCount / 1024).toFixed(0)} KB</span>
                      <span>•</span>
                      <span className="capitalize">{m.status.replace('_', ' ')}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-1 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-muted-foreground hover:text-foreground"
                      onClick={() => void handleInspectMaterial(m)}
                      title="Inspect extracted passages"
                    >
                      <Eye size={13} />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={() => void handleDeleteMaterial(m.id)}
                      title="Detach from course"
                    >
                      <Trash2 size={13} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Passages Preview Modal */}
        {inspectingMaterial && (
          <div className="p-4 rounded-xl border border-border bg-card shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Eye size={15} className="text-primary" />
                <h3 className="text-sm font-semibold">Extracted Passages: {inspectingMaterial.title}</h3>
              </div>
              <button
                type="button"
                onClick={() => setInspectingMaterial(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={14} />
              </button>
            </div>

            {loadingPassages ? (
              <div className="flex items-center justify-center p-6 text-muted-foreground gap-2">
                <Loader2 size={16} className="animate-spin text-primary" />
                <span className="text-xs">Loading extracted passages…</span>
              </div>
            ) : !passages || passages.length === 0 ? (
              <p className="text-xs text-muted-foreground p-3">No passages extracted yet. Material may still be processing.</p>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {passages.map((p, idx) => (
                  <div key={p.id || p.spanId || idx} className="p-2.5 rounded border border-border/50 bg-muted/20 text-xs space-y-1">
                    <span className="text-[10px] text-muted-foreground uppercase font-semibold">Passage {idx + 1} (Page {p.pageIndex + 1})</span>
                    <p className="text-foreground leading-relaxed whitespace-pre-wrap">{p.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Sessions & Notes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          {/* Recent Course Chats */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <MessageSquare size={15} />
                <span>Course Chats</span>
              </h2>
              <button
                type="button"
                onClick={() => onNewSession()}
                className="text-xs text-primary hover:underline font-medium"
              >
                + New chat
              </button>
            </div>

            {sessions.length === 0 ? (
              <div className="p-6 rounded-lg border border-dashed border-border/80 text-center space-y-2">
                <p className="text-xs text-muted-foreground">No chats in this course yet.</p>
                <Button size="sm" variant="outline" onClick={() => onNewSession()}>
                  Start first chat
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-border/50 rounded-lg border border-border/70 bg-card overflow-hidden">
                {sessions.slice(0, 5).map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => onOpenSession(s.id)}
                    className="w-full p-3 text-left hover:bg-muted/40 transition-colors flex items-center justify-between gap-3 group"
                  >
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <p className="text-xs font-medium text-foreground truncate group-hover:text-primary transition-colors">
                        {s.title}
                      </p>
                      <p className="text-[11px] text-muted-foreground flex items-center gap-2">
                        <span>{s.turnCount} {s.turnCount === 1 ? 'message' : 'messages'}</span>
                        <span>•</span>
                        <span>{new Date(s.updatedAt).toLocaleDateString()}</span>
                      </p>
                    </div>
                    <ChevronRight size={14} className="text-muted-foreground shrink-0" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Living Notes */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <FileText size={15} />
                <span>Living Notes</span>
              </h2>
            </div>

            {notes.length === 0 ? (
              <div className="p-6 rounded-lg border border-dashed border-border/80 text-center space-y-2">
                <p className="text-xs text-muted-foreground">No notes created in this course yet.</p>
                <p className="text-[11px] text-muted-foreground/80">Notes generated during your course chats will appear here.</p>
              </div>
            ) : (
              <div className="divide-y divide-border/50 rounded-lg border border-border/70 bg-card overflow-hidden">
                {notes.slice(0, 5).map((n) => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => onOpenNote?.(n.id)}
                    className="w-full p-3 text-left hover:bg-muted/40 transition-colors flex items-center justify-between gap-3 group"
                  >
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <p className="text-xs font-medium text-foreground truncate group-hover:text-primary transition-colors">
                        {n.title}
                      </p>
                      <p className="text-[11px] text-muted-foreground flex items-center gap-2">
                        {Array.isArray(n.frontmatter.tags) && typeof n.frontmatter.tags[0] === 'string' && <span>#{n.frontmatter.tags[0]}</span>}
                        <span>•</span>
                        <span>{new Date(n.updatedAt).toLocaleDateString()}</span>
                      </p>
                    </div>
                    <ChevronRight size={14} className="text-muted-foreground shrink-0" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
