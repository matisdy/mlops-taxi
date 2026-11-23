# Tâches de la roadmap exécutable (version allégée)

Version du 20 novembre 2026 : 20 tâches, 31.5 heures-personne en travaillant avec une IA, soit environ 8 h par personne. Rien à trancher : tout est fixé dans `06_Specifications.md` (copiée dans `docs/specifications.md` du dépôt). « Dépendances » = tâches à terminer avant de commencer ; après le socle (0.2), neuf tâches se font en parallèle. Statuts au rendu du 23 novembre 2026 : 19 tâches terminées sur 20 ; la 8.3 (séance de questions et répétition) se termine à la soutenance du 24 novembre. La source de vérité, statuts compris, est la roadmap Notion : https://app.notion.com/p/41df4ba8c5228108a2acca91de7bddf0

## 0 · Cadrage et socle

### 0.1 · Explorer les sources et préparer la roadmap

- **Jalon** : J0 · Lancement (ven. 10h30) · **Charge** : 0 h · **Statut** : Terminé
- **Démarre** : — (dépendances : —)
- **Objectif** : Explorer les sources du cours et préparer la roadmap.
- **Exigence du sujet** : Prérequis de cadrage, pas une exigence du sujet.
- **Méthode du cours (source)** : —
- **Spécifications** : — · **Choix liés** : — · **Exigences** : —
- **Fichiers produits** : `Pilotage/`
- **Étapes** :
  1. Fait : exploration des sources et roadmap.
- **Vérification** :
  - Fait.
- **Preuve à garder** : `Pilotage/`

### 0.2 · Socle commun : dépôt, uv, configuration, jeu synthétique et `drift.py`

- **Jalon** : J1 · Première chaîne (ven. 19h) · **Charge** : 1.5 h · **Statut** : Terminé
- **Démarre** : Tout de suite, en premier, par une seule personne (environ 1 h 30). C'est la seule tâche qui bloque les autres. (dépendances : —)
- **Objectif** : Créer le dépôt que tout le monde clone, avec les fichiers du contrat et les fonctions de dérive, pour que les autres tâches démarrent en parallèle.
- **Exigence du sujet** : Chacun commite, donner l'accès au dépôt (SUJET p.1) ; secrets dans .env, jamais dans Git ; clone neuf fonctionnel (SUJET p.2) ; surveillance de la dérive (SUJET p.1).
- **Méthode du cours (source)** : uv init, uv add, `uv.lock`, `--locked` (S2-UV p.4–11 ; WRAP p.10) ; `params.yaml` (L1 `params.yaml`, `train.py` l.25–30) ; `.gitignore` (L1) ; `.env` et secrets (L2 README « Secrets ») ; protection de main (S2-GHA p.22) ; données générées par script (L1 `gen_data.py`) ; `psi()` et déciles de référence (L4 `app.py` l.59–76 ; S5 p.8–9, 15).
- **Spécifications** : §1, §2, §3, §5, §6 · **Choix liés** : DEC-11, DEC-18, DEC-12, EC-8 · **Exigences** : E14, E18, E19, E20, E6, E16
- **Fichiers produits** : `pyproject.toml`, `uv.lock`, `params.yaml`, `policy.yaml`, `.env.example`, `.gitignore`, `make_synthetic.py`, `drift.py`, `tests/test_drift.py`, `docs/specifications.md`, `docs/taches.md`, `README.md`
- **Étapes** :
  1. Créer sur GitHub le dépôt privé `mlops-taxi`, inviter les trois autres membres, le cloner.
  2. Lancer les commandes uv de la section 1, puis ajouter le bloc `[tool.pytest.ini_options]`.
  3. Créer `params.yaml`, `policy.yaml`, `.env.example` et `.gitignore` en copiant la section 3, puis `cp .env.example .env`.
  4. Écrire `make_synthetic.py` (section 6) : 3 zones, 21 jours horaires à partir du 2020-01-08 ; y tiré d'une loi de Poisson dont la moyenne dépend de la zone et de l'heure (numpy, comme L1 `gen_data.py`) ; lags calculés avec `shift` ; split train pour les 14 premiers jours, valid ensuite ; `uv run python make_synthetic.py` écrit `data/synthetic.parquet`.
  5. Écrire `drift.py` (section 6). `reference_bins(values, bins=10)` : `edges = np.unique(np.quantile(values, np.linspace(0, 1, bins + 1)))` ; `shares = np.histogram(values, edges)[0] / len(values)` (parts mesurées, EC-8) ; renvoyer `{"edges": [...], "shares": [...]}` en listes, pour le JSON.
  6. `make_reference(df, features, bins=10)` : `{f: reference_bins(df[f].to_numpy(), bins) for f in features}`. `psi(ref, sample)` : la formule de L4 l.59–63, avec `ref["edges"]` et `ref["shares"]`.
  7. `tests/test_drift.py` : un échantillon tiré de la référence donne un PSI < 0,1 ; le même échantillon multiplié par 0,2 donne un PSI > 0,25 ; les parts somment à 1 ; avec beaucoup de zéros, les bornes n'ont pas de doublon.
  8. Copier les Spécifications dans `docs/specifications.md` et la liste des tâches (`Pilotage/Roadmap_Notion/05_Taches_detaillees.md`) dans `docs/taches.md` ; créer un `README.md` d'une ligne.
  9. Commit `[0.2] socle`, push, puis protéger `main` sur GitHub (pull request obligatoire).
- **Vérification** :
  - Sur une deuxième machine : `git clone`, `uv sync --locked`, `uv run python make_synthetic.py` et `uv run pytest -q` fonctionnent ; `data/synthetic.parquet` a les 9 colonnes de la section 4.
  - `git status` ne montre ni `.env` ni fichier de `data/`.
- **Preuve à garder** : Lien du commit du socle.

## 1 · Données et DVC

### 1.1 · `download.py` et DVC : télécharger janvier à mars 2020 et versionner les fichiers bruts

