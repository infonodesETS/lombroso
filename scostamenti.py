"""LOMBROSO - scostamenti dalla media del governo.

Legge prova/misure.json e, per ogni misura, calcola media e variabilità del
gruppo; poi esprime ogni persona come scostamento dalla media (in "deviazioni
standard": 0 = nella media, +2 = molto sopra, -2 = molto sotto).
Scrive prova/scostamenti.csv e stampa i casi estremi.

Uso:  .venv/Scripts/python scostamenti.py
"""
import csv
import json
import statistics as st
from pathlib import Path

BASE = Path(__file__).parent
SOGLIA = 1.5          # oltre questo scostamento il tratto "scatta"
MAX_ROTAZIONE = 16    # volti troppo girati: misure di larghezza inaffidabili

misure = json.loads((BASE / "prova" / "misure.json").read_text(encoding="utf-8"))
chiavi = [k for k in next(iter(misure.values())) if not k.startswith("_")]
# deviazione del naso e asimmetria contano in valore assoluto
ASSOLUTE = {"naso_deviazione_pct"}

validi = {n: m for n, m in misure.items()
          if abs(m["_rotazione_pct"]) <= MAX_ROTAZIONE}
esclusi = sorted(set(misure) - set(validi))


def val(m, k):
    return abs(m[k]) if k in ASSOLUTE else m[k]


stat = {k: (st.mean(val(m, k) for m in validi.values()),
            st.stdev(val(m, k) for m in validi.values())) for k in chiavi}

righe = []
for n, m in validi.items():
    r = {"id": n}
    for k in chiavi:
        media, dev = stat[k]
        r[k] = round((val(m, k) - media) / dev, 2)
    righe.append(r)

with open(BASE / "prova" / "scostamenti.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["id"] + chiavi)
    w.writeheader()
    w.writerows(righe)

print(f"Volti usati: {len(validi)}   esclusi perché troppo girati: {esclusi}\n")
for k in chiavi:
    media, dev = stat[k]
    alti = sorted((r for r in righe if r[k] >= SOGLIA), key=lambda r: -r[k])
    bassi = sorted((r for r in righe if r[k] <= -SOGLIA), key=lambda r: r[k])
    print(f"{k}  (media {media:.3f}, variabilità {dev:.3f})")
    print("   molto sopra:", ", ".join(f"{r['id']} {r[k]:+}" for r in alti) or "-")
    print("   molto sotto:", ", ".join(f"{r['id']} {r[k]:+}" for r in bassi) or "-")
conteggio = {r["id"]: sum(abs(r[k]) >= SOGLIA for k in chiavi) for r in righe}
print("\nTratti fuori media per persona:",
      ", ".join(f"{n} {c}" for n, c in sorted(conteggio.items(), key=lambda x: -x[1]) if c))
