# Clone neuf : le README suivi à la lettre (tâche 6.2)

**Résultat** : le README suffit. Sur un clone neuf, sans `mlflow.db`, sans données et sans le remote DVC, toutes ses commandes passent, de l'installation à la démo comprise, avec les sorties annoncées : mêmes données à l'octet près, mêmes MAE, API, surveillance, rejeu, alerte, réentraînement, promotion et rollback (8,2 s). Le test n'a trouvé aucun défaut dans le README ni dans le code. Il relève un écart d'environnement (le port 5001 était occupé sur la machine partagée, E1) et une phrase fausse dans `docs/data.md` (D1), corrigée par la pull request de cette tâche.

## Conditions du test

| | |
| --- | --- |
| Date | Du 22/11/2026 à 23:31 au 23/11/2026 à 11:59, heure de Paris. La nuit a interrompu le test entre deux étapes ; les durées données sont celles de chaque commande. |
| Machine | Mac Apple M2 (arm64), macOS 26.5. C'est le Mac de la copie de travail de l'équipe, mais le test part d'un dossier vide et n'en copie aucun fichier. Le cours fait le même test avec un second dossier (L1 README §5 : `git clone . ../teammate`). |
| Outils | uv 0.13.6, Git 2.50.1, Docker 29.1.3 (Docker Desktop, déjà lancé) avec Docker Compose v2.40.3 ; Python 3.12.15, choisi par uv. |
| Qui | Matis (IA, Claude Code), tâche 6.2. Le README vient de la tâche 6.1 (Jérémy). |
| Dépôt | `git clone https://github.com/matisdy/mlops-taxi.git` dans le dossier vide `test-clone-neuf/`, au commit `6885027` (`main` du 22/11 à 23:03). |
| Données | Ni `mlflow.db` ni données. `../dvc-store` n'existe pas à côté de ce clone : c'est donc le chemin du README pour une machine sans le remote DVC (`download.py`, puis `dvc add`). |
| Copies | Aucune. Seul le cache de uv a servi, d'où l'installation en moins d'une seconde. |

## Commandes, durées et sorties

Chaque commande est copiée telle qu'elle a été lancée, depuis la racine du clone. ✅ : sortie conforme au README ; E1 : voir les écarts.

### Installation

| N° | Commande | Durée | Sortie attendue (README) | Sortie obtenue | |
| --- | --- | --- | --- | --- | --- |
| 1 | `git clone https://github.com/matisdy/mlops-taxi.git && cd mlops-taxi` | 2 s | — | `Cloning into 'mlops-taxi'...` ; `HEAD` = `6885027` | ✅ |
| 2 | `uv sync --locked` | 0,8 s | l'environnement `.venv` est créé, sans erreur | `Creating virtual environment at: .venv`, `Resolved 167 packages`, `Installed 163 packages in 740ms` | ✅ |
| 3 | `uv run python download.py` | 15,7 s | `data/raw/yellow_tripdata_2020-01.parquet: 93.6 MB, downloaded` (puis 92.1 MB et 44.4 MB) | les trois lignes : `93.6 MB`, `92.1 MB`, `44.4 MB`, chacune `downloaded` (93 562 858, 92 134 881 et 44 442 590 octets, comme `docs/data.md`) | ✅ |
| 4 | `uv run dvc add data/raw` | 3,2 s | remplit le cache DVC ; ne pas suivre le conseil « git add data/raw.dvc » | le conseil `git add data/raw.dvc` s'affiche ; il n'a pas été suivi | ✅ |
| 5 | `git status --short data/raw.dvc` | 0,1 s | rien | rien | ✅ |
| 6 | `uv run python build_dataset.py` | 16,0 s | `data/features.parquet: 40320 rows`, puis les colonnes, les lignes par split et `data/zones.json` | `data/features.parquet: 40320 rows` ; train 19200, replay 14880, valid 6240 ; `data/zones.json` : 20 zones | ✅ |
| 7 | `uv run pytest -q` | 53 s | `24 passed` | `24 passed, 4 warnings in 23.41s` | ✅ |

