/* =====================================================================
   actualite.js — affiche le statut des points d'actualité en attente
   Source : table public.parametres_actualite (Supabase, lecture anon)

   Configuration, avant le chargement du script :
     <script>
       window.ACTUALITE = {
         url: 'https://ibkvyjlglwufxvzxnysa.supabase.co',
         key: 'sb_publishable_xUfZHSOHf4TnBRRyzU_qJA_TcXIMSKX',
         da:  'actualite-droit-assurances'
       };
     </script>
     <script src="actualite.js" defer></script>

   Si la page charge déjà supabase-js (window.supabase), il est réutilisé ;
   sinon le script interroge directement l'API REST.

   Trois emplacements possibles dans une page :
     Encart sous la vidéo  : <div data-actualite="ris-vote-pleniere" data-format="encart">texte de repli</div>
     Fiche « Où en est-on ? » : <div data-actualite-module="M1" data-format="fiche">texte de repli</div>
     Jalon de frise        : <span data-actualite="ris-vote-pleniere" data-format="jalon">11/11/2026</span>

   Le contenu écrit dans l'élément sert de repli : si la base ne répond
   pas, il reste affiché tel quel. Aucun contenu de la base n'est injecté
   en HTML (textContent uniquement).
   ===================================================================== */
(function () {
  'use strict';

  var LIBELLE_STATUT = {
    attendu: 'En attente',
    intervenu: 'Intervenu',
    reporte: 'Reporté',
    abandonne: 'Abandonné'
  };

  function dateFr(iso) {
    if (!iso) return '';
    var p = iso.split('-');
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  function el(tag, cls, texte) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (texte) e.textContent = texte;
    return e;
  }

  function ligne(libelle, texte) {
    var p = el('p', 'act-ligne');
    p.appendChild(el('strong', null, libelle + ' '));
    p.appendChild(document.createTextNode(texte));
    return p;
  }

  function echeance(r) {
    if (r.statut === 'intervenu') return dateFr(r.date_intervenue);
    if (r.date_attendue) return dateFr(r.date_attendue) + (r.date_attendue_libelle ? ' (' + r.date_attendue_libelle + ')' : '');
    return r.date_attendue_libelle || 'non fixée';
  }

  function carte(r, avecTitre) {
    var c = el('div', 'act-carte act-' + r.statut);
    var tete = el('div', 'act-tete');
    tete.appendChild(el('span', 'act-badge', LIBELLE_STATUT[r.statut] || r.statut));
    tete.appendChild(el('span', 'act-date', 'Situation au ' + dateFr(r.verifie_le)));
    c.appendChild(tete);
    if (avecTitre) c.appendChild(el('p', 'act-titre', r.intitule));
    c.appendChild(ligne('Ce qui est acquis :', r.acquis));
    if (r.statut === 'intervenu' && r.resultat) {
      c.appendChild(ligne('Résultat :', r.resultat));
    }
    if (r.attendu) {
      c.appendChild(ligne(r.statut === 'intervenu' ? 'Et ensuite :' : 'Ce qui est attendu :',
        r.attendu + (r.statut === 'intervenu' ? '' : ' Échéance : ' + echeance(r) + '.')));
    }
    var s = el('p', 'act-source');
    s.appendChild(document.createTextNode('Source : '));
    var a = el('a', null, r.source_libelle);
    a.href = r.source_url; a.target = '_blank'; a.rel = 'noopener';
    s.appendChild(a);
    c.appendChild(s);
    return c;
  }

  function remplacer(cible, contenu) {
    while (cible.firstChild) cible.removeChild(cible.firstChild);
    cible.appendChild(contenu);
  }

  function rendre(lignes) {
    var parCle = {};
    lignes.forEach(function (r) { parCle[r.cle] = r; });

    document.querySelectorAll('[data-actualite][data-format="encart"]').forEach(function (n) {
      var r = parCle[n.getAttribute('data-actualite')];
      if (r) remplacer(n, carte(r, false));
    });

    document.querySelectorAll('[data-actualite-module][data-format="fiche"]').forEach(function (n) {
      var mod = n.getAttribute('data-actualite-module');
      var liste = lignes.filter(function (r) { return r.module === mod; });
      if (!liste.length) return;
      var f = document.createDocumentFragment();
      liste.forEach(function (r) { f.appendChild(carte(r, true)); });
      remplacer(n, f);
    });

    document.querySelectorAll('[data-actualite][data-format="jalon"]').forEach(function (n) {
      var r = parCle[n.getAttribute('data-actualite')];
      if (!r) return;
      n.textContent = echeance(r);
      n.classList.remove('jalon-attendu', 'jalon-intervenu', 'jalon-reporte', 'jalon-abandonne');
      n.classList.add('jalon-' + r.statut);
      n.setAttribute('title', (LIBELLE_STATUT[r.statut] || r.statut) + ' — situation au ' + dateFr(r.verifie_le));
    });
  }

  function styles() {
    if (document.getElementById('act-styles')) return;
    var st = document.createElement('style');
    st.id = 'act-styles';
    st.textContent =
      '.act-carte{border:1px solid #d5dce4;border-left:4px solid #4a6a8a;border-radius:0;padding:12px 16px;margin:12px 0;background:#f7f9fb;font-size:15px;line-height:1.6}' +
      '.act-intervenu{border-left-color:#2e7d5b}.act-reporte,.act-abandonne{border-left-color:#a35a00}' +
      '.act-tete{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:6px}' +
      '.act-badge{font-size:12px;font-weight:600;padding:2px 8px;border-radius:10px;background:#e4ebf2;color:#1f2a37}' +
      '.act-intervenu .act-badge{background:#dff1e7;color:#1d5a40}' +
      '.act-date{font-size:12px;color:#6b7684}.act-titre{font-weight:600;margin:4px 0}' +
      '.act-ligne{margin:4px 0}.act-source{font-size:13px;color:#6b7684;margin:6px 0 0}' +
      '.jalon-attendu{font-style:italic;opacity:.75}.jalon-intervenu{font-weight:600}';
    document.head.appendChild(st);
  }

  /* Lecture : client supabase-js si la page le charge déjà, sinon API REST.
     Avec une clé « sb_publishable_ », l'appel REST n'envoie que l'en-tête apikey. */
  function lire(cfg) {
    if (window.supabase && typeof window.supabase.createClient === 'function') {
      var client = window.supabase.createClient(cfg.url, cfg.key);
      return client.from('parametres_actualite').select('*')
        .eq('da_code', cfg.da).order('ordre', { ascending: true })
        .then(function (res) { if (res.error) throw res.error; return res.data; });
    }
    var url = cfg.url.replace(/\/$/, '') + '/rest/v1/parametres_actualite' +
      '?select=*&da_code=eq.' + encodeURIComponent(cfg.da) + '&order=ordre.asc';
    return fetch(url, { headers: { apikey: cfg.key } })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  }

  function charger() {
    var cfg = window.ACTUALITE || {};
    cfg.key = cfg.key || cfg.anonKey;
    if (!cfg.url || !cfg.key || !cfg.da) return;
    if (!document.querySelector('[data-actualite],[data-actualite-module]')) return;
    styles();
    lire(cfg)
      .then(rendre)
      .catch(function (e) {
        /* repli : le texte statique de la page reste affiché */
        if (window.console) console.warn('[actualite] lecture impossible :', e && e.message ? e.message : e);
      });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', charger);
  else charger();
})();
