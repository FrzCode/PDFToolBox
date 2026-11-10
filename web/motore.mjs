// Motore PDF: nessuna dipendenza da DOM o Worker. Riceve il modulo mupdf.
// Nel browser gira dentro il Worker, in Node lo si prova direttamente.
import { normalizzaToc, scriviToc, leggiToc } from "./toc.mjs";

const LATO_MAX = 4096; // pixel massimi per lato di una pagina renderizzata

export function creaMotore(mupdf) {
  const docs = new Map();
  let prossimoId = 1;

  const voce = (id) => {
    const v = docs.get(id);
    if (!v) throw new Error("Documento non aperto");
    return v;
  };

  const apriPdf = (bytes) => {
    let doc;
    try {
      doc = mupdf.Document.openDocument(bytes, "application/pdf").asPDF();
    } catch (e) {
      throw new Error("Il file non è un PDF leggibile");
    }
    if (!doc) throw new Error("Il file non è un PDF");
    return doc;
  };

  // Se larghezza è data (miniature) la scala si ricava da lì e l'uscita è JPEG.
  const renderizza = (doc, pagina, scala, larghezza = 0) => {
    const page = doc.loadPage(pagina);
    try {
      const [x0, y0, x1, y1] = page.getBounds();
      const pw = x1 - x0, ph = y1 - y0;
      const voluta = larghezza ? larghezza / pw : scala;
      const s = Math.min(voluta, LATO_MAX / pw, LATO_MAX / ph);
      const pix = page.toPixmap(mupdf.Matrix.scale(s, s), mupdf.ColorSpace.DeviceRGB, false, true);
      try {
        return larghezza
          ? { img: pix.asJPEG(82, false).slice(), tipo: "image/jpeg", pw, ph }
          : { png: pix.asPNG().slice(), pw, ph };
      } finally {
        pix.destroy();
      }
    } finally {
      page.destroy();
    }
  };

  // graftPage copia solo il contenuto della pagina e perde /Annots: qui si
  // riportano collegamenti e annotazioni, come fa insert_pdf di PyMuPDF.
  // Non copiati: campi modulo (Widget) e popup, che richiedono /AcroForm.
  const SALTA_CHIAVI = new Set(["P", "Popup", "Parent", "IRT", "RT"]);
  const SALTA_TIPI = new Set(["Link", "Widget", "Popup"]);
  // coppie: [[indice pagina nel file sorgente, indice nel nuovo file], ...].
  // I collegamenti verso pagine non copiate vengono scartati.
  const copiaAnnotazioni = (out, srcDoc, coppie) => {
    const gm = out.newGraftMap();
    const mappa = new Map(coppie);
    for (const [i, o] of coppie) {
      const srcPage = srcDoc.loadPage(i);
      const dstPage = out.loadPage(o);
      try {
        // collegamenti: gli interni vengono rimappati sulle pagine del nuovo file
        for (const lk of srcPage.getLinks()) {
          try {
            const uri = lk.getURI();
            if (lk.isExternal()) {
              dstPage.createLink(lk.getBounds(), uri);
              continue;
            }
            const dest = srcDoc.resolveLinkDestination(uri);
            if (!dest || !mappa.has(dest.page)) continue;
            dstPage.createLink(lk.getBounds(),
              out.formatLinkURI({ ...dest, page: mappa.get(dest.page) }));
          } finally {
            lk.destroy();
          }
        }
        // altre annotazioni (evidenziazioni, note, timbri...)
        const annots = srcPage.getObject().get("Annots");
        if (annots.isArray()) {
          for (let k = 0; k < annots.length; k++) {
            const a = annots.get(k).resolve();
            if (!a.isDictionary()) continue;
            const tipo = a.get("Subtype");
            if (tipo.isName() && SALTA_TIPI.has(tipo.asName())) continue;
            const nuova = out.newDictionary();
            a.forEach((val, chiave) => {
              if (!SALTA_CHIAVI.has(chiave)) nuova.put(chiave, gm.graftObject(val));
            });
            const dstObj = dstPage.getObject();
            let arr = dstObj.get("Annots");
            if (!arr.isArray()) {
              arr = out.newArray();
              dstObj.put("Annots", arr);
            }
            arr.push(out.addObject(nuova));
          }
        }
      } finally {
        srcPage.destroy();
        dstPage.destroy();
      }
    }
  };

  // Annotazioni (modulo Annota): lavorano sul documento aperto, che resta modificato in memoria
  // finché non si chiama salvaConAnnotazioni. Il testo strutturato di una pagina si calcola una volta
  // sola: serve a ogni movimento del dito durante la selezione.
  const testi = new Map(); // "id|pagina" → StructuredText
  const testoPagina = (id, pagina) => {
    const k = `${id}|${pagina}`;
    let st = testi.get(k);
    if (!st) {
      const page = voce(id).doc.loadPage(pagina);
      try { st = page.toStructuredText("preserve-whitespace"); } finally { page.destroy(); }
      testi.set(k, st);
    }
    return st;
  };
  const dimenticaTesti = (id) => {
    for (const [k, st] of testi) if (k.startsWith(id + "|")) { st.destroy(); testi.delete(k); }
  };
  const idAnnot = (a) => a.getObject().asIndirect();
  const conPagina = (id, pagina, fn) => {
    const doc = voce(id).doc;
    if (!Number.isInteger(pagina) || pagina < 0 || pagina >= doc.countPages()) throw new Error(`Pagina non valida: ${pagina + 1}`);
    const page = doc.loadPage(pagina);
    try { return fn(page); } finally { page.destroy(); }
  };
  const trovaAnnot = (page, num) => {
    for (const a of page.getAnnotations()) if (idAnnot(a) === num) return a;
    throw new Error("Annotazione non trovata");
  };
  const colore3 = (c) => {
    if (!Array.isArray(c) || c.length !== 3 || c.some((x) => typeof x !== "number" || x < 0 || x > 1)) throw new Error("Colore non valido");
    return c;
  };

  return {
    // bytes: Uint8Array del file. Ritorna { protetto } oppure { id, numPagine }.
    apri(bytes) {
      const doc = apriPdf(bytes);
      if (doc.needsPassword()) {
        doc.destroy();
        return { protetto: true };
      }
      const id = prossimoId++;
      docs.set(id, { doc, bytes });
      return { id, numPagine: doc.countPages(), protetto: false };
    },

    chiudi(id) {
      const v = docs.get(id);
      if (v) {
        dimenticaTesti(id);
        v.doc.destroy();
        docs.delete(id);
      }
      return {};
    },

    dimensioni(id, pagina) {
      const page = voce(id).doc.loadPage(pagina);
      try {
        const [x0, y0, x1, y1] = page.getBounds();
        return { pw: x1 - x0, ph: y1 - y0 };
      } finally {
        page.destroy();
      }
    },

    // dimensioni in punti di tutte le pagine: [[pw, ph], ...]
    dimensioniTutte(id) {
      const { doc } = voce(id);
      const dim = [];
      for (let i = 0, n = doc.countPages(); i < n; i++) {
        const page = doc.loadPage(i);
        try {
          const [x0, y0, x1, y1] = page.getBounds();
          dim.push([x1 - x0, y1 - y0]);
        } finally {
          page.destroy();
        }
      }
      return { dim };
    },

    // scala = pixel per punto PDF (1 = 72 dpi)
    renderPagina(id, pagina, scala) {
      return renderizza(voce(id).doc, pagina, scala);
    },

    // miniatura JPEG larga `larghezza` pixel
    miniatura(id, pagina, larghezza) {
      return renderizza(voce(id).doc, pagina, 0, larghezza);
    },

    // Nuovo PDF con le pagine indicate (indici 0-based del file aperto), nell'ordine dato.
    // Serve a Riordina (salva tutte / esporta selezione) e a Dividi.
    estrai(id, indici) {
      const { doc } = voce(id);
      const n = doc.countPages();
      if (!indici.length) throw new Error("Non ci sono pagine da salvare");
      for (const i of indici) {
        if (!Number.isInteger(i) || i < 0 || i >= n) throw new Error(`Pagina non valida: ${i + 1}`);
      }
      const out = new mupdf.PDFDocument();
      try {
        for (const i of indici) out.graftPage(-1, doc, i);
        copiaAnnotazioni(out, doc, indici.map((s, o) => [s, o]));
        // Segnalibri: restano quelli che puntano a pagine mantenute, sulla posizione nuova.
        const nuovaPos = new Map();
        indici.forEach((s, o) => { if (!nuovaPos.has(s)) nuovaPos.set(s, o + 1); });
        let toc = [];
        try {
          for (const [lvl, titolo, pag] of leggiToc(doc)) {
            if (pag >= 1 && nuovaPos.has(pag - 1)) toc.push([lvl, titolo, nuovaPos.get(pag - 1)]);
          }
        } catch (_) { toc = []; } // un indice illeggibile non deve impedire il salvataggio
        if (toc.length) scriviToc(out, normalizzaToc(toc));
        const bytes = out.saveToBuffer("compress,garbage=compact").asUint8Array().slice();
        return { bytes, numPagine: indici.length, numSegnalibri: toc.length };
      } finally {
        out.destroy();
      }
    },

    leggiToc(id) {
      return { toc: leggiToc(voce(id).doc) };
    },

    // ids nell'ordine di unione; unisce anche i segnalibri con lo scarto di pagina
    unisci(ids) {
      const out = new mupdf.PDFDocument();
      const tocUnito = [];
      let offset = 0;
      try {
        for (const id of ids) {
          const { doc } = voce(id);
          for (const [lvl, titolo, pag] of leggiToc(doc)) {
            if (pag >= 1) tocUnito.push([lvl, titolo, pag + offset]);
          }
          const n = doc.countPages();
          for (let i = 0; i < n; i++) out.graftPage(-1, doc, i);
          copiaAnnotazioni(out, doc, Array.from({ length: n }, (_, i) => [i, offset + i]));
          offset += n;
        }
        if (tocUnito.length) scriviToc(out, normalizzaToc(tocUnito));
        const bytes = out.saveToBuffer("compress,garbage=compact").asUint8Array().slice();
        return { bytes, numPagine: offset, numSegnalibri: tocUnito.length };
      } finally {
        out.destroy();
      }
    },

    // toc: [[livello, titolo, pagina_1based], ...]. Lavora su una copia del file
    // aperto: il documento in memoria non cambia, quindi un errore non lo sporca.
    scriviTocESalva(id, toc) {
      const copia = apriPdf(voce(id).bytes);
      try {
        const valido = toc.filter(([, , pag]) => pag >= 1);
        scriviToc(copia, normalizzaToc(valido));
        const bytes = copia.saveToBuffer("compress,garbage=compact").asUint8Array().slice();
        return { bytes, numSegnalibri: valido.length };
      } finally {
        copia.destroy();
      }
    },

    // sostituzioni: [[posizione_0based, idDocSostituto, pagine?], ...]. `pagine` sono gli indici
    // 0-based delle pagine del sostituto da usare (default [0]): la prima prende il posto della
    // pagina indicata, le altre vengono inserite subito dopo e il documento si allunga. Con lista
    // vuota salva una copia identica, come "Salva come…" della Suite. Se la stessa posizione compare
    // due volte vale l'ultima. Lavora su una copia del file aperto. Il contenuto della prima pagina
    // si scrive dentro l'oggetto pagina esistente, quindi segnalibri e collegamenti che puntavano a
    // quella posizione restano validi (la Suite Python invece li lascia rotti: pagina -1); i
    // segnalibri puntano agli oggetti pagina, quindi seguono le pagine spostate dagli inserimenti.
    sostituisciESalva(id, sostituzioni) {
      const n = voce(id).doc.countPages();
      const voci = sostituzioni.map(([pos, idSost, pagine = [0]]) => [pos, idSost, pagine]);
      for (const [pos, idSost, pagine] of voci) {
        if (!Number.isInteger(pos) || pos < 0 || pos >= n) throw new Error(`Pagina non valida: ${pos + 1}`);
        const np = voce(idSost).doc.countPages();
        if (np < 1) throw new Error("Il PDF sostituto è vuoto.");
        if (!pagine.length) throw new Error("Indica almeno una pagina del PDF sostituto.");
        for (const p of pagine) {
          if (!Number.isInteger(p) || p < 0 || p >= np) throw new Error(`Pagina ${p + 1} del PDF sostituto non valida`);
        }
      }
      const ultime = [...new Map(voci.map((v) => [v[0], v])).values()];
      const copia = apriPdf(voce(id).bytes);
      try {
        // dalla posizione più alta alla più bassa: le pagine inserite non spostano quelle ancora da trattare
        for (const [pos, idSost, pagine] of ultime.sort((x, y) => y[0] - x[0])) {
          const src = voce(idSost).doc;
          const fine = copia.countPages();
          copia.graftPage(-1, src, pagine[0]);
          const vecchia = copia.findPage(pos);
          const nuova = copia.findPage(fine);
          const chiavi = [];
          vecchia.forEach((_, k) => chiavi.push(k));
          for (const k of chiavi) if (k !== "Parent" && k !== "Type") vecchia.delete(k);
          const daCopiare = [];
          nuova.forEach((v, k) => { if (k !== "Parent" && k !== "Type") daCopiare.push([k, v]); });
          for (const [k, v] of daCopiare) vecchia.put(k, v);
          copia.deletePage(fine);
          for (let k = 1; k < pagine.length; k++) copia.graftPage(pos + k, src, pagine[k]);
          copiaAnnotazioni(copia, src, pagine.map((p, k) => [p, pos + k]));
        }
        const bytes = copia.saveToBuffer("compress,garbage=compact").asUint8Array().slice();
        return { bytes, numPagine: copia.countPages() };
      } finally {
        copia.destroy();
      }
    },

    // ── annotazioni ───────────────────────────────────────────────────────────

    // Quadrilateri del testo tra due punti (coordinate di pagina, quelle di renderPagina divise per la
    // scala). Con i due punti vicini seleziona la parola sotto il punto. { quads: [[8 numeri], ...] }
    selezioneTesto(id, pagina, p, q) {
      const st = testoPagina(id, pagina);
      if (Math.hypot(p[0] - q[0], p[1] - q[1]) < 3) {
        // Lontano dal testo snap restituisce un quadrilatero che arriva fino al punto toccato: lo si scarta
        // se il punto non cade dentro la parola (strettamente: sul bordo è il caso sbagliato).
        const w = st.snap(p, p, "words");
        let buona = Array.isArray(w) && w.length === 8;
        if (buona) {
          const xs = [w[0], w[2], w[4], w[6]], ys = [w[1], w[3], w[5], w[7]];
          buona = Math.min(...xs) < p[0] && p[0] < Math.max(...xs) && Math.min(...ys) < p[1] && p[1] < Math.max(...ys);
        }
        return { quads: buona ? [w] : [] };
      }
      return { quads: st.highlight(p, q) };
    },

    // colore: [r, g, b] da 0 a 1. Annotazione Highlight vera, con aspetto generato (si vede in ogni lettore).
    aggiungiEvidenziatura(id, pagina, quads, colore) {
      if (!quads.length) throw new Error("Nessun testo selezionato");
      colore3(colore);
      return conPagina(id, pagina, (page) => {
        const a = page.createAnnotation("Highlight");
        a.setQuadPoints(quads);
        a.setColor(colore);
        a.setOpacity(0.5);
        a.update();
        return { num: idAnnot(a) };
      });
    },

    // rect: [x0, y0, x1, y1] di pagina. Annotazione FreeText (Helvetica), senza bordo né sfondo.
    aggiungiTesto(id, pagina, rect, testo, dimensione, colore) {
      if (!testo.trim()) throw new Error("Il testo è vuoto");
      if (!(dimensione >= 4 && dimensione <= 144)) throw new Error("Dimensione del testo non valida");
      colore3(colore);
      return conPagina(id, pagina, (page) => {
        const a = page.createAnnotation("FreeText");
        a.setRect(rect);
        a.setContents(testo);
        a.setDefaultAppearance("Helv", dimensione, colore);
        a.setBorderWidth(0);
        a.update();
        return { num: idAnnot(a) };
      });
    },

    // Evidenziazioni e testi della pagina (anche quelli già presenti nel file): [{ num, tipo, rect, testo, dimensione, colore }]
    annotazioni(id, pagina) {
      return conPagina(id, pagina, (page) => {
        const lista = [];
        for (const a of page.getAnnotations()) {
          const tipo = a.getType();
          if (tipo !== "Highlight" && tipo !== "FreeText") continue;
          const v = { num: idAnnot(a), tipo, rect: a.getBounds(), testo: "", dimensione: 0, colore: [0, 0, 0] };
          if (tipo === "FreeText") {
            v.testo = a.getContents();
            try {
              const da = a.getDefaultAppearance();
              v.dimensione = da.size;
              v.colore = da.color.length === 3 ? da.color : [0, 0, 0];
            } catch (_) { v.dimensione = 12; }
          }
          lista.push(v);
        }
        return { annotazioni: lista };
      });
    },

    // Cambia il testo di un FreeText ed eventualmente la casella (rect)
    modificaTesto(id, pagina, num, testo, rect) {
      if (!testo.trim()) throw new Error("Il testo è vuoto");
      return conPagina(id, pagina, (page) => {
        const a = trovaAnnot(page, num);
        if (a.getType() !== "FreeText") throw new Error("Si può modificare solo un testo");
        a.setContents(testo);
        if (rect) a.setRect(rect);
        a.update();
        return {};
      });
    },

    eliminaAnnotazione(id, pagina, num) {
      return conPagina(id, pagina, (page) => {
        page.deleteAnnotation(trovaAnnot(page, num));
        return {};
      });
    },

    // PDF con le annotazioni fatte finora. Il documento aperto resta com'è, si può continuare.
    salvaConAnnotazioni(id) {
      const bytes = voce(id).doc.saveToBuffer("compress,garbage=compact").asUint8Array().slice();
      return { bytes };
    },
  };
}