### Lancement en quatre terminaux

| N° | Terminal | Commande | Durée | Sortie attendue (README) | Sortie obtenue | |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | 1 · MLflow | `uv run mlflow ui --port 5011 --backend-store-uri sqlite:///mlflow.db --artifacts-destination ./mlartifacts` | prêt en 7 s | l'interface répond sur http://127.0.0.1:5001 | `Uvicorn running on http://127.0.0.1:5011` ; `/health` répond `OK` | E1 |
| 9 | 4 · entraînement | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python train.py` | 11,6 s | `mae_valid 28.4983 \| mae_baseline_valid 47.8886` puis `run_id = <RUN_ID>` | `mae_valid 28.4983 \| mae_baseline_valid 47.8886` puis `run_id = f3d9f12a08ec4e69a958afb0c6bb4dbb` | ✅ E1 |
| 10 | 4 · Registry | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python register.py f3d9f12a08ec4e69a958afb0c6bb4dbb` | 9,3 s | `taxi-demand v1 is now @production` | `taxi-demand v1 is now @production` | ✅ E1 |
| 11 | 2 · API | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 OMP_NUM_THREADS=1 uv run uvicorn app.main:app --port 8000` | prête au premier appel | `loaded models:/taxi-demand@production (version 1)` | `loaded models:/taxi-demand@production (version 1)` | ✅ E1 |
| 12 | 3 · surveillance | `cd monitoring && docker compose up -d && cd ..` | 2,1 s | Prometheus (cible `taxi-api` à `UP`), Alertmanager, Grafana sans identifiant | trois conteneurs `Started` ; cible `taxi-api` `up` (`http://host.docker.internal:8000/metrics/`) ; règles `ApiDown` et `InputDrift` chargées ; Alertmanager répond 200 ; Grafana 12.1.0 montre le tableau de bord « Taxi API » sans identifiant | ✅ |

À la ligne 12, Docker a écrit `Recreate` au lieu de `Create`. Le projet compose `monitoring` tournait déjà depuis la copie de l'équipe, qui porte le même nom de dossier : Compose a recréé les trois conteneurs avec les fichiers du clone. Sur une machine neuve, il les crée.

### Vérifier l'API

| N° | Commande | Sortie attendue (README) | Sortie obtenue | |
| --- | --- | --- | --- | --- |
| 13 | `curl -s localhost:8000/health` | `{"status":"ok","model_version":"1"}` | `{"status":"ok","model_version":"1"}` | ✅ |
| 14 | `curl -s -X POST localhost:8000/v1/predict -H 'Content-Type: application/json' -d '{"zone": 237, "ts": "2020-03-02T08:00:00", "lag_1h": 112.0, "lag_24h": 98.0, "lag_168h": 120.0}'` | `{"zone":237,"ts":"2020-03-02T08:00:00","prediction":…,"model_version":"1"}` | `{"zone":237,"ts":"2020-03-02T08:00:00","prediction":190.20255820567724,"model_version":"1"}` | ✅ |

### Démo

