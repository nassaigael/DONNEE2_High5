# DONNEE2_High5 – Pipeline ETL Continu d'Air Quality Index (AQI)

## Présentation du Projet

**DONNEE2_High5** est un pipeline ETL entièrement automatisé et serverless qui collecte, nettoie, valide et charge dans un data warehouse des données de **qualité de l'air (AQI)** en temps réel depuis l'API OpenWeather Air Pollution.

Le projet répond au cahier des charges du cours :
- ✅ Ingestion **horaire automatisée** pour 5 grandes villes mondiales
- ✅ Stockage brut **immuable** (source de vérité)
- ✅ Fichier propre **unique et déterministe** (reconstruction à chaque exécution)
- ✅ **Modélisation en étoile** (fact + 2 dimensions)
- ✅ **Exécution continue** post-rendu via GitHub Actions
- ✅ **Notifications** d'alerte par email

**Architecture** : Entièrement **serverless** via GitHub Actions + PostgreSQL cloud (Neon). Aucune infrastructure à maintenir.

**Data warehouse** : Accessible en permanence pour les requêtes du cours IA1.

---

## 🌍 Villes Surveillées

| # | Ville          | Pays            | Code | Latitude  | Longitude |
|---|---|---|---|---|---|
| 1 | Antananarivo   | Madagascar      | MG  | -18.8792  | 47.5079   |
| 2 | Paris          | France          | FR  | 48.8566   | 2.3522    |
| 3 | Nairobi        | Kenya           | KE  | -1.2921   | 36.8219   |
| 4 | New York       | États-Unis      | US  | 40.7128   | -74.0060  |
| 5 | Tokyo          | Japon           | JP  | 35.6762   | 139.6503  |

### Critères de Sélection
Les 5 villes ont été choisies pour représenter :
- **Diversité géographique** : Afrique, Europe, Asie, Amérique du Nord
- **Diversité climatique** : Tropical (Antananarivo), tempéré (Paris, Tokyo, New York), subtropical (Nairobi)
- **Pollution variée** : Mégapoles industrielles (Tokyo, New York, Paris) vs émergent (Antananarivo, Nairobi)
- **Relevance scientifique** : Cas d'étude pour modèles de qualité de l'air et impacts climatiques

---

## 📊 Format du Fichier `clean/air_quality_clean.csv`

Le fichier propre est l'artefact central du projet : une ligne par **ville et par heure**, sans doublons, trié par ville puis par date/heure croissante.

### Colonnes et Unités

| # | Colonne           | Type    | Unité       | Description | Exemple |
|---|---|---|---|---|---|
| 1 | `ville` | TEXT | — | Nom de la ville | "Antananarivo" |
| 2 | `pays` | TEXT | — | Code pays ISO 3166-1 (2 lettres) | "MG" |
| 3 | `latitude` | FLOAT | degrés | Latitude géographique | -18.8792 |
| 4 | `longitude` | FLOAT | degrés | Longitude géographique | 47.5079 |
| 5 | `timestamp_utc` | TEXT | ISO 8601 | Horodatage UTC (format : YYYY-MM-DDTHH:MM:SSZ) | "2026-07-29T16:00:00Z" |
| 6 | `date` | TEXT | YYYY-MM-DD | Date seule | "2026-07-29" |
| 7 | `heure` | INT | [0, 23] | Heure du jour (UTC) | 16 |
| 8 | `jour_semaine` | TEXT | — | Jour de la semaine en anglais | "Tuesday" |
| 9 | `is_weekend` | BOOL | — | True si samedi ou dimanche | False |
| 10 | `aqi` | INT | indice [1–5] | **Air Quality Index** (OpenWeather) : 1=Bon, 5=Très mauvais | 1 |
| 11 | `co` | FLOAT | μg/m³ | **Monoxyde de carbone** | 77.99 |
| 12 | `no` | FLOAT | μg/m³ | **Monoxyde d'azote** (NO) | 0.00 |
| 13 | `no2` | FLOAT | μg/m³ | **Dioxyde d'azote** (NO₂) | 0.35 |
| 14 | `o3` | FLOAT | μg/m³ | **Ozone** (O₃) | 55.01 |
| 15 | `so2` | FLOAT | μg/m³ | **Dioxyde de soufre** (SO₂) | 0.15 |
| 16 | `pm2_5` | FLOAT | μg/m³ | **Particules fines** (PM2.5) ≤ 2.5 micrometres | 1.33 |
| 17 | `pm10` | FLOAT | μg/m³ | **Particules** ≤ 10 micrometres | 2.20 |
| 18 | `nh3` | FLOAT | μg/m³ | **Ammoniac** (NH₃) | 0.34 |

### Conventions

- **Valeurs manquantes** : Cellules vides (pas de 0 inventé, pas de `NULL` textuel)
- **Séparateur** : Virgule `,` (pas de points-virgule)
- **Encodage** : UTF-8 sans BOM
- **Ordre des colonnes** : Strict (18 colonnes dans cet ordre, pas plus, pas moins)
- **Tri** : Alphabétique par ville, puis chronologique (timestamp_utc croissant)

