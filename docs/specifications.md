# Spécifications du projet : tout est fixé

> **Tout est fixé ici : on ne rediscute rien, on code contre ce contrat.** Chaque tâche de la base « Tâches » renvoie à ces sections. Une copie va dans le dépôt (`docs/specifications.md`, tâche 0.2, avec la liste des tâches dans `docs/taches.md`). Les choix suivent les labs du cours ; les sources sont indiquées entre parenthèses.

## 1. Dépôt et environnement

- Dépôt GitHub **mlops-taxi**, privé pendant le travail, rendu public le lundi 23 novembre vers 22:30 (tâche 6.3).
- Une branche par tâche (`t1-2-build-dataset`), une pull request vers `main`. Dès que la CI existe (3.2), elle doit être verte avant la fusion. Chaque message de commit commence par le numéro de la tâche : `[1.2] build_dataset: lags et split`.
- Python 3.12 et uv (S2-UV p.4–11). Commandes du socle :

```bash
uv init --python 3.12 && rm main.py
uv add pandas pyarrow scikit-learn mlflow fastapi "uvicorn[standard]" prometheus-client httpx requests pyyaml dvc
uv add --dev pytest
```

- Ajouter à `pyproject.toml`, pour que les tests importent les scripts de la racine :

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

- Toutes les commandes se lancent depuis la racine du dépôt, avec `uv run`. Chaque script lit ses variables avec `os.getenv(NOM, valeur du contrat)`, comme L1 `train.py` l.67.

## 2. Arborescence

Comme dans les labs, les scripts sont à la racine (L1 : `train.py`, `register.py` ; S5 p.27 : `drift.py`, `check_and_retrain.py`, `policy.yaml`).

```
mlops-taxi/
├── README.md  pyproject.toml  uv.lock  params.yaml  policy.yaml  .env.example  .gitignore
├── make_synthetic.py      0.2  jeu synthétique au format de features.parquet
├── download.py            1.1  télécharge les Parquet TLC dans data/raw/
├── build_dataset.py       1.2  écrit data/features.parquet et data/zones.json
├── train.py               2.1  fit(), mae(), baseline_mae(), data_md5(), log_model_run()
├── register.py            2.1  register(run_id, alias)
├── evaluate.py            2.1  MAE par semaine d'une version
├── drift.py               0.2  reference_bins(), make_reference(), psi()
├── replay.py              4.2  rejoue une période vers l'API, écrit data/truth.csv
├── check_and_retrain.py   5.2  decide() + réentraînement + gate
├── promote.py             5.1  @staging devient @production
├── rollback.py            5.1  @production revient à la version précédente
├── app/main.py            3.1  API FastAPI, métriques et PSI glissant
├── monitoring/            4.1  stack du lab 4 adaptée
├── tests/                 0.2, 1.2, 2.1, 3.2, 5.2
├── docs/                  specifications.md, taches.md, data.md, runbook.md, incident_report.md, architecture.png, evidence/
└── data/                  ignoré par Git, sauf les pointeurs .dvc
```

## 3. Fichiers de configuration (contenu exact)

`params.yaml` :

```yaml
data:
  months: ["2020-01", "2020-02", "2020-03"]
  url: "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{month}.parquet"
  raw_dir: data/raw
  features: data/features.parquet
  zones: data/zones.json
  n_zones: 20
split:
  train: ["2020-01-08 00:00", "2020-02-16 23:00"]
  valid: ["2020-02-17 00:00", "2020-02-29 23:00"]
  replay: ["2020-03-01 00:00", "2020-03-31 23:00"]
features: [zone, hour, dow, lag_1h, lag_24h, lag_168h]
target: y
model:
  max_iter: 200
  learning_rate: 0.1
  random_state: 42
mlflow:
  experiment: taxi-demand
  model_name: taxi-demand
```

`policy.yaml` (seuils du cours, S5 p.15 et p.24–32) :

```yaml
drift:
  features: [lag_1h, lag_24h]
  bins: 10
  window: 480        # 24 h x 20 zones
  every: 20          # recalcul toutes les 20 prédictions
  psi_watch: 0.10
  psi_act: 0.25
retrain:
  window_days: 7     # jours rejoués regardés
  holdout_days: 2    # derniers jours, réservés au gate
  min_new_days: 3
  cooldown_days: 7
  min_gain: 0.05     # le candidat doit réduire la MAE d'au moins 5 %
```

