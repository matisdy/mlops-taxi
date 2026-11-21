# Script de la démo de soutenance (4 minutes)

Déroulé exact de la démo, dans l'ordre de la section 12 des Spécifications : une requête, une alerte de dérive, un réentraînement avec promotion, puis un rollback chronométré. Le schéma du système est dans `docs/architecture.png`, les diapositives dans `docs/soutenance.pdf`.

Les commandes sont écrites pour macOS et Linux. Sous Windows (PowerShell), remplacer `OMP_NUM_THREADS=1 uv run …` par `$env:OMP_NUM_THREADS=1; uv run …` et `curl` par `curl.exe`.

## 1. Avant la soutenance : l'état de départ (environ 15 minutes)

À faire le matin même, sur la machine de la démo, depuis la racine du dépôt.

1. **Repartir propre**, si une répétition a déjà eu lieu sur cette machine. Sinon, `check_and_retrain.py` répondrait « cooldown » (un réentraînement de moins de 7 jours dans `decisions.jsonl`) et les numéros de version ne seraient plus v1 et v2.
   ```bash
   rm -f data/truth.csv data/decisions.jsonl data/promotions.jsonl
   rm -rf mlflow.db mlartifacts/      # le Registry repart de zéro : la v1 sera bien la version 1
   ```
2. **Terminal 1, MLflow** (laisser tourner) :
   ```bash
   uv run mlflow ui --port 5001 --backend-store-uri sqlite:///mlflow.db --artifacts-destination ./mlartifacts
   ```
