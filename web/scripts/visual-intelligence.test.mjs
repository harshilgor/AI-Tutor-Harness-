import assert from 'node:assert/strict';
import test from 'node:test';
import { binomialDistribution, compileMathExpression, normalDistribution, sampleFunction } from '../lib/visual-math.ts';
import { layoutDiagram } from '../lib/visual-layout.ts';
import { parseVisualization, visualTypes } from '../lib/visualization-spec.ts';

test('safe math interpreter supports familiar notation and rejects executable input', () => {
  assert.equal(compileMathExpression('2x + x²')(3), 15);
  assert.ok(Math.abs(compileMathExpression('sin(pi / 2)')(0) - 1) < 1e-12);
  assert.equal(compileMathExpression("__import__('os')"), null);
  assert.equal(compileMathExpression('x;alert(1)'), null);
  assert.equal(compileMathExpression('constructor(x)'), null);
});

test('function sampling bounds work and cuts undefined and discontinuous regions', () => {
  const inverse = sampleFunction('1/x', [-2, 2], 241);
  assert.equal(inverse.length, 241);
  assert.equal(inverse[120].y, null);
  assert.ok(inverse.every(point => point.y === null || Number.isFinite(point.y)));
  assert.equal(sampleFunction('x^10000', [-10, 10]).length, 181);
  assert.ok(sampleFunction('x^10000', [-10, 10]).some(point => point.y === null));
  assert.equal(sampleFunction('x', [-1e8, 1e8]).length, 0);
});

test('normal and binomial distributions produce bounded deterministic data', () => {
  const normal = normalDistribution(0, 1);
  const binomial = binomialDistribution(10, 0.5);
  assert.equal(normal.length, 121);
  assert.equal(binomial.length, 11);
  assert.ok(Math.abs(binomial.reduce((sum, point) => sum + point.y, 0) - 1) < 1e-12);
  assert.deepEqual(binomialDistribution(101, 0.5), []);
  assert.equal(normalDistribution(0, 1, 10000).length, 241);
  assert.deepEqual(binomialDistribution(2, Number.NaN), []);
});

test('client schema recognizes all renderer types and rejects invalid chart provenance', () => {
  for (const type of visualTypes) {
    const common = { version: 1, id: `test-${type}`, type, title: type };
    const specific = type === 'bar' || type === 'pie' ? { categories: ['A', 'B'], values: [2, 3], provenance: { kind: 'illustrative', label: 'Example' } }
      : type === 'line' || type === 'scatter' ? { provenance: { kind: 'illustrative', label: 'Example' }, series: [{ name: 'Data', points: [[0, 1], [1, 2]] }] }
      : type === 'function' ? { series: [{ name: 'Curve', expression: 'x^2' }] }
      : type === 'distribution' ? { distributionKind: 'normal', distributionParams: { mean: 0, sigma: 1 } }
      : type === 'flow' || type === 'concept' || type === 'architecture' ? { nodes: [{ id: 'a', label: 'A' }] }
      : type === 'science' ? { primitives: [{ kind: 'object', x: 0, y: 0 }] }
      : type === 'timeline' ? { provenance: { kind: 'illustrative', label: 'Example' }, events: [{ date: '1', order: 1, title: 'Event' }] }
      : { simulationModel: 'queue' };
    assert.ok(parseVisualization({ ...common, ...specific }), `expected ${type} to validate`);
  }
  assert.equal(parseVisualization({ version: 1, id: 'bad', type: 'bar', title: 'Bad', categories: ['A'], values: [1] }), null);
});

test('diagram layout places directed branches left-to-right and handles cycles deterministically', () => {
  const nodes = [{ id: 'input', label: 'Input' }, { id: 'left', label: 'Left' }, { id: 'right', label: 'Right' }, { id: 'done', label: 'Done' }];
  const edges = [{ source: 'input', target: 'left' }, { source: 'input', target: 'right' }, { source: 'left', target: 'done' }, { source: 'right', target: 'done' }];
  const layout = layoutDiagram(nodes, edges);
  const positions = Object.fromEntries(layout.nodes.map(node => [node.id, node]));
  assert.ok(positions.input.x < positions.left.x && positions.input.x < positions.right.x);
  assert.ok(positions.left.y !== positions.right.y);
  assert.equal(layout.edges.length, 4);
  assert.ok(Number.isFinite(layout.width) && Number.isFinite(layout.height));
  const cycle = layoutDiagram(nodes, [...edges, { source: 'done', target: 'input' }]);
  assert.deepEqual(cycle.nodes.map(node => [node.id, node.x, node.y]), layoutDiagram(nodes, [...edges, { source: 'done', target: 'input' }]).nodes.map(node => [node.id, node.x, node.y]));
});
