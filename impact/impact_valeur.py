#!/usr/bin/env python3
"""Repérage des contenus publiés qui citent une valeur de paramètre.

Lecture seule : télécharge les pages publiées des dépôts thle2 (GitHub Pages),
cherche la valeur sous ses différentes écritures (17,2 % · 17,2% · 48 060 € ...)
et, via compositions.json, les valeurs dérivées (30 % = 12,8 % + 17,2 %).

Usage :
  python3 impact_valeur.py CLE [CLE ...]            # valeurs lues dans v_echeances
  python3 impact_valeur.py --valeur 0.172 --unite % --cle epargne_ps_taux_assurance_vie
Options : --cache DIR (corpus réutilisé d'un passage à l'autre dans la même session)
          --json FICHIER (résultat brut)

Sortie : pour chaque valeur, les pages qui la citent (dépôt, fichier, nature,
nombre d'occurrences, extrait). Limites : seuls les fichiers HTML/JS publiés
sont lus (pas les PDF, Word, PowerPoint ni les vidéos).
"""
import argparse, concurrent.futures as cf, html, json, os, re, subprocess, sys, urllib.parse, urllib.request

OWNER = "thle2"
SUPA = "https://ibkvyjlglwufxvzxnysa.supabase.co/rest/v1"
KEY = "sb_publishable_xUfZHSOHf4TnBRRyzU_qJA_TcXIMSKX"
ICI = os.path.dirname(os.path.abspath(__file__))
EXCLUS = {"formation_parametres_actualite", "admin-fiscalite"}  # comparés en minuscules

NATURES = [  # ordre = priorité
    ("corrigé", r"corrig|correction|solution"),
    ("évaluation", r"evaluation|eval_|_eval|positionnement|examen"),
    ("QCM / quiz", r"qcm|quiz"),
    ("étude de cas", r"cas_|_cas|cas\d|etude|etude_de_cas"),
    ("exercice", r"exo|exercice|entrainement|calcul|simulat"),
    ("mémo / fiche", r"memo|fiche|lexique|synthese"),
    ("vidéo", r"video|vid-o|capsule|script"),
    ("exemple / support", r"exemple|module|support|cours"),
]


def nature(nom):
    n = nom.lower()
    for lab, pat in NATURES:
        if re.search(pat, n):
            return lab
    return "autre"


def get(url, timeout=20):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


# ---------- liste des dépôts ----------
def depots():
    noms, page = [], 1
    while True:
        out = subprocess.run(
            ["gh", "api", "-X", "GET", "search/repositories", "-f", f"q=user:{OWNER}",
             "-f", "per_page=100", "-f", f"page={page}", "--jq", "[.items[].name]"],
            capture_output=True, text=True)
        if out.returncode != 0:
            sys.exit("Liste des dépôts illisible : " + out.stderr.strip())
        lot = json.loads(out.stdout or "[]")
        noms += lot
        if len(lot) < 100 or page >= 10:
            break
        page += 1
    if len(noms) >= 1000:
        print("ATTENTION : 1000 dépôts ou plus, la recherche GitHub plafonne à 1000 ; liste incomplète.", file=sys.stderr)
    return sorted(n for n in set(noms) if n.lower() not in EXCLUS)


# ---------- corpus ----------
LIEN = re.compile(r'''(?:src|href)\s*=\s*["']([^"'#?]+\.(?:html?|js))["']|url=([^"'>\s]+\.html?)''', re.I)


def pages_depot(nom):
    """Renvoie {chemin: texte} pour index.html, sa cible de redirection et les .html/.js locaux liés."""
    for branche in ("main", "master", "gh-pages"):
        base = f"https://raw.githubusercontent.com/{OWNER}/{nom}/{branche}/"
        idx = get(base + "index.html")
        if idx is not None:
            break
    else:
        return {}
    vus, file, res = set(), ["index.html"], {}
    while file and len(res) < 15:
        chemin = file.pop(0)
        if chemin in vus:
            continue
        vus.add(chemin)
        txt = idx if chemin == "index.html" else get(base + urllib.parse.quote(chemin))
        if txt is None:
            continue
        res[chemin] = txt
        for m in LIEN.finditer(txt):
            c = (m.group(1) or m.group(2)).strip()
            if "://" in c or c.startswith("//"):
                continue
            c = os.path.normpath(os.path.join(os.path.dirname(chemin), c)).lstrip("./")
            if c not in vus:
                file.append(c)
    return res


def corpus(cache):
    fic = os.path.join(cache, "corpus.json") if cache else None
    if fic and os.path.exists(fic):
        return json.load(open(fic))
    noms = depots()
    data = {}
    with cf.ThreadPoolExecutor(24) as ex:
        for nom, pages in zip(noms, ex.map(pages_depot, noms)):
            if pages:
                data[nom] = pages
    if fic:
        os.makedirs(cache, exist_ok=True)
        json.dump(data, open(fic, "w"))
    print(f"Corpus : {len(data)} dépôts lus sur {len(noms)}.", file=sys.stderr)
    return data


def texte(t):
    t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.I | re.S)  # CSS : bruit (width:30%)
    t = re.sub(r"style\s*=\s*\"[^\"]*\"|style\s*=\s*'[^']*'", " ", t, flags=re.I)
    t = re.sub(r"\b(?:width|height|left|top|right|bottom|opacity|flex-basis|max-width|min-width)\s*:\s*[\d.]+%", " ", t, flags=re.I)  # CSS dans le JS
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"[   ]", " ", t)


