"""Versioned, bounded visual specifications. The model never supplies code or layout."""
from __future__ import annotations

import ast
import math
import re
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .session_models import ApiModel

VisualType = Literal["bar", "line", "scatter", "pie", "function", "distribution",
                     "flow", "concept", "architecture", "science", "timeline", "simulation"]
SimulationModel = Literal["gradient_descent", "projectile", "ohms_law", "queue", "cache", "network"]
FUNCTIONS = {"sin", "cos", "tan", "exp", "log", "sqrt", "abs"}


def normalize_expression(source: str) -> str:
    """Normalize familiar math notation before validating its syntax tree."""
    result = source.strip().replace("π", "pi").replace("−", "-").replace("×", "*").replace("÷", "/")
    for superscript, digit in (("²", "2"), ("³", "3")):
        result = result.replace(superscript, "^" + digit)
    result = re.sub(r"(\d|\))\s*(x|pi|e)\b", r"\1*\2", result)
    result = re.sub(r"(\d|x|\))\s*\(", r"\1*(", result)
    result = re.sub(r"(\d|\))\s*(sin|cos|tan|exp|log|sqrt|abs)\b", r"\1*\2", result)
    return result.replace("^", "**")


def validate_expression(source: str) -> str:
    if len(source) > 120:
        raise ValueError("expression is too long")
    normalized = normalize_expression(source)
    if not re.fullmatch(r"[A-Za-z0-9_+*/().,\s-]+", normalized):
        raise ValueError("expression has unsupported characters")
    try:
        nodes = list(ast.walk(ast.parse(normalized, mode="eval")))
    except SyntaxError as exc:
        raise ValueError("invalid expression") from exc
    if len(nodes) > 60:
        raise ValueError("expression is too complex")
    for node in nodes:
        if isinstance(node, ast.Name):
            if node.id not in {"x", "e", "pi"} | FUNCTIONS:
                raise ValueError("unknown mathematical symbol")
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or len(node.args) != 1 or node.keywords:
                raise ValueError("unsupported function")
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)) or not math.isfinite(node.value) or abs(node.value) > 1e6:
                raise ValueError("invalid numeric constant")
        elif not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult,
                                   ast.Div, ast.Pow, ast.UAdd, ast.USub, ast.Load)):
            raise ValueError("unsupported mathematical operation")
    return normalized


class VisualProvenance(ApiModel):
    kind: Literal["user", "tool", "calculated", "illustrative"]
    label: str = Field(min_length=1, max_length=160)
    source_ids: list[str] = Field(default_factory=list, max_length=8)


class VisualNode(ApiModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    label: str = Field(min_length=1, max_length=120)
    detail: str | None = Field(default=None, max_length=240)
    group: str | None = Field(default=None, max_length=60)
    emphasis: bool = False


class VisualEdge(ApiModel):
    source: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=80)
    label: str | None = Field(default=None, max_length=100)
    kind: Literal["data", "control", "relationship"] = "relationship"
    emphasis: bool = False


class VisualSeries(ApiModel):
    name: str = Field(min_length=1, max_length=80)
    expression: str | None = Field(default=None, max_length=120)
    points: list[tuple[float, float]] = Field(default_factory=list, max_length=120)


class VisualAnnotation(ApiModel):
    kind: Literal["point", "intercept", "extremum", "tangent", "secant", "derivative",
                  "region", "interval", "asymptote", "arrow", "label"]
    label: str = Field(min_length=1, max_length=120)
    x: float | None = Field(default=None, ge=-1e6, le=1e6, allow_inf_nan=False)
    y: float | None = Field(default=None, ge=-1e6, le=1e6, allow_inf_nan=False)
    x2: float | None = Field(default=None, ge=-1e6, le=1e6, allow_inf_nan=False)
    y2: float | None = Field(default=None, ge=-1e6, le=1e6, allow_inf_nan=False)


class TimelineEvent(ApiModel):
    date: str = Field(min_length=1, max_length=40)
    order: float
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=320)
    category: str | None = Field(default=None, max_length=60)
    emphasis: bool = False


class SciencePrimitive(ApiModel):
    kind: Literal["axis", "object", "particle", "charge", "vector", "force",
                  "velocity", "trajectory", "wave", "field_line", "circuit_component"]
    label: str | None = Field(default=None, max_length=100)
    x: float = Field(ge=-10, le=10)
    y: float = Field(ge=-10, le=10)
    x2: float | None = Field(default=None, ge=-10, le=10)
    y2: float | None = Field(default=None, ge=-10, le=10)
    magnitude: float | None = Field(default=None, ge=-1000, le=1000)


class SimulationParameter(ApiModel):
    id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    label: str = Field(min_length=1, max_length=80)
    minimum: float = Field(ge=-10000, le=10000)
    maximum: float = Field(ge=-10000, le=10000)
    step: float = Field(gt=0, le=1000)
    initial: float = Field(ge=-10000, le=10000)

    @model_validator(mode="after")
    def check_range(self):
        if self.minimum >= self.maximum or not self.minimum <= self.initial <= self.maximum:
            raise ValueError("invalid simulation parameter range")
        return self


