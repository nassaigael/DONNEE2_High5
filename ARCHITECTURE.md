# Architecture – Pipeline ETL d'Air Quality Index (AQI)

## Vue d'ensemble

Ce projet implémente un **pipeline ETL entièrement automatisé et serverless** qui collecte, nettoie, valide et charge des données de qualité de l'air issues de l'API OpenWeather Air Pollution. Le pipeline s'exécute en continu depuis avril 2026 via une orchestration cloud native, sans infrastructure à maintenir.

```
API OpenWeather
        │
        ▼
   [GitHub Actions]
        │
   ┌────┴────────────────────┐
   │                         │
   ▼                         ▼
collect.py            backfill.py (1x/jour)
   │                         │
   └────┬────────────────────┘
        │
        ▼
    raw/ (JSON)
        │ [immuable]
        ▼
   clean.py
        │
        ▼
   clean/ (CSV)
        │ [contrat de données]
        ▼
 validate_clean.py
        │ [bloquant]
        ▼
load_warehouse.py
        │
        ▼
PostgreSQL Neon
 (schéma en étoile)
        │
        ▼
   Warehouse
 [accessible en production]
```

---

## Stack Technique

### 1. Orchestrateur : GitHub Actions

**Technologie** : GitHub Actions (YAML workflows)

**Justification** :
- ✅ **Serverless** : aucune infrastructure à configurer ni maintenir
- ✅ **Timing précis** : crons POSIX natifs pour l'exécution horaire et daily backfill
- ✅ **Intégration GitHub** : déploiement + gestion du code + CI/CD en un seul service
- ✅ **Secrets gérés** : variables d'environnement (clés API, credentials BD) stockées de manière sécurisée
- ✅ **Notifications** : emails d'alerte sur succès/échec via le workflow SMTP
- ✅ **Gratuit** : 2000 minutes/mois incluses, plus que suffisant pour 24 exécutions/jour
- ✅ **Audit trail** : logs accessibles et consultables pour chaque exécution

**Exécution** :
- Horaire : `0 * * * *` (chaque heure à minute 0)
- Manuel : déclenchement via `workflow_dispatch`
- Push : également exécuté sur chaque commit sur `main`

---

### 2. Stockage Brut : Système de fichiers (GitHub / raw/)

**Technologie** : Fichiers JSON immuables versionnés via Git

**Justification** :
- ✅ **Source de vérité** : les données brutes ne sont JAMAIS modifiées, c'est l'audit trail
- ✅ **Traçabilité** : chaque appel API produit un fichier JSON horodaté, consultable dans git log
- ✅ **Simplicité** : aucune dépendance externe, pas de serveur de fichiers
- ✅ **Récupération** : rejouer tout le pipeline en relisant simplement les fichiers raw/
- ✅ **Conformité** : adhère au cahier des charges ("stockage brut immuable")
- ✅ **Déduplication** : si collect.py et backfill.py créent des doublons, on conserve les deux et on déduplique au stade `clean.py`

**Structure** :
```
raw/
├── antananarivo_20260426T050000Z.json  # 1 fichier = 1 appel API = 1 mesure
├── antananarivo_20260426T060000Z.json
├── paris_20260426T050000Z.json
└── ...
```

Chaque fichier contient :
- Réponse de l'API OpenWeather : `list` (tableau de mesures)
- Métadonnées projet : `_meta` (ville, pays, lat, lon, collected_at)

---

### 3. Stockage Propre : Fichier CSV Unique (clean/)

**Technologie** : CSV déterministe, reconstruit à chaque exécution

**Justification** :
- ✅ **Contrat de données** : schéma strictement défini et documenté (colonnes, types, unités)
- ✅ **Déterministe** : chaque exécution produit le MÊME fichier (même ordre, même dédoublonnage)
- ✅ **Lisibilité** : format universellement compréhensible, pas de dépendance
- ✅ **Versioning** : commité dans git, traçabilité complète des modifications
- ✅ **Validation** : contrat enforced par `validate_clean.py` avant le load
- ✅ **Récupération** : ré-exécuter `clean.py` à partir de `raw/` permet de reconstuire depuis zéro