| N° | Étape | Commande | Durée | Sortie attendue (README) | Sortie obtenue | |
| --- | --- | --- | --- | --- | --- | --- |
| 15 | 0. Avant | `uv run python replay.py --start 2020-02-17 --end 2020-02-29` | 33,0 s | `done: ok …, errors 0, rows appended to data/truth.csv` ; aucune alerte | `done: ok 6240, errors 0, rows appended to data/truth.csv` ; PSI final 0,034 (`lag_1h`) et 0,092 (`lag_24h`) ; aucune alerte en firing, rien dans Alertmanager (voir O1) | ✅ |
| 16 | 1. Une requête | les deux `curl` des lignes 13 et 14 | — | `/health` puis la prévision, en v1 | lancées 14 s avant l'étape 0, avec le même modèle v1 | ✅ |
| 17 | 2. La dérive | `uv run python replay.py --start 2020-03-01 --end 2020-03-31` | 76,6 s | dans Grafana, le PSI dépasse 0,25 ; `InputDrift` passe de pending à firing dans Prometheus, puis dans Alertmanager | `done: ok 14880, errors 0, rows appended to data/truth.csv`. Dans Grafana (requête du panneau PSI), `lag_1h` dépasse 0,25 à 11:48:40 (35 s après le début) et monte jusqu'à 7,88 ; `lag_24h` monte jusqu'à 8,31. `InputDrift` passe en pending dans Prometheus à +30 s, puis sans interruption à partir de +40 s ; elle passe en firing et arrive dans Alertmanager à +100,7 s | ✅ |
| 18 | 3. Réentraînement | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python check_and_retrain.py` | 14,4 s | `{"action": "retrain", …}` puis `taxi-demand v2 is now @staging` | `{"now": "2020-03-31T23:00:00", "psi": {"lag_1h": 7.7033, "lag_24h": 7.6443}, "days": 7, "action": "retrain", "mae_production": 21.6775, "mae_candidate": 3.9738, "run_id": "4c925bb2974f430fb62fce5da5c3c1ab", "version": "2"}` puis `taxi-demand v2 is now @staging (MAE 3.9738 vs 21.6775 in production)` | ✅ E1 |
| 19 | 4. Promotion | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python promote.py` | 3,3 s | `taxi-demand v2 is now @production (was v1)`, puis `Relancer l'API` | `taxi-demand v2 is now @production (was v1)` puis `Relancer l'API` | ✅ E1 |
| 20 | 4. Relance | terminal 2 : Ctrl+C, puis la commande de la ligne 11 ; `curl -s localhost:8000/health` | — | `/health` affiche v2 | `loaded models:/taxi-demand@production (version 2)` ; `{"status":"ok","model_version":"2"}` | ✅ |
| 21 | 5. Rollback | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python rollback.py`, puis le terminal 2 relancé comme à la ligne 20 | 11,7 s | `taxi-demand v1 is now @production`, puis `Relancer l'API`, puis `/health shows v1 after … s` | `taxi-demand v1 is now @production`, `Relancer l'API`, `/health shows v1 after 8.2 s` ; l'API relancée affiche `loaded models:/taxi-demand@production (version 1)` | ✅ E1 |

Le Ctrl+C du terminal 2 a été donné par un signal SIGINT au processus `uvicorn`. Au rollback, ce signal et la relance partaient d'un petit script, dès que `rollback.py` affichait « Relancer l'API » : les 8,2 s ne comptent donc pas de temps de réaction humain.

État à la fin de la démo :
- Registry du clone : `taxi-demand` v1 en `@production`, v2 en `@staging`.
- `data/decisions.jsonl` : une ligne, `"action": "retrain"`.
- `data/promotions.jsonl` : `{"ts": "2026-11-23T10:52:26Z", "from": "1", "to": "2"}`.
- `data/truth.csv` : 21 120 lignes, février puis mars.

## Comparaison avec le cours

Le cours tient un clone neuf pour reproduit quand le code, l'environnement et les données sont identiques et que les métriques sont égales (L1 README §5 ; WRAP p.8 : métriques égales à 1e-6 près).

| Ce qui est comparé | Clone neuf | Référence | |
| --- | --- | --- | --- |
| Code | tag `git_commit` du run v1 : `688502718d5adc48c9f2dd1d8b4ec067d947e55d` ; `git_dirty` : `False` | `main` au moment du clone | ✅ |
| Environnement | `uv sync --locked` : les 163 paquets de `uv.lock` | `uv.lock` commité | ✅ |
| Données brutes | `data/raw.dvc` inchangé après `dvc add` : `md5: 41afee30aa691264fa8da29312afb9db.dir`, 3 fichiers, 230 140 329 octets | pointeur commité | ✅ |
| Données dérivées | md5 calculé de `data/features.parquet` : `335cc10a28f85363c7bac4a41a0c58d4` ; de `data/zones.json` : `ac4da25717d2280ae39a13bd9378ce55` | `data/features.parquet.dvc` et `data/zones.json.dvc` : les mêmes empreintes | ✅ |
| Métriques | `mae_valid` 28.49834215371863 ; `mae_baseline_valid` 47.888621794871796 | README et `docs/evidence/t7.3_mesures.txt` : 28.4983 et 47.8886 | ✅ égales aux 4 décimales publiées |

Les deux références de métriques s'arrêtent à 4 décimales ; les valeurs complètes ci-dessus permettront une comparaison à 1e-6 près au prochain clone.

## Écarts et erreurs

| N° | Nature | Constat | Correction |
| --- | --- | --- | --- |
| E1 | Environnement : machine partagée | Le port 5001 était pris par le serveur MLflow officiel de l'équipe, lancé depuis sa copie de travail, et le pilote a décidé de ne pas l'arrêter. Le MLflow du clone a donc tourné sur le port 5011, avec la commande du README à part le port. `MLFLOW_TRACKING_URI=http://127.0.0.1:5011` a été placé devant chaque commande qui parle à MLflow : `train.py`, `register.py`, l'API, `check_and_retrain.py`, `promote.py` et `rollback.py`. Ces scripts, comme `evaluate.py`, lisent la variable avec `os.getenv` (Spécifications §1) ; 5001 n'est que la valeur par défaut, rien n'est codé en dur. Aucun fichier ne charge `.env` : la variable passe par l'environnement du terminal. | Aucune : ce n'est pas un défaut du README. Sur une machine où le port 5001 est libre, ses commandes s'appliquent telles quelles. |
| D1 | Documentation : `docs/data.md`, cité par le README | La phrase « `uv run dvc status` répond ensuite « Data and pipelines are up to date. » » est fausse sur un clone neuf. `dvc status` signale aussi `data/features.parquet` et `data/zones.json` comme « not in cache », avant comme après `build_dataset.py`. `uv run dvc status data/raw.dvc` répond bien « Data and pipelines are up to date. ». | Phrase corrigée dans la pull request de la tâche 6.2. Ni le README ni le code ne changent. |

