"""Shared inline/standalone assessment with private keys and atomic evidence."""
from datetime import datetime, timedelta

from .assessment_lifecycle import AssessmentLifecycle
from .assessment_models import AnswerCommand, QuizCreate
from .context_service import canonical_evidence, retrieve, save_manifest
from .material_service import MaterialService, problem
from .models import utc_now
from .workflow_store import WorkflowStore, uid


class QuizService:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider
        self.records = WorkflowStore(store)
        self.lifecycle = AssessmentLifecycle(store, provider)

    def create(self, owner, request: QuizCreate, connection, quiz_id):
        session = MaterialService(self.store).session(owner, request.session_id)
        graph = self.store.get_graph(session.graph_id)
        concepts = request.concept_ids or [session.current_concept_id or graph.concepts[0].id]
        if not set(concepts).issubset({c.id for c in graph.concepts}):
            problem("invalid_concept", "Choose concepts from this learning session.")
        quiz = {"id": quiz_id, "sessionId": session.id, "conceptIds": concepts, "graphId": graph.id,
                "graphVersion": graph.version, "title": session.goal or graph.title, "count": request.count,
                "difficulty": request.difficulty, "origin": request.origin, "status": "ready", "current": None,
                "attempts": [], "presentations": [], "revision": 1, "mode": request.mode,
                "modeConfig": request.mode_config, "selectedSpanIds": request.selected_span_ids,
                "deadlineAt": None, "remainingSeconds": request.mode_config.get("duration_seconds")}
        self.records.put(connection, owner, "quiz", quiz, session.id)
        return quiz

    def public(self, owner, quiz_id):
        quiz = self.records.read(owner, quiz_id, "quiz")
        MaterialService(self.store).session(owner, quiz["sessionId"])
        current = self.records.read(owner, quiz["current"], "presentation") if quiz["current"] else None
        history = [self.records.read(owner, aid, "attempt") for aid in quiz["attempts"]]
        first = [a for a in history if not a.get("retryOf")]
        evaluated = [a for a in first if a["score"] is not None and a["status"] != "contested"]
        quiz["summary"] = {"score": round(100 * sum(a["score"] for a in evaluated) / len(evaluated)) if evaluated else None,
                           "evaluated": len(evaluated), "attempted": len(first), "total": quiz["count"],
                           "assisted": sum(a["assisted"] for a in first), "skipped": sum(a["status"] == "skipped" for a in first),
                           "dontKnow": sum(a["outcome"] == "dont_know" for a in first),
                           "independentCorrect": sum(a["score"] == 1 and not a["assisted"] for a in evaluated),
                           "retries": sum(bool(a.get("retryOf")) for a in history),
                           "contested": sum(a["status"] == "contested" for a in first)}
        if quiz.get("mode") == "timed_short_quiz" and quiz.get("deadlineAt"):
            quiz["remainingSeconds"] = max(0, int((datetime.fromisoformat(quiz["deadlineAt"]) - utc_now()).total_seconds()))
        return {**quiz, "current": current, "attempts": history, "quality": {"approvedOnly": True}}

    def _ensure_active_time(self, quiz):
        if quiz.get("mode") != "timed_short_quiz" or not quiz.get("deadlineAt"):
            return
        deadline = datetime.fromisoformat(quiz["deadlineAt"])
        if utc_now() >= deadline:
            problem("quiz_time_elapsed", "Time is up for this quiz. Your saved answers remain available.", 409)

    def _exposure_count(self, owner, stem):
        return self.lifecycle.exposure_count(owner, stem)

    def _record_exposure(self, conn, owner, item_id, stem):
        self.lifecycle.record_exposure(conn, owner, item_id, stem, origin="quiz")

    def persist_rejections(self, owner, quiz_id, artifacts: list[dict]):
        self.lifecycle.persist_rejections(owner, quiz_id, artifacts)

    def prepare(self, owner, quiz_id, revision):
        quiz = self.records.read(owner, quiz_id, "quiz")
        self._ensure_active_time(quiz)
        if quiz["revision"] != revision:
            problem("revision_conflict", "Reload this quiz before continuing.", 409)
        if quiz["current"]:
            current = self.records.read(owner, quiz["current"], "presentation")
            if not current.get("attemptId"):
                problem("answer_pending", "Answer or skip the current question first.", 409)
        first = [self.records.read(owner, aid, "attempt") for aid in quiz["attempts"]]
        if len([a for a in first if not a.get("retryOf")]) >= quiz["count"]:
            return quiz, None, None, None
        if self.provider is None:
            problem("provider_required", "Connect a model and attach reference material to generate checked questions.", 503)
        session = MaterialService(self.store).session(owner, quiz["sessionId"])
        graph = self.store.get_graph(quiz["graphId"])
        if graph.version != quiz["graphVersion"]:
            problem("curriculum_changed", "The source graph changed. Start a new quiz.", 409)
        recent = next((a for a in reversed(first) if a["status"] != "contested"), None)
        index = len([a for a in first if not a.get("retryOf")]) % len(quiz["conceptIds"])
        concept_id = recent["conceptId"] if recent and recent["score"] is not None and recent["score"] < .5 else quiz["conceptIds"][index]
        concept = next(c for c in graph.concepts if c.id == concept_id)
        sources = retrieve(self.store, owner, session.id, f"{session.goal} {concept.title} {concept.summary}", selected_span_ids=quiz.get("selectedSpanIds"))
        manifest = save_manifest(self.store, owner, session.id, concept.title, sources, selected_span_ids=quiz.get("selectedSpanIds"))
        difficulty = quiz["difficulty"]
        if difficulty == "adaptive":
            difficulty = "stretch" if recent and recent["score"] == 1 and not recent["assisted"] else "foundational" if recent and recent["score"] != 1 else "standard"
        previous = self.records.listing(owner, "item")
        context = {"conceptIds": [concept_id], "concept": concept.title, "objective": session.goal,
                   "difficulty": difficulty, "sources": sources, "manifestId": manifest["id"], "evidence": canonical_evidence(self.store, owner, graph).model_dump(mode="json"),
                   "recentFeedback": recent["feedback"] if recent else None, "questionNumber": len(first) + 1}
        item, item_record, presentation = self.lifecycle.prepare_item(
            owner,
            context=context,
            previous=previous,
            origin=quiz.get("origin") or "quiz",
            parent_id=quiz_id,
            parent_kind="quiz",
        )
        return quiz, item, item_record, presentation

    def commit_prepared(self, conn, owner, prepared):
        quiz, item, item_record, presentation = prepared
        if item is None:
            quiz["status"] = "completed"
        else:
            self.lifecycle.commit_presentation(
                conn, owner,
                item=item,
                item_record=item_record,
                presentation=presentation,
                parent_kind="quiz",
                parent_id=quiz["id"],
            )
            quiz["current"] = presentation["id"]
            quiz["presentations"].append(presentation["id"])
            quiz["status"] = "in_progress"
            if quiz.get("mode") == "timed_short_quiz" and not quiz.get("deadlineAt"):
                quiz["deadlineAt"] = (utc_now() + timedelta(seconds=int(quiz["remainingSeconds"]))).isoformat()
        self.records.put(conn, owner, "quiz", quiz, expected=quiz["revision"])
        return {"quizId": quiz["id"]}

    def private_item(self, owner, presentation_id):
        return self.lifecycle.load_private(owner, presentation_id)

    def grade(self, owner, quiz_id, command: AnswerCommand):
        quiz = self.records.read(owner, quiz_id, "quiz")
        self._ensure_active_time(quiz)
        presentation, _item = self.private_item(owner, command.presentation_id)
        if presentation.get("quizId") != quiz_id or quiz["current"] != presentation["id"]:
            problem("invalid_presentation", "Answer the current question.", 409)
        if presentation["attemptId"] or quiz["revision"] != command.expected_revision:
            problem("revision_conflict", "This answer was already submitted or the quiz changed.", 409)
        presentation, item, attempt = self.lifecycle.evaluate_response(
            owner, command.presentation_id, command.model_dump(),
        )
        attempt["quizId"] = quiz_id
        return quiz, presentation, item, attempt

    def commit_grade(self, conn, owner, graded):
        quiz, presentation, item, attempt = graded
        self.lifecycle.commit_attempt(
            conn, owner,
            presentation=presentation,
            item=item,
            attempt=attempt,
            graph_id=quiz["graphId"],
            graph_version=quiz["graphVersion"],
            evidence_kind="assessment",
            provenance_extra={"sessionId": quiz["sessionId"], "quizId": quiz["id"], "origin": quiz.get("origin") or "quiz"},
            parent_id=quiz["id"],
        )
        quiz["attempts"].append(attempt["id"])
        first_count = sum(not self.records.read(owner, aid, "attempt", conn).get("retryOf") for aid in quiz["attempts"])
        quiz["status"] = "completed" if first_count >= quiz["count"] else "feedback"
        self.records.put(conn, owner, "quiz", quiz, expected=quiz["revision"])
        return {"quizId": quiz["id"], "attemptId": attempt["id"]}

    def hint(self, owner, presentation_id, conn):
        presentation = self.lifecycle.record_hint(conn, owner, presentation_id)
        return {"quizId": presentation.get("quizId")}

    def retry(self, conn, owner, quiz_id, revision):
        quiz = self.records.read(owner, quiz_id, "quiz", conn)
        self._ensure_active_time(quiz)
        original = self.records.read(owner, quiz["current"], "presentation", conn) if quiz["current"] else None
        if not original or not original["attemptId"]:
            problem("answer_required", "Submit the current answer before retrying.", 409)
        presentation = {**original, "id": uid("presentation"), "attemptId": None,
                        "retryOf": original.get("retryOf") or original["attemptId"], "hints": []}
        self.records.put(conn, owner, "presentation", presentation, quiz_id)
        quiz["current"] = presentation["id"]
        quiz["presentations"].append(presentation["id"])
        quiz["status"] = "in_progress"
        self.records.put(conn, owner, "quiz", quiz, expected=revision)
        return {"quizId": quiz_id}

    def challenge(self, conn, owner, presentation_id, reason):
        challenge = self.lifecycle.challenge_presentation(conn, owner, presentation_id, reason)
        presentation = self.records.read(owner, presentation_id, "presentation", conn)
        return {"quizId": presentation.get("quizId"), "challengeId": challenge["id"]}

    def pause(self, conn, owner, quiz_id, revision):
        quiz = self.records.read(owner, quiz_id, "quiz", conn)
        if quiz.get("mode") == "timed_short_quiz" and quiz.get("deadlineAt"):
            remaining = max(0, int((datetime.fromisoformat(quiz["deadlineAt"]) - utc_now()).total_seconds()))
            quiz["remainingSeconds"], quiz["deadlineAt"] = remaining, None
        quiz["status"] = "paused"
        self.records.put(conn, owner, "quiz", quiz, expected=revision)
        return {"quizId": quiz_id}

    def resume(self, conn, owner, quiz_id, revision):
        quiz = self.records.read(owner, quiz_id, "quiz", conn)
        if quiz.get("mode") == "timed_short_quiz":
            if not quiz.get("remainingSeconds"):
                problem("quiz_time_elapsed", "This timed quiz has no remaining time.", 409)
            quiz["deadlineAt"] = (utc_now() + timedelta(seconds=int(quiz["remainingSeconds"]))).isoformat()
        quiz["status"] = "in_progress" if quiz["current"] else "ready"
        self.records.put(conn, owner, "quiz", quiz, expected=revision)
        return {"quizId": quiz_id}
