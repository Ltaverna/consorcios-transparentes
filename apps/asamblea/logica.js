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

  function _propDe(uf, units){ const u = units.find(x => x.uf === uf); return u ? u.prop : null; }

  // Cuántos propietarios DISTINTOS (por 'prop') representa un mandatario.
  function contarRepresentados(mandatario, poderes, units){
    const props = new Set();
    for(const uf in poderes){ if(poderes[uf] === mandatario){ const p = _propDe(Number(uf), units); if(p) props.add(p); } }
    return props.size;
  }

  // ¿Puede 'mandatario' tomar el poder de la unidad 'uf'? Art. 25 h.
  function puedeAsignarMandatario(mandatario, uf, poderes, units){
    // Poder pendiente sin mandatario asignado (true/no-string): no aplica la validación.
    if(typeof mandatario !== 'string') return { ok:true };
    const mandUnit = units.find(x => x.prop === mandatario || ('tercero:' + x.prop) === mandatario);
    if(mandUnit && mandUnit.admin) return { ok:false, motivo:'El administrador no puede actuar como mandatario (art. 25 h).' };
    const u = units.find(x => x.uf === uf);
    const propDeUf = u ? u.prop : null;
    const props = new Set();
    for(const k in poderes){ if(poderes[k] === mandatario){ const p = _propDe(Number(k), units); if(p && p !== propDeUf) props.add(p); } }
    if(props.size >= 5) return { ok:false, motivo:'Un mandatario no puede representar a más de cinco propietarios (art. 25 h).' };
    return { ok:true };
  }

  // Estado de una proposición del art. 2060. La oposición de ausentes tumba la proposición
  // solo si alcanza la MISMA mayoría absoluta del total (doble: unidades y porcentual).
  function evaluarProposicion(oposicion, totales, vencida){
    const tumba = oposicion.n > totales.N/2 && oposicion.pct > totales.totalPct/2;
    if(tumba) return { estado:'decaida', tumba:true };
    if(!vencida) return { estado:'circulando', tumba:false };
    return { estado:'firme', tumba:false };
  }

  return { veredicto, contarRepresentados, puedeAsignarMandatario, evaluarProposicion };
})();
if (typeof module !== 'undefined' && module.exports) module.exports = CTLogica;