**Processus** :
1. Lire **tous** les fichiers JSON de `raw/`
2. Extraire mesures et métadonnées (fonction `parse_record()`)
3. **Dédupliquer** : une seule ligne par (ville, heure) ; en cas de doublon, garder la mesure la plus récemment collectée (`collected_at` le plus grand)
4. **Trier** : par ville, puis par timestamp_utc croissant
5. **Écrire** : en écrasant le fichier CSV précédent (pas d'ajout/concaténation)

**Colonnes du contrat** :
| Colonne        | Type      | Unité      | Description |
|---|---|---|---|
| `ville` | TEXT | — | Nom de la ville |
| `pays` | TEXT | — | Code pays 2 lettres |
| `latitude` | FLOAT | degrés | Latitude géographique |
| `longitude` | FLOAT | degrés | Longitude géographique |
| `timestamp_utc` | TEXT | ISO 8601 | Horodatage UTC (YYYY-MM-DDTHH:MM:SSZ) |
| `date` | TEXT | YYYY-MM-DD | Date seule |
| `heure` | INT | [0, 23] | Heure du jour |
| `jour_semaine` | TEXT | — | Jour semaine en anglais (Monday, Tuesday, …) |
| `is_weekend` | BOOL | — | True si samedi ou dimanche |
| `aqi` | INT | indice [1–5] | Air Quality Index OpenWeather |
| `co` | FLOAT | μg/m³ | Monoxyde de carbone |
| `no` | FLOAT | μg/m³ | Monoxyde d'azote |
| `no2` | FLOAT | μg/m³ | Dioxyde d'azote |
| `o3` | FLOAT | μg/m³ | Ozone |
| `so2` | FLOAT | μg/m³ | Dioxyde de soufre |
| `pm2_5` | FLOAT | μg/m³ | Particules fines ≤ 2.5 μm |
| `pm10` | FLOAT | μg/m³ | Particules ≤ 10 μm |
| `nh3` | FLOAT | μg/m³ | Ammoniac |

Valeurs manquantes = cellules vides (pas de 0 inventé, pas de suppression de ligne).

---

### 4. Data Warehouse : PostgreSQL (Cloud – Neon)

**Technologie** : PostgreSQL sur Neon (infrastructure cloud serverless)

**Justification** :
- ✅ **SQL standard** : requêtes portables, pas de vendor lock-in (contrairement à BigQuery, Snowflake)
- ✅ **Gratuit** : Neon offre un tier gratuit suffisant (5 GB storage, compute serverless)
- ✅ **Fiabilité** : base de données production-grade avec backups et haute disponibilité
- ✅ **Modélisation** : supporte les schémas en étoile (fact + dimensions)
- ✅ **Accessible** : connectivité JDBC/psycopg2 depuis GitHub Actions, facile à tester
- ✅ **Performance** : queries complexes sur millions de lignes en quelques secondes
- ✅ **Conformité** : répond au cahier des charges ("data warehouse")

**Credentials** :
- Stockés comme GitHub Secrets et Variables : `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Connexion SSL obligatoire (`sslmode='require'`)
- Connexion gérée via `psycopg2-binary`

---

## Modélisation du Warehouse

### Schéma en Étoile

Le warehouse suit un **schéma dimensionnel en étoile** (Kimball) pour optimiser l'analytique.

```
 ![alt text](<Screenshot From 2026-07-27 23-47-44-1.png>)

Contraintes:
- fact_air_quality.city_id (FK) → dim_city.city_id
- fact_air_quality.time_id (FK) → dim_time.time_id
- Clé unique : (city_id, time_id) — une seule mesure par ville/heure
```

### Tables

#### dim_city
Dimension des villes surveillées (petit volume, croissance lente).
```sql
CREATE TABLE dim_city (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) UNIQUE,
    country VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);
