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