# ---------- écritures d'une valeur ----------
def fr(x, dec):
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def motifs(valeur, unite):
    """Renvoie (regex, libellé lisible) ou None si la valeur est trop banale pour être cherchée seule."""
    v = float(valeur)
    u = (unite or "").strip().lower()
    if u == "%":
        p = v * 100 if abs(v) <= 1 else v  # quelques taux sont stockés en pourcentage (ex. 9.20)
        p = round(p, 4)
        ent = int(p) if p == int(p) else None
        dec = 0 if ent is not None else len(f"{p}".rstrip("0").split(".")[1])
        corps = [fr(p, dec).replace(",", "[,.]")]
        if ent is not None:
            corps.append(f"{ent}[,.]0+")
        num = "(?:" + "|".join(corps) + ")"
        return rf"(?<![\d,.]){num}\s?%", fr(p, dec) + " %"
    if u in ("eur", "€") or u.startswith("eur"):
        dec = 0 if v == int(v) else 2
        s = fr(v, dec)
        num = re.escape(s).replace(r"\ ", r"[ .]?")
        if v == int(v) and v < 1000:
            return rf"(?<![\d,.]){num}\s?(?:€|euros?)", s + " €"
        return rf"(?<![\d,.]){num}(?![\d]|[,.]\d)", s + " €"
    if u in ("ans", "jours", "mois", "trimestres", "années", "quinzaines"):
        n = int(v) if v == int(v) else v
        return rf"(?<![\d,.]){n}\s?{u[:-1] if u.endswith('s') else u}s?\b", f"{n} {u}"
    return None


# ---------- valeurs en base ----------
def valeurs_base():
    q = urllib.parse.urlencode({"select": "cle,valeur,unite,table_source,intitule", "apikey": KEY})
    d = json.loads(get(f"{SUPA}/v_echeances?{q}") or "[]")
    return {x["cle"]: x for x in d if x.get("valeur") not in (None, "")}


def cibles(cles, base):
    comp = json.load(open(os.path.join(ICI, "compositions.json")))["compositions"]
    out = []
    for c in cles:
        x = base.get(c)
        if not x:
            print(f"Clé inconnue ou sans valeur : {c}", file=sys.stderr)
            continue
        m = motifs(x["valeur"], x["unite"])
        if m:
            out.append({"cle": c, "type": "valeur", "regex": m[0], "affiche": m[1]})
        else:
            out.append({"cle": c, "type": "non cherchable", "affiche": f"{x['valeur']} {x['unite'] or ''}".strip()})
        for k in comp:
            if c in k["termes"] and all(t in base for t in k["termes"]):
                tot = sum(float(base[t]["valeur"]) for t in k["termes"])
                m = motifs(tot, k.get("unite", "%"))
                out.append({"cle": c, "type": "dérivée", "nom": k["nom"], "regex": m[0], "affiche": m[1]})
    return out


def chercher(cs, data):
    for c in cs:
        c["pages"] = []
        if "regex" not in c:
            continue
        rx = re.compile(c["regex"], re.I)
        for depot, pages in data.items():
            for chemin, t in pages.items():
                tt = texte(t)
                hits = list(rx.finditer(tt))
                if hits:
                    a = hits[0].start()
                    ext = re.sub(r"\s+", " ", tt[max(0, a - 70): a + 70]).strip()
                    c["pages"].append({"depot": depot, "fichier": chemin, "nature": nature(depot + " " + chemin),
                                       "occurrences": len(hits), "extrait": ext,
                                       "url": f"https://thle2.github.io/{depot}/{'' if chemin == 'index.html' else chemin}"})
        c["pages"].sort(key=lambda p: (-p["occurrences"], p["depot"]))
    return cs


def rapport(cs):
    lignes = []
    for c in cs:
        tete = f"{c['cle']} — {c['affiche']}" + (f" (valeur dérivée : {c['nom']} ; valeur courante, à trier : une partie des pages peut citer {c['affiche']} pour une autre raison)" if c["type"] == "dérivée" else "")
        if c["type"] == "non cherchable":
            lignes.append(f"{tete} : valeur trop courante pour être cherchée seule, contrôle manuel.")
            continue
        if not c["pages"]:
            lignes.append(f"{tete} : aucune page publiée ne la cite.")
            continue
        tot = sum(p["occurrences"] for p in c["pages"])
        lignes.append(f"{tete} : {tot} occurrence(s) dans {len(c['pages'])} page(s)")
        par = {}
        for p in c["pages"]:
            par.setdefault(p["nature"], []).append(p)
        for nat, ps in par.items():
            lignes.append(f"  {nat} :")
            for p in ps[:15]:
                lignes.append(f"    - {p['depot']}/{p['fichier']} ({p['occurrences']}) — {p['url']}\n      « …{p['extrait']}… »")
            if len(ps) > 15:
                lignes.append(f"    … et {len(ps) - 15} autre(s)")
    lignes.append("Périmètre : pages HTML et scripts publiés sur GitHub Pages ; PDF, Word, PowerPoint et vidéos non lus.")
    return "\n".join(lignes)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cles", nargs="*")
    ap.add_argument("--valeur"); ap.add_argument("--unite", default=""); ap.add_argument("--cle", default="(saisie)")
    ap.add_argument("--cache"); ap.add_argument("--json")
    a = ap.parse_args()
    if a.valeur:
        m = motifs(a.valeur, a.unite)
        cs = [{"cle": a.cle, "type": "valeur", "regex": m[0], "affiche": m[1]}] if m else []
    else:
        cs = cibles(a.cles, valeurs_base())
    cs = chercher(cs, corpus(a.cache))
    if a.json:
        json.dump(cs, open(a.json, "w"), ensure_ascii=False, indent=1)
    print(rapport(cs))
