# Clone neuf : le README suivi à la lettre (tâche 6.2)

**Résultat** : le README suffit. Sur un clone neuf, sans `mlflow.db`, sans données et sans le remote DVC, toutes ses commandes passent, de l'installation à la démo comprise, avec les sorties annoncées. Les données sont identiques à l'octet près et les MAE égales aux 4 décimales publiées. L'API, la surveillance, le rejeu, l'alerte, le réentraînement, la promotion et le rollback (8,2 s) fonctionnent. Le test n'a trouvé aucun défaut dans le README ni dans le code. Il relève trois écarts dus au test lui-même : deux d'environnement, car la machine est partagée (E1 pour le port 5001, E2 pour la stack de l'équipe), et un d'ordre (E3). Il relève aussi une phrase fausse dans `docs/data.md` (D1), corrigée par la pull request de cette tâche.

## Conditions du test

| | |
| --- | --- |
| Date | Du 22/11/2026 à 23:31 au 23/11/2026 à 11:59, heure de Paris. Deux pauses ont eu lieu, sans effet sur le résultat : entre le lancement de MLflow (23:47) et `train.py` (02:16), puis entre `train.py` et `register.py` (11:45). Le serveur MLflow du clone est resté en marche pendant ces pauses. La colonne « Heure » des tableaux donne le début de chaque commande. |
| Machine | Mac Apple M2 (arm64), macOS 26.5. C'est le Mac de la copie de travail de l'équipe, mais le test part d'un dossier vide et n'en copie aucun fichier. Le cours fait le même test avec un second dossier, le « clone du coéquipier » (L1 README §5 : `git clone . ../teammate`). |
| Outils | uv 0.13.6, Git 2.50.1, Docker 29.1.3 (Docker Desktop, déjà lancé) avec Docker Compose v2.40.3-desktop.1. uv a pris le Python 3.12.15 de Homebrew, déjà installé : `Using CPython 3.12.15 interpreter at: /opt/homebrew/opt/python@3.12/bin/python3.12`. |
| Qui | Matis (IA, Claude Code), tâche 6.2. Le README vient de la tâche 6.1 (Jérémy). |
| Dépôt | `git clone https://github.com/matisdy/mlops-taxi.git` dans le dossier vide `test-clone-neuf/`. Le clone est au commit `6885027`, la fusion de la PR #20 du 22/11 à 14:34, qui était le `HEAD` de `main` au moment du clone (22/11 à 23:31). |
| Données | Ni `mlflow.db` ni données. `../dvc-store` n'existe pas à côté de ce clone : c'est donc le chemin du README pour une machine sans le remote DVC (`download.py`, puis `dvc add`). |
| Caches | Le cache de uv a fourni les paquets ; les images Docker étaient déjà sur la machine, aucune n'a été téléchargée. |
| Relevés | Les 16 commandes qui se terminent d'elles-mêmes (lignes 2 à 7, 9, 10, 12 à 15, 17 à 19 et le `rollback.py` de la ligne 21) ont été lancées telles quelles à travers un petit script de relevé. Il note l'heure de début, la durée et la sortie dans un fichier, sans changer le texte de la commande. Le clone, les deux serveurs (MLflow et API) et les relances de l'API ont été lancés directement, les serveurs en arrière-plan. |

## Ce que ce test ne couvre pas

Fait sur le Mac de l'équipe, le test ne vérifie pas ce qu'une autre machine aurait à faire en plus : l'installation de Python 3.12 par uv (README, « Prérequis »), le téléchargement des paquets et des trois images Docker, ni le passage sous Linux ou sous Windows. Les durées de `uv sync --locked` (0,8 s) et de `docker compose up -d` (2,1 s) ne valent donc pas pour une machine neuve.

## Commandes, durées et sorties

Chaque commande est copiée telle qu'elle a été lancée, depuis la racine du clone. ✅ signale une sortie conforme au README ; E1 à E3 renvoient aux écarts.

### Installation

| N° | Heure | Commande | Durée | Sortie attendue (README) | Sortie obtenue | |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 23:31 | `git clone https://github.com/matisdy/mlops-taxi.git`, puis `cd mlops-taxi` | 2 s | — | `Cloning into 'mlops-taxi'...` ; `HEAD` = `6885027` | ✅ |
| 2 | 23:32:38 | `uv sync --locked` | 0,8 s | l'environnement `.venv` est créé, sans erreur | `Creating virtual environment at: .venv`, `Resolved 167 packages in 7ms`, `Installed 163 packages in 740ms` | ✅ |
| 3 | 23:33:02 | `uv run python download.py` | 15,7 s | `data/raw/yellow_tripdata_2020-01.parquet: 93.6 MB, downloaded` (puis 92.1 MB et 44.4 MB) | les trois lignes : `93.6 MB`, `92.1 MB`, `44.4 MB`, chacune `downloaded`. Taille des fichiers : 93 562 858, 92 134 881 et 44 442 590 octets, comme dans `docs/data.md` | ✅ |
| 4 | 23:33:33 | `uv run dvc add data/raw` | 3,2 s | remplit le cache DVC ; ne pas suivre le conseil « git add data/raw.dvc » | le conseil `git add data/raw.dvc` s'affiche ; il n'a pas été suivi | ✅ |
| 5 | 23:33:36 | `git status --short data/raw.dvc` | 0,1 s | rien | rien | ✅ |
| 6 | 23:33:44 | `uv run python build_dataset.py` | 16,0 s | `data/features.parquet: 40320 rows`, puis les colonnes, les lignes par split et `data/zones.json` | `data/features.parquet: 40320 rows` ; train 19200, replay 14880, valid 6240 ; `data/zones.json` : 20 zones | ✅ |
| 7 | 23:34:18 | `uv run pytest -q` | 53 s | `24 passed` | `24 passed, 4 warnings in 23.41s` | ✅ |

À la ligne 1, le README enchaîne les deux commandes avec `&&` ; ici, `cd` a suivi la fin du clone. Les durées sont mesurées de l'extérieur, démarrage de `uv run` compris : pour la ligne 7, 53 s au total, dont 23,41 s selon pytest. Les 4 avertissements de pytest sont décrits en O5.

### Lancement en quatre terminaux

| N° | Heure | Terminal | Commande | Durée | Sortie attendue (README) | Sortie obtenue | |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 23:47:01 | 1 · MLflow | `uv run mlflow ui --port 5011 --backend-store-uri sqlite:///mlflow.db --artifacts-destination ./mlartifacts` | prêt en 7 s | l'interface répond sur http://127.0.0.1:5001 | `Uvicorn running on http://127.0.0.1:5011` (23:47:08) ; `/health` répond `OK` | E1 |
| 9 | 02:16:42 | 4 · entraînement | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python train.py` | 11,6 s | `mae_valid 28.4983 \| mae_baseline_valid 47.8886` puis `run_id = <RUN_ID>` | `mae_valid 28.4983 \| mae_baseline_valid 47.8886` puis `run_id = f3d9f12a08ec4e69a958afb0c6bb4dbb` | ✅ E1 |
| 10 | 11:45:06 | 4 · Registry | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python register.py f3d9f12a08ec4e69a958afb0c6bb4dbb` | 9,3 s | `taxi-demand v1 is now @production` | `taxi-demand v1 is now @production` | ✅ E1 |
| 11 | 11:45:30 | 2 · API | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 OMP_NUM_THREADS=1 uv run uvicorn app.main:app --port 8000` | prête au premier appel | `loaded models:/taxi-demand@production (version 1)` ; documentation sur http://127.0.0.1:8000/docs | `loaded models:/taxi-demand@production (version 1)` ; `/docs` n'a pas été ouvert pendant le test (contrôle fait ensuite : O6) | ✅ E1 |
| 12 | 11:46:11 | 3 · surveillance | `cd monitoring && docker compose up -d && cd ..` | 2,1 s | Prometheus (cible `taxi-api` à `UP`), Alertmanager, Grafana sans identifiant | trois conteneurs `Recreated`, puis `Started`. La cible `taxi-api` est `up` (`http://host.docker.internal:8000/metrics/`) et les règles `ApiDown` et `InputDrift` sont chargées. Alertmanager répond 200 ; Grafana 12.1.0 montre le tableau de bord « Taxi API » sans identifiant | ✅ E2 |

À la ligne 12, Docker a écrit `Recreate` et non `Create` : voir E2. Sur une machine neuve, il télécharge les images, puis crée les conteneurs.

### Vérifier l'API

| N° | Heure | Commande | Durée | Sortie attendue (README) | Sortie obtenue | |
| --- | --- | --- | --- | --- | --- | --- |
| 13 | 11:46:58 | `curl -s localhost:8000/health` | < 0,1 s | `{"status":"ok","model_version":"1"}` | `{"status":"ok","model_version":"1"}` | ✅ |
| 14 | 11:46:58 | `curl -s -X POST localhost:8000/v1/predict -H 'Content-Type: application/json' -d '{"zone": 237, "ts": "2020-03-02T08:00:00", "lag_1h": 112.0, "lag_24h": 98.0, "lag_168h": 120.0}'` | 0,3 s | `{"zone":237,"ts":"2020-03-02T08:00:00","prediction":…,"model_version":"1"}` | `{"zone":237,"ts":"2020-03-02T08:00:00","prediction":190.20255820567724,"model_version":"1"}` | ✅ |

### Démo

| N° | Heure | Étape | Commande | Durée | Sortie attendue (README) | Sortie obtenue | |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 15 | 11:47:12 | 0. Avant | `uv run python replay.py --start 2020-02-17 --end 2020-02-29` | 33,0 s | `done: ok …, errors 0, rows appended to data/truth.csv` ; aucune alerte | `done: ok 6240, errors 0, rows appended to data/truth.csv`. PSI final : 0,034 pour `lag_1h`, 0,092 pour `lag_24h`. Aucune alerte en firing, rien dans Alertmanager (voir O1) | ✅ |
| 16 | 11:46:58 | 1. Une requête | les deux `curl` des lignes 13 et 14 | — | `/health` puis la prévision, en v1 | lancées 14 s avant l'étape 0 et non après (voir E3) ; modèle v1 | E3 |
| 17 | 11:48:05 | 2. La dérive | `uv run python replay.py --start 2020-03-01 --end 2020-03-31` | 76,6 s | dans Grafana, le PSI dépasse 0,25 ; `InputDrift` passe de pending à firing dans Prometheus, puis dans Alertmanager | `done: ok 14880, errors 0, rows appended to data/truth.csv`. Dans Grafana (requête du panneau PSI), `lag_1h` dépasse 0,25 à 11:48:40, 35 s après le début, et monte jusqu'à 7,88 ; `lag_24h` monte jusqu'à 8,31. `InputDrift` passe en pending dans Prometheus à +30 s, puis sans interruption à partir de +40 s ; elle passe en firing et arrive dans Alertmanager à +100,7 s | ✅ |
| 18 | 11:51:57 | 3. Réentraînement | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python check_and_retrain.py` | 14,4 s | `{"action": "retrain", …}` puis `taxi-demand v2 is now @staging` | `{"now": "2020-03-31T23:00:00", "psi": {"lag_1h": 7.7033, "lag_24h": 7.6443}, "days": 7, "action": "retrain", "mae_production": 21.6775, "mae_candidate": 3.9738, "run_id": "4c925bb2974f430fb62fce5da5c3c1ab", "version": "2"}` puis `taxi-demand v2 is now @staging (MAE 3.9738 vs 21.6775 in production)` | ✅ E1 |
| 19 | 11:52:23 | 4. Promotion | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python promote.py` | 3,3 s | `taxi-demand v2 is now @production (was v1)`, puis `Relancer l'API` | `taxi-demand v2 is now @production (was v1)` puis `Relancer l'API` | ✅ E1 |
| 20 | 11:53:49 | 4. Relance | terminal 2 : Ctrl+C, puis la commande de la ligne 11 ; `curl -s localhost:8000/health` | — | `/health` affiche v2 | API arrêtée à 11:53:49, relancée à 11:53:52 : `loaded models:/taxi-demand@production (version 2)` ; `{"status":"ok","model_version":"2"}` | ✅ E1 |
| 21 | 11:59:05 | 5. Rollback | `MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python rollback.py`, puis le terminal 2 relancé (script ci-dessous) | 11,7 s | `taxi-demand v1 is now @production`, puis `Relancer l'API`, puis `/health shows v1 after … s` | `taxi-demand v1 is now @production`, `Relancer l'API`, `/health shows v1 after 8.2 s` ; l'API relancée affiche `loaded models:/taxi-demand@production (version 1)` | ✅ E1 |

### Relances de l'API, le Ctrl+C du terminal 2

Le Ctrl+C du terminal 2 a été donné par un signal SIGINT au processus `uvicorn` qui écoute sur le port 8000. La commande de la ligne 11 a ensuite été relancée.

- Après la promotion, à la main : `kill -INT 91206` (arrêt à 11:53:49), puis la commande de la ligne 11 (11:53:52).
- Au rollback, par un petit script, `rollback_and_restart.sh`, gardé hors du dépôt. Ainsi, la durée mesurée ne dépend pas du délai entre deux commandes. Ses commandes, en substance (le PID est trouvé avec `lsof`, et les boucles d'attente sont résumées en commentaires) :

```zsh
# terminal 4 : rollback.py en arrière-plan, sa sortie dans un fichier
MLFLOW_TRACKING_URI=http://127.0.0.1:5011 uv run python rollback.py > 17-rollback.log 2>&1 &
# dès que « Relancer l'API » apparaît dans ce fichier (relu toutes les 0,2 s), le Ctrl+C du terminal 2
kill -INT <PID du processus qui écoute sur le port 8000>
# attente que le port 8000 se libère (relu toutes les 0,2 s), puis la commande de la ligne 11
export MLFLOW_TRACKING_URI=http://127.0.0.1:5011
export OMP_NUM_THREADS=1
exec uv run uvicorn app.main:app --port 8000
```

« Relancer l'API » est apparu à 11:59:09, et l'API a été arrêtée puis relancée dans la même seconde. Les 8,2 s ne comptent donc pas de temps de réaction humain (O3).

État à la fin de la démo :
- Registry du clone : `taxi-demand` v1 en `@production`, v2 en `@staging`.
- `data/decisions.jsonl` : une ligne, `"action": "retrain"`.
- `data/promotions.jsonl` : `{"ts": "2026-11-23T10:52:26Z", "from": "1", "to": "2"}`.
- `data/truth.csv` : 21 120 lignes, février puis mars.

## Comparaison avec le cours

Pour le cours, un clone neuf reproduit le modèle quand le code, l'environnement et les données sont identiques, et que les métriques sont égales à 1e-6 près (L1 README §5 ; WRAP p.8).

| Ce qui est comparé | Clone neuf | Référence | |
| --- | --- | --- | --- |
| Code | tag `git_commit` du run v1 : `688502718d5adc48c9f2dd1d8b4ec067d947e55d` ; `git_dirty` : `False` | `main` au moment du clone | ✅ |
| Environnement | `uv sync --locked` : 163 paquets installés sur les 167 de `uv.lock`. Les 4 autres sont le projet lui-même et trois paquets réservés à Windows (`pywin32`, `tzdata`, `waitress`) | `uv.lock` commité | ✅ |
| Données brutes | `data/raw.dvc` inchangé après `dvc add` : `md5: 41afee30aa691264fa8da29312afb9db.dir`, 3 fichiers, 230 140 329 octets | pointeur commité | ✅ |
| Données dérivées | md5 calculé de `data/features.parquet` : `335cc10a28f85363c7bac4a41a0c58d4` ; de `data/zones.json` : `ac4da25717d2280ae39a13bd9378ce55` | `data/features.parquet.dvc` et `data/zones.json.dvc` : les mêmes empreintes | ✅ |
| Métriques | `mae_valid` 28.49834215371863 ; `mae_baseline_valid` 47.888621794871796 | README et `docs/evidence/t7.3_mesures.txt` : 28.4983 et 47.8886 | ⚠️ égales aux 4 décimales publiées |

Les deux références de métriques s'arrêtent à 4 décimales : le critère du cours (1e-6) n'a donc pas pu être vérifié. Les valeurs complètes ci-dessus serviront de référence au prochain clone.

## Écarts et erreurs

| N° | Nature | Constat | Correction |
| --- | --- | --- | --- |
| E1 | Environnement : machine partagée | Le port 5001 était pris par le serveur MLflow officiel de l'équipe, lancé depuis sa copie de travail, et le pilote a décidé de ne pas l'arrêter. Le MLflow du clone a donc tourné sur le port 5011, avec la commande du README à part le port. `MLFLOW_TRACKING_URI=http://127.0.0.1:5011` a été placé devant chaque commande qui parle à MLflow : `train.py`, `register.py`, l'API, `check_and_retrain.py`, `promote.py` et `rollback.py`. Ces scripts, comme `evaluate.py`, lisent la variable avec `os.getenv` (Spécifications §1) ; 5001 n'est que la valeur par défaut, rien n'est codé en dur. Aucun fichier ne charge `.env` : la variable passe par l'environnement du terminal. `uv run pytest -q` n'en a pas besoin, car la fixture de `tests/conftest.py` utilise un store SQLite temporaire. Aucune commande du test n'a donc visé le MLflow officiel du port 5001. | Aucune : ce n'est pas un défaut du README. Sur une machine où le port 5001 est libre, ses commandes s'appliquent telles quelles. |
| E2 | Environnement : machine partagée | Les ports 9090, 9093 et 3000, que le README demande libres, étaient pris par la stack de surveillance de l'équipe, lancée depuis sa copie de travail. Les deux dossiers s'appellent `monitoring`, d'où le même nom de projet Compose. Lancé depuis le clone, `docker compose up -d` a donc recréé les trois conteneurs avec les fichiers du clone. La consigne du pilote pour ce test le prévoyait : la stack de l'équipe était cédée à la 6.2 pendant son tour. | Aucune : ce n'est pas un défaut du README. Remise en place après le test, le 23/11 à 12:08 : `docker compose up -d` depuis `mlops-taxi/monitoring`, et `docker compose ls` montre de nouveau `mlops-taxi/monitoring/docker-compose.yml`. |
| E3 | Ordre du test | L'étape 1 de la démo (les deux `curl`) a été faite 14 s avant l'étape 0, au titre de « Vérifier l'API », et n'a pas été refaite ensuite. | Aucune : c'est un écart du test, pas du README, sans effet sur la sortie (même modèle v1). |
| D1 | Documentation : `docs/data.md`, cité par le README | La phrase « `uv run dvc status` répond ensuite « Data and pipelines are up to date. » » est fausse sur un clone neuf : `dvc status` signale `data/features.parquet` et `data/zones.json` comme « not in cache ». C'est le cas après `build_dataset.py` (relevé du 22/11 à 23:34) comme avant : cet état a été reconstitué le 23/11 vers 12:05 en sortant les deux fichiers de `data/`, puis en les remettant, md5 inchangés. `uv run dvc status data/raw.dvc` répond bien « Data and pipelines are up to date. ». La phrase date de la 1.1 (`1c794d7`, le 21/11 à 05:02), quand `data/raw.dvc` était le seul pointeur. La 1.2 l'a rendue fausse 42 minutes plus tard, en ajoutant `features.parquet.dvc` et `zones.json.dvc` (`04e5bfb`). | Phrase corrigée dans la pull request de la tâche 6.2 (branche `t6-2-clone-neuf`). Ni le README ni le code ne changent. |

## Observations, sans écart au README

- **O1, début du rejeu de février.** Au départ, la fenêtre du PSI ne contient que les premières prédictions. `lag_24h` a valu 0,369 sur un relevé (11:47:20), et `InputDrift` (`lag_24h`) est passée une fois en pending (11:47:25). Il n'y a eu ni firing ni alerte dans Alertmanager, et le PSI est ensuite resté sous 0,25 (fin de février : 0,034 et 0,092). « Aucune alerte » reste donc vrai. Dans Grafana, sur les 15 dernières minutes, ce pic apparaît si février a été rejoué moins de 15 minutes avant la démo.
- **O2, délai de l'alerte.** `InputDrift` est en pending sans interruption à partir de +40 s, après un premier relevé pending de `lag_24h` à +30 s. Elle passe en firing à +100,7 s (1 min 41 s) : `lag_1h` à 11:49:45, `lag_24h` à 11:49:50, une minute après le début de leur pending continu (`for: 1m`). C'est la fourchette calculée dans `docs/demo_script.md` §3 (1 min 35 à 1 min 45). Le rejeu de mars se termine avant le firing (76,6 s), et la jauge garde sa dernière valeur (7,88), comme prévu.
- **O3, durée du rollback.** 8,2 s ici, avec une relance de l'API scriptée ; 22,4 s pendant l'incident, avec une relance à la main. Les deux restent sous les 300 s visées.
- **O4, version testée.** Pendant le test, `main` est passé de `6885027` à `68cc184` (PR #21, tâche 6.3). Cette PR renomme des captures dans `docs/evidence/`, supprime `mae_par_semaine copy.csv` et modifie `t7.3_mesures.txt` (seuls des chemins d'images y changent), `incident/chronologie.md`, `docs/incident_report.md` et `docs/qa_prep.md`. Aucun fichier de code ne change, ni le README, ni `docs/data.md`. Sur `68cc184`, `uv sync --locked` passe et `uv run pytest -q` donne 24 passed : le résultat vaut aussi pour cette version.
- **O5, avertissements.** MLflow affiche trois avertissements sans effet sur le résultat. `Failed to resolve installed pip version` et l'indication `Inferred schema contains integer column(s)` viennent de `train.py` et de `check_and_retrain.py`. `Run with id … has no artifacts at artifact path 'model', registering model based on models:/m-… instead` vient de `register.py` et de `check_and_retrain.py` : MLflow 3 range le modèle à part (`models:/m-…`), et la version est bien créée. Les 4 avertissements de pytest sont trois annonces de dépréciation (Starlette, SQLAlchemy, pandas) et une indication de MLflow sur les colonnes entières du schéma.
- **O6, documentation de l'API.** Le README annonce aussi, pour le terminal 2, la documentation sur http://127.0.0.1:8000/docs. Elle n'a pas été ouverte pendant le test. Le contrôle a été fait ensuite, le 23/11 à 12:22, sans serveur : le TestClient de FastAPI, sans le démarrage (lifespan), n'appelle pas MLflow. `GET /docs` répond 200 avec la page « Taxi demand API - Swagger UI », et `/openapi.json` décrit `/health` et `/v1/predict`.

## Résultat final

- L'API, la surveillance et le rejeu fonctionnent en suivant le README, sans étape absente du README, aux écarts d'environnement E1 et E2 près.
- La démo passe en entier : v1 en production, alerte de dérive, v2 en `@staging`, v2 en `@production`, puis retour à la v1 en 8,2 s.
- Les données sont identiques à l'octet près. Les MAE sont égales aux 4 décimales publiées ; le critère de 1e-6 du cours n'a pas pu être vérifié, faute de référence plus précise.
- Seule correction : `docs/data.md` (D1).
