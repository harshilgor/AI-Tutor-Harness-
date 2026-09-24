import pytest
from pydantic import ValidationError

from backend.app.visualization_models import VisualizationSpec, validate_expression, validate_visualization_bundle
from backend.app.visualization_planner import has_visual_simulation_update, plan_visualizations, should_reserve_visual
from backend.app.visualization_parts import make_visual_parts
from backend.app.visualization_service import VisualChange, changed_spec, replace_in_journey

PROVENANCE = {"kind": "illustrative", "label": "Teaching example", "sourceIds": []}


@pytest.mark.parametrize("kind,data", [
    ("bar", {"categories": ["A", "B"], "values": [2, 3], "provenance": PROVENANCE}),
    ("pie", {"categories": ["A", "B"], "values": [2, 3], "provenance": PROVENANCE}),
    ("line", {"series": [{"name": "trend", "points": [[0, 2], [1, 3]]}], "provenance": PROVENANCE}),
    ("scatter", {"series": [{"name": "observations", "points": [[1, 2], [2, 4]]}], "provenance": PROVENANCE}),
    ("function", {"series": [{"name": "square", "expression": "x²"}, {"name": "line", "expression": "2x"}]}),
    ("distribution", {"distributionKind": "normal", "distributionParams": {"mean": 0, "sigma": 1}}),
    ("flow", {"nodes": [{"id": "a", "label": "Start"}, {"id": "b", "label": "End"}], "edges": [{"source": "a", "target": "b"}]}),
    ("concept", {"nodes": [{"id": "a", "label": "Supervised"}, {"id": "b", "label": "Unsupervised"}], "edges": [{"source": "a", "target": "b"}]}),
    ("architecture", {"nodes": [{"id": "cpu", "label": "CPU"}, {"id": "memory", "label": "Memory"}], "edges": [{"source": "cpu", "target": "memory"}]}),
    ("science", {"primitives": [{"kind": "object", "x": 0, "y": 0, "label": "Ball"}, {"kind": "force", "x": 0, "y": 0, "x2": 0, "y2": -2, "label": "Gravity"}]}),
    ("timeline", {"events": [{"date": "1947", "order": 1947, "title": "Transistor"}, {"date": "1971", "order": 1971, "title": "Microprocessor"}], "provenance": PROVENANCE}),
    ("simulation", {"simulationModel": "gradient_descent", "parameters": [{"id": "rate", "label": "Learning rate", "minimum": 0.01, "maximum": 1, "step": 0.01, "initial": 0.2}]}),
])
def test_every_renderer_has_a_valid_server_contract(kind, data):
    spec = VisualizationSpec.model_validate({"version": 1, "id": kind, "type": kind, "title": kind, **data})
    assert spec.type == kind
    assert spec.model_dump(mode="json", by_alias=True)["rendererVersion"] == 1


@pytest.mark.parametrize("data", [
    {"type": "bar", "categories": ["A"], "values": [1]},
    {"type": "scatter", "series": [{"name": "x", "points": []}], "provenance": PROVENANCE},
    {"type": "pie", "categories": ["A", "B"], "values": [2, -1], "provenance": PROVENANCE},
    {"type": "flow", "nodes": [{"id": "a", "label": "A"}], "edges": [{"source": "a", "target": "missing"}]},
    {"type": "science", "primitives": [{"kind": "force", "x": 999, "y": 0}]},
    {"type": "simulation", "simulationModel": "gradient_descent"},
    {"type": "timeline", "events": [{"date": "today", "order": float("nan"), "title": "Bad"}]},
    {"type": "function", "series": [{"name": "x", "expression": "x"}], "annotations": [{"kind": "point", "label": "bad", "x": float("inf"), "y": 0}]},
])
def test_malformed_specs_are_rejected(data):
    with pytest.raises(ValidationError):
        VisualizationSpec.model_validate({"version": 1, "id": "bad", "title": "Bad", **data})


@pytest.mark.parametrize("expression", ["__import__('os')", "x;alert(1)", "x.__class__", "x[0]", "pow(x,2)"])
def test_model_expressions_cannot_inject_program_code(expression):
    with pytest.raises(ValueError):
        validate_expression(expression)


