# 🌍 DONNEE2_High5 – Pipeline de Qualité de l’Air (AQI)

## Descriptions

**DONNEE2_High5** est un pipeline ETL **100 % automatisé et serverless** qui collecte, nettoie, valide et livre en continu des données de qualité de l’air (Air Quality Index – AQI) pour **5 grandes villes mondiales**.  
Il fournit un flux de données **fiable, traçable et prêt à l’emploi** pour des analyses statistiques, des tableaux de bord ou des modèles de machine learning (notamment pour le module IA1 qui consommera ces données en temps réel).

**Valeur ajoutée** :
- 🔁 **Historique complet** : 3 mois de données (et en croissance) disponibles pour des études rétrospectives.
- 🧹 **Qualité garantie** : dédoublonnage, validation stricte, valeurs manquantes conservées (pas d’imputation arbitraire).
- 🗄️ **Modélisation dimensionnelle** : schéma en étoile prêt pour des requêtes analytiques complexes.
- 📡 **Disponibilité permanente** : le pipeline tourne 24h/24, 7j/7, sans intervention.

## Aperçu du pipeline

Le flux de données s’articule en quatre étapes, orchestrées automatiquement toutes les heures via GitHub Actions :

![alt text](<Capture d’écran_2026-07-29_22-12-05.png>)

1. **Extraction** – `collect.py`  
   Interroge l’API OpenWeather Air Pollution pour chaque ville et enregistre la réponse brute (JSON) dans le dossier `raw/`. Un backfill quotidien (`backfill.py`) comble les trous historiques.

2. **Nettoyage** – `clean.py`  
   Lit tous les fichiers `raw/`, extrait les mesures, dédoublonne (une ligne par ville/heure), calcule des attributs temporels (date, jour, week-end) et produit un fichier CSV unique dans `clean/`.

3. **Validation** – `validate_clean.py`  
   Vérifie rigoureusement le schéma, l’absence de doublons, le tri, les plages de valeurs, etc. Si la validation échoue, le chargement en base est bloqué.

4. **Chargement** – `load_warehouse.py`  
   Alimente une base PostgreSQL (Neon) selon un schéma en étoile : dimensions `dim_city` et `dim_time`, table de faits `fact_air_quality`.

Chaque étape est traçable (logs dans GitHub Actions) et le pipeline envoie une notification par email en cas de succès ou d’échec.

![alt text](<Screenshot From 2026-07-27 23-46-20.png>)

---

## 🏙️ Villes surveillées

Cinq villes sélectionnées pour leur diversité géographique, climatique et de niveau de pollution.

![alt text](<Screenshot From 2026-07-28 00-06-51.png>)

---

## 📄 Colonnes et unités – `clean/air_quality_clean.csv`

Le fichier final est trié par ville, puis par `timestamp_utc` croissant.  
Chaque ligne représente une mesure horaire unique.

| Colonne | Type | Unité | Description |
|---------|------|-------|-------------|
| `ville` | TEXT | — | Nom de la ville |
| `pays` | TEXT | — | Code ISO 3166‑1 (2 lettres) |
| `latitude` | FLOAT | degrés | Latitude géographique |
| `longitude` | FLOAT | degrés | Longitude géographique |
| `timestamp_utc` | TEXT | ISO 8601 | Horodatage UTC (ex: `2026-07-29T16:00:00Z`) |
| `date` | TEXT | YYYY-MM-DD | Date seule |
| `heure` | INT | [0,23] | Heure du jour (UTC) |
| `jour_semaine` | TEXT | — | Jour en anglais (`Monday`, `Tuesday`, …) |
| `is_weekend` | BOOL | — | `True` si samedi ou dimanche |
| `aqi` | INT | indice 1–5 | Air Quality Index (1 = bon, 5 = très mauvais) |
| `co` | FLOAT | μg/m³ | Monoxyde de carbone |
| `no` | FLOAT | μg/m³ | Monoxyde d’azote |
| `no2` | FLOAT | μg/m³ | Dioxyde d’azote |
| `o3` | FLOAT | μg/m³ | Ozone |
| `so2` | FLOAT | μg/m³ | Dioxyde de soufre |
| `pm2_5` | FLOAT | μg/m³ | Particules fines ≤ 2.5 μm |
| `pm10` | FLOAT | μg/m³ | Particules ≤ 10 μm |
| `nh3` | FLOAT | μg/m³ | Ammoniac |

