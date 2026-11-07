# formation_parametres_actualite

Affichage du statut des points d'actualité en attente (votes, navettes parlementaires, arrêts attendus) dans les pages des DA.

| Fichier | Rôle |
|---|---|
| `actualite.js` | Script commun : lit la table `public.parametres_actualite` (Supabase) et remplit les encarts, fiches « Où en est-on ? » et jalons de frise |
| `exemple_actualite.html` | Page d'exemple des trois emplacements |
| `index.html` | Redirection vers la page d'exemple |
| `sql/parametres_actualite.sql` | Création de la table, du journal et des règles d'accès (déjà exécuté le 01/11/2026) |

## Intégration dans une page de DA

```html
<script>
  window.ACTUALITE = {
    url: 'https://ibkvyjlglwufxvzxnysa.supabase.co',
    key: 'sb_publishable_xUfZHSOHf4TnBRRyzU_qJA_TcXIMSKX',
    da:  'actualite-droit-assurances'
  };
</script>
<script src="https://thle2.github.io/formation_parametres_actualite/actualite.js" defer></script>

<div data-actualite="ris-vote-pleniere" data-format="encart">Texte de repli…</div>
<div data-actualite-module="M4" data-format="fiche">Texte de repli…</div>
<span data-actualite="ris-vote-pleniere" data-format="jalon">11/11/2026</span>
```

Le texte écrit dans chaque élément reste affiché si la base ne répond pas.

## Mise à jour d'un statut

Dans Supabase (Table Editor), modifier la ligne concernée : `statut`, `resultat`, `date_intervenue`, `verifie_le`. Les pages se mettent à jour au chargement suivant ; l'état précédent est conservé dans `parametres_actualite_journal`.

## Repérage des contenus touchés par une valeur (`impact/`)

`impact/impact_valeur.py` liste les pages publiées (QCM, exercices, corrigés, mémos, études de cas, évaluations) qui citent la valeur d'une clé, sous toutes ses écritures, ainsi que les valeurs dérivées déclarées dans `impact/compositions.json` (ex. 30 % = 12,8 % + 17,2 %). Lecture seule : il ne modifie ni la base ni les pages.

```
python3 impact/impact_valeur.py epargne_ps_taux_assurance_vie
python3 impact/impact_valeur.py --valeur 0.172 --unite % --cle epargne_ps_taux_assurance_vie
```

Utilisé par la veille hebdomadaire pour chaque écart constaté. Périmètre : HTML et JS publiés sur GitHub Pages ; les PDF, Word, PowerPoint et vidéos ne sont pas lus.
