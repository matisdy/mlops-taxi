# Fiche de passage de la démo (4 minutes)

Qui tape quoi, à quel moment, et ce qui doit s'afficher, pendant la démo de la diapositive 5 de `docs/soutenance.pdf`. La mise en place est au §1 de `docs/demo_script.md`, le détail et les explications au §2 et au §3. Les temps et les sorties viennent de la répétition chronométrée du 23/11 (`docs/evidence/repetition/t8.3_durees.md`).

La répétition du 23/11 a utilisé un MLflow à part, sur le port 5012, pour ne pas toucher au serveur officiel. Mardi matin, la démo repart du §1 de `docs/demo_script.md`, sur le port 5001, dans des terminaux neufs.

## Rôles

L'équipe choisit les personnes à la répétition de mardi matin.

| Rôle | Ce qu'il fait | Qui |
| --- | --- | --- |
| Pilote | Seul au clavier et à la souris du Mac : terminal 4 (commandes), terminal 2 (API), navigateur. | Prénom : ____ |
| Voix | Raconte, une phrase par étape. Ne touche à rien. | Prénom : ____ |
| Chrono | Suit le temps sur cette fiche, déclenche le plan B, garde la vidéo de secours prête, hors ligne. | Prénom : ____ |

## Avant d'entrer

D'abord tout le §1 de `docs/demo_script.md`. Puis le Pilote vérifie :

| Contrôle | Où | Ce qui doit s'afficher |
| --- | --- | --- |
| Bon serveur MLflow | terminal 4 : `echo $MLFLOW_TRACKING_URI` | une ligne vide, ou `http://127.0.0.1:5001` |
| Registry propre | MLflow `http://127.0.0.1:5001`, onglet Models, `taxi-demand` | une seule version : la v1, avec `@production` |
| API en v1 | terminal 4 : `curl -s localhost:8000/health` | `{"status":"ok","model_version":"1"}` |
| Aucun reste de répétition | terminal 4 : `ls data/decisions.jsonl data/promotions.jsonl` | `No such file or directory` pour les deux fichiers |
| Février rejoué au moins 15 minutes avant la démo | terminal 4, dernière ligne ; le Chrono note l'heure du rejeu | `done: ok 6240, errors 0, rows appended to data/truth.csv` |
| Grafana sans le pic de février | tableau de bord « Taxi API », 15 dernières minutes | les deux courbes du PSI plates, sous la ligne rouge de 0,25 |
| Prometheus lit l'API | `http://localhost:9090/targets` | `taxi-api` à `UP` |
| Aucune alerte | Prometheus `/alerts`, puis Alertmanager | `ApiDown` et `InputDrift` ni pending ni firing ; aucune alerte dans Alertmanager |
| Onglets et écran | navigateur, terminaux | Grafana, Prometheus `/alerts`, Alertmanager, MLflow, dans cet ordre ; terminaux 4 et 2 à gauche, police agrandie |
| Plan B | Chrono | `docs/soutenance.pdf` prêt aux diapositives 11 et 12 ; vidéo de secours ouverte, testée hors ligne |

## Le déroulé

T4 = terminal 4 (commandes), T2 = terminal 2 (API). Le rejeu de mars part à 0:30 ; les repères marqués « ≈ » en découlent et peuvent varier de quelques secondes.

