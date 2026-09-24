import { z } from 'zod';

const number = z.number().finite();
const point = z.tuple([number, number]);
const short = (length: number) => z.string().trim().min(1).max(length);

export const visualTypes = ['bar', 'line', 'scatter', 'pie', 'function', 'distribution',
  'flow', 'concept', 'architecture', 'science', 'timeline', 'simulation'] as const;
export type VisualType = typeof visualTypes[number];

const provenance = z.object({
  kind: z.enum(['user', 'tool', 'calculated', 'illustrative']),
  label: short(160),
  sourceIds: z.array(short(160)).max(8).default([]),
});
const series = z.object({
  name: short(80),
  expression: short(120).optional(),
  points: z.array(point).max(120).default([]),
});
const node = z.object({
  id: short(80), label: short(120), detail: z.string().max(240).optional(),
  group: z.string().max(60).optional(), emphasis: z.boolean().default(false),
});
const edge = z.object({
  source: short(80), target: short(80), label: z.string().max(100).optional(),
  kind: z.enum(['data', 'control', 'relationship']).default('relationship'),
  emphasis: z.boolean().default(false),
});
const annotation = z.union([short(120), z.object({
  kind: z.enum(['point', 'intercept', 'extremum', 'tangent', 'secant', 'derivative',
    'region', 'interval', 'asymptote', 'arrow', 'label']),
  label: short(120), x: number.optional(), y: number.optional(),
  x2: number.optional(), y2: number.optional(),
})]);
const event = z.object({
  date: short(40), order: number, title: short(120),
  description: z.string().max(320).optional(),
  category: z.string().max(60).optional(), emphasis: z.boolean().default(false),
});
const primitive = z.object({
  kind: z.enum(['axis', 'object', 'particle', 'charge', 'vector', 'force', 'velocity',
    'trajectory', 'wave', 'field_line', 'circuit_component']),
  label: z.string().max(100).optional(), x: number.min(-10).max(10),
  y: number.min(-10).max(10), x2: number.min(-10).max(10).optional(),
  y2: number.min(-10).max(10).optional(), magnitude: number.min(-1000).max(1000).optional(),
});
const parameter = z.object({
  id: z.string().regex(/^[A-Za-z][A-Za-z0-9_]*$/).max(40),
  label: short(80), minimum: number.min(-10000).max(10000),
  maximum: number.min(-10000).max(10000), step: number.positive().max(1000),
  initial: number.min(-10000).max(10000),
}).refine(p => p.minimum < p.maximum && p.minimum <= p.initial && p.initial <= p.maximum);

export const visualizationSchema = z.object({
  version: z.literal(1), revision: z.number().int().positive().default(1), rendererVersion: z.literal(1).default(1),
  sourceLessonId: z.string().max(100).optional(),
  id: z.string().regex(/^[A-Za-z0-9_-]+$/).max(100), type: z.enum(visualTypes),
  title: short(140), purpose: z.string().max(180).optional(),
  description: z.string().max(280).optional(), provenance: provenance.optional(),
  blockIndex: z.number().int().min(0).max(20).default(0),
  afterParagraph: z.number().int().min(0).max(20).default(0),
  xLabel: z.string().max(80).optional(), yLabel: z.string().max(80).optional(),
  categories: z.array(short(80)).max(24).default([]),
  values: z.array(number.min(-1e9).max(1e9)).max(24).default([]),
  series: z.array(series).max(6).default([]),
  nodes: z.array(node).max(24).default([]), edges: z.array(edge).max(40).default([]),
  annotations: z.array(annotation).max(12).default([]),
  xDomain: z.tuple([number, number]).default([-10, 10]),
  distributionKind: z.enum(['normal', 'binomial', 'histogram', 'empirical']).optional(),
  distributionParams: z.record(z.string(), number).default({}),
  events: z.array(event).max(32).default([]),
  primitives: z.array(primitive).max(40).default([]),
  simulationModel: z.enum(['gradient_descent', 'projectile', 'ohms_law', 'queue', 'cache', 'network']).optional(),
  parameters: z.array(parameter).max(5).default([]),
  controls: z.record(z.string(), number).default({}),
}).superRefine((s, ctx) => {
  const issue = (message: string) => ctx.addIssue({ code: z.ZodIssueCode.custom, message });
  if (!(s.xDomain[0] < s.xDomain[1]) || Math.max(...s.xDomain.map(Math.abs)) > 1e6) issue('Invalid x range');
  if (['bar', 'pie'].includes(s.type) && (!s.categories.length || s.categories.length !== s.values.length)) issue('Chart data is incomplete');
  if (['bar', 'line', 'scatter', 'pie', 'timeline'].includes(s.type) && !s.provenance) issue('Chart provenance is required');
  if (s.type === 'pie' && (s.values.length > 8 || s.values.some(v => v < 0) || s.values.filter(v => v > 0).length < 2)) issue('Pie proportions are invalid');
  if (['line', 'scatter', 'function'].includes(s.type) && !s.series.length) issue('Series are required');
  if (['flow', 'concept', 'architecture'].includes(s.type) && !s.nodes.length) issue('Diagram nodes are required');
  const ids = new Set(s.nodes.map(n => n.id));
  if (ids.size !== s.nodes.length || s.edges.some(e => !ids.has(e.source) || !ids.has(e.target))) issue('Diagram connections are invalid');
  if (s.type === 'science' && !s.primitives.length) issue('Scientific primitives are required');
  if (s.type === 'timeline' && !s.events.length) issue('Timeline events are required');
  if (s.type === 'distribution' && !s.distributionKind) issue('Distribution model is required');
  if (s.type === 'simulation' && !s.simulationModel) issue('Simulation model is required');
});

export type VisualizationSpec = z.infer<typeof visualizationSchema>;
export function parseVisualization(value: unknown): VisualizationSpec | null {
  const parsed = visualizationSchema.safeParse(value);
  return parsed.success ? parsed.data : null;
}
