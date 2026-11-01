-- =====================================================================
-- parametres_actualite — statut des points d'actualité en attente
-- DA concerné : actualite-droit-assurances (table réutilisable par d'autres DA)
--
-- Conventions reprises de la base existante :
--   · schéma public, comme les autres tables parametres_*
--   · RLS activée : lecture publique, écriture réservée au personnel
--     via lms.est_personnel()
--   · privilèges de table accordés explicitement (une politique RLS
--     sans GRANT ne donne aucun accès)
-- Rejouable : création « if not exists », amorçage par upsert sur la clé.
-- =====================================================================

begin;

-- 1. Table ------------------------------------------------------------
create table if not exists public.parametres_actualite (
  cle                    text primary key
                         check (cle ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  da_code                text not null,
  module                 text not null,                 -- ex. 'M1'
  ordre                  int  not null default 0,       -- ordre d'affichage (frise, fiche)
  intitule               text not null,
  statut                 text not null default 'attendu'
                         check (statut in ('attendu','intervenu','reporte','abandonne')),
  acquis                 text not null,                 -- ce qui est certain à ce jour
  attendu                text,                          -- ce qui reste à intervenir
  resultat               text,                          -- issue, une fois intervenue
  date_attendue          date,
  date_attendue_libelle  text,                          -- 'date indicative', 'non fixée'…
  date_intervenue        date,
  source_libelle         text not null,
  source_url             text not null check (source_url ~ '^https://'),
  verifie_le             date not null,                 -- dernière vérification à la source
  maj_le                 timestamptz not null default now(),
  maj_par                uuid default auth.uid(),
  constraint actualite_intervenu_complet check (
    statut <> 'intervenu' or (resultat is not null and date_intervenue is not null)
  )
);

comment on table public.parametres_actualite is
  'Statut des points d''actualité en attente (votes, navettes, arrêts attendus). Lu par les pages des DA : encart vidéo, fiche « Où en est-on ? », jalons de frise.';
comment on column public.parametres_actualite.cle is
  'Clé citée dans la colonne parametres_cites de la matrice du DA.';

-- 2. Journal des modifications -----------------------------------------
create table if not exists public.parametres_actualite_journal (
  id           bigint generated always as identity primary key,
  cle          text not null,
  ancien       jsonb,
  nouveau      jsonb,
  modifie_le   timestamptz not null default now(),
  modifie_par  uuid default auth.uid()
);

-- 3. Horodatage et journalisation --------------------------------------
create or replace function public.parametres_actualite_horodater()
returns trigger language plpgsql as $$
begin
  new.maj_le  := now();
  new.maj_par := auth.uid();
  return new;
end $$;

create or replace function public.parametres_actualite_journaliser()
returns trigger language plpgsql security definer
set search_path = public, pg_temp as $$
begin
  insert into public.parametres_actualite_journal (cle, ancien, nouveau)
  values (coalesce(new.cle, old.cle),
          case when tg_op <> 'INSERT' then to_jsonb(old) end,
          case when tg_op <> 'DELETE' then to_jsonb(new) end);
  return coalesce(new, old);
end $$;

drop trigger if exists actualite_horodater on public.parametres_actualite;
create trigger actualite_horodater
  before update on public.parametres_actualite
  for each row execute function public.parametres_actualite_horodater();

drop trigger if exists actualite_journaliser on public.parametres_actualite;
create trigger actualite_journaliser
  after insert or update or delete on public.parametres_actualite
  for each row execute function public.parametres_actualite_journaliser();

-- 4. RLS et privilèges ---------------------------------------------------
alter table public.parametres_actualite         enable row level security;
alter table public.parametres_actualite_journal enable row level security;

drop policy if exists actualite_lecture  on public.parametres_actualite;
drop policy if exists actualite_ecriture on public.parametres_actualite;
drop policy if exists actualite_journal_lecture on public.parametres_actualite_journal;

create policy actualite_lecture on public.parametres_actualite
  for select to anon, authenticated using (true);

create policy actualite_ecriture on public.parametres_actualite
  for all to authenticated
  using (lms.est_personnel()) with check (lms.est_personnel());

create policy actualite_journal_lecture on public.parametres_actualite_journal
  for select to authenticated using (lms.est_personnel());

revoke all on public.parametres_actualite, public.parametres_actualite_journal from anon, authenticated;
grant select on public.parametres_actualite to anon, authenticated;
grant insert, update, delete on public.parametres_actualite to authenticated;
grant select on public.parametres_actualite_journal to authenticated;

-- 5. Amorçage — points vérifiés le 01/11/2026 ---------------------------
insert into public.parametres_actualite
  (cle, da_code, module, ordre, intitule, statut, acquis, attendu,
   date_attendue, date_attendue_libelle, source_libelle, source_url, verifie_le)
values
  ('ris-vote-pleniere', 'actualite-droit-assurances', 'M1', 10,
   'Vote de la Retail Investment Strategy en plénière du Parlement européen', 'attendu',
   'Accord politique du 18/12/2025. Compromis approuvé par la commission ECON le 23/06/2026 (33 voix pour, 23 contre, 2 abstentions).',
   'Vote en plénière, puis adoption par le Conseil et publication au Journal officiel de l''Union européenne. Transposition dans les 2 ans, application 30 mois après la publication (18 mois pour les règles PRIIPs).',
   '2026-11-11', 'date indicative',
   'Parlement européen — Legislative Train, Retail Investment Strategy',
   'https://www.europarl.europa.eu/legislative-train/theme-economic-and-monetary-affairs-econ/file-retail-investment-strategy',
   '2026-11-01'),

  ('catnat-ppl-barusseau', 'actualite-droit-assurances', 'M4', 20,
   'Proposition de loi Barusseau : adaptation des mécanismes d''assurance au changement climatique', 'attendu',
   'Adoptée en première lecture par l''Assemblée nationale le 8/04/2026, puis par le Sénat le 19/10/2026 dans une rédaction modifiée (réparation résiliente, réexamen quinquennal de la surprime ; surprime différenciée des résidences secondaires supprimée).',
   'Deuxième lecture à l''Assemblée nationale.',
   null, 'non fixée',
   'Sénat — compte rendu de la séance du 19 octobre 2026',
   'https://www.senat.fr/seances/s202610/s20261019/s20261019018.html',
   '2026-11-01'),

  ('solvabilite2-transposition', 'actualite-droit-assurances', 'M4', 30,
   'Transposition de la révision de Solvabilité II et de la directive IRRD', 'attendu',
   'Directives (UE) 2025/1 (redressement et résolution des assureurs) et 2025/2 (révision de Solvabilité II) publiées au Journal officiel de l''Union européenne le 8/01/2025.',
   'Transposition en droit français au plus tard le 29/01/2027, application à compter du 30/01/2027.',
   '2027-01-29', 'date limite de transposition',
   'Lefebvre Dalloz — Solvabilité II révisée, échéance 2027',
   'https://formation.lefebvre-dalloz.fr/actualite/solvabilite-ii-revisee-impacts-concrets-et-enjeux-de-preparation-du-secteur-de-lassurance-face-lecheance-2027',
   '2026-11-01'),

  ('dpf-pourvoi-cjue', 'actualite-droit-assurances', 'M5', 40,
   'Pourvoi contre l''arrêt validant le Data Privacy Framework (affaire C-703/25 P)', 'attendu',
   'Data Privacy Framework adopté par décision d''adéquation du 10/07/2023, validé par le Tribunal de l''Union européenne le 3/09/2025 (affaire T-553/23, Latombe).',
   'Arrêt de la Cour de justice de l''Union européenne sur le pourvoi.',
   null, 'non fixée',
   'CURIA — communiqué de presse n° 106/25',
   'https://curia.europa.eu/jcms/jcms/p1_5126456/ga',
   '2026-11-01')
on conflict (cle) do update set
  da_code = excluded.da_code, module = excluded.module, ordre = excluded.ordre,
  intitule = excluded.intitule, statut = excluded.statut, acquis = excluded.acquis,
  attendu = excluded.attendu, date_attendue = excluded.date_attendue,
  date_attendue_libelle = excluded.date_attendue_libelle,
  source_libelle = excluded.source_libelle, source_url = excluded.source_url,
  verifie_le = excluded.verifie_le;

-- 6. Vérification ---------------------------------------------------------
do $$
declare n int;
begin
  select count(*) into n from public.parametres_actualite
   where da_code = 'actualite-droit-assurances';
  if n <> 4 then
    raise exception 'parametres_actualite : 4 lignes attendues, % trouvées', n;
  end if;
end $$;

commit;

-- =====================================================================
-- Mise à jour type, après le vote de la RIS (à adapter au résultat réel) :
--
-- update public.parametres_actualite
--    set statut = 'intervenu',
--        resultat = 'Texte adopté en plénière le JJ/MM/AAAA (xxx pour, xxx contre, xxx abstentions).',
--        date_intervenue = 'AAAA-MM-JJ',
--        attendu = 'Adoption par le Conseil et publication au JOUE.',
--        verifie_le = current_date
--  where cle = 'ris-vote-pleniere';
--
-- Le journal conserve l'état précédent ; l'encart, la fiche et la frise
-- du M1 affichent le nouveau statut au prochain chargement.
-- =====================================================================
