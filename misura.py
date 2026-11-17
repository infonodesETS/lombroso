"""LOMBROSO - misurazione dei volti.

Per ogni foto in foto/ individua i punti del viso (MediaPipe Face Landmarker,
478 punti) e ne ricava alcune proporzioni. Scrive:
  - prova/misure.json   : le misure di ogni persona
  - prova/<nome>_punti.jpg : la foto con i punti disegnati sopra

Uso:  .venv/Scripts/python misura.py
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

BASE = Path(__file__).parent
FOTO = BASE / "foto"
OUT = BASE / "prova"
MODELLO = BASE / "modelli" / "face_landmarker.task"

# Punti della maglia MediaPipe usati per le misure
P = {
    "fronte_alta": 10, "mento": 152,
    "zigomo_sx": 234, "zigomo_dx": 454,
    "mandibola_sx": 172, "mandibola_dx": 397,
    "occhio_est_sx": 33, "occhio_int_sx": 133,
    "occhio_int_dx": 362, "occhio_est_dx": 263,
    "glabella": 9, "radice_naso": 168, "punta_naso": 1, "base_naso": 2,
    "ala_naso_sx": 129, "ala_naso_dx": 358,
    "bocca_sx": 61, "bocca_dx": 291,
    "labbro_sup": 0, "labbro_inf": 17,
    "sopracciglio_sx": 105, "sopracciglio_dx": 334,
}
# Coppie simmetriche (sinistra, destra) per l'asimmetria
COPPIE = [(234, 454), (172, 397), (33, 263), (133, 362), (129, 358),
          (61, 291), (105, 334), (58, 288), (132, 361), (136, 365)]
LINEA_MEDIANA = [10, 9, 168, 1, 2, 0, 17, 152]


def dist(a, b):
    return float(np.linalg.norm(a - b))


def misura(percorso, landmarker):
    img = cv2.imread(str(percorso))
    h, w = img.shape[:2]
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                      data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    ris = landmarker.detect(mp_img)
    if not ris.face_landmarks:
        return None, img
    lm = ris.face_landmarks[0]
    pts = np.array([[p.x * w, p.y * h] for p in lm])
    z = np.array([p.z * w for p in lm])

    # Raddrizza la testa: ruota finché gli occhi sono in orizzontale
    occhi = pts[263] - pts[33]
    inclinazione = math.degrees(math.atan2(occhi[1], occhi[0]))
    a = -math.radians(inclinazione)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    centro = pts.mean(axis=0)
    r = (pts - centro) @ R.T + centro

    # Quanto la testa è girata di lato, prima di ogni correzione
    # (0 = perfettamente frontale): serve a scartare le foto inadatte
    asse0 = float(np.mean([r[i][0] for i in LINEA_MEDIANA]))
    larg0 = dist(r[234], r[454])
    rotazione = ((r[454][0] - asse0) - (asse0 - r[234][0])) / larg0 * 100

    # Raddrizza anche la rotazione laterale usando la profondità stimata:
    # ruota attorno all'asse verticale finché i due zigomi sono alla stessa
    # distanza dall'obiettivo
    dx = r[454][0] - r[234][0]
    dz = z[454] - z[234]
    imbardata = math.atan2(dz, dx)
    cx, cz = r[:, 0].mean(), z.mean()
    x_nuovo = (r[:, 0] - cx) * math.cos(imbardata) + (z - cz) * math.sin(imbardata) + cx
    r = np.column_stack([x_nuovo, r[:, 1]])
    g = lambda nome: r[P[nome]]

    alt_viso = dist(g("fronte_alta"), g("mento"))
    larg_zigomi = dist(g("zigomo_sx"), g("zigomo_dx"))
    larg_mandibola = dist(g("mandibola_sx"), g("mandibola_dx"))
    larg_naso = dist(g("ala_naso_sx"), g("ala_naso_dx"))
    alt_naso = dist(g("radice_naso"), g("base_naso"))
    larg_bocca = dist(g("bocca_sx"), g("bocca_dx"))
    spess_labbra = dist(g("labbro_sup"), g("labbro_inf"))
    dist_occhi = dist(g("occhio_int_sx"), g("occhio_int_dx"))
    larg_occhio = (dist(g("occhio_est_sx"), g("occhio_int_sx")) +
                   dist(g("occhio_int_dx"), g("occhio_est_dx"))) / 2
    alt_fronte = abs(g("glabella")[1] - g("fronte_alta")[1])
    alt_mento = abs(g("mento")[1] - g("labbro_inf")[1])

    # Asse mediano = retta verticale media dei punti centrali
    asse_x = float(np.mean([r[i][0] for i in LINEA_MEDIANA]))
    scarti = []
    for sx, dx in COPPIE:
        d_sx = asse_x - r[sx][0]
        d_dx = r[dx][0] - asse_x
        scarti.append(abs(d_sx - d_dx))            # differenza orizzontale
        scarti.append(abs(r[sx][1] - r[dx][1]))    # differenza verticale
    asimmetria = float(np.mean(scarti)) / larg_zigomi * 100
    deviazione_naso = (g("punta_naso")[0] - asse_x) / larg_zigomi * 100


    m = {
        "mandibola_su_zigomi": larg_mandibola / larg_zigomi,
        "zigomi_su_altezza_viso": larg_zigomi / alt_viso,
        "fronte_su_altezza_viso": alt_fronte / alt_viso,
        "mento_su_altezza_viso": alt_mento / alt_viso,
        "naso_larghezza_su_altezza": larg_naso / alt_naso,
        "naso_deviazione_pct": deviazione_naso,
        "labbra_spessore_su_bocca": spess_labbra / larg_bocca,
        "distanza_occhi_su_occhio": dist_occhi / larg_occhio,
        "occhio_su_zigomi": larg_occhio / larg_zigomi,
        "naso_altezza_su_viso": alt_naso / alt_viso,
        "asimmetria_pct": asimmetria,
        "_inclinazione_gradi": inclinazione,
        "_rotazione_pct": rotazione,
        "_imbardata_gradi": math.degrees(imbardata),
        "_larghezza_viso_pixel": larg_zigomi,
    }
    m = {k: round(float(v), 3) for k, v in m.items()}

    # Immagine con i punti (ingrandita 3x per leggibilità)
    k = 3
    vis = cv2.resize(img, (w * k, h * k), interpolation=cv2.INTER_CUBIC)
    for x, y in pts:
        cv2.circle(vis, (int(x * k), int(y * k)), 1, (200, 255, 200), -1)
    for i in P.values():
        x, y = pts[i]
        cv2.circle(vis, (int(x * k), int(y * k)), 4, (0, 0, 255), -1)
    for a_, b_ in [("zigomo_sx", "zigomo_dx"), ("mandibola_sx", "mandibola_dx"),
                   ("fronte_alta", "mento")]:
        pa, pb = pts[P[a_]], pts[P[b_]]
        cv2.line(vis, (int(pa[0] * k), int(pa[1] * k)),
                 (int(pb[0] * k), int(pb[1] * k)), (0, 220, 255), 2)
    return m, vis


def main():
    opzioni = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODELLO)),
        num_faces=1)
    OUT.mkdir(exist_ok=True)
    tutte = {}
    with vision.FaceLandmarker.create_from_options(opzioni) as lmk:
        # le foto frontali fornite a mano (foto_manuali/<id>_fronte.*)
        # hanno la precedenza su quelle scaricate (foto/<id>.jpg)
        scelte = {f.stem: f for f in sorted(FOTO.glob("*.jpg"))}
        for f in sorted((BASE / "foto_manuali").glob("*_fronte.*")):
            scelte[f.stem.removesuffix("_fronte")] = f
        for nome, f in sorted(scelte.items()):
            m, vis = misura(f, lmk)
            if m is None:
                print(f"{f.name}: NESSUN VOLTO TROVATO", file=sys.stderr)
                continue
            m["_foto"] = f.relative_to(BASE).as_posix()
            tutte[nome] = m
            cv2.imwrite(str(OUT / f"{nome}_punti.jpg"), vis)
    (OUT / "misure.json").write_text(
        json.dumps(tutte, indent=2, ensure_ascii=False), encoding="utf-8")
    nomi = list(tutte)
    print(f"{'misura':32}" + "".join(f"{n:>10}" for n in nomi))
    for chiave in next(iter(tutte.values())):
        print(f"{chiave:32}" + "".join(f"{tutte[n][chiave]:>10}" for n in nomi))


if __name__ == "__main__":
    main()
