import type { VisualizationSpec } from './visualization-spec';

type Node = VisualizationSpec['nodes'][number];
type Edge = VisualizationSpec['edges'][number];
export type PositionedNode = Node & { x: number; y: number };
export type DiagramLayout = {
  width: number; height: number; nodes: PositionedNode[];
  edges: Array<Edge & { x1: number; y1: number; x2: number; y2: number }>;
  groups: Array<{ label: string; x: number; y: number; width: number; height: number }>;
};

/** Bounded left-to-right layout. Cycles fall back to stable input order. */
export function layoutDiagram(nodes: Node[], edges: Edge[]): DiagramLayout {
  const byId = new Map(nodes.map(n => [n.id, n]));
  const indegree = new Map(nodes.map(n => [n.id, 0]));
  for (const edge of edges) if (byId.has(edge.source) && byId.has(edge.target)) {
    indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
  }
  const rank = new Map(nodes.map(n => [n.id, 0]));
  const queue = nodes.filter(n => indegree.get(n.id) === 0).map(n => n.id);
  const visited = new Set<string>();
  while (queue.length) {
    const id = queue.shift()!;
    if (visited.has(id)) continue;
    visited.add(id);
    for (const edge of edges.filter(e => e.source === id && byId.has(e.target))) {
      rank.set(edge.target, Math.min(8, Math.max(rank.get(edge.target) ?? 0, (rank.get(id) ?? 0) + 1)));
      indegree.set(edge.target, (indegree.get(edge.target) ?? 1) - 1);
      if (indegree.get(edge.target) === 0) queue.push(edge.target);
    }
  }
  for (const node of nodes) if (!visited.has(node.id)) rank.set(node.id, Math.min(8, Math.floor(visited.size / 4)));
  const columns = new Map<number, Node[]>();
  for (const node of nodes) columns.set(rank.get(node.id) ?? 0, [...(columns.get(rank.get(node.id) ?? 0) ?? []), node]);
  const maxRows = Math.max(1, ...[...columns.values()].map(column => column.length));
  const height = Math.max(280, maxRows * 106 + 48);
  const width = Math.max(620, (Math.max(0, ...columns.keys()) + 1) * 210 + 72);
  const positioned = nodes.map(node => {
    const column = columns.get(rank.get(node.id) ?? 0) ?? [];
    const row = column.findIndex(item => item.id === node.id);
    return { ...node, x: 110 + (rank.get(node.id) ?? 0) * 210, y: 52 + (row + 1) * height / (column.length + 1) };
  });
  const points = new Map(positioned.map(node => [node.id, node]));
  const connections = edges.flatMap(edge => {
    const source = points.get(edge.source), target = points.get(edge.target);
    return source && target ? [{ ...edge, x1: source.x + 82, y1: source.y, x2: target.x - 82, y2: target.y }] : [];
  });
  const groups = [...new Set(positioned.map(n => n.group).filter((x): x is string => Boolean(x)))].map(label => {
    const members = positioned.filter(n => n.group === label);
    const left = Math.min(...members.map(n => n.x)) - 96;
    const top = Math.min(...members.map(n => n.y)) - 48;
    return { label, x: left, y: top, width: Math.max(...members.map(n => n.x)) - left + 96,
      height: Math.max(...members.map(n => n.y)) - top + 55 };
  });
  return { width, height, nodes: positioned, edges: connections, groups };
}
