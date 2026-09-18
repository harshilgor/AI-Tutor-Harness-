"""Offline deterministic policy regression runner; it has no provider dependency."""
from __future__ import annotations
import json
from pathlib import Path
from .assessment_generation import deterministic_quality_failures
from .assessment_models import Candidate, Criterion, Option
FIXTURES = Path(__file__).resolve().parents[1] / "evaluation" / "fixtures.json"
def run(fixtures: Path = FIXTURES) -> dict:
    data = json.loads(fixtures.read_text(encoding="utf-8")); results=[]
    results.append({"id":"recommendation-next-action","passed":data["recommendation"]["expectedNext"] == "backpropagation" and "quiz-without-material" in data["recommendation"]["unavailable"]})
    note=data["noteContext"]; excerpt=note["body"][note["start"]:note["end"]]
    results.append({"id":"note-context-boundary","passed":excerpt == note["expected"] and "IGNORE" not in excerpt})
    a=data["assessment"]; item=Candidate(concept_id="c",family="arithmetic",kind="single",stem="Which claim is correct: " + a["duplicateStem"],reasoning_target="Infer a result from the addition rule.",options=[Option(id="a",label="Four"),Option(id="b",label="Five")],correct_ids=["a"],solution="Two plus two equals four by ordinary integer addition.",criteria=[Criterion(id="result",description="Identifies the supported result.",weight=1)],hints=["Add the two values."],source_ids=["owned-span"])
    results.append({"id":"assessment-quality","passed":a["expectedFailure"] in deterministic_quality_failures(item,[{"spanId":"owned-span"}],[{"stem":"Which claim is correct: " + a["previousStem"],"family":"arithmetic"}])})
    grading=data["grading"]; results.append({"id":"grading-contract","passed":float(set(grading["selected"]) == set(grading["correct"])) == grading["expectedScore"]})
    source=data["sourceSupport"]; results.append({"id":"source-support","passed":set(source["candidateSources"]).issubset(source["allowedSources"]) == source["expectedSupported"]})
    results.append({"id":"false-mastery","passed":data["falseMastery"]["event"] == "recommendation_selection" and not data["falseMastery"]["expectedStateWrite"]})
    return {"suite":"forma-deterministic-evaluation","fixtureVersion":data["version"],"passed":all(x["passed"] for x in results),"outcomes":results}
if __name__ == "__main__": print(json.dumps(run(),sort_keys=True))
