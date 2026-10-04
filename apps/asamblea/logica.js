// Lógica pura de la asamblea. Sin DOM ni estado global: entra data, sale resultado.
// Se embebe en index.html (make_votacion.py) y se importa desde logica.test.mjs.
// IMPORTANTE: este archivo NO debe contener la secuencia "</script" — se inyecta crudo
// dentro de un <script> del HTML generado y cerraría el tag antes de tiempo.
const CTLogica = (function () {
  // Veredicto de una opción de moción según la regla y la doble mayoría (unidades y porcentual).
  // regla: 'abs' (>50% del total), '2/3' (>=2/3 del total), 'pres' (>50% de los presentes).
  // o: {n, pct, abst}; totales: {N, totalPct}; part: {partN, partPct} (presentes+poderes).
  function veredicto(regla, o, totales, part) {
    if (o.abst) return null;
    let needN, needPct, base;
    if (regla === 'abs') { needN = totales.N / 2; needPct = totales.totalPct / 2; base = 'del total'; }
    else if (regla === '2/3') { needN = totales.N * 2 / 3; needPct = totales.totalPct * 2 / 3; base = 'del total'; }
    else { needN = part.partN / 2; needPct = part.partPct / 2; base = 'de los presentes'; }
    const okN = regla === '2/3' ? o.n >= needN : o.n > needN;
    const okP = regla === '2/3' ? o.pct >= needPct : o.pct > needPct;
    return { ok: okN && okP, okN, okP, needN, needPct, base };
  }

  return { veredicto };
})();
if (typeof module !== 'undefined' && module.exports) module.exports = CTLogica;