- **Jalon** : J1 · Première chaîne (ven. 19h) · **Charge** : 1 h · **Statut** : Terminé
- **Démarre** : Après 0.2. (dépendances : 0.2)
- **Objectif** : Reproduire les données brutes avec un script et les suivre avec DVC, sans les commiter.
- **Exigence du sujet** : Données NYC TLC yellow, un Parquet par mois ; ne pas commiter les fichiers bruts : un script de téléchargement et DVC les reproduisent ; citer la TLC (SUJET p.1).
- **Méthode du cours (source)** : `requests` avec timeout (S3 p.8 ; S5 p.30) ; `dvc init`, `dvc remote add -d`, `dvc add`, `dvc push`, `dvc status -c` (L1 README §1 ; S1-MLF p.40–43) ; DVC lancé par uv (L1 README l.17).
- **Spécifications** : §3, §4 · **Choix liés** : DEC-02, DEC-09, EC-4, EC-5 · **Exigences** : E2, E10, E13, E14
- **Fichiers produits** : `download.py`, `data/raw.dvc`, `docs/data.md`
- **Étapes** :
  1. `download.py` : pour chaque mois de `params.yaml`, construire l'URL avec `data.url` et l'enregistrer dans `data/raw/yellow_tripdata_{month}.parquet` avec `requests.get(url, stream=True, timeout=60)` et une écriture par blocs ; ne pas retélécharger un fichier présent ; afficher la taille de chaque fichier.
  2. `uv run python download.py`.
  3. `uv run dvc init`, `uv run dvc remote add -d local ../dvc-store`, puis `uv run dvc add data/raw`.
  4. `git add .dvc data/raw.dvc data/.gitignore download.py`, commit, puis `uv run dvc push`.
  5. `docs/data.md` : la source citée de la section 4 avec son lien, les mois utilisés, les colonnes lues.
- **Vérification** :
  - `uv run dvc status -c` indique que le cache et le remote sont synchronisés.
  - `git ls-files | grep parquet` ne renvoie rien.
  - Sur une autre machine, `uv run python download.py` puis `uv run dvc status` ne signalent aucun changement.
- **Preuve à garder** : Sortie de `dvc status -c`.

### 1.2 · `build_dataset.py` : une ligne par zone et par heure, variables décalées et découpage temporel

- **Jalon** : J1 · Première chaîne (ven. 19h) · **Charge** : 1.5 h · **Statut** : Terminé
- **Démarre** : Après 0.2. Le code et les tests s'écrivent sur un petit tableau fait à la main ; l'exécution sur les vrais fichiers attend 1.1. (dépendances : 0.2)
- **Objectif** : Produire `data/features.parquet` exactement au format de la section 4.
- **Exigence du sujet** : Prédire les prises en charge d'une zone pour l'heure suivante à partir des heures récentes et du calendrier ; une ligne par zone et par heure ; découper par le temps, jamais au hasard ; une période de référence et une période de dérive (SUJET p.1).
- **Méthode du cours (source)** : `groupby` pandas (L4 `join_labels.py` l.19) ; données produites par un script puis `dvc add` (L1 `gen_data.py`, README §1) ; ne jamais évaluer sur les données d'entraînement (WRAP p.15 et 45) ; tests pytest (L3 `test_app.py`). Le cours n'a pas d'exemple de variables décalées ni de découpage temporel (EC-1, EC-3) : les labs découpent au hasard (L1 `train.py` l.37), à ne pas reproduire.
- **Spécifications** : §3, §4 · **Choix liés** : DEC-02, DEC-03, DEC-04, DEC-05, EC-1, EC-3 · **Exigences** : E11, E15, E16, E2
- **Fichiers produits** : `build_dataset.py`, `tests/test_features.py`, `data/features.parquet.dvc`, `data/zones.json.dvc`
- **Étapes** :
  1. Écrire `build_features(trips, params, zones=None)` qui renvoie `(features, zones)` : `ts = tpep_pickup_datetime.dt.floor("h")` ; garder la plage de la section 4 ; si `zones` est vide, prendre les 20 `PULocationID` les plus fréquents sur la période train.
  2. Compter les trajets par (zone, ts), puis compléter la grille toutes heures × zones avec 0 (`pd.MultiIndex.from_product`, puis `reindex(fill_value=0)`).
  3. Trier par zone puis ts ; `lag_1h`, `lag_24h` et `lag_168h` = `groupby("zone").y.shift(1)`, `shift(24)` et `shift(168)` ; `hour` et `dow` depuis ts.
  4. Poser `split` avec les dates de `params.yaml`, supprimer les lignes hors des trois plages, ordonner les colonnes comme la section 4, passer les lags et y en float.
  5. Partie principale : lire les trois Parquet de `data/raw` (colonnes `tpep_pickup_datetime` et `PULocationID` seulement), écrire `data/features.parquet` et `data/zones.json`.
  6. `tests/test_features.py`, sur 9 jours fabriqués pour 2 zones avec des dates de split passées en paramètre : une ligne par zone et par heure ; le `lag_1h` d'une heure égale le nombre de trajets de l'heure précédente ; une heure sans trajet vaut 0 ; aucune ligne train après la fin de la plage train.
  7. Après 1.1 : `uv run python build_dataset.py`, puis `uv run dvc add data/features.parquet data/zones.json`, commit des pointeurs, `uv run dvc push`.
- **Vérification** :
  - `uv run pytest tests/test_features.py -q` est vert.
  - `data/features.parquet` : 40 320 lignes, les 9 colonnes dans l'ordre, les trois valeurs de split.
- **Preuve à garder** : Sortie de pytest et de `df.shape`.

## 2 · Modèle MLflow et Registry

### 2.1 · `train.py`, `register.py` et `evaluate.py` : entraîner, tout journaliser dans MLflow, évaluer par semaine

