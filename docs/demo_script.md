# Script de la démo de soutenance (4 minutes)

Déroulé exact de la démo, dans l'ordre de la section 12 des Spécifications : une requête, une alerte de dérive, un réentraînement avec promotion, puis un rollback chronométré. Le schéma du système est dans `docs/architecture.png`, les diapositives dans `docs/soutenance.pdf`. Qui tape quoi, et à quel moment : `docs/fiche_passage.md`.

Les commandes sont écrites pour macOS et Linux. Sous Windows (PowerShell), remplacer `OMP_NUM_THREADS=1 uv run …` par `$env:OMP_NUM_THREADS=1; uv run …` et `curl` par `curl.exe`.

## 1. Avant la soutenance : l'état de départ (environ 15 minutes)

À faire le matin même, sur la machine de la démo, depuis la racine du dépôt. La répétition du 23/11 a utilisé un MLflow à part, sur le port 5012. Mardi matin, tout ce §1 se fait sur le port 5001, dans des terminaux neufs. Les commandes prennent environ 1 minute de machine (63 s mesurées le 23/11 : MLflow 2 s, `train.py` 17,9 s, `register.py` 2,4 s, API 7,0 s, stack 1,4 s, février 32,1 s). Le reste est le temps de taper les commandes et d'ouvrir les onglets. Février se rejoue au moins 15 minutes avant la démo (étape 7).

1. **Vérifier les terminaux et les données.** Dans les terminaux 4 et 2, `echo $MLFLOW_TRACKING_URI` doit afficher une ligne vide ou `http://127.0.0.1:5001`. La répétition du 23/11 visait le port 5012 : si un terminal y pointe encore, `train.py`, `register.py` et l'API viseraient le mauvais Registry. Remplacer un tel terminal par un terminal neuf. Les fichiers de données ne sont pas dans Git, seuls leurs pointeurs `.dvc` le sont.
   ```bash
   echo $MLFLOW_TRACKING_URI                  # terminaux 4 et 2 : ligne vide ou http://127.0.0.1:5001
   ls data/features.parquet data/zones.json   # les deux fichiers doivent être listés
   uv run dvc pull                            # seulement s'il en manque un : 1 s sur le Mac de la démo
   ```
   `uv run dvc pull` les rapatrie depuis le remote local `../dvc-store`. Sur le Mac de la démo, où les données manquaient, il a affiché `6 files fetched and 5 files added`.
2. **Repartir propre**, obligatoire avant la démo. La veille de la soutenance, le Registry du port 5001 contenait encore les deux versions du jalon J1, entraînées sur le jeu synthétique, dont la v1 en `@production` : sans cette étape, l'API servirait le modèle synthétique et `check_and_retrain.py` créerait une v3. Après une répétition, c'est pareil : `check_and_retrain.py` répondrait « cooldown » (un réentraînement de moins de 7 jours dans `decisions.jsonl`) et les numéros de version ne seraient plus v1 et v2.

   D'abord, arrêter MLflow s'il tourne déjà : sinon, le serveur garde ouverte la base qu'on supprime. Deux façons : Ctrl+C dans son terminal (terminal 1) ; s'il tourne sans terminal, lancé en arrière-plan, `lsof -ti tcp:5001 -sTCP:LISTEN | xargs kill`. Arrêter de la même façon une API restée lancée, qui garde le modèle chargé à son démarrage : Ctrl+C dans le terminal 2, ou `lsof -ti tcp:8000 -sTCP:LISTEN | xargs kill`. Ensuite :
   ```bash
   lsof -i tcp:5001 -sTCP:LISTEN      # aucune ligne : MLflow est arrêté
   rm -f data/truth.csv data/decisions.jsonl data/promotions.jsonl
   rm -rf mlflow.db mlartifacts/      # le Registry repart de zéro : la v1 sera bien la version 1
   ```
   Sans `-sTCP:LISTEN`, `lsof` listerait aussi les connexions du navigateur au port 5001.
3. **Terminal 1, MLflow** (laisser tourner) :
   ```bash
   uv run mlflow ui --port 5001 --backend-store-uri sqlite:///mlflow.db --artifacts-destination ./mlartifacts
   ```
   L'interface répond en 2 à 7 s (7 s sur le clone neuf de la 6.2, `docs/evidence/fresh_clone.md`) : attendre la ligne `Uvicorn running on http://127.0.0.1:5001 (Press CTRL+C to quit)` avant de lancer `train.py`.