**Règles** :
- Valeurs manquantes → cellule vide (pas de `0` ni de `NULL` textuel).
- Ordre des colonnes strict, tel qu’indiqué ci-dessus.

## Schéma du warehouse

Le warehouse est hébergé sur **PostgreSQL (Neon)**, un service serverless avec pooling de connexions et scaling automatique.

![alt text](<Capture d’écran_2026-07-30_07-11-17.png>)
![alt text](<Capture d’écran_2026-07-30_07-11-25.png>)

## Période couverte

- **Début** : 26 avril 2026, 04:00 UTC  
- **Fin** : collecte en cours (dernière mise à jour : 29 juillet 2026, 22:00 UTC)  
- **Fréquence** : une mesure par heure et par ville (soit 5 × 24 = 120 mesures par jour)  
- **Volume actuel** : ~11 000 lignes dans la table `fact_air_quality` (écarts expliqués ci-dessous)

---

## Trous connus et données manquantes

| Ville | Heures manquantes | Période concernée | Cause |
|-------|-------------------|-------------------|-------|
| Antananarivo | ~22 h | 26–27 avril 2026 | Démarrage progressif du backfill |
| Paris | ~8 h | Dispersées | Indisponibilité temporaire de l’API |
| Nairobi | ~15 h | Dispersées | Arrêt du pipeline (~1 jour) |
| New York | ~5 h | Dispersées | Erreurs réseau ponctuelles |
| Tokyo | ~5 h | Dispersées | Erreurs réseau ponctuelles |

**Colonnes avec valeurs manquantes** :
- `nh3` : manquant dans ~0,6 % des lignes
- `co` : manquant dans ~0,03 % des lignes  
Les autres colonnes sont complètes. Ces lacunes sont conservées (cellules vides) pour ne pas fausser les statistiques.

---

## Connexion à la base de données

Les identifiants sont stockés de manière sécurisée dans **GitHub Secrets** et ne sont pas exposés dans le code.  
Pour accéder au warehouse, utilisez les paramètres suivants (à remplacer par vos valeurs secrètes) :

| Paramètre | Description | Où le trouver |
|-----------|-------------|---------------|
| `DB_HOST` | Hôte PostgreSQL (ex: `ep-noisy-pond-zaviipgj-pooler.c-2.eu-west-2.aws.neon.tech`) | GitHub Variable |
| `DB_PORT` | Port (par défaut `5432`) | Fixe |
| `DB_NAME` | Nom de la base (ex: `neondb`) | GitHub Variable |
| `DB_USER` | Utilisateur | GitHub Variable |
| `DB_PASSWORD` | Mot de passe | GitHub Secret |
| `SSL Mode` | `require` | Obligatoire |

**Exemple de connexion Python** :
```python
import os, psycopg2
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    sslmode="require"
)
```

---

## 🛠️ Installation et configuration

### 1. Cloner le dépôt
```bash
git clone https://github.com/nyyanja/DONNEE2_High5.git
cd DONNEE2_High5
```