- **Jalon** : J1 · Première chaîne (ven. 19h) · **Charge** : 2 h · **Statut** : Terminé
- **Démarre** : Après 0.2, sur `data/synthetic.parquet` (`drift.py` est déjà dans le socle). (dépendances : 0.2)
- **Objectif** : Un run MLflow complet, une version enregistrée et un tableau d'évaluation par semaine, d'abord sur le jeu synthétique.
- **Exigence du sujet** : Chaque run journalise paramètres, métriques, commit Git et empreinte des données ; modèles dans le Registry MLflow ; choisir ses métriques (SUJET p.1).
- **Méthode du cours (source)** : L1 `train.py` l.25–92 (fit pur sans MLflow, tags `git_commit`, `git_dirty`, `data_md5`, `log_model` avec signature et `skops_trusted_types`) ; L1 `register.py` l.11–14 ; lancement de MLflow (L1 README l.35) ; baseline (S1-INTRO p.28) ; artefacts d'un run (S1-MLF p.20) ; évaluer le modèle d'un alias (L1 `score.py` l.18) ; score du modèle de janvier sur février (L1 README §6) ; « Does it hurt? » (S5 p.22).
- **Spécifications** : §5, §6 · **Choix liés** : DEC-06, DEC-07, DEC-10, EC-2 · **Exigences** : E1, E3, E17, E9, E12
- **Fichiers produits** : `train.py`, `register.py`, `evaluate.py`, `tests/test_model.py`
- **Étapes** :
  1. Lancer MLflow dans un terminal avec la commande de la section 5.
  2. Dans `train.py`, écrire les fonctions de la section 6 : `fit` construit le pipeline de la section 5 et l'entraîne sur `split == "train"` avec les colonnes `params["features"]` ; `mae` ; `baseline_mae` (prédiction = `lag_168h`) ; `data_md5` lit `path + ".dvc"` comme L1 l.60–62, ou calcule le md5 du fichier s'il n'y a pas de pointeur.
  3. `log_model_run` : `mlflow.start_run`, `log_params`, `log_metrics`, tags `git_commit`, `git_dirty`, `data_md5` (L1 l.75–82), `mlflow.sklearn.log_model(model, name="model", signature=..., input_example=..., skops_trusted_types=[...])` comme L1 l.83–90, puis `mlflow.log_dict(reference, "reference.json")` ; renvoie le run_id.
  4. Partie principale : `uv run python train.py [--data chemin]` (défaut `data/features.parquet`) ; métriques `mae_valid` et `mae_baseline_valid` sur `split == "valid"` ; afficher le run_id.
  5. `register.py` : `register(run_id, alias)` comme L1 `register.py` ; en ligne de commande, alias par défaut `production`.
  6. `uv run python evaluate.py [alias] [--data chemin]` : charge `models:/taxi-demand@alias` (défaut `production`) avec `mlflow.pyfunc.load_model`, comme L1 `score.py` l.18. Il calcule, sur les lignes valid et replay, par semaine (lundi) : nombre de lignes, moyenne de y, MAE du modèle, MAE de la baseline, MAE relative = MAE / moyenne de y. Il affiche le tableau et l'écrit dans `docs/evidence/mae_par_semaine.csv`.
  7. `tests/test_model.py` : deux `fit` sur `make_synthetic()` donnent les mêmes prédictions ; `mae` et `baseline_mae` renvoient des nombres positifs.
- **Vérification** :
  - `uv run python train.py --data data/synthetic.parquet`, puis `uv run python register.py RUN_ID` : dans MLflow (`http://127.0.0.1:5001`), le run montre les paramètres, `mae_valid`, `mae_baseline_valid`, les trois tags et les artefacts `model` et `reference.json` ; `taxi-demand` v1 porte l'alias `production`.
  - `uv run pytest tests/test_model.py -q` est vert.
  - `uv run python evaluate.py --data data/synthetic.parquet` affiche le tableau sans erreur.
- **Preuve à garder** : Capture du run et du Registry.

## 3 · Service et tests

### 3.1 · API FastAPI : chargement de `@production`, `/health`, `/v1/predict`, `/metrics` et PSI glissant

- **Jalon** : J1 · Première chaîne (ven. 19h) · **Charge** : 2 h · **Statut** : Terminé
- **Démarre** : Après 0.2 (`drift.py` est dans le socle). Pour un essai réel il faut un modèle enregistré : celui du jeu synthétique (2.1) suffit. (dépendances : 0.2)
- **Objectif** : Servir le modèle `@production` selon le contrat HTTP de la section 7, avec les métriques et le PSI des entrées.
- **Exigence du sujet** : Service FastAPI (SUJET p.1).
- **Méthode du cours (source)** : L3 `app.py` : lifespan l.26–37, `extra="forbid"` l.53, `Field` avec contraintes, middleware `X-Request-ID` l.96–107, gestionnaire 500 l.110–115, `/health` 503 l.118–123, routeur `/v1` l.126 ; chargement par alias (S3 p.26 ; L1 `score.py` l.18) ; métriques Prometheus et `/metrics` (L4 `app.py` l.31–39 et l.80) ; `download_artifacts` (L2 `export_model.py`) ; fenêtre glissante et recalcul toutes les N prédictions (L4 `app.py` l.28–29 et l.119–131 ; S4 p.25–29).
- **Spécifications** : §3, §7 · **Choix liés** : DEC-08, DEC-11, DEC-12, EC-6, EC-7 · **Exigences** : E4, E11, E6
- **Fichiers produits** : `app/main.py`
- **Étapes** :
  1. Copier la structure de L3 `app.py` dans `app/main.py` : lifespan, middleware, gestionnaire d'erreur, `/health`, routeur `/v1`.
  2. Modèles Pydantic : `PredictRequest` (`extra="forbid"`, zone entier de 1 à 265, ts datetime, trois lags ≥ 0) et `PredictResponse` (zone, ts, prediction, model_version).
  3. Lifespan : `mv = MlflowClient().get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)` ; `state["model"] = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@{MODEL_ALIAS}")` ; `state["version"] = mv.version` ; `state["reference"]` = contenu de `reference.json`, téléchargé avec `mlflow.artifacts.download_artifacts(run_id=mv.run_id, artifact_path="reference.json")`. En cas d'erreur, démarrer sans modèle comme L3 l.30–35.
  4. `POST /v1/predict` : 503 sans modèle ; DataFrame d'une ligne avec les colonnes `params["features"]` (`hour = ts.hour`, `dow = ts.weekday()`) ; `prediction = float(model.predict(X)[0])` ; incrémenter `taxi_predictions_total` avec le label `model_version`.
  5. Métriques de la section 7, déclarées comme L4 l.31–39 ; `app.mount("/metrics", make_asgi_app())` ; le middleware observe `taxi_request_seconds` pour `/v1/predict` ; `taxi_input_psi` est mise à 0 au démarrage pour `lag_1h` et `lag_24h`.
  6. Lire `policy.yaml` au démarrage ; une `deque(maxlen=window)` par variable de `drift.features`. À chaque prédiction, ajouter `lag_1h` et `lag_24h` à leur fenêtre et incrémenter un compteur. Toutes les `every` prédictions, si la fenêtre est pleine : `taxi_input_psi.labels(f).set(psi(state["reference"][f], np.array(fenetre)))`.