```

#### dim_time
Dimension temporelle (croissance linéaire, une heure = une ligne).
```sql
CREATE TABLE dim_time (
    time_id SERIAL PRIMARY KEY,
    timestamp_hour TIMESTAMP UNIQUE,
    date_value DATE,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    hour INTEGER,
    day_of_week VARCHAR(20),
    is_weekend BOOLEAN
);
```

#### fact_air_quality
Table de faits (concentrations de polluants, AQI).
```sql
CREATE TABLE fact_air_quality (
    fact_id SERIAL PRIMARY KEY,
    city_id INTEGER REFERENCES dim_city(city_id),
    time_id INTEGER REFERENCES dim_time(time_id),
    aqi INTEGER,
    co DOUBLE PRECISION,
    no DOUBLE PRECISION,
    no2 DOUBLE PRECISION,
    o3 DOUBLE PRECISION,
    so2 DOUBLE PRECISION,
    pm2_5 DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    nh3 DOUBLE PRECISION,
    UNIQUE (city_id, time_id)
);
```

**Avantages** :
- Séparation faits/dimensions → jointures efficaces
- Denormalisation mineure (coordonnées en dim_city) → requêtes géographiques rapides
- Extensibilité : ajouter des attributs temps (trimestre, season) sans re-modéliser
- Historique complet : chaque heure est une ligne, pas de mises à jour en place

---

## Flux de Données et Étapes du Pipeline

### Étape 1 : Collecte (collect.py)

**Fréquence** : Hourly (via GitHub Actions cron)

**Entée** : Rien
**Sortie** : `raw/` (fichiers JSON)

**Processus** :
1. Boucle sur 5 villes : Antananarivo, Paris, Nairobi, New York, Tokyo
2. Appel API `GET /data/2.5/air_pollution?lat=x&lon=y&appid=KEY`
3. **Retry** : en cas d'erreur réseau ou HTTP 5xx, retry jusqu'à 3 fois avec délai de 5s
4. Ajoute métadonnées (ville, pays, lat, lon, `collected_at` = timestamp UTC actuel)
5. Sauvegarde dans `raw/{ville}_{YYYYMMDDTHHMMSSZ}.json` (jamais modifié après)
6. Logs détaillés (OK/FAIL pour chaque ville)

**Fiabilité** :
- Timeout 15s par requête (API timeout standard)
- Retry non-idempotent : en cas d'erreur, on relance dans l'heure suivante
- Rate limit (50 calls/min sur OpenWeather gratuit) : géré implicitement (5 villes × 1 appel/heure = 5 calls/heure)

---

### Étape 2 : Backfill Historique (backfill.py)

**Fréquence** : Daily (1x/jour, au premier appel du jour)

**Entrée** : Rien
**Sortie** : `raw/` (fichiers JSON historiques)

**Processus** :
1. Vérifie si le backfill a déjà roulé aujourd'hui (via `last_backfill_date.txt`)
2. Si oui → skip
3. Si non :
   - Récupère les 3 derniers mois d'historique (période configurable)
   - Pour chaque heure en arrière, appelle l'API forecast/history de OpenWeather
   - Sauvegarde les résultats dans `raw/`
   - Écrit la date du jour dans `last_backfill_date.txt` (dédoublonnage du backfill)
   - Git commit si nouveau backfill

**Note** : Cette étape est optionnelle si vous avez accès à des données historiques complètes. Elle permet de combler les trous initiaux lors du lancement du projet.

---

### Étape 3 : Nettoyage et Normalisation (clean.py)

**Fréquence** : À chaque exécution du pipeline

**Entrée** : `raw/` (tous les fichiers JSON)
**Sortie** : `clean/air_quality_clean.csv`

**Processus** :
1. **Lecture** : Boucle sur tous les fichiers JSON de `raw/`
   - Ignore les fichiers JSON invalides (logs de debug)
   - Ignore les fichiers sans `_meta` ou `list` vide
2. **Extraction** : Pour chaque mesure, extrait :
   - Métadonnées : ville, pays, lat, lon
   - Composants : CO, NO, NO₂, O₃, SO₂, PM2.5, PM10, NH₃
   - AQI (indice OpenWeather, 1–5)
   - Timestamp UTC
   - Colonnes calculées : date, heure, jour_semaine, is_weekend
3. **Dédoublonnage** : Une seule ligne par (ville, heure)
   - Clé de dédup : `(ville_slug, unix_timestamp)`
   - En cas de doublon (collect.py + backfill.py couvrant la même heure), garde la mesure la plus récemment collectée (max `collected_at`)
   - Logs : nombre de doublons supprimés
4. **Tri** : Ordre final : ville (alphabétique), puis timestamp_utc (croissant)
5. **Écriture** : Écrase le fichier CSV précédent avec la version propre

**Exemple de dédup** :
```
antananarivo 2026-04-26 05:00:00  [collected at 05:15:00] ← Doublon
antananarivo 2026-04-26 05:00:00  [collected at 05:20:00] ← Gardé (plus récent)
→ Une seule ligne en sortie
```

---

### Étape 4 : Validation (validate_clean.py)

**Fréquence** : À chaque exécution du pipeline (AVANT le load)

**Entrée** : `clean/air_quality_clean.csv`
**Sortie** : Rapport de validation (stdout/stderr)

**Processus bloquant** (exit code 1 si un seul échoue) :
1. **Existence** : Fichier présent et non vide
2. **Schéma** : Colonnes exactes (ordre et names), pas plus, pas moins
3. **Pas de doublons** : Clé `(ville, timestamp_utc)` unique
4. **Tri** : Lignes triées par ville, puis timestamp_utc croissant
5. **Minimum 5 villes** : Validation du contrat projet
6. **Types et plages** :
   - Latitude in `[-90, 90]`, Longitude in `[-180, 180]`
   - Heure in `[0, 23]`
   - is_weekend in `{True, False}`
   - AQI in `[1, 5]` ou vide
   - Polluants `>= 0` ou vide
   - Timestamp parseable en ISO 8601 UTC

**Processus non-bloquant** (avertissements seulement) :
1. **Valeurs manquantes** : Compte par colonne
2. **Trous horaires** : Par ville, heures attendues vs présentes
   - Ex : "Antananarivo : 50h manquantes sur les 72h attendues pour ce range"

**Exemple de rapport** :
```
Validation de clean/air_quality_clean.csv
✓ Fichier trouvé, 42083 lignes
✓ Schéma correct : 18 colonnes attendues, 18 trouvées
✓ Pas de doublons : 42083 lignes uniques
✓ Tri OK : ville + timestamp_utc croissant
✓ 5 villes minimum : trouvées 5 villes

