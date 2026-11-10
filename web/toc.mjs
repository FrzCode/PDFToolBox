// Candidato per la web app: lettura/scrittura dei segnalibri con mupdf.js.
// Porta di normalizza_toc (main.py) e di set_toc (PyMuPDF) costruendo /Outlines a mano.

export function normalizzaToc(toc) {
  const out = [];
  let prec = 0;
  for (const [lvl0, titolo, pag] of toc) {
    const lvl = Math.max(1, Math.min(lvl0, prec + 1));
    out.push([lvl, titolo, pag]);
    prec = lvl;
  }
  return out;
}

// toc: [[livello, titolo, pagina_1based], ...], già normalizzato.
// Sostituisce l'eventuale indice esistente.
export function scriviToc(doc, toc) {
  const catalog = doc.getTrailer().get("Root");
  if (toc.length === 0) {
    catalog.delete("Outlines");
    return;
  }
  // 1. albero dai livelli piatti
  const radice = { figli: [] };
  const pila = [radice];
  for (const [lvl, titolo, pag] of toc) {
    const nodo = { titolo, pag, figli: [] };
    pila.length = lvl;               // torna al genitore del livello lvl
    pila[lvl - 1].figli.push(nodo);
    pila[lvl] = nodo;
  }
  // 2. oggetti PDF
  const outlines = doc.addObject(doc.newDictionary());
  outlines.put("Type", doc.newName("Outlines"));

  const contaDiscendenti = (n) =>
    n.figli.reduce((s, f) => s + 1 + contaDiscendenti(f), 0);

  const crea = (nodo, genitore) => {
    nodo.ref = doc.addObject(doc.newDictionary());
    nodo.ref.put("Title", doc.newString(nodo.titolo));
    nodo.ref.put("Parent", genitore);
    const dest = doc.newArray();
    dest.push(doc.findPage(nodo.pag - 1));
    dest.push(doc.newName("Fit"));
    nodo.ref.put("Dest", dest);
    for (const f of nodo.figli) crea(f, nodo.ref);
  };
  const collega = (fratelli, genitore) => {
    fratelli.forEach((n, i) => {
      if (i > 0) n.ref.put("Prev", fratelli[i - 1].ref);
      if (i < fratelli.length - 1) n.ref.put("Next", fratelli[i + 1].ref);
      if (n.figli.length) {
        n.ref.put("First", n.figli[0].ref);
        n.ref.put("Last", n.figli[n.figli.length - 1].ref);
        n.ref.put("Count", contaDiscendenti(n));
        collega(n.figli, n.ref);
      }
    });
    genitore.put("First", fratelli[0].ref);
    genitore.put("Last", fratelli[fratelli.length - 1].ref);
  };
  for (const f of radice.figli) crea(f, outlines);
  collega(radice.figli, outlines);
  outlines.put("Count", contaDiscendenti(radice));
  catalog.put("Outlines", outlines);
}

// Lettura: [[livello, titolo, pagina_1based], ...] con loadOutline.
export function leggiToc(doc) {
  const out = [];
  const visita = (voci, lvl) => {
    for (const v of voci || []) {
      let pag = 0; // 0 = voce senza pagina (link esterno o destinazione non risolvibile)
      try {
        const p = v.page !== undefined ? v.page : doc.resolveLink(v.uri);
        if (Number.isInteger(p) && p >= 0) pag = p + 1;
      } catch (_) { /* resta 0 */ }
      out.push([lvl, v.title ?? "", pag]);
      visita(v.down, lvl + 1);
    }
  };
  visita(doc.loadOutline(), 1);
  return out;
}