4. **Terminal 4, la v1 en production** (le Registry vient d'être vidé). `git status --short` ne doit rien afficher : sinon, le run de la v1 porte le tag `git_dirty` à `True`.
   ```bash
   git status --short                     # rien : le code est celui du dernier commit
   uv run python train.py                 # 8 à 18 s
   uv run python register.py <RUN_ID>     # 2,4 s
   ```
   La sortie de `train.py` se termine ainsi, après les lignes de MLflow « View run … » et « View experiment … » :
   ```text
   mae_valid 28.4983 | mae_baseline_valid 47.8886
   run_id = <RUN_ID>
   ```
   Le `<RUN_ID>` fait 32 caractères. Sur un Registry vide, `register.py` affiche d'abord `Successfully registered model 'taxi-demand'.`, parmi les messages de MLflow, puis se termine par :
   ```text
   Created version '1' of model 'taxi-demand'.
   taxi-demand v1 is now @production
   ```
5. **Terminal 2, l'API** (laisser tourner) :
   ```bash
   OMP_NUM_THREADS=1 uv run uvicorn app.main:app --port 8000
   ```
   Le journal doit afficher `INFO:     loaded models:/taxi-demand@production (version 1)` ; `/health` répond 4 à 7 s après le lancement. Si la stack de surveillance tourne déjà (étape 6), l'alerte `ApiDown` est en firing dans Prometheus et dans Alertmanager tant que l'API n'est pas lancée. Elle disparaît seule, environ 15 s après le lancement de l'API. Pendant une relance de l'API (promotion, rollback), `ApiDown` peut passer en pending un instant, pas en firing si l'API revient en moins de 30 s (`for: 30s`).
6. **Terminal 3, la surveillance** :
   ```bash
   cd monitoring && docker compose up -d && cd ..
   ```
   Docker Desktop doit être lancé. Si la stack était arrêtée, la commande affiche des lignes `Started` ; si elle tourne déjà, `Running`. Dans Prometheus (`http://localhost:9090/targets`), la cible `taxi-api` doit être `UP`.
7. **Rejouer février**, la période normale, au moins 15 minutes avant la démo :
   ```bash
   uv run python replay.py --start 2020-02-17 --end 2020-02-29
   ```
   32 s à la vitesse par défaut (10 heures simulées par seconde, Spécifications §9). La dernière ligne est `done: ok 6240, errors 0, rows appended to data/truth.csv`.

   Le PSI passe deux fois au-dessus de 0,25, pendant 1 à 3 s : au départ (`lag_24h` jusqu'à 0,57, `lag_1h` à 0,35), puis le 25 au matin (`lag_24h` à 0,38). La cause : un dimanche ou un jour férié (le 17 février 2020) n'a pas le profil d'un jour de semaine. Prometheus peut montrer `InputDrift` en pending pendant une évaluation, pas en firing : le dépassement dure 1 à 3 s, et la règle attend 1 minute au-dessus du seuil (`for: 1m`, S4 p.43). Rien n'arrive dans Alertmanager. À la fin du rejeu, le PSI vaut 0,035 (`lag_1h`) et 0,077 (`lag_24h`) ; ces valeurs restent affichées jusqu'au rejeu de mars. Grafana montre le pic tant qu'il est dans la fenêtre affichée, les 15 dernières minutes : d'où ce rejeu au moins 15 minutes avant la démo. Si quelqu'un voit le pic, on dit « aucune fausse alerte », pas « aucun pic » (§4).
8. **Ouvrir les onglets**, dans cet ordre :
   - Grafana `http://localhost:3000`, tableau de bord « Taxi API », 15 dernières minutes ;
   - Prometheus `http://localhost:9090/alerts` (règle `InputDrift`) ;
   - Alertmanager `http://localhost:9093` ;
   - MLflow `http://127.0.0.1:5001/#/models/taxi-demand` : une seule version, la v1, avec l'alias `@production`.
9. **Disposer l'écran** : le terminal 4 (commandes) et le terminal 2 (API) à gauche, le navigateur à droite. Agrandir la police des terminaux.

## 2. La démo, minute par minute

| Temps | Terminal | Commande | Ce qu'on montre | Ce qu'on dit |
| --- | --- | --- | --- | --- |
| 0:00 | 4 | `curl -s localhost:8000/health` | `{"status":"ok","model_version":"1"}` | « L'API sert la v1, chargée depuis le Registry par son alias `@production`. » |
| 0:15 | 4 | `curl -s -X POST localhost:8000/v1/predict -H 'Content-Type: application/json' -d '{"zone": 237, "ts": "2020-03-02T08:00:00", "lag_1h": 112.0, "lag_24h": 98.0, "lag_168h": 120.0}'` | `{"zone":237,"ts":"2020-03-02T08:00:00","prediction":190.20255820567724,"model_version":"1"}` | « Une requête : la zone 237, l'heure suivante. » |
| 0:30 | 4 | `uv run python replay.py --start 2020-03-01 --end 2020-03-31` | `2020-03-01 to 2020-03-31: 744 hours x 20 zones, 10 hours/s, http://127.0.0.1:8000, Ctrl+C to stop`, puis une ligne par jour simulé (`2020-03-01 sent 480, ok 480, errors 0`…) ; dans Grafana, le PSI décolle | « On rejoue mars 2020 : la demande s'effondre avec le confinement. » |
| ≈ 0:37, puis ≈ 0:51 à 0:54 | navigateur | Grafana | Des pics brefs du PSI, souvent invisibles dans Grafana, qui trace un point toutes les 15 s : le 3 mars simulé (`lag_24h` à 0,29), puis les 9 et 10 mars, après le dimanche 8 (`lag_1h` jusqu'à 0,53). Un dimanche n'a pas le profil d'un jour de semaine | Si un pic se voit : « Un pic ne suffit pas : la règle attend une minute au-dessus du seuil. » |
| ≈ 1:03 à 1:20 | navigateur | Grafana | Le PSI passe 0,25 pour de bon à 1:03 (14 mars simulé). Rester sur Grafana jusqu'à ce que les deux courbes passent la ligne rouge, entre 1:05 et 1:20 (un point toutes les 15 s) | « La couche des entrées voit la dérive en premier : les lags tombent dans la classe la plus basse. » |
| ≈ 1:20 | navigateur | Prometheus, `/alerts` (recharger la page, Cmd+R) | `InputDrift` en **pending** (orange) depuis 1:08, sur les deux variables, jusqu'au firing de 2:08 | « La règle attend une minute au-dessus du seuil, pour ne pas sonner sur un pic. » |
| ≈ 1:46 | 4 | (rien à taper) | `done: ok 14880, errors 0, rows appended to data/truth.csv` ; le PSI reste à 7,88 (`lag_1h`) et 7,76 (`lag_24h`) tant qu'aucune prédiction n'arrive | « À 10 heures simulées par seconde, cette minute vaut 25 jours simulés : c'est un effet du rejeu, pas une règle lente. » |
| ≈ 2:08 | navigateur | Prometheus `/alerts` (recharger la page, Cmd+R), puis Alertmanager (recharger la page, Cmd+R) | `InputDrift` en **firing** (rouge) pour `lag_1h` et `lag_24h`, puis les deux alertes dans Alertmanager, à la même seconde. Alertmanager ne reçoit que le firing, jamais le pending (S4 p.43) | « L'alerte est partie seule, sans personne. » |
| 2:15 | 4 | `uv run python check_and_retrain.py` | En 7 s, après les messages de MLflow, dont `Created version '2' of model 'taxi-demand'.` : la ligne JSON avec `"action": "retrain"`, `"mae_production": 21.6775`, `"mae_candidate": 3.9738` et `"version": "2"`, puis `taxi-demand v2 is now @staging (MAE 3.9738 vs 21.6775 in production)`. Dans MLflow (`http://127.0.0.1:5001/#/models/taxi-demand`, recharger la page, Cmd+R), la v2 avec l'alias `@staging` | « Pas un bug, ça fait mal, assez de jours : on réentraîne. Le candidat passe le gate : il bat la production d'au moins 5 %. » |
| 2:50 | 4 | `uv run python promote.py` | `taxi-demand v2 is now @production (was v1)` puis `Relancer l'API`, en 2 s | « La promotion reste une décision humaine. » |
| 3:00 | 2 | Ctrl+C, puis `OMP_NUM_THREADS=1 uv run uvicorn app.main:app --port 8000` | `INFO:     loaded models:/taxi-demand@production (version 2)` ; `/health` répond en v2 environ 5 s après la relance | « L'API ne charge le modèle qu'au démarrage, d'où la relance. » |
| 3:10 | 4 | `curl -s localhost:8000/health` | `{"status":"ok","model_version":"2"}` | |
| 3:20 | 4 | `uv run python rollback.py` | `taxi-demand v1 is now @production`, puis `Relancer l'API` environ 3 s après Entrée ; le script attend que `/health` affiche la v1 | « Si la v2 se comportait mal : retour arrière par l'alias. » |
| 3:25 | 2 | Ctrl+C, puis la même commande de lancement | `INFO:     loaded models:/taxi-demand@production (version 1)` | |
| ≈ 3:30 | 4 | (rien à taper) | `/health shows v1 after … s` : `8.5 s` à la répétition, avec 3 s pour changer de terminal ; le chiffre dépend de la vitesse au clavier | « Retour à la v1 en quelques secondes ; l'objectif du cours est moins de 5 minutes. » (S6 p.36) |

Les repères de 0:30 à 2:08 ont été mesurés d'une traite pendant la répétition du 23/11 (`docs/evidence/repetition/t8.3_durees.md`, §2). Les autres temps sont des créneaux : avec les durées mesurées (décision 7,3 s, promotion 2,2 s, relance 5,4 s, rollback 8,5 s), ils tiennent en 4 minutes. La répétition a joué ces étapes plus lentement, de 12:44 à 12:49, pour prendre les captures.

Les commandes viennent des Spécifications : §7 pour l'API et la requête d'exemple, §9 pour le rejeu et la réaction, §11 pour les terminaux. Les sorties et les durées sont celles de cette répétition ; les mêmes sorties avaient été vues pendant l'incident de la tâche 7.2 (`docs/evidence/incident/`).

## 3. Réglage de `--hours-per-second`

La roadmap demande que l'alerte arrive en moins de 2 minutes. Le calcul :

- L'alerte part quand le PSI reste au-dessus de 0,25 pendant 1 minute (`for: 1m`, Spécifications §8), plus jusqu'à 10 s de délai : 5 s entre deux lectures de Prometheus et 5 s entre deux évaluations de la règle.
- Pendant l'incident de la 7.2, le PSI a franchi durablement 0,25 vers le 13-14 mars simulé (`docs/incident_report.md` §2), soit environ 324 heures après le début du rejeu.
- À **2 heures simulées par seconde**, la vitesse de la 7.2, le seuil est franchi après environ 2 min 45 et l'alerte part vers 3 min 45 : c'est trop long pour une démo de 4 minutes.
- À **10 heures simulées par seconde**, la valeur par défaut de `replay.py` et celle du §9, le seuil est franchi après environ 32 s et l'alerte part vers 1 min 35 à 1 min 45 : **moins de 2 minutes**. On garde donc la valeur par défaut, sans option.
- Le rejeu de mars (744 heures) dure alors environ 75 s et se termine avant le firing. Ce n'est pas un problème : la jauge `taxi_input_psi` garde sa dernière valeur (environ 7,9) tant qu'aucune prédiction n'arrive, donc la règle continue de la voir au-dessus du seuil.

Ces durées ont été mesurées pendant la répétition chronométrée du 23/11, sur le Mac de la démo (`docs/evidence/repetition/t8.3_durees.md`). Cette répétition a utilisé un MLflow à part, sur le port 5012, pour ne pas toucher au serveur officiel ; mardi matin, la démo repart du §1, sur le port 5001. Le temps t part du lancement du rejeu de mars, placé à 0:30 dans la démo.

| Repère | t | Démo |
| --- | --- | --- |
| Pic bref du PSI (`lag_24h` à 0,29, 3 mars simulé) | + 7 s | 0:37 |
| Pic bref des 9 et 10 mars (`lag_1h` jusqu'à 0,53) | + 21 à 24 s | 0:51 à 0:54 |
| Premier pending, bref, sur `lag_24h` | + 27,8 s | 0:58 |
| PSI au-dessus de 0,25 pour de bon (14 mars simulé) | + 33 s | 1:03 |
| `InputDrift` en pending continu, sur les deux variables | + 37,8 s | 1:08 |
| Fin du rejeu (commande de 75,9 s) ; PSI à 7,88 et 7,76 | + 75,8 s | 1:46 |
| `InputDrift` en firing, 60 s après le début du pending continu | + 97,8 s | 2:08 |
| Les deux alertes dans Alertmanager | + 98,0 s | 2:08 |

Le calcul se vérifie : le seuil est franchi à t = 33 s (32 s calculées) et le firing arrive à t = 98 s, soit 1 min 38 après le lancement du rejeu : moins de 2 minutes. Sur son clone neuf, l'équipe de la tâche 6.2 a mesuré le firing dans Alertmanager à t = 100,7 s (2:11 dans la démo), avec un pending continu dès t = 40 s (`docs/evidence/fresh_clone.md`, O2).

Si l'alerte n'est pas partie à 2:15, enchaîner quand même sur `check_and_retrain.py`, qui ne dépend pas de l'alerte. Revenir sur Alertmanager juste après `promote.py`, avant de relancer l'API : chaque relance remet le PSI à 0, et `InputDrift` s'éteint.

## 4. Si la démo échoue

- **Grafana ne répond pas** : montrer le PSI dans Prometheus avec la requête `taxi_input_psi` (Spécifications §14).
- **Grafana montre un pic de février au-dessus de 0,25** : cela n'arrive pas si février a été rejoué au moins 15 minutes avant la démo (§1, étape 7). Sinon, c'est attendu : le PSI passe au-dessus du seuil pendant 1 à 3 s, au départ puis le 25 au matin, car un dimanche ou un jour férié (le 17 février 2020) n'a pas le profil d'un jour de semaine. Prometheus a pu montrer un pending d'une évaluation ; la règle demande 1 minute au-dessus de 0,25 (`for: 1m`, S4 p.43), donc rien n'est parti. Dire « aucune fausse alerte », pas « aucun pic » (`docs/qa_prep.md`). Le repli du §14 (fenêtre de 960) n'est pas appliqué : le dépassement dure 1 à 3 s et ne déclenche pas d'alerte ; c'est la lecture retenue depuis la 7.1 (`docs/qa_prep.md`).
- **Le gate refuse le candidat** : c'est un résultat valable (« the old model stays in production », S5 p.24). Pour enchaîner sur le rollback, enregistrer le candidat à la main avec `uv run python register.py <RUN_ID> staging`, le `run_id` étant dans la sortie (Spécifications §14, sans l'essai à 10 jours, trop long en direct).
- **Une commande échoue** : passer sur les annexes de secours, diapositives 11 et 12 de `docs/soutenance.pdf` : Backup 1, de a à d (requête et alerte de dérive), puis Backup 2, de a à e (réentraînement, promotion, rollback). Elles reprennent les preuves de l'incident réel de la 7.2, rangées dans `docs/evidence/incident/` : `t7.2_psi_fevrier.png`, `t7.2_psi_mars.png`, `t7.2_inputdrift_firing.png`, `t7.2_check_and_retrain.png`, `t7.2_v2_staging.png`, `t7.2_health_v2.png`, `t7.2_rollback.png` (rollback en 22,4 s) et `t7.2_cooldown.png`. La requête vient du contrôle de la 3.1 (`docs/evidence/t3.1_sorties_curl.txt`, premier modèle, jeu synthétique). Les captures des répétitions 7.1 et 8.3 sont dans `docs/evidence/repetition/` : `t7.1_*.png`, et `t8.3_*.png`, dont le pending, le firing et Alertmanager.
- **Tout échoue** : la vidéo de secours de la tâche 8.3.

## 5. Après la démo

Arrêter l'API (Ctrl+C dans le terminal 2) et MLflow (Ctrl+C dans le terminal 1, ou `lsof -ti tcp:5001 -sTCP:LISTEN | xargs kill` s'il tourne sans terminal), puis `cd monitoring && docker compose down`. Avant une nouvelle répétition, refaire tout le §1 de ce script, de la vérification des terminaux et des données au rejeu de février. Sinon, `check_and_retrain.py` répond « cooldown » et les numéros de version sont décalés.