def test_safe_math_accepts_familiar_notation_and_bounds_output():
    assert validate_expression("2x + x²") == "2*x + x**2"
    assert validate_expression("e^x") == "e**x"
    assert validate_visualization_bundle({"visualizations": [{"html": "<script>"}]}) == []


def test_duplicate_visual_ids_in_one_bundle_are_rejected():
    value = {"version": 1, "id": "same", "type": "function", "title": "Square", "series": [{"name": "y", "expression": "x^2"}]}
    assert validate_visualization_bundle({"visualizations": [value, value]}) == []


def test_visual_parts_survive_reopen_between_text_paragraphs():
    spec = VisualizationSpec.model_validate({"version": 1, "id": "square", "type": "function",
        "title": "Square", "series": [{"name": "y", "expression": "x^2"}]})
    parts = make_visual_parts("First idea.\n\nNow inspect the curve.\n\nNotice its minimum.", [spec])
    assert [part["kind"] for part in parts] == ["text", "visualization", "text", "text"]
    assert parts[1]["visualizationId"] == "square"


def test_visual_planner_respects_decision_and_invalid_output_fallback():
    class Provider:
        def __init__(self, payload): self.payload = payload
        def complete_json(self, prompt, max_tokens):
            assert "Never return HTML" in prompt and max_tokens == 2400
            return self.payload
    square = {"version": 1, "id": "square", "type": "function", "title": "Square",
              "series": [{"name": "y", "expression": "x^2"}]}
    assert plan_visualizations(Provider({"visualizations": [square]}), {}, "Plot y=x^2")[0].id == "square"
    assert plan_visualizations(Provider({"visualizations": [{"html": "unsafe"}]}), {}, "Definition") == []
    assert should_reserve_visual("Plot y=x²")
    assert not should_reserve_visual("What is an activation function?")
    assert should_reserve_visual("Explain how supervised learning differs from unsupervised learning")
    assert should_reserve_visual("Teach me Newton's second law")


def test_explicit_visual_type_is_enforced():
    class Provider:
        def complete_json(self, prompt, max_tokens):
            return {"visualizations": [
                {"version": 1, "id": "bar", "type": "bar", "title": "Bars", "categories": ["A", "B"], "values": [1, 2], "provenance": PROVENANCE},
                {"version": 1, "id": "curve", "type": "function", "title": "Curve", "series": [{"name": "y", "expression": "x^2"}]},
            ]}
    result = plan_visualizations(Provider(), {"visualType": "function"}, "Plot the function")
    assert [visual.type for visual in result] == ["function"]


def test_parameter_followup_updates_same_addressable_visual():
    prior = VisualizationSpec.model_validate({"version": 1, "id": "gradient", "type": "simulation", "title": "Gradient descent",
        "simulationModel": "gradient_descent", "parameters": [{"id": "rate", "label": "Learning rate", "minimum": 0.01, "maximum": 1, "step": 0.01, "initial": 0.2}]})
    lesson = {"id": "lesson_old", "blocks": [{"visualizations": [prior.model_dump(mode="json", by_alias=True)]}]}
    journey = {"turns": [{"lesson": lesson}, {"lesson": {"id": "lesson_new", "blocks": []}}]}
    assert has_visual_simulation_update({"journey": journey}, "Make it 0.01")
    assert not has_visual_simulation_update({"journey": {"turns": []}}, "Make it 0.01")
    updated = plan_visualizations(object(), {"journey": journey}, "Make the learning rate 0.01")[0]
    assert updated.id == prior.id and updated.revision == 2 and updated.source_lesson_id == "lesson_old"
    assert updated.parameters[0].initial == 0.01
    assert replace_in_journey(journey, "lesson_old", updated)
    assert journey["turns"][0]["lesson"]["blocks"][0]["visualizations"][0]["revision"] == 2
    with pytest.raises(Exception):
        changed_spec(updated, VisualChange(operation="change_parameter", expectedRevision=1, parameterId="rate", value=0.3))