## Observations, sans écart au README

- **O1, début du rejeu de février.** Au départ, la fenêtre du PSI ne contient que les premières prédictions. `lag_24h` a valu 0,369 sur un relevé (11:47:20), et `InputDrift` (`lag_24h`) est passée une fois en pending (11:47:25). Il n'y a eu ni firing ni alerte dans Alertmanager, et le PSI est ensuite resté sous 0,25 (fin de février : 0,034 et 0,092). « Aucune alerte » reste donc vrai. Dans Grafana, sur les 15 dernières minutes, ce pic apparaît si février a été rejoué moins de 15 minutes avant la démo.
- **O2, délai de l'alerte.** `InputDrift` est en pending sans interruption à partir de +40 s, après un premier relevé pending de `lag_24h` à +30 s. Elle passe en firing à +100,7 s (1 min 41 s) : `lag_1h` à 11:49:45, `lag_24h` à 11:49:50, une minute après le début de leur pending continu (`for: 1m`). C'est la fourchette calculée dans `docs/demo_script.md` §3 (1 min 35 à 1 min 45). Le rejeu de mars se termine avant le firing (76,6 s), et la jauge garde sa dernière valeur (7,88), comme prévu.
- **O3, durée du rollback.** 8,2 s ici, avec une relance de l'API scriptée ; 22,4 s pendant l'incident, avec une relance à la main. Les deux restent sous les 300 s visées.
- **O4, version testée.** Pendant le test, `main` est passé de `6885027` à `68cc184` (PR #21, tâche 6.3 : captures renommées dans `docs/evidence/`, `docs/incident_report.md`, `docs/qa_prep.md`). Aucun fichier de code ne change, ni le README, ni `docs/data.md` : le résultat vaut aussi pour `68cc184`.

## Résultat final

- L'API, la surveillance et le rejeu fonctionnent en suivant le README, sans étape absente du README, à l'écart d'environnement E1 près.
- La démo passe en entier : v1 en production, alerte de dérive, v2 en `@staging`, v2 en `@production`, puis retour à la v1 en 8,2 s.
- Les données et les métriques du clone neuf sont identiques à celles du dépôt et du README.
- Seule correction : `docs/data.md` (D1).