`.env.example` (copié en `.env`, jamais commité ; L2 README « Secrets ») :

```
MLFLOW_TRACKING_URI=http://127.0.0.1:5001
MODEL_NAME=taxi-demand
MODEL_ALIAS=production
API_URL=http://127.0.0.1:8000
```

`.gitignore` :

```
.venv/
__pycache__/
.env
mlflow.db
mlartifacts/
mlruns/
data/*
!data/*.dvc
!data/.gitignore
```

## 4. Données

- Source : NYC Taxi and Limousine Commission (TLC), Trip Record Data, `https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page`, à citer dans le README et `docs/data.md`. Fichiers : `yellow_tripdata_2020-01.parquet`, `-02`, `-03`.
- Colonnes lues : `tpep_pickup_datetime`, `PULocationID`. Heure locale de New York, sans conversion.
- On garde les trajets du 2020-01-01 00:00 au 2020-03-31 23:59 (les fichiers contiennent quelques dates aberrantes).
- Zones : les 20 `PULocationID` les plus fréquents sur la période train, écrits dans `data/zones.json` (liste d'entiers).
- Une ligne par zone et par heure, du 2020-01-01 00:00 au 2020-03-31 23:00 ; une heure sans trajet vaut 0. L'heure 02:00 du 8 mars 2020 n'existe pas (passage à l'heure d'été) : elle vaut 0, c'est normal.
- `data/features.parquet`, colonnes dans cet ordre :

| Colonne | Type | Définition |
| --- | --- | --- |
| ts | datetime64 | début de l'heure à prédire |
| zone | int64 | `PULocationID` |
| hour | int64 | heure de ts (0 à 23) |
| dow | int64 | jour de ts (lundi = 0) |
| lag_1h | float64 | prises en charge de la zone entre ts − 1 h et ts |
| lag_24h | float64 | même heure, la veille |
| lag_168h | float64 | même heure, une semaine avant |
| y | float64 | prises en charge de la zone entre ts et ts + 1 h |
| split | str | train, valid ou replay selon `params.yaml` ; les heures avant le 2020-01-08 sont supprimées |

- Taille attendue : 20 zones × 2 016 heures = 40 320 lignes.
- DVC : `data/raw` (dossier), `data/features.parquet` et `data/zones.json` ; remote local `../dvc-store`, un dossier à côté du dépôt (L1 README §1).

## 5. MLflow et modèle

- Lancement : `uv run mlflow ui --port 5001 --backend-store-uri sqlite:///mlflow.db --artifacts-destination ./mlartifacts` (L1 README : le port 5000 est pris par AirPlay sur macOS).
- Expérience `taxi-demand` ; modèle enregistré `taxi-demand` ; alias `production` (servi par l'API) et `staging` (candidat).
- Modèle : `Pipeline([("pre", ColumnTransformer([("zone", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["zone"])], remainder="passthrough")), ("reg", HistGradientBoostingRegressor(max_iter=200, learning_rate=0.1, random_state=42))])`, entraîné sur `split == "train"` (L1 `train.py` l.40–50, en régression). `sparse_output=False` : avec 20 zones, la sortie du one-hot serait creuse et `HistGradientBoostingRegressor` la refuse (`TypeError`) ; ajout validé le 20/11 (tâche 2.1, PR #2).
- Chaque run contient :
  - paramètres : `model.*` de `params.yaml` et les dates de split ;
  - métriques : `mae_valid` et `mae_baseline_valid` (baseline : prédire `lag_168h`, S1-INTRO p.28) ;
  - tags : `git_commit`, `git_dirty`, `data_md5` (lu dans le pointeur `.dvc`, L1 `train.py` l.56–62) ;
  - artefacts : `model` (`mlflow.sklearn.log_model` avec signature, input_example et `skops_trusted_types`, L1 l.83–90) et `reference.json`.
- `reference.json` : pour chaque variable de `policy.drift.features`, `{"edges": [...], "shares": [...]}` calculés sur les lignes d'entraînement par `drift.make_reference`.

## 6. Fonctions partagées (contrat Python)

| Fichier | Fonctions | Ligne de commande |
| --- | --- | --- |
| `make_synthetic.py` | `make_synthetic(days=21, zones=(132, 161, 237), seed=0) -> DataFrame` au format de features.parquet (14 premiers jours train, 7 derniers valid) | `uv run python make_synthetic.py` écrit `data/synthetic.parquet` |
| `train.py` | `fit(params, df) -> Pipeline` ; `mae(model, df) -> float` ; `baseline_mae(df) -> float` ; `data_md5(path) -> str` ; `log_model_run(model, params, metrics, reference, data_path) -> run_id` | `uv run python train.py [--data data/synthetic.parquet]` |
| `register.py` | `register(run_id, alias) -> version` | `uv run python register.py RUN_ID [alias]` (alias par défaut : production) |
| `drift.py` | `reference_bins(values, bins=10) -> dict` ; `make_reference(df, features, bins=10) -> dict` ; `psi(ref, sample) -> float` (formule de L4 `app.py` l.59–63) | — |
| `check_and_retrain.py` | `decide(psi_max, days, days_since_retrain, policy) -> "wait" \| "watch" \| "cooldown" \| "retrain"` | `uv run python check_and_retrain.py` |

## 7. API (contrat HTTP)

- Lancement : `uv run uvicorn app.main:app --port 8000`, avec un seul worker comme au lab 4.
- Le modèle est chargé au démarrage depuis `models:/taxi-demand@production`, avec son `reference.json` (S3 p.26 ; L1 `score.py` l.18). Changer d'alias impose de relancer l'API (S3 p.41).
- `GET /health` : 200 `{"status": "ok", "model_version": "1"}` ; 503 `{"status": "degraded", "detail": "model not loaded"}` sans modèle (L3 `app.py` l.118–123).
- `POST /v1/predict` :
  - requête : `{"zone": 237, "ts": "2020-03-02T08:00:00", "lag_1h": 112.0, "lag_24h": 98.0, "lag_168h": 120.0}` ; champ inconnu, zone hors de 1–265 ou lag négatif : 422 ;
  - réponse : `{"zone": 237, "ts": "2020-03-02T08:00:00", "prediction": 104.3, "model_version": "1"}` ;
  - `hour` et `dow` sont calculés par l'API à partir de `ts`.
- `GET /metrics/` (Prometheus, monté comme L4 `app.py` l.80) : `taxi_request_seconds` (histogram, label `endpoint`), `taxi_predictions_total` (counter, label `model_version`), `taxi_input_psi` (gauge, label `feature`, mise à 0 au démarrage).

## 8. Surveillance

- `monitoring/` est une copie de la stack du lab 4 (Prometheus v3.5.0, Alertmanager v0.28.1, Grafana 12.1.0) : `cd monitoring && docker compose up -d`.
- Prometheus : job `taxi-api`, `metrics_path: /metrics/`, cible `host.docker.internal:8000`, toutes les 5 s.
- `monitoring/prometheus/alerts.yml` :

```yaml
groups:
  - name: taxi-model
    rules:
      - alert: ApiDown
        expr: up{job="taxi-api"} == 0
        for: 30s
        labels: { severity: page }
        annotations:
          summary: "the taxi API does not answer /metrics"
      - alert: InputDrift
        expr: taxi_input_psi > 0.25
        for: 1m
        labels: { severity: page }
        annotations:
          summary: "{{ $labels.feature }} drifted (PSI {{ $value | printf \"%.2f\" }})"
```

- Grafana (`http://localhost:3000`) : tableau de bord « Taxi API » avec trois panneaux : requêtes par seconde, latence P95, PSI par variable avec le seuil 0,25. Prometheus `http://localhost:9090`, Alertmanager `http://localhost:9093`.

## 9. Rejeu, vérité terrain et réaction

- `uv run python replay.py --start 2020-02-17 --end 2020-02-29 --hours-per-second 10` : pour chaque heure de la plage (jours inclus), une requête par zone ; 10 heures simulées par seconde.
- `data/truth.csv` (lignes ajoutées, en-tête si le fichier est nouveau) : `ts,zone,hour,dow,lag_1h,lag_24h,lag_168h,y,prediction,model_version`.
- `uv run python check_and_retrain.py` : maintenant = dernier `ts` de `truth.csv` ; fenêtre = 7 derniers jours ; `decide()`. Si la décision est « retrain » :
  - le candidat est entraîné sur la fenêtre sauf les 2 derniers jours ;
  - il est toujours journalisé dans MLflow (un run) ;
  - il n'est enregistré avec l'alias `staging` que si sa MAE sur les 2 derniers jours est inférieure d'au moins 5 % à celle de la production.
- `data/decisions.jsonl`, une ligne par exécution : `{"now", "psi", "days", "action", "mae_production", "mae_candidate", "run_id", "version"}`, avec `action` parmi wait, watch, cooldown, retrain, refused.
- `uv run python promote.py` : `@production` prend la version `@staging` ; une ligne `{"ts", "from", "to"}` est ajoutée à `data/promotions.jsonl`.
- `uv run python rollback.py [VERSION]` : `@production` revient à VERSION, ou au « from » de la dernière promotion. Le script attend que `/health` affiche cette version après la relance de l'API, puis affiche la durée.

## 10. Tests et CI

- `uv run pytest -q` lance `tests/test_features.py` (1.2), `test_model.py` (2.1), `test_drift.py` (0.2), `test_api.py` et `conftest.py` (3.2), `test_check.py` (5.2).
- `.github/workflows/ci.yml` (S2-UV p.11) :

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v9.0.0
        with:
          version: "0.13.5"
          enable-cache: true
      - run: uv sync --locked
      - run: uv run pytest -q
```

## 11. Terminaux pendant le développement et la démo

| Terminal | Commande | Adresse |
| --- | --- | --- |
| 1 | `uv run mlflow ui --port 5001 --backend-store-uri sqlite:///mlflow.db --artifacts-destination ./mlartifacts` | `http://127.0.0.1:5001` |
| 2 | `uv run uvicorn app.main:app --port 8000` | `http://127.0.0.1:8000/docs` |
| 3 | `cd monitoring && docker compose up -d` | Prometheus 9090, Alertmanager 9093, Grafana 3000 |
| 4 | `replay.py`, `check_and_retrain.py`, `promote.py`, `rollback.py` | — |

## 12. Démo de la soutenance (4 minutes, dans cet ordre)

1. `curl localhost:8000/health` affiche v1, puis `POST /v1/predict` avec l'exemple du contrat.
2. `replay.py --start 2020-03-01 --end 2020-03-31` : dans Grafana le PSI dépasse 0,25, puis `InputDrift` passe de pending à firing dans Alertmanager.
3. `check_and_retrain.py` répond « retrain » : la version 2 apparaît avec l'alias `@staging` dans MLflow.
4. `promote.py`, relance de l'API : `/health` affiche v2.
5. `rollback.py`, relance de l'API : `/health` affiche v1, et la durée est affichée.

Février est rejoué avant la soutenance. La vidéo de secours (8.3) montre la démo complète.

## 13. Hypothèses (à recopier dans le README)

- Le groupe compte quatre membres ; chacun commite.
- La dérive injectée est la période de mars 2020, rejouée dans l'API en marche. Le sujet cite mars 2020 comme période de dérive, et le cours décrit le projet avec « a drift period that you inject » (S5 p.33).
- `check_and_retrain.py` est lancé à la main, comme le script unique du lab (S5 p.33) ; l'alerte, elle, se déclenche seule.
- La grille détaillée annoncée par le sujet n'y figure pas : nous suivons ce qui est écrit.

## 14. Plan de repli (décidé d'avance)

- Si le PSI dépasse 0,25 pendant le rejeu de février : passer `policy.drift.window` à 960 (48 h) et recommencer.
- Si le gate refuse le candidat : passer `retrain.window_days` à 10 et relancer `check_and_retrain.py`. S'il refuse encore, c'est un résultat valable (« Fail at the gate: the old model stays in production », S5 p.24). Pour l'exercice de rollback, enregistrer alors le run du candidat avec `uv run python register.py RUN_ID staging`.
- Si Grafana pose problème : montrer le PSI dans Prometheus (requête `taxi_input_psi`).
- Si le jalon J3 n'est pas atteint dimanche à 18:00 : la CI se limite à pytest en local et la démo s'appuie sur la vidéo.
