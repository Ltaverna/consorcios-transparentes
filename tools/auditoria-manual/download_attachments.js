async (page) => {
  const fs = require('fs'); const path = require('path');
  const SC = '/tmp/claude-1000/-tmp-expensa/6a21c58a-78d1-4c71-bbae-3c304135eb13/scratchpad/';
  const OUT = '/home/novakorp/Descargas/Comprobantes Rivadavia 2069/';
  const load = f => { let d = JSON.parse(fs.readFileSync(SC + f, 'utf8')); if (typeof d === 'string') d = JSON.parse(d); return d; };
  const sets = [['2026-08 Agosto', load('redconar_agosto.json')], ['2026-07 Julio', load('redconar_julio.json')]];
  const safe = s => s.normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9 ._-]+/g, '_').replace(/\s+/g, ' ').trim().slice(0, 80);
  const log = []; const manifest = [];
  for (const [folder, rows] of sets) {
    const dir = path.join(OUT, folder); fs.mkdirSync(dir, { recursive: true });
    let n = 0;
    for (const r of rows) {
      n++;
      const prov = safe(r.prov).slice(0, 30);
      const valor = r.valor.replace(/[^0-9.,]/g, '');
      let k = 0;
      for (const a of r.att) {
        k++;
        try {
          const resp = await page.request.get(a.url);
          const ct = resp.headers()['content-type'] || '';
          const body = await resp.body();
          let ext = 'bin';
          if (ct.includes('pdf') || body.slice(0, 4).toString() === '%PDF') ext = 'pdf';
          else if (ct.includes('jpeg') || ct.includes('jpg')) ext = 'jpg';
          else if (ct.includes('png')) ext = 'png';
          else if (ct.includes('html')) ext = 'html';
          const base = `${String(n).padStart(2, '0')}-${k} ${r.fecha} ${prov} ${valor} ${a.src[0]} ${safe(a.name).replace(/\.(pdf|jpg|jpeg|png)$/i, '')}`;
          const file = path.join(dir, base + '.' + ext);
          fs.writeFileSync(file, body);
          manifest.push({ mes: folder, n, k, fecha: r.fecha, proveedor: r.prov, valor: r.valor, caja: r.caja, factura: r.fact, categoria: r.cat, desc: r.desc, src: a.src, nombre: a.name, archivo: path.basename(file), bytes: body.length, ct, status: resp.status() });
        } catch (e) { log.push(`ERR ${folder} ${n}-${k} ${a.name}: ${e.message}`); manifest.push({ mes: folder, n, k, fecha: r.fecha, proveedor: r.prov, valor: r.valor, nombre: a.name, error: e.message }); }
      }
      if (r.att.length === 0) manifest.push({ mes: folder, n, k: 0, fecha: r.fecha, proveedor: r.prov, valor: r.valor, caja: r.caja, factura: r.fact, categoria: r.cat, desc: r.desc, nombre: '(sin adjuntos)' });
    }
  }
  fs.writeFileSync(SC + 'manifest.json', JSON.stringify(manifest, null, 1));
  const ok = manifest.filter(m => m.archivo).length;
  return JSON.stringify({ descargados: ok, errores: log.slice(0, 20), sinAdjuntos: manifest.filter(m => m.k === 0).length });
}