3. **Terminal 4, la v1 en production** (si le Registry vient d'être vidé) :
   ```bash
   uv run python train.py                 # affiche mae_valid … et run_id = <RUN_ID>
   uv run python register.py <RUN_ID>     # taxi-demand v1 is now @production
   ```
4. **Terminal 2, l'API** (laisser tourner) :
   ```bash
   OMP_NUM_THREADS=1 uv run uvicorn app.main:app --port 8000
   ```
   Le journal doit afficher `loaded models:/taxi-demand@production (version 1)`.
5. **Terminal 3, la surveillance** :
   ```bash
   cd monitoring && docker compose up -d && cd ..
   ```
   Dans Prometheus (`http://localhost:9090/targets`), la cible `taxi-api` doit être `UP`.
6. **Rejouer février**, la période normale, avant que le jury n'entre :
   ```bash
   uv run python replay.py --start 2020-02-17 --end 2020-02-29
   ```
   Environ 31 s à la vitesse par défaut (10 heures simulées par seconde, Spécifications §9). Dans Grafana, le PSI reste sous 0,25 et aucune alerte ne part.
7. **Ouvrir les onglets**, dans cet ordre :
   - Grafana `http://localhost:3000`, tableau de bord « Taxi API », 15 dernières minutes ;
   - Prometheus `http://localhost:9090/alerts` (règle `InputDrift`) ;
   - Alertmanager `http://localhost:9093` ;
   - MLflow `http://127.0.0.1:5001`, onglet Models, `taxi-demand`.
8. **Disposer l'écran** : le terminal 4 (commandes) et le terminal 2 (API) à gauche, le navigateur à droite. Agrandir la police des terminaux.

## 2. La démo, minute par minute

| Temps | Terminal | Commande | Ce qu'on montre | Ce qu'on dit |
| --- | --- | --- | --- | --- |
| 0:00 | 4 | `curl -s localhost:8000/health` | `{"status":"ok","model_version":"1"}` | « L'API sert la v1, chargée depuis le Registry par son alias `@production`. » |
| 0:15 | 4 | `curl -s -X POST localhost:8000/v1/predict -H 'Content-Type: application/json' -d '{"zone": 237, "ts": "2020-03-02T08:00:00", "lag_1h": 112.0, "lag_24h": 98.0, "lag_168h": 120.0}'` | La prévision et `"model_version": "1"` | « Une requête : la zone 237, l'heure suivante. » |
| 0:30 | 4 | `uv run python replay.py --start 2020-03-01 --end 2020-03-31` | Le terminal compte les jours rejoués ; dans Grafana, le PSI décolle | « On rejoue mars 2020 : la demande s'effondre avec le confinement. » |
| ≈ 1:05 | navigateur | Grafana | Les deux courbes du PSI passent au-dessus de la ligne rouge de 0,25 (vers le 13-14 mars simulé) | « La couche des entrées voit la dérive en premier : les lags tombent dans la classe la plus basse. » |
| ≈ 1:10 | navigateur | Prometheus, `/alerts` | `InputDrift` en **pending** (orange) | « La règle attend une minute au-dessus du seuil, pour ne pas sonner sur un pic. » |
| ≈ 2:10 | navigateur | Prometheus puis Alertmanager | `InputDrift` en **firing** (rouge), puis l'alerte dans Alertmanager | « L'alerte est partie seule, sans personne. » |
| 2:15 | 4 | `uv run python check_and_retrain.py` | `"action": "retrain"`, MAE du candidat contre la production, `taxi-demand v2 is now @staging` ; dans MLflow, la v2 avec l'alias `@staging` | « Pas un bug, ça fait mal, assez de jours : on réentraîne. Le candidat passe le gate : il bat la production d'au moins 5 %. » |
| 2:50 | 4 | `uv run python promote.py` | `taxi-demand v2 is now @production (was v1)` puis `Relancer l'API` | « La promotion reste une décision humaine. » |
| 3:00 | 2 | Ctrl+C, puis `OMP_NUM_THREADS=1 uv run uvicorn app.main:app --port 8000` | `loaded models:/taxi-demand@production (version 2)` | « L'API ne charge le modèle qu'au démarrage, d'où la relance. » |
| 3:10 | 4 | `curl -s localhost:8000/health` | `"model_version":"2"` | |
| 3:20 | 4 | `uv run python rollback.py` | `taxi-demand v1 is now @production`, puis `Relancer l'API` | « Si la v2 se comportait mal : retour arrière par l'alias. » |
| 3:25 | 2 | Ctrl+C, puis la même commande de lancement | `loaded … (version 1)` | |
| 3:40 | 4 | (rien à taper) | `/health shows v1 after … s` | « Retour à la v1 en quelques secondes ; l'objectif du cours est moins de 5 minutes. » |

Les commandes viennent des Spécifications : §7 pour l'API et la requête d'exemple, §9 pour le rejeu et la réaction, §11 pour les terminaux. Les sorties attendues sont celles des scripts, déjà vues pendant l'incident de la tâche 7.2 (`docs/evidence/`).

## 3. Réglage de `--hours-per-second`

La roadmap demande que l'alerte arrive en moins de 2 minutes. Le calcul :

- L'alerte part quand le PSI reste au-dessus de 0,25 pendant 1 minute (`for: 1m`, Spécifications §8), plus jusqu'à 10 s de délai : 5 s entre deux lectures de Prometheus et 5 s entre deux évaluations de la règle.
- Pendant l'incident de la 7.2, le PSI a franchi durablement 0,25 vers le 13-14 mars simulé, soit environ 324 heures après le début du rejeu (`docs/incident_report.md` §2).
- À **2 heures simulées par seconde**, la vitesse de la 7.2, le seuil est franchi après environ 2 min 45 et l'alerte part vers 3 min 45 : c'est trop long pour une démo de 4 minutes.
- À **10 heures simulées par seconde**, la valeur par défaut de `replay.py` et celle du §9, le seuil est franchi après environ 32 s et l'alerte part vers 1 min 35 à 1 min 45 : **moins de 2 minutes**. On garde donc la valeur par défaut, sans option.
- Le rejeu de mars (744 heures) dure alors environ 75 s et se termine avant le firing. Ce n'est pas un problème : la jauge `taxi_input_psi` garde sa dernière valeur (environ 7,9) tant qu'aucune prédiction n'arrive, donc la règle continue de la voir au-dessus du seuil.

Ces durées sont calculées à partir de la 7.2, pas encore mesurées à 10 heures par seconde. La répétition chronométrée de la tâche 8.3 doit les confirmer. Si l'alerte n'est pas partie à 2:15, enchaîner quand même sur `check_and_retrain.py`, qui ne dépend pas de l'alerte, et revenir sur Alertmanager après la promotion.

## 4. Si la démo échoue

- **Grafana ne répond pas** : montrer le PSI dans Prometheus avec la requête `taxi_input_psi` (Spécifications §14).
- **Le gate refuse le candidat** : c'est un résultat valable (« the old model stays in production », S5 p.24). Pour enchaîner sur le rollback, enregistrer le candidat à la main avec `uv run python register.py <RUN_ID> staging`, le `run_id` étant dans la sortie (Spécifications §14).
- **Une commande échoue** : passer sur les captures de l'incident réel, à la fin des diapositives (annexe). Elles viennent de `docs/evidence/` : PSI de mars, alerte en firing, décision de réentraîner, v2 en `@staging`, `/health` en v2, rollback en 22,4 s.
- **Tout échoue** : la vidéo de secours de la tâche 8.3.

## 5. Après la démo

Arrêter l'API et MLflow (Ctrl+C), puis `cd monitoring && docker compose down`. Avant une nouvelle répétition, refaire l'étape 1 de ce script.