⚠ Valeurs manquantes :
  - nh3: 250 (0.6%)
  - co: 12 (0.03%)
⚠ Trous horaires :
  - Antananarivo : 22h manquantes (2026-04-26 à 2026-04-27)
  - Tokyo : 5h manquantes

Validation RÉUSSIE.
```

---

### Étape 5 : Chargement en Warehouse (load_warehouse.py)

**Fréquence** : À chaque exécution du pipeline (APRÈS validation)

**Entrée** : `clean/air_quality_clean.csv`
**Sortie** : Données insérées/mises à jour dans PostgreSQL

**Processus** :
1. **Connexion** : Établit une connexion SSL à PostgreSQL (via `psycopg2`)
2. **Dimensions – Villes** :
   - Pour chaque ville unique du CSV, insère dans `dim_city` (si N'EXISTE PAS)
   - Query : `INSERT … ON CONFLICT (city_name) DO NOTHING`
3. **Dimensions – Temps** :
   - Pour chaque timestamp unique du CSV, insère dans `dim_time`
   - Query : `INSERT … ON CONFLICT (timestamp_hour) DO UPDATE …`
4. **Faits – AQI** :
   - Charge `fact_air_quality` en batch (toutes les lignes à la fois)
   - Récupère les city_id et time_id via lookups
   - Query : `INSERT INTO fact_air_quality (city_id, time_id, aqi, co, …) VALUES (?, ?, …)`
   - Contrainte unique `(city_id, time_id)` prévient les doublons
5. **Commit** : Validation transactionnelle, rollback en cas d'erreur

**Performance** :
- ~42,000 lignes insérées en < 10 secondes (batch insert)
- Mises à jour incrementales : seules les nouvelles heures sont chargées (temps croissant)

---

## Résilience et Monitoring

### Gestion des Erreurs

| Composant | Scénario d'erreur | Récupération |
|---|---|---|
| **collect.py** | API down, timeout, 429 (rate limit) | Retry up to 3 times + 5s delay |
| **collect.py** | Réseau instable | Timeout 15s, continue w/ autres villes |
| **clean.py** | Fichier JSON corrompu | Ignore file, log IGNORE + continue |
| **validate_clean.py** | Schéma invalide | Exit code 1 (FAIL), bloque le load |
| **load_warehouse.py** | Connexion BD perdue | Retry psycopg2 (timeout 30s), sinon fail |

### Notifications

Chaque exécution du pipeline envoie un email Gmail (via GitHub Actions action `dawidd6/action-send-mail@v4`) :
- **Succès** : "Pipeline ETL Réussi"
- **Échec** : "ÉCHEC du Pipeline ETL"
  - Logs complets accessibles via URL GitHub Actions
  - Détails de l'erreur affichés dans l'email

### Audit et Observabilité

1. **Git History** : Chaque fichier `raw/` et le CSV `clean/` sont commités → traçabilité complète
2. **Logs** : Chaque exécution GitHub Actions génère des logs détaillés (retenus 90 jours)
3. **Database** : Toutes les mesures stockées avec horodatage → traçabilité des données chargées
4. **Monitoring** : À implémenter (optional) :
   - Dashboard Grafana queryant PostgreSQL pour visualiser AQI en temps réel
   - Alertes sur absence de données (ex : plus de 2h sans collecte)

---

## Sécurité et Compliance

### Gestion des Secrets

- **API Key OpenWeather** : Stockée dans GitHub Secrets (`OPENWEATHER_API_KEY`)
- **BD Credentials** : Stockés en GitHub Secrets/Variables
  - `DB_PASSWORD` = Secret
  - `DB_HOST`, `DB_USER`, `DB_NAME` = Variables (non-sensibles)
- **Email** : Optionnel, via Gmail App Password

### Recommandations

1. **Rotation des secrets** : Alterner la clé OpenWeather tous les 6 mois
2. **Least Privilege** : DB user ne peut que SELECT/INSERT sur warehouse (pas de DROP, DELETE)
3. **Versionning** : Toutes les modifications du code passer par des pull requests (reviews)
4. **HTTPS** : Connexion PostgreSQL SSL obligatoire
5. **Données** : Pas de données personnelles, uniquement agrégées publiques (AQI par ville)

---

## Opérations et Déploiement

### Première Exécution (Setup)

```bash
# 1. Configurer les secrets GitHub
# Settings → Secrets and variables
# OPENWEATHER_API_KEY = <your api key>
# DB_PASSWORD = <your postgres password>
# EMAIL_PASSWORD = <gmail app password>

