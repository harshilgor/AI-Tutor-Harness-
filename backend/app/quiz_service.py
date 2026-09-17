"""Shared inline/standalone assessment with private keys and atomic evidence."""
import json
import random
from datetime import datetime, timedelta
from sqlalchemy import text
from .assessment_models import AnswerCommand, Candidate, QuizCreate
from .assessment_generation import QualityRejected, evaluate, generate_item
from .context_service import canonical_evidence, retrieve, save_manifest
from .material_service import MaterialService, problem
from .state_models import EvidenceCreate
from .state_service import LearnerStateService
from .workflow_store import WorkflowStore, encoded, uid
from .models import utc_now


class QuizService:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider
        self.records = WorkflowStore(store)

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
        with self.store.engine.connect() as conn:
            row = conn.execute(text("SELECT presented_count FROM assessment_item_exposure WHERE owner_id=:owner AND fingerprint=:fingerprint"), {"owner": owner, "fingerprint": __import__("backend.app.assessment_generation", fromlist=["fingerprint"]).fingerprint(stem)}).first()
            return int(row[0]) if row else 0

    def _record_exposure(self, conn, owner, item_id, stem):
        from .assessment_generation import fingerprint
        values = {"owner": owner, "fingerprint": fingerprint(stem), "item": item_id, "now": utc_now()}
        if self.store.engine.dialect.name == "postgresql":
            conn.execute(text("INSERT INTO assessment_item_exposure(owner_id,fingerprint,item_id,presented_count,last_presented_at) VALUES(:owner,:fingerprint,:item,1,:now) ON CONFLICT(owner_id,fingerprint) DO UPDATE SET presented_count=assessment_item_exposure.presented_count+1,last_presented_at=EXCLUDED.last_presented_at"), values)
        else:
            conn.execute(text("INSERT INTO assessment_item_exposure(owner_id,fingerprint,item_id,presented_count,last_presented_at) VALUES(:owner,:fingerprint,:item,1,:now) ON CONFLICT(owner_id,fingerprint) DO UPDATE SET presented_count=presented_count+1,last_presented_at=excluded.last_presented_at"), values)

    def persist_rejections(self, owner, quiz_id, artifacts: list[dict]):
        """Keep private author/checker audit records, without creating an assessable item."""
        with self.store.transaction() as conn:
            for artifact in artifacts:
                rejection_id = uid("rejected_item")
                self.records.put(conn, owner, "assessment_author", {"id": uid("author"), "rejectedItemId": rejection_id, **artifact["author"]}, quiz_id)
                self.records.put(conn, owner, "assessment_checker", {"id": uid("checker"), "rejectedItemId": rejection_id, **artifact["checker"]}, rejection_id)

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
        try:
            item, author, check = generate_item(self.provider, context, previous)
        except QualityRejected as rejected:
            self.persist_rejections(owner, quiz_id, rejected.artifacts)
            raise
        if self._exposure_count(owner, item.stem) >= 3:
            problem("item_overexposed", "A similar question has already been shown often. Generate a new question.", 409)
        public = item.model_dump(exclude={"solution", "correct_ids", "criteria", "hints"})
        item_id, presentation_id = uid("item"), uid("presentation")
        options = public["options"][:]
        random.SystemRandom().shuffle(options)
        presentation = {**public, "id": presentation_id, "itemId": item_id, "quizId": quiz_id,
                        "options": options, "hints": [], "attemptId": None, "difficulty": difficulty,
                        "contextId": manifest["id"], "sources": sources, "hintCount": len(item.hints)}
        # The author/checker are separate durable records. A presentation is only constructed after checker approval.
        return quiz, item, {**public, "id": item_id, "author": author, "checker": check, "qualityStatus": "approved", "contextId": manifest["id"], "provider": self.provider.provider_name}, presentation

    def commit_prepared(self, conn, owner, prepared):
        quiz, item, item_record, presentation = prepared
        if item is None:
            quiz["status"] = "completed"
        else:
            if item_record.get("qualityStatus") != "approved" or item_record.get("checker", {}).get("status") != "approved":
                problem("item_not_approved", "This question did not pass quality checks.", 409)
            self.records.put(conn, owner, "item", item_record, quiz["id"])
            self.records.put(conn, owner, "assessment_author", {"id": uid("author"), "itemId": item_record["id"], **item_record["author"]}, item_record["id"])
            self.records.put(conn, owner, "assessment_checker", {"id": uid("checker"), "itemId": item_record["id"], **item_record["checker"]}, item_record["id"])
            conn.execute(text("INSERT INTO item_solutions(item_id,payload) VALUES(:id,:payload)"), {"id": item_record["id"], "payload": item.model_dump_json()})
            self.records.put(conn, owner, "presentation", presentation, quiz["id"])
            self._record_exposure(conn, owner, item_record["id"], item.stem)
            quiz["current"] = presentation["id"]
            quiz["presentations"].append(presentation["id"])
            quiz["status"] = "in_progress"
            if quiz.get("mode") == "timed_short_quiz" and not quiz.get("deadlineAt"):
                quiz["deadlineAt"] = (utc_now() + timedelta(seconds=int(quiz["remainingSeconds"]))).isoformat()
        self.records.put(conn, owner, "quiz", quiz, expected=quiz["revision"])
        return {"quizId": quiz["id"]}

    def private_item(self, owner, presentation_id):
        presentation = self.records.read(owner, presentation_id, "presentation")
        item_record = self.records.read(owner, presentation["itemId"], "item")
        if item_record.get("qualityStatus") != "approved" or presentation.get("contested"):
            problem("item_not_approved", "This question is no longer available for assessment.", 409)
        with self.store.engine.connect() as conn:
            row = conn.execute(text("SELECT payload FROM item_solutions WHERE item_id=:id"), {"id": presentation["itemId"]}).one()
        return presentation, Candidate.model_validate_json(row[0])

    def grade(self, owner, quiz_id, command: AnswerCommand):
        quiz = self.records.read(owner, quiz_id, "quiz")
        self._ensure_active_time(quiz)
        presentation, item = self.private_item(owner, command.presentation_id)
        if presentation["quizId"] != quiz_id or quiz["current"] != presentation["id"]:
            problem("invalid_presentation", "Answer the current question.", 409)
        if presentation["attemptId"] or quiz["revision"] != command.expected_revision:
            problem("revision_conflict", "This answer was already submitted or the quiz changed.", 409)
        if command.outcome == "answer":
            if item.kind == "short" and (not command.response.strip() or command.selected_ids):
                problem("answer_required", "Write your reasoning before submitting.")
            if item.kind != "short" and (not command.selected_ids or not set(command.selected_ids).issubset({o.id for o in item.options}) or len(set(command.selected_ids)) != len(command.selected_ids)):
                problem("invalid_selection", "Select a valid answer.")
            if item.kind == "single" and len(command.selected_ids) != 1:
                problem("invalid_selection", "Select one answer.")
        result = evaluate(self.provider, item, command.model_dump())
        attempt = {**result, "id": uid("attempt"), "presentationId": presentation["id"], "quizId": quiz_id,
                   "conceptId": item.concept_id, "response": command.response, "selectedIds": command.selected_ids,
                   "outcome": command.outcome, "assisted": bool(presentation["hints"] or presentation.get("retryOf")), "solution": item.solution,
                   "retryOf": presentation.get("retryOf"),
                   "correctIds": item.correct_ids, "evidenceId": None, "conceptState": None}
        return quiz, presentation, item, attempt

    def commit_grade(self, conn, owner, graded):
        quiz, presentation, item, attempt = graded
        if presentation.get("contested"):
            attempt.update(status="contested", score=None, feedback="Question flagged. This response is excluded from scoring and learning evidence.")
        # Revision is checked before state admission; a racing hint forces reevaluation.
        presentation["attemptId"] = attempt["id"]
        self.records.put(conn, owner, "presentation", presentation, expected=presentation["revision"])
        if attempt["score"] is not None:
            # Selection and model evaluations remain uncalibrated. Reliability below
            # the reducer's independent-demonstration threshold avoids false mastery.
            admitted = LearnerStateService(self.store).admit_evidence(owner, EvidenceCreate(
                evidence_key=attempt["id"], concept_id=item.concept_id, graph_id=quiz["graphId"], graph_version=quiz["graphVersion"],
                kind="assessment", outcome="correct" if attempt["score"] == 1 else "partial" if attempt["score"] > 0 else "incorrect",
                condition="assisted" if attempt["assisted"] else "independent", score=attempt["score"],
                evaluator="quiz-rubric-v1", reliability=.4,
                provenance={"attemptId": attempt["id"], "itemId": presentation["itemId"], "outcome": attempt["outcome"], "uncalibrated": True}), connection=conn)
            attempt["evidenceId"] = admitted.evidence.id
            attempt["conceptState"] = admitted.learner_state.status.value if admitted.learner_state else None
        self.records.put(conn, owner, "attempt", attempt, quiz["id"])
        self.records.put(conn, owner, "assessment_evaluation", {"id": uid("evaluation"), "attemptId": attempt["id"], "itemId": presentation["itemId"], "role": "evaluator", "status": attempt["status"], "score": attempt["score"], "assisted": attempt["assisted"]}, attempt["id"])
        quiz["attempts"].append(attempt["id"])
        first_count = sum(not self.records.read(owner, aid, "attempt", conn).get("retryOf") for aid in quiz["attempts"])
        quiz["status"] = "completed" if first_count >= quiz["count"] else "feedback"
        self.records.put(conn, owner, "quiz", quiz, expected=quiz["revision"])
        return {"quizId": quiz["id"], "attemptId": attempt["id"]}

    def hint(self, owner, presentation_id, conn):
        presentation, item = self.private_item(owner, presentation_id)
        if presentation["attemptId"]:
            problem("already_answered", "Hints are only available before answering.", 409)
        index = len(presentation["hints"])
        if index < len(item.hints):
            presentation["hints"].append(item.hints[index])
            self.records.put(conn, owner, "presentation", presentation, expected=presentation["revision"])
        return {"quizId": presentation["quizId"]}

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
        presentation = self.records.read(owner, presentation_id, "presentation", conn)
        presentation["contested"] = True
        self.records.put(conn, owner, "presentation", presentation, expected=presentation["revision"])
        challenge = {"id": uid("challenge"), "presentationId": presentation_id, "reason": reason, "status": "excluded_pending_review"}
        item = self.records.read(owner, presentation["itemId"], "item", conn)
        item["qualityStatus"] = "withdrawn"
        item["withdrawalReason"] = "learner_challenged"
        self.records.put(conn, owner, "item", item, expected=item["revision"])
        if presentation["attemptId"]:
            attempt = self.records.read(owner, presentation["attemptId"], "attempt", conn)
            if attempt.get("evidenceId"):
                LearnerStateService(self.store).withdraw_evidence(owner, attempt["evidenceId"], "assessment_disputed", connection=conn)
            attempt.update(status="contested", conceptState=None)
            self.records.put(conn, owner, "attempt", attempt, expected=attempt["revision"])
        self.records.put(conn, owner, "challenge", challenge, presentation_id)
        return {"quizId": presentation["quizId"], "challengeId": challenge["id"]}

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
