"""LOMBROSO - dai numeri ai profili, e l'elenco delle foto.

Legge:
  membri.csv              chi sono i membri del governo
  fonti.csv               da dove viene la foto di ciascuno
  prova/scostamenti.csv   quanto ciascuno si discosta dalla media
  regole.csv              quale scostamento fa scattare quale tratto
Scrive:
  prova/profili.json      i profili, pronti per il sito
  PROFILI.md              gli stessi profili, leggibili
  ELENCO-FOTO.md          chi ha una foto utilizzabile e chi no

Uso:  .venv/Scripts/python profili.py
"""
import csv
import json
from pathlib import Path

BASE = Path(__file__).parent
SOGLIA = 1.5   # scostamento dalla media oltre il quale il tratto scatta


def leggi(nome):
    with open(BASE / nome, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def tipo(n):
    # Lombroso: "tipo criminale completo" con 5 o più anomalie,
    # "mezzo tipo" con 3 o 4  (DA VERIFICARE sul testo)
    if n >= 5:
        return "tipo criminale completo"
    if n >= 3:
        return "mezzo tipo"
    return "nessun tipo"


membri = leggi("membri.csv")
fonti = {r["id"]: r for r in leggi("fonti.csv")}
scost = {r["id"]: r for r in leggi("prova/scostamenti.csv")}
regole = leggi("regole.csv")
tipi = [t for t in leggi("tipi.csv") if t["attivo"].strip().lower() == "si"]
SENZA_TIPO = "criminaloide"   # Lombroso: delinquente d'occasione, privo di anomalie proprie


def etichetta(tratti):
    """Il tipo con più tratti corrispondenti; a parità, quello con lo
    scostamento più forte. Senza corrispondenze: criminaloide."""
    n = sum(x["anomalia"] for x in tratti)
    # 1) tipi che dipendono dal numero di anomalie (delinquente nato)
    for t in tipi:
        if t["min_anomalie"] and n >= int(t["min_anomalie"]):
            return t["tipo"]
    # 2) tipi legati a tratti precisi
    migliore, punteggio = SENZA_TIPO, (0, 0.0)
    for t in tipi:
        if t["min_anomalie"]:
            continue
        if t["senza_anomalie"].strip().lower() == "si" and n > 0:
            continue
        suoi = set(x.strip() for x in t["tratti"].split(";"))
        trovati = [x for x in tratti if x["tratto"] in suoi]
        p = (len(trovati), max((abs(x["scostamento"]) for x in trovati), default=0.0))
        if p > punteggio:
            migliore, punteggio = t["tipo"], p
    return migliore
misure = json.loads((BASE / "prova" / "misure.json").read_text(encoding="utf-8"))

profili = []
for m in membri:
    if m["id"] not in scost:
        continue
    s = scost[m["id"]]
    tratti = []
    for r in regole:
        v = float(s[r["misura"]])
        soglia = float(r["soglia"]) if r.get("soglia") else SOGLIA
        if (r["verso"] == "alto" and v >= soglia) or (r["verso"] == "basso" and v <= -soglia):
            tratti.append({"tratto": r["tratto"], "scostamento": v, "nota": r["nota"],
                           "misura": r["misura"],
                           "anomalia": r["anomalia"].strip().lower() == "si"})
    n_anomalie = sum(x["anomalia"] for x in tratti)
    profili.append({"id": m["id"], "nome": f"{m['nome']} {m['cognome']}",
                    "carica": m["carica"], "foto": misure[m["id"]]["_foto"],
                    "fonte_foto": fonti[m["id"]]["fonte"],
                    "tratti": tratti, "anomalie": n_anomalie,
                    "etichetta": etichetta(tratti),
                    "classificazione": tipo(n_anomalie)})

(BASE / "prova" / "profili.json").write_text(
    json.dumps(profili, indent=2, ensure_ascii=False), encoding="utf-8")

righe = ["# Profili (bozza)", "",
         f"Calcolati su {len(profili)} volti. Un tratto scatta quando la misura si "
         f"discosta dalla media del gruppo di almeno {SOGLIA} deviazioni standard.",
         "I nomi dei tratti e la classificazione sono ancora da verificare sui testi di Lombroso.", "",
         "| Nome | Carica | Etichetta | Tratti rilevati | Anomalie | Classificazione |",
         "|---|---|---|---|---|---|"]
for p in sorted(profili, key=lambda p: -p["anomalie"]):
    t = ", ".join(f"{x['tratto']} ({x['scostamento']:+})" for x in p["tratti"]) or "—"
    righe.append(f"| {p['nome']} | {p['carica']} | **{p['etichetta']}** | {t} | {p['anomalie']} | {p['classificazione']} |")
(BASE / "PROFILI.md").write_text("\n".join(righe) + "\n", encoding="utf-8")

# ---- elenco delle foto ----
MAN = BASE / "foto_manuali"


def profilo(sigla, lato):
    return "sì" if list(MAN.glob(f"{sigla}_profilo_{lato}.*")) else "—"


ok, mancanti = [], []
for m in membri:
    nome = f"{m['nome']} {m['cognome']}"
    if m["id"] in scost:
        f = fonti[m["id"]]["fonte"]
        nota = "foto del 2018 circa" if "XVIII" in f else ""
        if misure[m["id"]]["_foto"].startswith("foto_manuali"):
            f, nota = "fornita a mano", ""
        ok.append(f"| {nome} | {m['carica']} | `{m['id']}` | {f} | "
                  f"{nota} |")
    else:
        if m["id"] in misure:
            motivo = "la foto che abbiamo ha la testa troppo girata"
        elif "Senato" in fonti[m["id"]]["fonte"]:
            motivo = "senatore/senatrice: il ritratto ufficiale è di tre quarti"
        else:
            motivo = "non parlamentare: nessun ritratto ufficiale trovato"
        mancanti.append(f"| {nome} | {m['carica']} | `{m['id']}` | {motivo} |")

testo = [
    "# Elenco delle foto", "",
    f"Ministri e ministre: {len(membri)}. Con foto utilizzabile: {len(ok)}. Da cercare: {len(mancanti)}.", "",
    "## Come consegnare le foto", "",
    "Servono solo foto frontali (i profili sono troppo difficili da trovare: sul sito li chiediamo ai ministri stessi).",
    "Metti il file nella cartella `foto_manuali`, nominato `sigla_fronte.jpg` (la sigla è nella colonna «Sigla»).",
    "Esempio: `salvini_fronte.jpg`. Vanno bene anche .png e .webp.", "",
    "Annota in `foto_manuali/fonti.txt` da dove viene ogni foto (indirizzo della pagina, autore, licenza).", "",
    "Caratteristiche di una foto adatta:", "",
    "- **Frontale**: sguardo in macchina, testa dritta, entrambe le orecchie visibili allo stesso modo.",
    "- Viso largo almeno 300 pixel, a fuoco, luce uniforme.",
    "- Espressione il più possibile neutra, bocca chiusa (il sorriso falsa labbra e mandibola).",
    "- Niente occhiali da sole, cappelli, microfoni o mani davanti al viso.", "",
    f"## Da cercare ({len(mancanti)})", "",
    "| Nome | Carica | Sigla | Perché manca |", "|---|---|---|---|", *mancanti, "",
    f"## Foto frontale già presente ({len(ok)})", "",
    "Per queste persone la frontale c'è. «Fornita a mano» = foto messa da te in `foto_manuali`.", "",
    "| Nome | Carica | Sigla | Frontale | Nota |",
    "|---|---|---|---|---|", *ok, ""]
(BASE / "ELENCO-FOTO.md").write_text("\n".join(testo), encoding="utf-8")
print(f"profili: {len(profili)}   foto ok: {len(ok)}   da cercare: {len(mancanti)}")
for p in sorted(profili, key=lambda p: -p["anomalie"]):
    if p["anomalie"]:
        print(f"  {p['nome']:28}{p['etichetta']:14}{', '.join(x['tratto'] for x in p['tratti'])}")
