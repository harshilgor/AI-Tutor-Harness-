import LearningWorkspace from "@/components/learning-workspace";

/** Stable session route — server snapshot is authoritative; path survives cleared localStorage. */
export default async function SessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <LearningWorkspace initialSessionId={sessionId} />;
}