class VisualizationSpec(ApiModel):
    version: Literal[1] = 1
    revision: int = Field(default=1, ge=1)
    renderer_version: Literal[1] = 1
    source_lesson_id: str | None = Field(default=None, max_length=100)
    id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    type: VisualType
    title: str = Field(min_length=1, max_length=140)
    purpose: str | None = Field(default=None, max_length=180)
    description: str | None = Field(default=None, max_length=280)
    provenance: VisualProvenance | None = None
    block_index: int = Field(default=0, ge=0, le=20)
    after_paragraph: int = Field(default=0, ge=0, le=20)
    x_label: str | None = Field(default=None, max_length=80)
    y_label: str | None = Field(default=None, max_length=80)
    categories: list[str] = Field(default_factory=list, max_length=24)
    values: list[float] = Field(default_factory=list, max_length=24)
    series: list[VisualSeries] = Field(default_factory=list, max_length=6)
    nodes: list[VisualNode] = Field(default_factory=list, max_length=24)
    edges: list[VisualEdge] = Field(default_factory=list, max_length=40)
    annotations: list[str | VisualAnnotation] = Field(default_factory=list, max_length=12)
    x_domain: tuple[float, float] = (-10, 10)
    distribution_kind: Literal["normal", "binomial", "histogram", "empirical"] | None = None
    distribution_params: dict[str, float] = Field(default_factory=dict)
    events: list[TimelineEvent] = Field(default_factory=list, max_length=32)
    primitives: list[SciencePrimitive] = Field(default_factory=list, max_length=40)
    simulation_model: SimulationModel | None = None
    parameters: list[SimulationParameter] = Field(default_factory=list, max_length=5)
    controls: dict[str, float] = Field(default_factory=dict)

    @field_validator("categories")
    @classmethod
    def check_categories(cls, value):
        if any(not label.strip() or len(label) > 80 for label in value):
            raise ValueError("chart categories need short labels")
        return value

    @model_validator(mode="after")
    def check_shape(self):
        if any(not math.isfinite(v) or abs(v) > 1e9 for v in self.values):
            raise ValueError("chart values must be finite and bounded")
        if any(not math.isfinite(v) or abs(v) > 1e9 for s in self.series for point in s.points for v in point):
            raise ValueError("series points must be finite and bounded")
        if any(not math.isfinite(v) or abs(v) > 1e6 for v in self.x_domain) or self.x_domain[0] >= self.x_domain[1]:
            raise ValueError("x domain must be finite, increasing and bounded")
        if self.type in {"bar", "pie"} and (not self.categories or len(self.categories) != len(self.values)):
            raise ValueError("bar and pie need matching categories and values")
        if self.type == "pie" and (len(self.values) > 8 or any(v < 0 for v in self.values) or sum(v > 0 for v in self.values) < 2):
            raise ValueError("pie needs two to eight nonnegative parts")
        if self.type in {"line", "scatter"} and (not self.series or any(not s.points for s in self.series)):
            raise ValueError("line and scatter need point series")
        if self.type in {"bar", "line", "scatter", "pie", "timeline"} and self.provenance is None:
            raise ValueError("quantitative charts need provenance")
        if self.type == "function" and not self.series:
            raise ValueError("function graph needs series")
        if self.type == "distribution":
            if self.distribution_kind is None:
                raise ValueError("distribution needs a named model")
            if self.distribution_kind in {"histogram", "empirical"} and not self.series:
                raise ValueError("empirical distribution needs observations")
            if self.distribution_kind == "normal" and self.distribution_params.get("sigma", 0) <= 0:
                raise ValueError("normal distribution needs positive sigma")
            if self.distribution_kind == "binomial" and (not 1 <= self.distribution_params.get("n", 0) <= 100 or not 0 <= self.distribution_params.get("p", -1) <= 1):
                raise ValueError("binomial distribution needs n and p")
        if any(not math.isfinite(v) or abs(v) > 1e6 for v in self.distribution_params.values()):
            raise ValueError("distribution parameters must be finite and bounded")
        for series in self.series:
            if series.expression:
                if self.type != "function":
                    raise ValueError("expressions belong in function graphs")
                validate_expression(series.expression)
            elif not series.points:
                raise ValueError("series needs points or a function")
        if self.type in {"flow", "concept", "architecture"} and not self.nodes:
            raise ValueError("diagram needs nodes")
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes) or any(e.source not in ids or e.target not in ids for e in self.edges):
            raise ValueError("diagram edges must reference distinct existing nodes")
        if self.type == "science" and not self.primitives:
            raise ValueError("science visual needs primitives")
        if self.type == "timeline" and not self.events:
            raise ValueError("timeline needs events")
        if any(not math.isfinite(event.order) or abs(event.order) > 1e6 for event in self.events):
            raise ValueError("timeline order must be finite and bounded")
        if self.type == "simulation":
            if self.simulation_model is None:
                raise ValueError("simulation needs an approved model")
            if self.simulation_model in {"gradient_descent", "projectile", "ohms_law"} and not self.parameters:
                raise ValueError("continuous simulation needs parameters")
        if len({p.id for p in self.parameters}) != len(self.parameters):
            raise ValueError("simulation parameter ids must be unique")
        if any(not math.isfinite(v) or not -1e4 <= v <= 1e4 for v in self.controls.values()):
            raise ValueError("controls must be finite and bounded")
        return self


class VisualizationBundle(ApiModel):
    visualizations: list[VisualizationSpec] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [visual.id for visual in self.visualizations]
        if len(ids) != len(set(ids)):
            raise ValueError("visualization ids must be unique")
        return self


def validate_visualization_bundle(value: Any) -> list[VisualizationSpec]:
    """Malformed visuals are omitted; text delivery remains authoritative."""
    try:
        return VisualizationBundle.model_validate(value).visualizations
    except Exception:
        return []