# 2. Configurer les variables GitHub
# DB_HOST = <neon.tech host>
# DB_PORT = 5432
# DB_NAME = neondb
# DB_USER = neondb_user
# EMAIL_USERNAME = your-email@gmail.com
# EMAIL_TO = your-email@gmail.com

# 3. Initialiser la base de données
# Exécuter sql/create_schema.sql sur Neon

# 4. Lancer un premier backfill (optionnel)
python src/backfill.py --months 12

# 5. Déclencher le workflow manuellement
# GitHub Actions → Daily airflow → Run workflow → Dispatch
```

### Monitoring Continu

- Consulter la page GitHub Actions pour vérifier le statut (✅ / ❌)
- Consulter les logs de chaque étape (collect, clean, validate, load)
- Vérifier les emails d'alerte
- Query PostgreSQL pour valider les données chargées :
  ```sql
  SELECT city_name, COUNT(*) as nb_mesures, 
         MIN(DATE(timestamp_hour)) as date_min, 
         MAX(DATE(timestamp_hour)) as date_max
  FROM fact_air_quality f
  JOIN dim_city c ON f.city_id = c.city_id
  GROUP BY city_name
  ORDER BY city_name;
  ```

---

## Considérations Futures

1. **Scaling** : Si >> 5 villes, migrer `raw/` vers cloud storage (S3, GCS) pour réduire la taille du dépôt Git
2. **Optimisation** : Indexes PostgreSQL sur `(city_id, time_id)`, `timestamp_hour` pour accélérer les queries
3. **Audit externe** : Implement dbt (data build tool) pour tester les transformations
4. **ML** : Intégrer un modèle de prédiction d'AQI (ex : Prophet) pour forecasting
5. **API** : Exposer un endpoint REST (FastAPI) pour servir les données en temps réel

---

## Conclusion

Cette architecture combine **simplicité** (Git + CSV + crons), **fiabilité** (ETL déterministe, validation stricte), et **scalabilité** (cloud-native, serverless) pour créer un pipeline de qualité production capable de supporter une course continue du cours IA1.

**Stack résumé** :
- 🚀 Orchestrateur : GitHub Actions (serverless, gratuit)
- 📁 Stockage brut : Git (immuable, audit trail)
- 📊 Stockage propre : CSV (déterministe, contrat)
- 🗄️ Data warehouse : PostgreSQL/Neon (dimensionnel, SQL)
