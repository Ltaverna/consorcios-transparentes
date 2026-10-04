import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { veredicto } = require('./logica.js');

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
