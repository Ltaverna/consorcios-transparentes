import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { veredicto, contarRepresentados, puedeAsignarMandatario } = require('./logica.js');

const TOT = { N: 100, totalPct: 100 };
const PART = { partN: 60, partPct: 60 };

test('abs: gana si supera el 50% del total en unidades y porcentual', () => {
  const v = veredicto('abs', { n: 51, pct: 51, abst: false }, TOT, PART);
  assert.equal(v.ok, true);
});

test('abs: no alcanza si una de las dos mayorías falla', () => {
  const v = veredicto('abs', { n: 51, pct: 49, abst: false }, TOT, PART);
  assert.equal(v.ok, false);
});

test('2/3: usa >= y se mide sobre el total', () => {
  const v = veredicto('2/3', { n: 67, pct: 67, abst: false }, TOT, PART);
  assert.equal(v.ok, true);
});

test('2/3: pasa en el límite exacto (>=, no >)', () => {
  // N=99 -> needN=66 exacto; 66 >= 66 es true con >=, sería false con >
  const v = veredicto('2/3', { n: 66, pct: 66, abst: false }, { N: 99, totalPct: 99 }, PART);
  assert.equal(v.ok, true);
  assert.equal(v.okN, true);
});

test('pres: se mide sobre los presentes', () => {
  const v = veredicto('pres', { n: 31, pct: 31, abst: false }, TOT, PART);
  assert.equal(v.ok, true);
});

test('pres: no alcanza si solo una de las dos mayorías llega', () => {
  // n=31 supera partN/2=30, pero pct=28 no supera partPct/2=30
  const v = veredicto('pres', { n: 31, pct: 28, abst: false }, TOT, PART);
  assert.equal(v.ok, false);
  assert.equal(v.okN, true);
  assert.equal(v.okP, false);
});

test('abstención devuelve null', () => {
  assert.equal(veredicto('abs', { n: 0, pct: 0, abst: true }, TOT, PART), null);
});

const UNITS3 = [
  {uf:1, prop:'A'}, {uf:2, prop:'A'},
  {uf:3, prop:'B'}, {uf:4, prop:'C'}, {uf:5, prop:'D'},
  {uf:6, prop:'E'}, {uf:7, prop:'F'}, {uf:8, prop:'ADMIN', admin:true},
];

test('cuenta propietarios representados, no unidades', () => {
  assert.equal(contarRepresentados('MAND', {1:'MAND', 2:'MAND'}, UNITS3), 1);
});
test('permite hasta 5 propietarios y bloquea el 6º', () => {
  const poderes = {3:'MAND',4:'MAND',5:'MAND',6:'MAND',7:'MAND'};
  const r = puedeAsignarMandatario('MAND', 1, poderes, UNITS3);
  assert.equal(r.ok, false);
  assert.match(r.motivo, /cinco|5/i);
});
test('el administrador no puede ser mandatario', () => {
  const r = puedeAsignarMandatario('ADMIN', 3, {}, UNITS3);
  assert.equal(r.ok, false);
  assert.match(r.motivo, /administrador/i);
});
test('reasignar una unidad ya contada al mismo mandatario no suma de más', () => {
  const poderes = {3:'MAND',4:'MAND',5:'MAND',6:'MAND',7:'MAND'};
  assert.equal(puedeAsignarMandatario('MAND', 3, poderes, UNITS3).ok, true);
});
test('un poder pendiente (true, sin mandatario) no dispara el tope', () => {
  // 5 poderes pendientes (true) no son un mandatario: marcar un 6º debe permitirse
  const poderes = {1:true,2:true,3:true,4:true,5:true};
  assert.equal(puedeAsignarMandatario(true, 6, poderes, UNITS3).ok, true);
});

const { evaluarProposicion } = require('./logica.js');

test('firme si la oposición no alcanza la mayoría absoluta del total', () => {
  assert.equal(evaluarProposicion({n:10, pct:10}, {N:100, totalPct:100}, true).estado, 'firme');
});
test('decae si la oposición alcanza igual mayoría (ambos ejes)', () => {
  assert.equal(evaluarProposicion({n:51, pct:51}, {N:100, totalPct:100}, true).estado, 'decaida');
});
test('en una sola dimensión no alcanza: sigue firme', () => {
  assert.equal(evaluarProposicion({n:51, pct:49}, {N:100, totalPct:100}, true).estado, 'firme');
});
test('antes del vencimiento está en circulación', () => {
  assert.equal(evaluarProposicion({n:10, pct:10}, {N:100, totalPct:100}, false).estado, 'circulando');
});
test('si la oposición tumba, decae aún antes del vencimiento', () => {
  assert.equal(evaluarProposicion({n:60, pct:60}, {N:100, totalPct:100}, false).estado, 'decaida');
});
