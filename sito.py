"""LOMBROSO - genera la pagina di prova (docs/index.html).

Legge prova/profili.json, prova/scostamenti.csv e membri.csv, copia le foto
in sito/foto/ e scrive una pagina unica, apribile in locale.

Uso:  .venv/Scripts/python sito.py
"""
import csv
import html
import json
import shutil
from pathlib import Path

BASE = Path(__file__).parent
SITO = BASE / "docs"
SOGLIA = 1.5

ETICHETTE = [
    ("mandibola_su_zigomi", "Mandibola"),
    ("zigomi_su_altezza_viso", "Zigomi"),
    ("naso_larghezza_su_altezza", "Larghezza del naso"),
    ("naso_deviazione_pct", "Deviazione del naso"),
    ("labbra_spessore_su_bocca", "Spessore delle labbra"),
    ("asimmetria_pct", "Asimmetria del volto"),
    ("occhio_su_zigomi", "Grandezza degli occhi"),
    ("naso_altezza_su_viso", "Lunghezza del naso"),
]


def leggi(nome):
    with open(BASE / nome, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    return f"{v:+.1f}".replace(".", ",").replace("-", "−")


def elenco(parole):
    if len(parole) <= 1:
        return "".join(parole)
    return ", ".join(parole[:-1]) + " e " + parole[-1]


def referto(p):
    if not p["tratti"]:
        return ("Nessuna anomalia propria. Delinquente d'occasione: "
                "nulla lo distingue dalla media del gruppo.")
    t = elenco([x["tratto"] for x in p["tratti"]])
    return f"Il soggetto presenta {t}."


profili = json.loads((BASE / "prova" / "profili.json").read_text(encoding="utf-8"))
scost = {r["id"]: r for r in leggi("prova/scostamenti.csv")}
membri = leggi("membri.csv")
misurati = {p["id"] for p in profili}
attesa = [m for m in membri if m["id"] not in misurati]

(SITO / "foto").mkdir(parents=True, exist_ok=True)
for vecchio in (SITO / "foto").glob("*"):
    vecchio.unlink()

schede = {}
conteggio = {}
misure = json.loads((BASE / "prova" / "misure.json").read_text(encoding="utf-8"))
CATEGORIE = [
    ("delinquente nato", "I delinquenti nati", "Il «tipo criminale completo»: cinque o più anomalie riunite nello stesso volto."),
    ("omicida", "Gli omicidi", "Mandibole robuste, zigomi larghi, labbra sottili."),
    ("ladro", "I ladri", "Naso torto o camuso."),
    ("truffatore", "I truffatori", "Occhi piccoli e naso lungo, sotto un'aria di bonarietà."),
    ("anarchico", "Gli anarchici", "L'asimmetria del volto, secondo Lombroso, tradisce l'animo ribelle."),
    ("delinquente per passione", "I delinquenti per passione", "Lineamenti belli e armonici, nessuna anomalia: delinquono per impeto, non per natura."),
    ("criminaloide", "I criminaloidi", "Nessun tratto che li distingua dal gruppo: delinquenti d'occasione, in attesa dell'occasione."),
]
ORDINE = {c[0]: i for i, c in enumerate(CATEGORIE)}
profili.sort(key=lambda p: (ORDINE.get(p["etichetta"], 99), -p["anomalie"], p["nome"].split()[-1]))
for n, p in enumerate(profili, 1):
    origine = BASE / p["foto"]
    shutil.copy(origine, SITO / "foto" / f"{p['id']}{origine.suffix}")
    shutil.copy(BASE / "prova" / f"{p['id']}_punti.jpg", SITO / "foto" / f"{p['id']}_punti.jpg")
    attivi = {x["tratto"]: x for x in p["tratti"]}
    conteggio[p["etichetta"]] = conteggio.get(p["etichetta"], 0) + 1
    righe = []
    for chiave, etichetta in ETICHETTE:
        z = float(scost[p["id"]][chiave])
        pos = max(2, min(98, 50 + z / 3 * 50))
        fuori = any(x["misura"] == chiave for x in p["tratti"])
        righe.append(
            f'<div class="mis{" fuori" if fuori else ""}"><span class="lab">{etichetta}</span>'
            f'<span class="barra"><i style="left:{pos:.1f}%"></i></span>'
            f'<span class="val">{num(z)}</span></div>')
    tratti = "".join(f"<li>{html.escape(t)}</li>" for t in attivi) or ""
    classe = "nessuno" if p["etichetta"] == "criminaloide" else "mezzo"
    mm = misure[p["id"]]
    scarsa = mm["_larghezza_viso_pixel"] < 300 or abs(mm["_rotazione_pct"]) > 12
    avviso = ('<p class="affid">Fotografia di bassa qualità: risultato da confermare. '
              'Se il soggetto ci invia un suo ritratto migliore, ricalcoliamo.</p>') if scarsa else ""
    schede.setdefault(p["etichetta"], []).append(f'''
<article class="scheda {classe}">
  <header><span class="num">Soggetto n. {n:02d}</span><span class="anom">{p["anomalie"]} anomali{"a" if p["anomalie"] == 1 else "e"}</span></header>
  <figure>
    <img class="ritratto" src="foto/{p["id"]}{origine.suffix}" alt="Ritratto di {html.escape(p["nome"])}" loading="lazy">
    <img class="punti" src="foto/{p["id"]}_punti.jpg" alt="" loading="lazy">
    <span class="timbro">{html.escape(p["etichetta"])}</span>
  </figure>
  <h2>{html.escape(p["nome"])}</h2>
  <p class="carica">{html.escape(p["carica"])}</p>
  <p class="tipo"><span>Tipo</span>{html.escape(p["etichetta"])}</p>
  <div class="misure">{"".join(righe)}</div>
  <p class="referto">{html.escape(referto(p))}</p>
  {f'<ul class="tratti">{tratti}</ul>' if tratti else ''}
  {avviso}
  <p class="fonte">Foto: {html.escape(p["fonte_foto"] or "raccolta dalla redazione")}</p>
</article>''')

in_attesa = "".join(
    f'<li><b>{html.escape(m["nome"])} {html.escape(m["cognome"])}</b><span>{html.escape(m["carica"])}</span></li>'
    for m in attesa)

sezioni = "".join(
    f'<section class="categoria"><h3 class="cat-titolo">{html.escape(nome)} <small>({len(schede[k])})</small></h3>'
    f'<p class="cat-nota">{html.escape(desc)}</p><div class="griglia">{"".join(schede[k])}</div></section>'
    for k, nome, desc in CATEGORIE if k in schede)

pagina = f'''<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LOMBROSO — Atlante antropometrico dei ministri</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {{
  --carta: #ece3cf; --carta2: #e2d7bd; --inchiostro: #231c14; --seppia: #6b5a43;
  --riga: #b9a98a; --rosso: #9c1c12;
  --serif: "IM Fell English", "Iowan Old Style", Georgia, serif;
  --maiuscoletto: "IM Fell English SC", Georgia, serif;
  --macchina: "Courier Prime", "Courier New", monospace;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--carta); color: var(--inchiostro); font-family: var(--serif);
  font-size: 18px; line-height: 1.45;
  background-image: radial-gradient(circle at 20% 10%, #f3ecdc 0, transparent 55%),
                    radial-gradient(circle at 85% 90%, #d9ccae 0, transparent 50%); }}
.avviso {{ background: var(--inchiostro); color: var(--carta); font-family: var(--macchina);
  font-size: 13px; text-align: center; padding: 8px 16px; letter-spacing: .04em; }}
.testata {{ max-width: 1000px; margin: 0 auto; padding: 56px 20px 28px; text-align: center; }}
.testata .sopra {{ font-family: var(--maiuscoletto); letter-spacing: .2em; color: var(--seppia); font-size: 15px; }}
.testata h1 {{ font-family: var(--maiuscoletto); font-weight: 400; font-size: clamp(54px, 13vw, 132px);
  letter-spacing: .06em; margin: 6px 0 0; line-height: 1; }}
.testata .sotto {{ font-style: italic; font-size: clamp(19px, 3vw, 26px); margin: 10px 0 0; }}
.filetto {{ border: 0; border-top: 3px double var(--inchiostro); max-width: 420px; margin: 26px auto; }}
.premessa {{ max-width: 680px; margin: 0 auto; text-align: left; }}
.premessa p {{ margin: 0 0 14px; }}
.cifre {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 12px 40px; margin: 30px auto 0;
  font-family: var(--macchina); font-size: 14px; text-transform: uppercase; letter-spacing: .08em; }}
.cifre b {{ display: block; font-family: var(--maiuscoletto); font-size: 40px; letter-spacing: 0; line-height: 1; }}
main {{ max-width: 1240px; margin: 0 auto; padding: 20px 16px 60px; }}
.titolo-sez {{ font-family: var(--maiuscoletto); font-weight: 400; font-size: 26px; letter-spacing: .12em;
  text-align: center; margin: 44px 0 6px; }}
.nota-sez {{ text-align: center; font-style: italic; color: var(--seppia); margin: 0 0 26px; }}
.griglia {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 22px; }}
.scheda {{ background: #f4eddc; border: 1px solid var(--inchiostro); padding: 14px 16px 12px;
  box-shadow: 4px 4px 0 var(--carta2); display: flex; flex-direction: column; }}
.scheda header {{ display: flex; justify-content: space-between; font-family: var(--macchina); font-size: 12px;
  text-transform: uppercase; letter-spacing: .08em; border-bottom: 1px solid var(--inchiostro);
  padding-bottom: 6px; margin-bottom: 12px; }}
.scheda .anom {{ color: var(--seppia); }}
.scheda.mezzo .anom, .scheda.completo .anom {{ color: var(--rosso); font-weight: 700; }}
figure {{ margin: 0; position: relative; aspect-ratio: 4 / 5; overflow: hidden; border: 1px solid var(--inchiostro);
  background: #cfc3a6; }}
figure img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: 50% 22%;
  filter: grayscale(1) sepia(.35) contrast(1.08); transition: opacity .25s; }}
figure .punti {{ opacity: 0; filter: grayscale(1) contrast(1.15); }}
figure:hover .punti, figure:focus-within .punti {{ opacity: 1; }}
.timbro {{ position: absolute; right: 8px; bottom: 10px; font-family: var(--macchina); font-weight: 700;
  font-size: 12px; text-transform: uppercase; letter-spacing: .1em; padding: 4px 8px;
  border: 2px solid currentColor; transform: rotate(-5deg); background: rgba(244,237,220,.82); color: var(--seppia); }}
.mezzo .timbro, .completo .timbro {{ color: var(--rosso); }}
.scheda h2 {{ font-family: var(--maiuscoletto); font-weight: 400; font-size: 25px; line-height: 1.1; margin: 14px 0 2px; }}
.categoria {{ margin: 56px 0 8px; }}
.cat-titolo {{ font-family: var(--maiuscoletto); font-weight: 400; font-size: 34px; margin: 0;
  border-bottom: 2px solid var(--inchiostro); padding-bottom: 4px; }}
.cat-titolo small {{ font-size: 18px; color: var(--seppia); }}
.cat-nota {{ font-style: italic; color: var(--seppia); margin: 8px 0 22px; }}
.affid {{ font-family: var(--macchina); font-size: 13px; color: var(--rosso); margin: 8px 0 0; }}
.carica {{ font-style: italic; color: var(--seppia); margin: 0 0 12px; font-size: 16px; line-height: 1.25; min-height: 2.5em; }}
.tipo {{ margin: 0 0 12px; font-family: var(--maiuscoletto); font-size: 30px; line-height: 1; color: var(--seppia); }}
.tipo span {{ display: block; font-family: var(--macchina); font-size: 11px; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 3px; }}
.mezzo .tipo {{ color: var(--rosso); }}
.timbro {{ font-size: 15px !important; }}
.misure {{ border-top: 1px solid var(--riga); padding-top: 8px; }}
.mis {{ display: grid; grid-template-columns: 1fr 74px 40px; gap: 8px; align-items: center;
  font-family: var(--macchina); font-size: 12.5px; padding: 2px 0; }}
.mis .val {{ text-align: right; }}
.barra {{ position: relative; height: 10px; border-left: 1px solid var(--riga); border-right: 1px solid var(--riga);
  background: linear-gradient(to right, rgba(156,28,18,.16) 0 25%, transparent 25% 75%, rgba(156,28,18,.16) 75% 100%); }}
.barra::before {{ content: ""; position: absolute; left: 50%; top: -2px; bottom: -2px; border-left: 1px solid var(--inchiostro); }}
.barra i {{ position: absolute; top: 1px; width: 8px; height: 8px; margin-left: -4px; border-radius: 50%; background: var(--inchiostro); }}
.mis.fuori {{ color: var(--rosso); font-weight: 700; }}
.mis.fuori .barra i {{ background: var(--rosso); }}
.referto {{ margin: 12px 0 0; font-size: 17px; line-height: 1.35; }}
.tratti {{ list-style: none; padding: 0; margin: 8px 0 0; display: flex; flex-wrap: wrap; gap: 6px; }}
.tratti li {{ font-family: var(--macchina); font-size: 12px; text-transform: uppercase; letter-spacing: .06em;
  border: 1px solid var(--rosso); color: var(--rosso); padding: 2px 7px; }}
.fonte {{ margin: auto 0 0; padding-top: 12px; font-family: var(--macchina); font-size: 10.5px; color: var(--seppia); }}
.legenda {{ max-width: 680px; margin: 0 auto 30px; font-family: var(--macchina); font-size: 13px; color: var(--seppia); text-align: center; }}
.attesa {{ list-style: none; padding: 0; margin: 0; columns: 3 260px; column-gap: 28px; }}
.attesa li {{ break-inside: avoid; border-bottom: 1px dotted var(--riga); padding: 6px 0; font-size: 16px; }}
.attesa b {{ font-weight: 400; font-family: var(--maiuscoletto); display: block; }}
.attesa span {{ font-style: italic; color: var(--seppia); font-size: 14.5px; }}
.metodo {{ max-width: 680px; margin: 0 auto; }}
.metodo h3 {{ font-family: var(--maiuscoletto); font-weight: 400; font-size: 21px; margin: 22px 0 4px; }}
.metodo p {{ margin: 0 0 12px; }}
footer {{ border-top: 3px double var(--inchiostro); text-align: center; padding: 22px 16px 40px;
  font-family: var(--macchina); font-size: 12.5px; color: var(--seppia); }}
</style>
</head>
<body>
<div class="avviso">BOZZA DI LAVORO · SATIRA · LE CLASSIFICAZIONI NON HANNO ALCUN VALORE SCIENTIFICO</div>

<div class="testata">
  <div class="sopra">Atlante antropometrico dei ministri e delle ministre</div>
  <h1>Lombroso</h1>
  <p class="sotto">I volti del potere, misurati con il metodo che il potere vuole usare su di noi</p>
  <hr class="filetto">
  <div class="premessa">
    <p>Nel 1876 Cesare Lombroso sostenne che il delinquente si riconosce dalla faccia: mandibola, zigomi, naso. Era falso allora ed è falso oggi. Eppure la stessa idea, misurare i tratti di un volto, il colore della pelle, il tipo di camminata, per decidere chi sei, è tornata in voga. Maranza, anarco-insurrezionalisti, zecche rosse, sono i bersagli preferiti delle destre al potere, compresa la nostra.</p>
    <p>Rispetto ai criminologi e ai poliziotti di fine '800, i nostri post-fascisti hanno però delle tecnologie in più per identificare, controllare, sorvegliare, fermare, chiunque secondo loro sia un criminale: tecnologie come il riconoscimento facciale.</p>
    <p>C'è una cosa che però non hanno tenuto in conto: queste tecnologie sono oggi alla portata di tutti, anche di chi non vuole arrendersi alla deriva autoritaria, repressiva e fascistoide del proprio paese.</p>
    <p>Allora abbiamo preso le fotografie dei ministri e delle ministre e le abbiamo passate a una macchina. Poi abbiamo applicato le regole di Lombroso, alla lettera.</p>
    <p>Di profilo, purtroppo, non ne esistono quasi: nessuna fotografia ufficiale mostra il lato del viso che Lombroso considerava decisivo. Abbiamo dovuto accontentarci delle poche frontali disponibili. I ministri e le ministre che desiderano un'identificazione più accurata sono invitati a inviarci di propria iniziativa le loro fotografie di profilo, destro e sinistro. Le foto che preferiscono, perché al contrario di quanto fa questo governo, noi non andremo a prenderli in casa o a fermarli nelle zone rosse per identificarli in maniera coatta.</p>
  </div>
  <div class="cifre">
    <div><b>{len(profili)}</b>soggetti misurati</div>
    {"".join(f"<div><b>{n}</b>{html.escape(e)}</div>" for e, n in sorted(conteggio.items(), key=lambda x: -x[1]))}
    <div><b>{len(attesa)}</b>in attesa di misurazione</div>
  </div>
</div>

<main>
  <h2 class="titolo-sez">Tavole</h2>
  <p class="nota-sez">Passa sopra un ritratto per vedere ciò che vede la macchina.</p>
  <p class="legenda">Ogni riga mostra quanto il soggetto si discosta dalla media del gruppo: al centro la media, nelle fasce rosse l'anomalia.</p>
  {sezioni}

  <h2 class="titolo-sez">In attesa di misurazione</h2>
  <p class="nota-sez">Soggetti di cui non disponiamo ancora di un ritratto frontale adatto.</p>
  <ul class="attesa">{in_attesa}</ul>

  <h2 class="titolo-sez">Metodo</h2>
  <div class="metodo">
    <h3>Come misuriamo</h3>
    <p>Un programma individua 478 punti su ogni volto e ne ricava alcune proporzioni. Ogni soggetto è confrontato con la media dei colleghi: chi se ne allontana troppo riceve il tratto corrispondente.</p>
    <h3>Stessa faccia, due verdetti</h3>
    <p>Basta cambiare fotografia perché la stessa persona passi da «anomala» a «normale». È successo durante la costruzione di questo atlante. <em>[Sezione da sviluppare.]</em></p>
    <h3>Perché lo facciamo</h3>
    <p><em>[Testo da scrivere: sorveglianza, identificazione, norme a tutela di libertà e riservatezza.]</em></p>
  </div>
</main>

<footer>Un progetto info.nodes · collegato all'Oracolo del Dissenso · versione di prova, non pubblicata</footer>
</body>
</html>
'''
(SITO / "index.html").write_text(pagina, encoding="utf-8")
print(f"pagina scritta: {len(profili)} schede, {len(attesa)} in attesa")
