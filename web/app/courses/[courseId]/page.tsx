import LearningWorkspace from "@/components/learning-workspace";

/** Dedicated Course route — deep links directly into the course workspace. */
export default async function CoursePage({
  params,
}: {
  params: Promise<{ courseId: string }>;
}) {
  const { courseId } = await params;
  return <LearningWorkspace initialCourseId={courseId} />;
}