- **Vérification** :
  - `uv run uvicorn app.main:app --port 8000`, puis `curl localhost:8000/health` affiche la version.
  - `curl -X POST localhost:8000/v1/predict -H 'content-type: application/json' -d '{"zone": 237, "ts": "2020-03-02T08:00:00", "lag_1h": 112, "lag_24h": 98, "lag_168h": 120}'` répond 200 avec prediction et model_version.
  - Le même appel avec un champ en trop répond 422 ; `curl localhost:8000/metrics/` contient `taxi_predictions_total` et `taxi_input_psi`.
  - Après 480 prédictions (rejeu 4.2 sur le jeu synthétique), `taxi_input_psi` n'est plus à 0.
- **Preuve à garder** : Sorties de curl.

### 3.2 · Tests d'intégration et CI GitHub Actions

- **Jalon** : J2 · Composants réels (sam. 19h) · **Charge** : 1.5 h · **Statut** : Terminé
- **Démarre** : Après 2.1 et 3.1 (la fixture réutilise leurs fonctions et `drift.py`). (dépendances : 2.1, 3.1)
- **Objectif** : Tester l'API avec un vrai modèle enregistré, en local et dans GitHub Actions.
- **Exigence du sujet** : Tests d'intégration (SUJET p.1) ; livrer tôt et souvent (SUJET p.2, conseils).
- **Méthode du cours (source)** : Fixture `TestClient` qui exécute le démarrage (L3 `test_app.py` l.9–12) ; cas 200 et 422 (L3 `test_app.py`) ; « register a test model » (S3 p.29) ; workflow uv (S2-UV p.11) ; protection de main (S2-GHA p.22).
- **Spécifications** : §6, §10 · **Choix liés** : DEC-16, EC-9 · **Exigences** : E5, E23
- **Fichiers produits** : `tests/conftest.py`, `tests/test_api.py`, `.github/workflows/ci.yml`
- **Étapes** :
  1. `tests/conftest.py`, fixture `client` (scope module) : dossier temporaire (`tmp_path_factory`) ; `MLFLOW_TRACKING_URI=sqlite:///<tmp>/mlflow.db` (variable d'environnement et `mlflow.set_tracking_uri`) ; expérience créée avec `artifact_location` dans ce dossier ; `df = make_synthetic()` ; `model = fit(params, df)` ; `run_id = log_model_run(...)` avec `make_reference` ; `register(run_id, "production")` ; puis `with TestClient(app) as c: yield c`.
  2. `tests/test_api.py` : `/health` répond 200 avec `model_version` ; une requête valide répond 200 avec un nombre ; deux requêtes identiques donnent la même prédiction ; un champ en trop et un lag négatif répondent 422 ; `/metrics/` contient `taxi_input_psi`.
  3. `.github/workflows/ci.yml` : copier la section 10.
  4. Sur GitHub, rendre le statut de la CI obligatoire avant toute fusion sur `main`.
- **Vérification** :
  - `uv run pytest -q` est vert en local.
  - L'onglet Actions est vert sur la pull request.
- **Preuve à garder** : Capture de la CI verte.

## 4 · Surveillance et dérive

### 4.1 · Stack de surveillance du lab 4 : Prometheus, Alertmanager, Grafana et alerte de dérive

- **Jalon** : J1 · Première chaîne (ven. 19h) · **Charge** : 1.5 h · **Statut** : Terminé
- **Démarre** : Après 0.2. L'API n'est pas nécessaire pour monter la stack. (dépendances : 0.2)
- **Objectif** : Une stack qui interroge l'API, déclenche `InputDrift` et affiche le PSI.
- **Exigence du sujet** : Surveillance de la dérive (SUJET p.1) ; démo avec déclenchement d'une alerte de dérive (SUJET p.2).
- **Méthode du cours (source)** : L4 `docker-compose.yml`, `prometheus/prometheus.yml`, `prometheus/alerts.yml`, `alertmanager/alertmanager.yml`, `grafana/` (S4 p.17–19, 41–47, 56–57) ; règles avec `for`, états pending puis firing (S4 p.43).
- **Spécifications** : §8 · **Choix liés** : DEC-12 · **Exigences** : E6, E21
- **Fichiers produits** : `monitoring/`
- **Étapes** :
  1. Copier dans `monitoring/` les fichiers du lab 4 : `docker-compose.yml`, `prometheus/`, `alertmanager/`, `grafana/`.
  2. `prometheus/prometheus.yml` : `job_name: taxi-api` ; garder `metrics_path: /metrics/` et la cible `host.docker.internal:8000`.
  3. `prometheus/alerts.yml` : remplacer le contenu par celui de la section 8.
  4. Grafana : renommer `grafana/dashboards/fraud.json` en `taxi.json`, titre « Taxi API » ; garder les panneaux « requests per second » (`sum(rate(taxi_predictions_total[1m]))`), « P95 latency » (avec `taxi_request_seconds_bucket`) et le panneau PSI (`taxi_input_psi`, une courbe par variable, seuil 0,25) ; supprimer les panneaux des couches 3 et 4.
  5. `cd monitoring && docker compose up -d` ; après une modification des règles, `docker compose restart prometheus`, comme au lab 4.
- **Vérification** :
  - `http://localhost:9090/rules` montre `ApiDown` et `InputDrift`.
  - `http://localhost:9090/targets` montre `taxi-api`, down tant que l'API ne tourne pas, up ensuite.
  - Grafana (`http://localhost:3000`) affiche le tableau de bord « Taxi API ».
- **Preuve à garder** : Captures des règles et du tableau de bord.

### 4.2 · `replay.py` : rejouer une période vers l'API et écrire la vérité terrain

- **Jalon** : J1 · Première chaîne (ven. 19h) · **Charge** : 1 h · **Statut** : Terminé
- **Démarre** : Après 0.2 : se développe sur `data/synthetic.parquet` ; l'essai réel demande l'API (3.1) en marche. (dépendances : 0.2)
- **Objectif** : Injecter une période (février normal, puis mars 2020) dans l'API en marche, comme `traffic.py` au lab 4.
- **Exigence du sujet** : Injecter une dérive ; le sujet cite mars à juin 2020 comme exemple de période de dérive (SUJET p.1).
- **Méthode du cours (source)** : L4 `traffic.py` (client `httpx`, cadence, CSV de vérité l.42–50 et l.75–79) ; « push the drifted data » (S4 p.48) ; « a drift period that you inject » (S5 p.33).
- **Spécifications** : §9 · **Choix liés** : DEC-15, EC-11 · **Exigences** : E9, E12
- **Fichiers produits** : `replay.py`
- **Étapes** :
  1. Arguments : `--start`, `--end` (jours inclus), `--hours-per-second` (défaut 10), `--data` (défaut `data/features.parquet`), `--url` (défaut `API_URL`).
  2. Lire le Parquet, garder les lignes de la plage, les grouper par heure dans l'ordre de ts.
  3. Pour chaque heure, envoyer une requête `POST /v1/predict` par zone avec un `httpx.Client` (zone, ts au format ISO, trois lags), puis attendre pour respecter la cadence.
  4. Ajouter chaque réponse à `data/truth.csv` avec les colonnes de la section 9 (en-tête si le fichier est nouveau) ; compter les erreurs.
  5. Afficher la progression toutes les 24 heures simulées, comme `traffic.py` l.91–92.
- **Vérification** :
  - Avec l'API sur un modèle synthétique, `uv run python replay.py --data data/synthetic.parquet --start 2020-01-22 --end 2020-01-28` écrit 7 × 24 × 3 = 504 lignes dans `truth.csv`, sans erreur.
  - `taxi_predictions_total` augmente dans `/metrics/`.
- **Preuve à garder** : Extrait de `truth.csv`.

## 5 · Réentraînement et rollback

### 5.1 · `promote.py` et `rollback.py` : promotion manuelle et retour arrière en moins de 5 minutes

- **Jalon** : J1 · Première chaîne (ven. 19h) · **Charge** : 1 h · **Statut** : Terminé
- **Démarre** : Après 0.2. Pour tester, il faut deux versions enregistrées : lancer deux fois `train.py` sur le jeu synthétique (2.1), ou enregistrer deux `DummyRegressor` de scikit-learn. (dépendances : 0.2)
- **Objectif** : Changer l'alias `production` dans les deux sens, et mesurer le retour arrière.
- **Exigence du sujet** : Procédure de rollback ; modèles dans le Registry (SUJET p.1) ; démo avec un rollback (SUJET p.2).
- **Méthode du cours (source)** : Un humain déplace `@production` après le gate (S5 p.24–25) ; rollback = remettre l'alias (S5 p.25 ; WRAP p.7) ; moins de 5 minutes, décidé d'avance (S6 p.36) ; une version chargée ne change pas sans relance (S3 p.41) ; `set_registered_model_alias` (L1 `register.py` l.13) ; runbook en cinq lignes (S4 p.58).
- **Spécifications** : §9 · **Choix liés** : DEC-14, EC-6 · **Exigences** : E8, E3, E21
- **Fichiers produits** : `promote.py`, `rollback.py`, `docs/runbook.md`
- **Étapes** :
  1. `promote.py` : `MlflowClient().get_model_version_by_alias(name, "staging")` ; noter la version actuelle de `production` ; `set_registered_model_alias(name, "production", version_staging)` ; ajouter `{"ts", "from", "to"}` à `data/promotions.jsonl` ; afficher « Relancer l'API ».
  2. `rollback.py [VERSION]` : cible = VERSION, ou le « from » de la dernière ligne de `data/promotions.jsonl` ; poser `production` sur la cible ; afficher « Relancer l'API » ; interroger `GET /health` toutes les 2 s jusqu'à `model_version == cible` (300 s au plus), puis afficher la durée.
  3. `docs/runbook.md`, cinq lignes (S4 p.58) : symptôme, première vérification, commande, relance de l'API, vérification de `/health`.
- **Vérification** :
  - Avec deux versions, `promote.py` fait passer `production` à v2 ; après la relance de l'API, `/health` affiche 2.
  - `rollback.py` remet v1 ; après la relance, il affiche une durée inférieure à 300 s.
- **Preuve à garder** : Sortie console de `rollback.py`.

### 5.2 · `check_and_retrain.py` : décider, réentraîner et passer le gate

- **Jalon** : J3 · Boucle complète (dim. 18h) · **Charge** : 2 h · **Statut** : Terminé
- **Démarre** : Après 2.1 (`drift.py` est dans le socle). Se teste avec un `truth.csv` produit par le rejeu (4.2) sur le jeu synthétique, puis sur mars (7.1). (dépendances : 2.1)
- **Objectif** : Le déclencheur de réentraînement du cours, en un seul script comme au lab.
- **Exigence du sujet** : Déclencheur de réentraînement ; réagir par réentraînement (SUJET p.1).
- **Méthode du cours (source)** : Arbre de décision (S5 p.22) ; chaîne : PSI > 0,25 et cooldown, entraînement, gate, `@staging`, approbation humaine (S5 p.24–25) ; `check_and_retrain.py` et `policy.yaml` (S5 p.27) ; gate contre la production sur des données récentes (S5 p.31) ; cooldown et une exécution à la fois (S5 p.32) ; réaction en un seul script (S5 p.33).
- **Spécifications** : §3, §6, §9 · **Choix liés** : DEC-07, DEC-13, EC-2, EC-10 · **Exigences** : E7, E3
- **Fichiers produits** : `check_and_retrain.py`, `tests/test_check.py`
- **Étapes** :
  1. `decide(psi_max, days, days_since_retrain, policy)` : `wait` si days < `min_new_days` ; `watch` si psi_max < `psi_act` ; `cooldown` si days_since_retrain < `cooldown_days` ; sinon `retrain`.
  2. Lire `params.yaml`, `policy.yaml` et `data/truth.csv` ; maintenant = dernier ts ; fenêtre = les `window_days` derniers jours ; days = nombre de jours distincts de la fenêtre.
  3. Charger le `reference.json` de la version `@production` (comme en 3.1) ; PSI de chaque variable de `drift.features` sur la fenêtre ; dernier « retrain » lu dans `data/decisions.jsonl`, en jours simulés.
  4. Si `retrain` : holdout = les `holdout_days` derniers jours ; candidat = `fit(params, reste de la fenêtre avec split = "train")` ; MAE du candidat et de la production (`mlflow.pyfunc.load_model`) sur le holdout ; journaliser le candidat avec `log_model_run` (référence calculée sur sa fenêtre) ; si MAE candidat ≤ (1 − `min_gain`) × MAE production, `register(run_id, "staging")` et action `retrain`, sinon `refused`.
  5. Ajouter une ligne à `data/decisions.jsonl` avec les champs de la section 9, et l'afficher.
  6. `tests/test_check.py` : un test par résultat possible de `decide()`.
- **Vérification** :
  - `uv run pytest tests/test_check.py -q` est vert.
  - Après le rejeu de mars (7.1), la ligne de `decisions.jsonl` indique `retrain` et une version `@staging` apparaît dans MLflow ; relancé aussitôt, le script répond `cooldown`.
- **Preuve à garder** : Extrait de `decisions.jsonl` et capture du Registry.

## 6 · Reproductibilité et rendu

### 6.1 · README : installation, lancement, démo, rollback, hypothèses

- **Jalon** : J5 · Gel du code (lun. 20h) · **Charge** : 1.5 h · **Statut** : Terminé
- **Démarre** : Après 0.2 : se rédige dès vendredi à partir des Spécifications, puis se met à jour quand une commande change. (dépendances : 0.2)
- **Objectif** : Qu'un clone neuf suivi à la lettre donne un système qui marche.
- **Exigence du sujet** : Un clone neuf et le README suffisent pour obtenir un système qui fonctionne (SUJET p.2) ; citer la TLC (SUJET p.1).
- **Méthode du cours (source)** : Format des README de lab : commandes et sortie attendue (L1 à L4) ; clone du coéquipier (L1 README §5).
- **Spécifications** : §11, §12, §13 · **Choix liés** : DEC-01, DEC-18 · **Exigences** : E20, E13
- **Fichiers produits** : `README.md`
- **Étapes** :
  1. Sections : but ; schéma (8.1) ; source des données (TLC, avec le lien) ; prérequis (uv, Docker, Git, ports 5001, 8000, 9090, 9093 et 3000 libres) ; installation ; lancement en quatre terminaux (section 11) ; démo (section 12) ; rollback (`docs/runbook.md`) ; tests ; hypothèses (section 13) ; membres du groupe.
  2. Pour chaque commande, la sortie attendue en une ligne, comme dans les README des labs.
  3. Dépannage : le port 5000 est pris par AirPlay sur macOS (d'où 5001) ; sous Linux, `host.docker.internal` passe par `extra_hosts`, déjà présent dans le compose du lab.
- **Vérification** :
  - Suivi à la lettre en 6.2, sans étape manquante.
- **Preuve à garder** : Compte rendu de 6.2.

### 6.2 · Tester depuis un clone neuf sur une autre machine

- **Jalon** : J5 · Gel du code (lun. 20h) · **Charge** : 1.5 h · **Statut** : Terminé
- **Démarre** : Après 6.1 et 7.2, par un membre qui n'a pas écrit le README, sur sa propre machine. (dépendances : 6.1, 7.2)
- **Objectif** : Vérifier l'exigence du clone neuf avant le rendu.
- **Exigence du sujet** : Clone neuf et README → système fonctionnel (SUJET p.2).
- **Méthode du cours (source)** : Clone du coéquipier ; le même résultat sur un clone neuf (L1 README §5) ; WRAP p.8.
- **Spécifications** : §11 · **Choix liés** : — · **Exigences** : E20, E2
- **Fichiers produits** : `docs/evidence/fresh_clone.md`
- **Étapes** :
  1. Cloner dans un dossier vide, sans `mlflow.db` ni données.
  2. Suivre le README à la lettre jusqu'à la démo ; noter chaque écart et chaque erreur.
  3. Corriger le README ou le code par pull request, puis refaire les étapes qui avaient échoué.
- **Vérification** :
  - API, surveillance et rejeu fonctionnent sans étape absente du README.
- **Preuve à garder** : `docs/evidence/fresh_clone.md`

### 6.3 · Livrer le dépôt avant lundi 23 h 59

- **Jalon** : J6 · Rendu (lun. 23h59) · **Charge** : 0.5 h · **Statut** : Terminé
- **Démarre** : Après 3.2, 6.2 et 7.3. Gel du code à 20:00, rendu visé à 22:30. (dépendances : 3.2, 6.2, 7.3)
- **Objectif** : Rendre un dépôt complet et accessible, avec un historique où chacun a commité.
- **Exigence du sujet** : Rendu le 23 novembre à 23 h 59 ; accès au dépôt ; chacun commite ; dépôt et historique notés (SUJET p.1–2).
- **Méthode du cours (source)** : Tags (L1 README §1 et §6) ; statuts requis (S2-GHA p.22).
- **Spécifications** : §1 · **Choix liés** : DEC-01 · **Exigences** : E0, E18, E24, E14
- **Fichiers produits** : Tag `v1.0`
- **Étapes** :
  1. `git shortlog -sn` : les quatre membres ont des commits.
  2. CI verte sur `main` ; `git tag v1.0 && git push --tags`.
  3. Rendre le dépôt public (Settings, General, Change visibility).
  4. Envoyer le lien par le canal de rendu du cours.
- **Vérification** :
  - Le lien s'ouvre dans une fenêtre de navigation privée ; tout est fait avant 23:59.
- **Preuve à garder** : Capture du tag et du lien envoyé.

## 7 · Incident simulé

### 7.1 · Intégration sur les vraies données et répétition générale

- **Jalon** : J2 · Composants réels (sam. 19h) · **Charge** : 2 h · **Statut** : Terminé
- **Démarre** : Après 1.1, 1.2, 2.1, 3.1, 4.1 et 4.2. (dépendances : 1.1, 1.2, 2.1, 3.1, 4.1, 4.2)
- **Objectif** : Passer du jeu synthétique aux vraies données, mettre v1 en production, puis vérifier que février ne déclenche rien et que mars déclenche `InputDrift`.
- **Exigence du sujet** : Run avec paramètres, métriques, commit et empreinte des données ; données sous DVC ; modèles dans le Registry ; le système remarque la dérive (SUJET p.1) ; démo avec une alerte de dérive (SUJET p.2).
- **Méthode du cours (source)** : Enchaînement du lab 1 : données sous DVC, `train.py`, `register.py`, score (L1 README §1–4) ; récit d'incident et couches qui réagissent (S4 p.48–50) ; états pending puis firing (S4 p.43).
- **Spécifications** : §4, §5, §11, §14 · **Choix liés** : DEC-02, DEC-12, DEC-15 · **Exigences** : E1, E2, E3, E6, E12, E21
- **Fichiers produits** : `data/features.parquet.dvc`, run et version 1 dans MLflow, `docs/evidence/mae_par_semaine.csv`, `docs/evidence/repetition/`
- **Étapes** :
  1. `uv run python download.py`, puis `uv run python build_dataset.py` ; si ce n'est pas déjà fait en 1.2, `dvc add`, commit des pointeurs, `dvc push`.
  2. Commiter tout le code en cours, pour que `git_dirty` vaille False ; puis `uv run python train.py` et `uv run python register.py RUN_ID production`.
  3. `uv run python evaluate.py production` (tableau MAE par semaine de février à fin mars), puis `git tag data-v1 && git push --tags`.
  4. Lancer les terminaux 1 à 3 de la section 11 : MLflow, API sur v1, stack.
  5. `uv run python replay.py --start 2020-02-17 --end 2020-02-29` : le PSI reste sous 0,25 et aucune alerte ne se déclenche. Si le PSI dépasse 0,25, appliquer le plan de repli de la section 14, puis recommencer.
  6. `uv run python replay.py --start 2020-03-01 --end 2020-03-31` : noter la date simulée où le PSI passe 0,25 ; `InputDrift` passe de pending à firing sur `http://localhost:9093`.
- **Vérification** :
  - La version 1 porte l'alias `production` ; son run a un `data_md5` égal à celui de `data/features.parquet.dvc` et `git_dirty` = False.
  - Captures horodatées du PSI de février, du PSI de mars et de l'alerte firing ; `mae_par_semaine.csv` rangé dans `docs/evidence/`.
- **Preuve à garder** : `docs/evidence/repetition/` et `docs/evidence/mae_par_semaine.csv`

### 7.2 · Jouer l'incident complet et garder les preuves

- **Jalon** : J4 · Incident joué (dim. 21h) · **Charge** : 1.5 h · **Statut** : Terminé
- **Démarre** : Après 5.1, 5.2 et 7.1. (dépendances : 5.1, 5.2, 7.1)
- **Objectif** : Dérive injectée, détection, réentraînement, promotion puis rollback chronométré, avec une preuve à chaque étape.
- **Exigence du sujet** : On injecte une dérive, le système la remarque, on réagit par réentraînement ou rollback (SUJET p.1).
- **Méthode du cours (source)** : Attendus du projet : période de dérive injectée, le pipeline remarque seul, on montre l'alerte et le run (S5 p.33) ; chaîne et gate (S5 p.24–25, 31) ; rollback en moins de 5 minutes (S6 p.36).
- **Spécifications** : §9, §12, §14 · **Choix liés** : DEC-15, EC-11 · **Exigences** : E9, E7, E8, E6
- **Fichiers produits** : `docs/evidence/incident/`
- **Étapes** :
  1. Partir propre : supprimer `data/truth.csv`, `data/decisions.jsonl` et `data/promotions.jsonl` ; v1 en `production` ; API relancée ; stack lancée.
  2. Rejouer février (aucune alerte), puis mars (alerte firing) ; captures Grafana et Alertmanager.
  3. `uv run python check_and_retrain.py` : action `retrain` et nouvelle version `@staging` ; captures de la sortie et de MLflow. Si le gate refuse : plan de repli de la section 14.
  4. `uv run python promote.py`, relance de l'API, `curl localhost:8000/health` affiche la nouvelle version ; capture.
  5. Exercice de rollback : `uv run python rollback.py`, relance de l'API, durée affichée ; capture.
  6. Noter pour chaque étape l'heure réelle et la date simulée dans `docs/evidence/incident/chronologie.md`.
- **Vérification** :
  - Chaque étape a sa capture et sa ligne dans la chronologie.
- **Preuve à garder** : `docs/evidence/incident/`

### 7.3 · Rapport d'incident sous forme de revue sans reproche

- **Jalon** : J5 · Gel du code (lun. 20h) · **Charge** : 1.5 h · **Statut** : Terminé
- **Démarre** : Après 7.2. (dépendances : 7.2)
- **Objectif** : Le rapport d'incident demandé par le sujet, appuyé sur les preuves de 7.2.
- **Exigence du sujet** : Rapport d'incident simulé : dérive injectée, détection, réaction (SUJET p.1).
- **Méthode du cours (source)** : Attendus du rapport : chronologie, couche qui a vu en premier, ce qu'on automatiserait ensuite (S5 p.33) ; revue sans reproche (S6 p.42) ; récit d'incident (S4 p.48) ; arbre de décision (S5 p.22).
- **Spécifications** : §13 · **Choix liés** : DEC-18 · **Exigences** : E9
- **Fichiers produits** : `docs/incident_report.md`
- **Étapes** :
  1. Résumé en cinq lignes ; contexte : périodes de `params.yaml`, version servie.
  2. Chronologie (heures réelles et dates simulées) du premier signal à la fin du rollback.
  3. Couche qui a vu en premier (le PSI des entrées) et pourquoi les autres n'ont rien vu.
  4. Décision selon l'arbre du cours (S5 p.22) : pas un bug (toutes les zones baissent ensemble), effet mesuré (`mae_par_semaine.csv`), assez de jours ; réentraînement puis gate.
  5. Ce qui a manqué et ce qu'on automatiserait ensuite : l'exécution nocturne du contrôle, comme le DAG Airflow de S5 p.28–29.
- **Vérification** :
  - Chaque affirmation renvoie à un fichier de `docs/evidence/`.
- **Preuve à garder** : `docs/incident_report.md`

## 8 · Soutenance

### 8.1 · Schéma, diapositives de 10 minutes et script de démo

- **Jalon** : J5 · Gel du code (lun. 20h) · **Charge** : 2.5 h · **Statut** : Terminé
- **Démarre** : Après 0.2 : le schéma, la trame et le script se font à partir des Spécifications ; les captures s'ajoutent après 7.2. (dépendances : 0.2)
- **Objectif** : Le support de l'oral et le déroulé exact de la démo, avec la structure conseillée par le sujet.
- **Exigence du sujet** : 10 à 15 minutes de présentation et 5 de questions ; structure conseillée : problème et schéma, démo, choix et compromis, un mois de plus (SUJET p.2).
- **Méthode du cours (source)** : Exemples de schéma système (S5 p.25 ; S4 p.17) ; états pending puis firing (S4 p.43) ; démo du récit d'incident (S4 p.48).
- **Spécifications** : §2, §12 · **Choix liés** : DEC-18, DEC-15 · **Exigences** : E21
- **Fichiers produits** : `docs/architecture.png`, diapositives, `docs/demo_script.md`
- **Étapes** :
  1. Un seul schéma : TLC → `download.py` → DVC → `build_dataset.py` → `train.py` → MLflow (runs, Registry, alias) → API → Prometheus, Alertmanager, Grafana → `replay.py` et `check_and_retrain.py` → `promote.py` et `rollback.py`.
  2. Diapositives : problème et schéma (1 min 30) ; démo (4 min, section 12) ; choix et compromis (2 min 30 : découpage temporel, PSI sur 24 h, gate en MAE, rollback par alias, ce qui n'est pas fait et pourquoi) ; un mois de plus (1 min).
  3. `docs/demo_script.md` : état de départ (MLflow lancé, v1 en `production`, stack lancée, février déjà rejoué), puis les commandes de la section 12 avec ce qu'on montre à l'écran. Régler aussi `--hours-per-second` pour que l'alerte arrive en moins de 2 minutes.
  4. Après 7.2, ajouter les captures de l'incident, qui servent aussi de secours si la démo échoue.
- **Vérification** :
  - Répétition chronométrée en 10 minutes au plus ; la démo du script tient en 4 minutes.
- **Preuve à garder** : Fichier des diapositives et `docs/demo_script.md`.

### 8.2 · Préparer les questions : chacun explique sa partie aux autres

- **Jalon** : J5 · Gel du code (lun. 20h) · **Charge** : 3 h · **Statut** : Terminé
- **Démarre** : Après 7.2. (dépendances : 7.2)
- **Objectif** : Que chacun puisse répondre sur n'importe quelle partie et défendre un choix sans préparation.
- **Exigence du sujet** : Le jury peut interroger n'importe quel membre sur n'importe quelle partie ; chacun défend un choix technique sans préparation, 10 % (SUJET p.2).
- **Méthode du cours (source)** : Exercices du wrap-up : critique d'un plan, étude de cas (WRAP p.43–47).
- **Spécifications** : toutes · **Choix liés** : — · **Exigences** : E22, E24
- **Fichiers produits** : `docs/qa_prep.md`
- **Étapes** :
  1. Séance de 45 minutes à quatre : chaque partie expliquée en 8 minutes par qui l'a faite (données, modèle, API, surveillance, réaction).
  2. `docs/qa_prep.md` : questions probables et réponses courtes (pourquoi un découpage temporel, pourquoi le PSI et pourquoi 0,25, pourquoi la MAE, comment marche le gate, pourquoi un rollback par alias, pourquoi ni Kubernetes ni Airflow).
  3. Chacun s'entraîne sur deux choix qu'il n'a pas faits lui-même.
- **Vérification** :
  - Chacun répond à trois questions sur des parties qu'il n'a pas faites.
- **Preuve à garder** : `docs/qa_prep.md`

### 8.3 · Vidéo de secours, répétition chronométrée et soutenance

- **Jalon** : J7 · Soutenance (mar.) · **Charge** : 2.5 h · **Statut** : En cours
- **Démarre** : Après 7.2 et 8.1. La vidéo se tourne dès que le code est gelé, la répétition le mardi matin. (dépendances : 7.2, 8.1)
- **Objectif** : Arriver à la soutenance avec une démo répétée et une vidéo de secours testée.
- **Exigence du sujet** : Démo en direct et plan de secours (SUJET p.2) ; soutenance le 24 novembre (SUJET p.1–2).
- **Méthode du cours (source)** : États pending puis firing (S4 p.43) ; démo du récit d'incident (S4 p.48).
- **Spécifications** : §12 · **Choix liés** : DEC-15 · **Exigences** : E21, E23, E0
- **Fichiers produits** : Vidéo de la démo
- **Étapes** :
  1. Enregistrer une vidéo de la démo complète en suivant `docs/demo_script.md`, lisible hors ligne.
  2. Répétition complète et chronométrée sur l'ordinateur de démo.
  3. Vérifier que la vidéo de secours se lance hors ligne.
- **Vérification** :
  - 10 minutes au plus ; démo ou vidéo fonctionnelle.
- **Preuve à garder** : Vidéo de la démo.
