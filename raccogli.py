"""LOMBROSO - raccolta dei ritratti ufficiali.

Abbina ogni membro del governo (membri.csv) agli elenchi aperti di Camera e
Senato (dati/deputati19.csv, dati/senatori19.csv), scarica il ritratto
ufficiale in foto/<id>.jpg e scrive fonti.csv con la provenienza di ogni foto.
Le fonti trovate a mano stanno in fonti_manuali.csv (id,fonte,url) e hanno
la precedenza.

Uso:  .venv/Scripts/python raccogli.py
"""
import csv
import re
import unicodedata
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
FOTO = BASE / "foto"
UA = {"User-Agent": "Mozilla/5.0"}
URL_CAMERA = ("https://documenti.camera.it/_dati/leg19/schededeputatinuovosito/"
              "fotoDefinitivo/big/d{id}.jpg")


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def leggi(percorso):
    with open(percorso, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def trova(elenco, m):
    """Stesso cognome e nome compatibile (uno inizia con l'altro)."""
    c, n = norm(m["cognome"]), norm(m["nome"])
    ris = []
    for r in elenco:
        rc, rn = norm(r["cognome"]), norm(r["nome"])
        if rc == c and (rn.startswith(n) or n.startswith(rn)):
            ris.append(r)
    return ris


def scarica(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        dati = r.read()
    if dati[:3] != b"\xff\xd8\xff" and dati[:4] != b"\x89PNG" and dati[:4] != b"RIFF":
        raise ValueError("la risposta non è un'immagine")
    dest.write_bytes(dati)
    return len(dati)


def main():
    FOTO.mkdir(exist_ok=True)
    membri = leggi(BASE / "membri.csv")
    deputati = leggi(BASE / "dati" / "deputati19.csv")
    senatori = leggi(BASE / "dati" / "senatori19.csv")
    deputati18 = leggi(BASE / "dati" / "deputati18.csv")
    manuali = {}
    fm = BASE / "fonti_manuali.csv"
    if fm.exists():
        manuali = {r["id"]: r for r in leggi(fm)}

    righe = []
    for m in membri:
        fonte, url = "", ""
        if m["id"] in manuali:
            fonte, url = manuali[m["id"]]["fonte"], manuali[m["id"]]["url"]
        else:
            d = trova(deputati, m)
            s = trova(senatori, m)
            if len(d) == 1:
                idc = re.search(r"/d(\d+)_19", d[0]["d"]).group(1)
                fonte, url = "Camera dei deputati", URL_CAMERA.format(id=idc)
            elif len(s) == 1 and s[0]["foto"]:
                fonte = "Senato della Repubblica"
                url = s[0]["foto"].replace("http://", "https://")
            else:
                # non parlamentare oggi: era deputato nella XVIII legislatura?
                d18 = trova(deputati18, m)
                if len(d18) == 1:
                    idc = re.search(r"/d(\d+)_18", d18[0]["d"]).group(1)
                    fonte = "Camera dei deputati (XVIII leg.)"
                    url = URL_CAMERA.replace("leg19", "leg18").format(id=idc)
        esito = "NESSUNA FONTE"
        if url:
            try:
                n = scarica(url, FOTO / f"{m['id']}.jpg")
                esito = f"ok ({n // 1024} KB)"
            except Exception as e:  # noqa: BLE001
                esito = f"ERRORE: {e}"
        righe.append({"id": m["id"], "nome": f"{m['nome']} {m['cognome']}",
                      "fonte": fonte, "url": url, "esito": esito})
        print(f"{m['id']:14}{fonte:34}{esito}")

    with open(BASE / "fonti.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(righe[0]))
        w.writeheader()
        w.writerows(righe)
    ok = sum(r["esito"].startswith("ok") for r in righe)
    print(f"\n{ok} foto su {len(righe)}")


if __name__ == "__main__":
    main()