| Temps | Qui | Où | Ce qu'on tape (commande exacte) | Ce qui doit s'afficher | Ce que dit la Voix |
| --- | --- | --- | --- | --- | --- |
| 0:00 | Pilote | T4 | `curl -s localhost:8000/health` | `{"status":"ok","model_version":"1"}` | « L'API sert la v1, chargée depuis le Registry par son alias `@production`. » |
| 0:15 | Pilote | T4 | `curl -s -X POST localhost:8000/v1/predict -H 'Content-Type: application/json' -d '{"zone": 237, "ts": "2020-03-02T08:00:00", "lag_1h": 112.0, "lag_24h": 98.0, "lag_168h": 120.0}'` | `{"zone":237,"ts":"2020-03-02T08:00:00","prediction":190.20255820567724,"model_version":"1"}` | « Une requête : la zone 237, l'heure suivante. » |
| 0:30 | Pilote | T4, puis Grafana | `uv run python replay.py --start 2020-03-01 --end 2020-03-31` | `2020-03-01 to 2020-03-31: 744 hours x 20 zones, 10 hours/s, http://127.0.0.1:8000, Ctrl+C to stop`, puis une ligne par jour simulé | « On rejoue mars 2020 : la demande s'effondre avec le confinement. » |
| ≈ 0:37, puis ≈ 0:51 à 0:54 | Pilote | Grafana | — | des pics brefs du PSI peuvent apparaître, puis redescendre | Si un pic se voit : « Un pic ne suffit pas : la règle attend une minute au-dessus du seuil. » |
| ≈ 0:58 | — | Prometheus `/alerts`, s'il est à l'écran | — | un `InputDrift` en pending, bref, sur `lag_24h`, qui disparaît | — |
| ≈ 1:03 à 1:20 | Pilote | Grafana | — | le PSI passe la ligne rouge de 0,25 pour de bon à 1:03 ; Grafana l'affiche entre 1:05 et 1:20 (un point toutes les 15 s), les deux courbes au-dessus | « La couche des entrées voit la dérive en premier : les lags tombent dans la classe la plus basse. » |
| ≈ 1:08 | Pilote | Prometheus `/alerts` | — | `InputDrift` en pending (orange), sur les deux variables | « La règle attend une minute au-dessus du seuil, pour ne pas sonner sur un pic. » |
| ≈ 1:46 | — | T4 | — | `done: ok 14880, errors 0, rows appended to data/truth.csv` | « À 10 heures simulées par seconde, cette minute vaut 25 jours simulés : c'est un effet du rejeu, pas une règle lente. » |
| ≈ 2:08 | Pilote | Prometheus `/alerts`, puis Alertmanager | — | `InputDrift` en firing (rouge), pour `lag_1h` et `lag_24h` ; les deux alertes dans Alertmanager, à la même seconde | « L'alerte est partie seule, sans personne. » |
| 2:15 | Chrono, puis Pilote | T4 | `uv run python check_and_retrain.py` | en 7 s, après les lignes de MLflow : la ligne JSON avec `"action": "retrain"`, puis `taxi-demand v2 is now @staging (MAE 3.9738 vs 21.6775 in production)` | « Pas un bug, ça fait mal, assez de jours : on réentraîne. » |
| ≈ 2:22 | Pilote | MLflow, onglet Models, `taxi-demand` (recharger la page) | — | la v2 avec `@staging`, la v1 avec `@production` | « Le candidat passe le gate : il bat la production d'au moins 5 %. » |
| 2:50 | Pilote | T4 | `uv run python promote.py` | en 2 s : `taxi-demand v2 is now @production (was v1)` puis `Relancer l'API` | « La promotion reste une décision humaine. » |
| 3:00 | Pilote | T2 | Ctrl+C, puis `OMP_NUM_THREADS=1 uv run uvicorn app.main:app --port 8000` (flèche du haut, Entrée) | `INFO:     loaded models:/taxi-demand@production (version 2)` ; `/health` répond environ 5 s après la relance | « L'API ne charge le modèle qu'au démarrage, d'où la relance. » |
| 3:10 | Pilote | T4 | `curl -s localhost:8000/health` | `{"status":"ok","model_version":"2"}` | — |
| 3:20 | Pilote | T4 | `uv run python rollback.py` | `taxi-demand v1 is now @production`, puis `Relancer l'API` environ 3 s après Entrée ; le script attend | « Si la v2 se comportait mal : retour arrière par l'alias. » |
| 3:25 | Pilote | T2 | Ctrl+C, puis la même commande (flèche du haut, Entrée) | `INFO:     loaded models:/taxi-demand@production (version 1)` | — |
| ≈ 3:30 | — | T4 | — | `/health shows v1 after … s` : `8.5 s` à la répétition, avec 3 s pour changer de terminal ; le chiffre dépend de la vitesse du Pilote | « Retour à la v1 en quelques secondes ; l'objectif du cours est moins de 5 minutes. » |
| 4:00 | Chrono | — | — | fin de la démo | — |

## Si ça ne vient pas

On ne débogue pas devant le jury : le Chrono annonce le geste, le Pilote l'exécute, la Voix continue le récit.

| Étape | Ce qu'on voit | Geste de secours |
| --- | --- | --- |
| 0:00, `/health` | pas de réponse, un 503, ou une autre version que 1 | Annexes : diapositive 11 (a à d), puis 12 (a à e). |
| 0:15, requête | une erreur 422 | Faute de frappe : recoller la commande de cette fiche. Sinon diapositive 11, a. |
| 0:30, rejeu | `errors` différent de 0 | Diapositive 11, c et d. |
| Grafana | ne répond pas | Prometheus `http://localhost:9090`, requête `taxi_input_psi` (Spécifications §14). |
| Grafana | un pic de février au-dessus de 0,25 | N'arrive pas si février a été rejoué au moins 15 minutes avant. Sinon, la Voix : « Un pic de 1 à 3 s n'est pas une alerte : la règle demande une minute au-dessus de 0,25. » On dit « aucune fausse alerte », pas « aucun pic » (`for: 1m`, S4 p.43). Cause du premier pic : le lundi 17 février 2020 est férié. |
| ≈ 0:58 | un pending bref, qui disparaît | Normal : Prometheus a lu le pic des 9 et 10 mars ; la règle attend une minute. |
| Alerte | pas de firing à 2:15 | Le Chrono dit « on enchaîne » : `check_and_retrain.py` ne dépend pas de l'alerte. Revenir sur Alertmanager juste après `promote.py`, avant la relance de 3:00 : la relance remet le PSI à 0 et éteint `InputDrift`. |
| 2:15, décision | `decision: cooldown` | Le §1 n'a pas été refait : diapositive 12, a à e. |
| 2:15, décision | `candidate refused at the gate (MAE … vs …): production stays as it is` | Résultat valable (« the old model stays in production », S5 p.24). Pour le rollback : `uv run python register.py <RUN_ID> staging`, avec le `run_id` de la ligne JSON, puis `promote.py` (Spécifications §14). |
| 2:50, promotion | une erreur | Diapositive 12, c. |
| 3:00 ou 3:25, relance | pas de ligne `loaded models` | Lire le message du terminal 2. S'il ne dit rien d'évident : diapositive 12, c ou d. |
| 3:00 ou 3:25, relance | `ApiDown` en pending dans Prometheus | Normal : un instant, jamais en firing (`for: 30s`). |
| Après 3:00 | `InputDrift` s'éteint | Normal : la relance remet le PSI à 0. |
| 3:20, rollback | `/health shows v1` n'arrive pas | Vérifier que l'API a bien été relancée (terminal 2) ; sinon diapositive 12, d (22,4 s pendant l'incident). |
| Tout | plusieurs étapes en échec | Le Chrono lance la vidéo de secours. |

## Après

- Arrêter l'API : Ctrl+C dans le terminal 2. Si la stack tourne encore, `ApiDown` repasse en firing : c'est normal, l'API ne répond plus.
- Avant toute nouvelle répétition, refaire tout le §1 de `docs/demo_script.md`. Sinon, `check_and_retrain.py` répond `decision: cooldown` et les numéros de version sont décalés.