### 2. Créer un environnement virtuel Python
```bash
python -m venv venv
source venv/bin/activate          # Linux/macOS
# ou
venv\Scripts\activate             # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d’environnement
Copier le fichier `.env.example` en `.env` et renseigner vos clés :
```bash
cp .env.example .env
```
Contenu type :
```ini
OPENWEATHER_API_KEY=votre_cle_api
DB_HOST=ep-noisy-pond-zaviipgj-pooler.c-2.eu-west-2.aws.neon.tech
DB_PORT=5432
DB_NAME=neondb
DB_USER=neondb_user
DB_PASSWORD=votre_mot_de_passe
```
> **Note** : Ne jamais committer le fichier `.env` (déjà dans `.gitignore`).

### 5. Initialiser le warehouse (créer les tables)
```bash
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f sql/create_schema.sql
```

---

## 🚀 Utilisation locale

### Collecte manuelle d’une heure
```bash
python src/collect.py
```
Les fichiers JSON apparaîtront dans `raw/`.

### Backfill historique (3 mois minimum)
```bash
python src/backfill.py --months 3
```

### Nettoyage et génération du CSV
```bash
python src/clean.py
```
Le fichier `clean/air_quality_clean.csv` est créé (écrasé à chaque exécution).

### Validation du CSV
```bash
python src/validate_clean.py
```
Si la validation échoue, le code de sortie est `1` et le chargement ne doit pas être effectué.

### Chargement dans le warehouse
```bash
python src/load_warehouse.py
```
Insère les données dans les tables `dim_city`, `dim_time` et `fact_air_quality`.

### Exécuter tout le pipeline en local
```bash
bash scripts/run_pipeline_local.sh   # (si vous créez ce script)
```
Ou manuellement les étapes ci-dessus.

---

## Explorer les données

### Requêtes SQL utiles (exécutez-les via `psql` ou un client SQL)

**Nombre total de mesures par ville :**
```sql
SELECT c.city_name, COUNT(*) AS nb_mesures
FROM fact_air_quality f
JOIN dim_city c ON f.city_id = c.city_id
GROUP BY c.city_name
ORDER BY nb_mesures DESC;
```

**AQI moyen journalier (sur la dernière semaine) :**
```sql
SELECT c.city_name, dt.date_value, ROUND(AVG(f.aqi), 2) AS aqi_moyen
FROM fact_air_quality f
JOIN dim_city c ON f.city_id = c.city_id
JOIN dim_time dt ON f.time_id = dt.time_id
WHERE dt.date_value >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY c.city_name, dt.date_value
ORDER BY dt.date_value DESC, c.city_name;
```

**Top 5 des heures les plus polluées (PM2.5) :**
```sql
SELECT c.city_name, dt.timestamp_hour, f.pm2_5
FROM fact_air_quality f
JOIN dim_city c ON f.city_id = c.city_id
JOIN dim_time dt ON f.time_id = dt.time_id
WHERE f.pm2_5 IS NOT NULL
ORDER BY f.pm2_5 DESC
LIMIT 5;
```

---

## Monitoring du pipeline en production

Le pipeline tourne sur **GitHub Actions** :
- Accéder à l’onglet **Actions** du dépôt.
- Voir le workflow `daily_airflow.yml` pour l’exécution horaire.
- Les logs de chaque job sont consultables.
- En cas d’échec, une notification email est envoyée (si configurée).

![alt text](<Screenshot From 2026-07-27 23-46-20.png>)

---

Voici la section **Ressources** enrichie avec le rôle de l’IA dans le projet :

---

## 📚 Ressources

### Documentation des outils utilisés
- [OpenWeather Air Pollution API](https://openweathermap.org/api/air-pollution) – documentation de l’API source.
- [PostgreSQL](https://www.postgresql.org/docs/) – base de données relationnelle.
- [GitHub Actions](https://docs.github.com/en/actions) – orchestration et CI/CD.
- [Python psycopg2](https://www.psycopg.org/docs/) – connecteur PostgreSQL.

### Tutoriels recommandés
- [Créer un pipeline ETL avec Python et PostgreSQL](https://realpython.com/python-etl/)
- [Introduction à la modélisation en étoile](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/star-schema/)
- [GitHub Actions pour débutants](https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions)

### Articles liés au projet
- [Pourquoi surveiller la qualité de l’air ?](https://www.who.int/health-topics/air-pollution)
- [Indice AQI – signification des niveaux](https://www.airnow.gov/aqi/aqi-basics/)

---

### Rôle de l’IA dans ce projet

L’intelligence artificielle (via des assistants comme GitHub Copilot ou des modèles de langage) a été utilisée comme **outil d’aide à la conception et au développement**, sans se substituer à l’expertise des membres de l’équipe. Voici ses principales contributions :

- **Documentation** : génération de premières versions de la documentation technique (README, ARCHITECTURE.md), rédaction des descriptions de colonnes et des schémas, structuration des fichiers markdown.
- **Explication des concepts** : clarification des notions de modélisation dimensionnelle (étoile vs flocon), des mécanismes d’ETL, des bonnes pratiques de validation de données, et des particularités de l’API OpenWeather.
- **Revue de code** : suggestion d’améliorations de syntaxe, de performance et de lisibilité sur les scripts Python (gestion des retries, normalisation des coordonnées, déduplication, etc.).
- **Débogage** : identification rapide d’erreurs courantes (ex : URL incorrecte, parsing JSON, problèmes de type, gestion des valeurs manquantes) et propositions de correctifs, facilitant l’itération et réduisant le temps de résolution.

L’IA a agi comme un **assistant augmentant la productivité** de l’équipe, mais chaque décision finale (choix technologiques, architecture, validation des données) a été prise et validée par les membres humains du projet.

