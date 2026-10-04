import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const marked = require('./vendor/marked.min.js');

const enc = readFileSync(new URL('./encargado.md', import.meta.url), 'utf8');
const html = marked.parse(enc);

test('negritas: no quedan ** sin convertir en el encargado', () => {
  assert.ok(!html.includes('**'), 'quedaron ** literales en el HTML');
  assert.ok(html.includes('<strong>'), 'no se generó ninguna negrita');
});

test('listas numeradas: se generan <ol>', () => {
  assert.ok(html.includes('<ol'), 'no se generó ninguna lista ordenada');
});

test('listas con viñeta: se generan <ul>', () => {
  assert.ok(html.includes('<ul'), 'no se generó ninguna lista con viñeta');
});

test('encabezados: se generan <h2>', () => {
  assert.ok(html.includes('<h2'), 'no se generó ningún h2');
});

test('blockquotes: se generan <blockquote>', () => {
  assert.ok(html.includes('<blockquote'), 'no se generó ningún blockquote');
});

// Verificar reglamento.md también
const reg = readFileSync(new URL('./reglamento.md', import.meta.url), 'utf8');
const regHtml = marked.parse(reg);

test('reglamento: no quedan ** sin convertir', () => {
  assert.ok(!regHtml.includes('**'), 'quedaron ** literales en el HTML del reglamento');
});