---

## 📅 Période Couverte

| Aspect | Valeur |
|---|---|
| **Date de début** | 26 avril 2026 (04:00 UTC) |
| **Date de fin** | 24 juillet 2026 (17:00 UTC) — en cours |
| **Durée approximative** | 90 jours (~2160 heures) |
| **Fréquence de collecte** | Horaire (un appel API par ville chaque heure) |
| **Résolution temporelle** | Heure UTC (granularité minimale) |
| **Total attendu** | ~10,800 mesures (5 villes × 24 heures × 90 jours) |
| **Nombre de lignes dans clean/** | **42,083 lignes** (2026-07-29 dernier commit) |

### Évolution Temporelle

```
2026-04-26T04:00:00Z  ◄─ Lancement initial (collect.py)
    ↓
2026-04-26T23:00:00Z  ◄─ Fin du premier jour
    ↓
2026-04-27T00:00:00Z  ◄─ Backfill historique lancé (1x/jour)
    ↓
2026-07-24T17:00:00Z  ◄─ Dernier commit observé (data: automated collection)
    ↓
2026-07-28T23:59:59Z  ◄─ Aujourd'hui (en cours)
```

---

## 🕳️ Trous Connus et Données Manquantes

### Trous Horaires Identifiés

| Ville | Heures manquantes | Raison probable | Impact |
|---|---|---|---|
| **Antananarivo** | ~22h (26–27 avril) | Absence de données historiques dans les backfill initiaux | Minimal (début du projet) |
| **Paris** | ~8h (dispersées) | Indisponibilité temporaire API OpenWeather | < 1% |
| **Nairobi** | ~15h (dispersées) | Arrêt du pipeline ~ 1 jour | ~0.7% |
| **New York** | ~5h (dispersées) | Erreurs réseau ponctuelles | < 0.3% |
| **Tokyo** | ~5h (dispersées) | Erreurs réseau ponctuelles | < 0.3% |

### Valeurs Manquantes par Colonne

| Colonne | # Vides | % Vides | Raison |
|---|---|---|---|
| `nh3` | ~250 | 0.6% | Ammoniac non rapporté par l'API pour certaines heures |
| `co` | ~12 | 0.03% | Très rare, erreur API ponctuelles |
| Autres | 0 | 0% | Collecte complète |

### Recommandations pour l'Analyse

1. **Imutation** : Pour les analyses de tendance, imputer les valeurs manquantes (forward-fill, moyenne mobile)
2. **Filtrage** : Pour les analyses statiques, exclure les lignes avec colonnes manquantes critiques (optionnel)
3. **Validation** : Les trous ne remettent pas en cause la validité des données adjacentes

---

## 🗄️ Data Warehouse – Schéma et Connexion

### Architecture du Warehouse

Le warehouse suit un **schéma en étoile (Kimball)** avec une table de faits et deux dimensions :

![alt text](<Screenshot From 2026-07-27 23-47-44.png>)

```

### Table dim_city

Dimension des villes (petite table, ~5 lignes).

```sql
CREATE TABLE IF NOT EXISTS dim_city (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) UNIQUE NOT NULL,
    country VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);
```

**Exemples de lignes** :
![alt text](<Screenshot From 2026-07-28 00-06-51.png>)

### Table dim_time

Dimension temporelle (une ligne par heure unique collectée, ~10,800 lignes).

```sql
CREATE TABLE IF NOT EXISTS dim_time (
    time_id SERIAL PRIMARY KEY,
    timestamp_hour TIMESTAMP UNIQUE NOT NULL,
    date_value DATE,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    hour INTEGER,
    day_of_week VARCHAR(20),
    is_weekend BOOLEAN
);
```

**Exemples de lignes** :
![alt text](<Screenshot From 2026-07-28 00-07-47.png>)
```

### Table fact_air_quality

Table de faits (mesures de polluants et AQI, ~42,000 lignes).

```sql
CREATE TABLE IF NOT EXISTS fact_air_quality (
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

**Exemples de lignes** :
![alt text](<Screenshot From 2026-07-28 00-08-20.png>)

### Queries Utiles

#### Récupérer les dernières mesures pour chaque ville

```sql
SELECT 
    c.city_name,
    c.country,
    dt.timestamp_hour,
    faq.aqi,
    faq.pm2_5,
    faq.no2
FROM fact_air_quality faq
JOIN dim_city c ON faq.city_id = c.city_id
JOIN dim_time dt ON faq.time_id = dt.time_id
WHERE (faq.city_id, dt.timestamp_hour) IN (
    SELECT city_id, MAX(timestamp_hour) 
    FROM fact_air_quality 
    JOIN dim_time USING (time_id) 
    GROUP BY city_id
)
ORDER BY c.city_name;
```

#### AQI moyen par ville et mois

```sql
SELECT 
    c.city_name,
    dt.year,
    dt.month,
    ROUND(AVG(faq.aqi), 2) AS aqi_moyen,
    COUNT(*) AS nb_mesures
FROM fact_air_quality faq
JOIN dim_city c ON faq.city_id = c.city_id
JOIN dim_time dt ON faq.time_id = dt.time_id
GROUP BY c.city_name, dt.year, dt.month
ORDER BY c.city_name, dt.year, dt.month;
```

#### PM2.5 les plus élevées (top 10)

```sql
SELECT 
    c.city_name,
    dt.timestamp_hour,
    faq.pm2_5,
    faq.aqi
FROM fact_air_quality faq
JOIN dim_city c ON faq.city_id = c.city_id
JOIN dim_time dt ON faq.time_id = dt.time_id
WHERE faq.pm2_5 IS NOT NULL
ORDER BY faq.pm2_5 DESC
LIMIT 10;
```

---

## 🔐 Connexion à la Base de Données

### Informations de Connexion

| Paramètre | Valeur | Remarques |
|---|---|---|
| **Type de BD** | PostgreSQL | Version 14+ |
| **Hôte** | `<à configurer en GitHub Secrets>` | Neon.tech ou autre cloud |
| **Port** | `5432` | Port PostgreSQL standard |
| **Nom de base** | `neondb` | Ou autre selon config |
| **Utilisateur** | `<à configurer en GitHub Secrets>` | Compte avec droits INSERT/SELECT |
| **Mot de passe** | `<à configurer en GitHub Secrets>` | Stocké en GitHub Secrets |
| **SSL Mode** | `require` | Obligatoire pour la sécurité |
| **Timeout connexion** | 30s | Connectivité cloud |

### Configuration (pour le cours IA1)

Les credentials d'accès au warehouse seront **fournis via email** avant le début du cours.

**Variables GitHub Secrets à configurer** (voir `.github/workflows/daily_airflow.yml`) :
```yaml
OPENWEATHER_API_KEY  # Clé API OpenWeather (collect.py)
DB_PASSWORD          # Mot de passe PostgreSQL
EMAIL_PASSWORD       # Gmail app password (notifications)
```

**Variables GitHub (non-secrètes)** :
```yaml
DB_HOST              # Adresse serveur (ex: ep-calm-xyz.neon.tech)
DB_PORT              # 5432
DB_NAME              # neondb
DB_USER              # neondb_user
EMAIL_USERNAME       # Email Gmail sender
EMAIL_TO             # Email destinataire alerts
```

### Test de Connexion

```bash
# En local (après configurer .env)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM fact_air_quality;"

# Via Python
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT"),
    sslmode="require"
)
print("✓ Connexion OK")
conn.close()
```

---

## 🚀 Installation et Utilisation

### Prérequis

- Python 3.11+
- Git
- Accès à GitHub (secrets configurés)
- Compte Neon.tech (gratuit, pour le warehouse)

### Installation Locale (Dev)

```bash
# 1. Cloner le dépôt
git clone https://github.com/<votre-org>/DONNEE2_High5.git
cd DONNEE2_High5

# 2. Créer et activer un venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer .env (local dev)
cat > .env << EOF
OPENWEATHER_API_KEY=<your-key>
DB_HOST=<neon-host>
DB_PORT=5432
DB_NAME=neondb
DB_USER=<user>
DB_PASSWORD=<password>
EOF

# 5. Tester la collecte
python src/collect.py

# 6. Tester le nettoyage
python src/clean.py

# 7. Valider
python src/validate_clean.py

# 8. Charger
python src/load_warehouse.py
```

### Utilisation en Production (GitHub Actions)

Le pipeline s'exécute **automatiquement** :
- **Chaque heure** : `collect.py` + `clean.py` + `validate_clean.py` + `load_warehouse.py`
- **1x/jour** : `backfill.py` (remplissage historique)
- **Manuellement** : Via GitHub Actions "Run workflow"

Pour vérifier les logs : GitHub → Actions → Cliquer sur l'exécution récente.

---

## 📈 Statistiques du Projet

| Métrique | Valeur |
|---|---|
| **Nombre de villes** | 5 |
| **Nombre de colonnes clean/** | 18 |
| **Nombre de lignes clean/** | ~42,000 |
| **Nombre d'appels API collectés** | ~12,000 (24h × 5 villes × 90j + backfill) |
| **Uptime du pipeline** | ~98% (erreurs réseau ponctuelles) |
| **Taille du dépôt Git** | ~15 MB (fichiers JSON + CSV) |
| **Taille du warehouse** | ~5 MB (PostgreSQL) |
| **Coût estimé** | $0 (GitHub Actions gratuit + Neon free tier) |

---

## 📚 Ressources et Liens

- **Documentation OpenWeather Air Pollution API** : https://openweathermap.org/api/air-pollution
- **PostgreSQL Documentation** : https://www.postgresql.org/docs/
- **GitHub Actions Docs** : https://docs.github.com/actions
- **Neon Cloud** : https://neon.tech (free tier)
- **Architecture détaillée** : Voir [ARCHITECTURE.md](ARCHITECTURE.md)
