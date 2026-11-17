"""LOMBROSO - ricerca su Wikimedia Commons dei ritratti ufficiali del Senato.

Il sito del Senato non consente lo scaricamento automatico. Su Commons
esistono copie dei ritratti ufficiali, riconoscibili dal nome del file
("... datisenato 2022.jpg"). Per ogni membro del governo che in fonti.csv
risulta senza foto, cerca quel file e stampa cosa trova.
Con --scrivi aggiunge i risultati a fonti_manuali.csv.

Uso:  .venv/Scripts/python commons.py [--scrivi]
"""
import csv
import json
import sys
import time
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "ritratti-ufficiali-script/0.1 (python urllib)"}


def api(**par):
    par["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(par)
    for attesa in (0, 20, 60, 120):   # riprova con calma se il sito chiede di rallentare
        time.sleep(attesa)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    raise RuntimeError("Commons continua a rispondere 'troppe richieste'")


def cerca(nome):
    cognome = nome.split()[-1]
    ris = api(action="query", generator="search", gsrnamespace=6, gsrlimit=20,
              gsrsearch=f'intitle:datisenato intitle:"{cognome}"',
              prop="imageinfo", iiprop="url|extmetadata|size")
    pagine = list(ris.get("query", {}).get("pages", {}).values())
    # tieni solo i file che contengono anche il primo nome
    primo = nome.split()[0].lower()
    pagine = [p for p in pagine if primo in p["title"].lower()]
    # preferisci la foto più recente (anno nel nome del file)
    anno = lambda p: int((re.findall(r"(?:19|20)\d\d", p["title"]) or ["0"])[-1])
    pagine.sort(key=anno, reverse=True)
    return pagine


def main():
    scrivi = "--scrivi" in sys.argv
    with open(BASE / "fonti.csv", encoding="utf-8", newline="") as f:
        mancanti = [r for r in csv.DictReader(f) if not r["esito"].startswith("ok")]
    trovati = []
    for r in mancanti:
        pagine = cerca(r["nome"])
        time.sleep(3)
        if not pagine:
            print(f"{r['id']:14}-")
            continue
        p = pagine[0]
        ii = p["imageinfo"][0]
        lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "?")
        print(f"{r['id']:14}{p['title']}  [{ii['width']}x{ii['height']}, {lic}]")
        trovati.append({"id": r["id"],
                        "fonte": f"Senato della Repubblica, via Wikimedia Commons ({lic})",
                        "url": ii["url"]})
    print(f"\ntrovati {len(trovati)} su {len(mancanti)} mancanti")
    if scrivi and trovati:
        fm = BASE / "fonti_manuali.csv"
        nuovo = not fm.exists()
        with open(fm, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id", "fonte", "url"])
            if nuovo:
                w.writeheader()
            w.writerows(trovati)
        print("aggiunti a fonti_manuali.csv")


if __name__ == "__main__":
    main()
