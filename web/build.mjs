// Costruisce dist/index.html: un solo file con mupdf.js, WASM (gzip+base64) e il Worker incorporati.
import fs from "node:fs";
import zlib from "node:zlib";

const MUPDF = process.argv[2] || "/home/claude/mupdf-env/node_modules/mupdf/dist";
const NM = process.argv[3] || "/home/claude/mupdf-env/node_modules"; // marked, mammoth, jszip
const leggi = (p) => fs.readFileSync(p, "utf8");

const senzaModuli = (testo) =>
  testo.replace(/^import .*$/gm, "").replace(/^export /gm, "");

const gestore = `
let motore = null;
const trasferibili = (r) => (r && typeof r === "object")
  ? Object.values(r).filter((v) => v instanceof Uint8Array).map((v) => v.buffer) : [];
export async function gestisci(op, args) {
  if (op === "init") {
    const [wasm, urlMupdf] = args;
    globalThis["$libmupdf_wasm_Module"] = { wasmBinary: new Uint8Array(wasm), locateFile: (nome) => nome };
    motore = creaMotore(await import(urlMupdf));
    return {};
  }
  if (!motore || typeof motore[op] !== "function") throw new Error("Operazione sconosciuta: " + op);
  return motore[op](...args);
}
if (typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope) {
  self.onmessage = async (e) => {
    const { id, op, args } = e.data;
    try {
      const r = await gestisci(op, args);
      self.postMessage({ id, ok: true, r }, trasferibili(r));
    } catch (err) {
      self.postMessage({ id, ok: false, errore: (err && err.message) || String(err) });
    }
  };
}
`;

const worker = senzaModuli(leggi("toc.mjs")) + "\n" + senzaModuli(leggi("motore.mjs")) + gestore;
const mupdfJs = leggi(`${MUPDF}/mupdf.js`);
const wasmJs = leggi(`${MUPDF}/mupdf-wasm.js`);
// "<!--" dentro uno <script> confonde il parser HTML: "<\!--" ha lo stesso valore in stringhe ed espressioni regolari (senza flag u).
const proteggi = (t) => t.replace(/^\/\/# sourceMappingURL=.*$/m, "").replaceAll("<!--", "<\\!--");
const marked = proteggi(leggi(`${NM}/marked/lib/marked.umd.js`));
const mammoth = proteggi(leggi(`${NM}/mammoth/mammoth.browser.min.js`));
const jszip = leggi(`${NM}/jszip/dist/jszip.min.js`);
const wasmB64 = zlib.gzipSync(fs.readFileSync(`${MUPDF}/mupdf-wasm.wasm`), { level: 9 }).toString("base64");

for (const [nome, t] of [["mupdf.js", mupdfJs], ["mupdf-wasm.js", wasmJs], ["worker", worker], ["marked", marked], ["mammoth", mammoth], ["jszip", jszip]]) {
  if (/<\/script|<!--/i.test(t)) throw new Error(`${nome} contiene una sequenza che chiuderebbe lo <script>`);
}
if (!mupdfJs.includes('"./mupdf-wasm.js"')) throw new Error("specificatore di import di mupdf.js cambiato");

let html = leggi("app.src.html");
const metti = (segnaposto, testo) => {
  if (!html.includes(segnaposto)) throw new Error("segnaposto mancante: " + segnaposto);
  html = html.replace(segnaposto, () => testo);
};
metti("/*__MUPDF__*/", mupdfJs);
metti("/*__WASMJS__*/", wasmJs);
metti("/*__WORKER__*/", worker);
metti("/*__WASMB64__*/", wasmB64);
metti("/*__MARKED__*/", marked);
metti("/*__MAMMOTH__*/", mammoth);
metti("/*__JSZIP__*/", jszip);

fs.mkdirSync("dist", { recursive: true });
fs.writeFileSync("dist/index.html", html);
console.log("dist/index.html:", (html.length / 1048576).toFixed(1), "MB");
