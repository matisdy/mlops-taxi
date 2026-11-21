# Rapport d'incident : dérive des entrées en mars 2020

Incident simulé, joué le samedi 21 novembre 2026 de 16:31 à 16:53 (heure de Paris, tâche 7.2), puis analysé en tâche 7.3. Il est écrit comme une revue sans reproche (S6 p.42) : on décrit ce qui a rendu l'incident possible et ce que nos contrôles ont vu, pas qui a fait quoi. Chaque affirmation renvoie entre crochets à un fichier de `docs/evidence/` (liste complète en fin de rapport).

## 1. Résumé

1. Le modèle `taxi-demand` v1, entraîné sur janvier et février 2020, a reçu en rejeu le mois de mars 2020, quand la demande de taxis jaunes s'est effondrée à New York [`t7.3_mesures.txt` §4].
2. La couche des entrées a vu en premier et seule : le PSI de `lag_1h` et `lag_24h` a dépassé 0,25 vers le 14 mars simulé, et l'alerte `InputDrift` est passée en firing environ une minute plus tard, sans action humaine [`March retrain.png`, `InputDriftFiring.png`].
3. L'effet est réel : la MAE de la v1 passe de 28,0 (semaine du 17 février) à 50,6 (semaine du 16 mars), soit +80 %, et l'erreur relative monte jusqu'à 268 % [`t7.3_mesures.txt` §2].
4. `check_and_retrain.py` a décidé « retrain » ; le candidat a passé le gate (MAE 3,97 contre 21,68 pour la production sur le 30 et le 31 mars, soit 81,7 % de mieux) et est devenu la v2 `@staging`, puis une personne l'a promu ; le rollback a ensuite été exercé en 22,4 s [`action retrain.png`, `incident/promotions.jsonl`, `Rollback.png`].
5. Ce qui manquait : le contrôle de dérive et le réentraînement sont lancés à la main ; la prochaine étape est de les lancer chaque nuit, comme le DAG Airflow du cours (S5 p.28–29).

## Contexte

- **Périodes** (`params.yaml`) : entraînement du 8 janvier au 16 février 2020, validation du 17 au 29 février (période de référence rejouée sans alerte), rejeu du 1er au 31 mars 2020 (période de dérive). 20 zones, 40 320 lignes « zone × heure » [`t7.3_mesures.txt`, préparation].
- **Version servie au départ** : v1 en `@production`, run `vaunted-seal-31`, commit `c169bc4`, `data_md5` `335cc10a…` [`MLFlow run.png`]. Sur la validation, sa MAE est de 28,50 prises en charge par heure, contre 47,89 pour la baseline `lag_168h` (même heure, une semaine avant) [`t7.3_mesures.txt` §1].
- **Dérive « injectée »** : mars 2020 rejoué dans l'API en marche avec `replay.py`, sans modifier les données à la main ; c'est la période citée par le sujet (écart EC-11, Spécifications §13) [`incident/chronologie.md`].
- **Seuils** (`policy.yaml`) : PSI recalculé toutes les 20 prédictions sur les 480 dernières (24 h × 20 zones), alerte au-dessus de 0,25 pendant 1 minute ; réentraînement sur une fenêtre de 7 jours dont les 2 derniers servent au gate, au moins 3 jours de données, 7 jours de cooldown, gain minimal de 5 % [`InputDriftFiring.png`, `incident/decisions.jsonl`].
- **Point de départ propre** : `truth.csv`, `decisions.jsonl` et `promotions.jsonl` supprimés ; MLflow, l'API et la stack Prometheus, Alertmanager et Grafana lancés [`incident/chronologie.md`].

## 2. Chronologie, du premier signal à la fin du rollback

Heures réelles du 21/11/2026, heure de Paris. Le rejeu avance de 2 heures simulées par seconde, soit environ 12 s par jour simulé. Les heures marquées « ≈ » sont lues sur les graphiques ou estimées d'après la vitesse du rejeu ; la façon dont chaque heure a été établie est décrite dans [`incident/chronologie.md`].

| Heure réelle | Date simulée | Événement | Couche | Preuve |
| --- | --- | --- | --- | --- |
| ≈ 16:31:30 → 16:35:30 | 17 → 29 février | Rejeu de février, la période de référence : PSI maximal 0,07 (`lag_1h`) et 0,095 (`lag_24h`), loin de 0,25. Aucune alerte. | 2 · entrées | `Feb Retrain.png` |
| ≈ 16:37 | 1er mars | Début du rejeu de mars. | | `incident/chronologie.md` |
| ≈ 16:38:50 | ≈ 11 mars | Pic bref du PSI de `lag_1h` à 0,55 ; il retombe avant la minute exigée par la règle : pas d'alerte. | 2 · entrées | `March retrain.png` |
| ≈ 16:39:30 → 16:39:45 | ≈ 14 mars | **Premier signal** : les deux PSI passent au-dessus de 0,25 et y restent. Le même jour, les prises en charge des 20 zones tombent à 48 608, contre 110 658 le 11 mars. | 2 · entrées | `March retrain.png`, `t7.3_mesures.txt` §4 |
| ≈ 16:39:30 | ≈ 14 mars | `InputDrift` passe en pending pour `lag_1h` puis `lag_24h` (sur la capture de 16:45, l'alerte est active depuis 5 min 34 s et 5 min 24 s). | 2 · entrées | `InputDriftFiring.png` |
| ≈ 16:40:30 | ≈ 15 mars | **`InputDrift` en firing**, après la minute du `for: 1m`. Le PSI continue de monter jusqu'à 7,88 et 7,76 en fin de mois. | 2 · entrées | `InputDriftFiring.png`, `March retrain.png` |
| ≈ 16:43 | 31 mars, 23:00 | Fin du rejeu de mars. | | `incident/chronologie.md` |
| 16:46:14 → 16:46:16 | 31 mars, 23:00 | `check_and_retrain.py`, lancé à la main : décision **retrain** (PSI 7,70 et 7,64 sur les 7 derniers jours, 7 jours de données). Gate passé : 3,97 contre 21,68. **v2 en `@staging`** à 16:46:16. | 4 · résultat | `action retrain.png`, `MLFlow Staging.png`, `incident/decisions.jsonl` |
| ≈ 16:48 | 31 mars, 23:00 | Second lancement aussitôt après : **cooldown**, pas de nouveau candidat. | | `Cooldown.png`, `incident/decisions.jsonl` |
| 16:48:55 | | `promote.py`, décision humaine : `@production` passe de v1 à v2, puis l'API est relancée. | | `incident/promotions.jsonl` |
| ≈ 16:51 | | `/health` répond `{"status": "ok", "model_version": "2"}`. | 1 · infrastructure | `Curl new version.png` |
| ≈ 16:52 | | **Exercice de rollback** : `rollback.py` remet v1 en `@production` ; après la relance de l'API, `/health` affiche v1 au bout de **22,4 s** (objectif : moins de 300 s). | 1 · infrastructure | `Rollback.png` |

**Durées clés.** Le PSI dépasse le seuil environ 1 jour simulé après le début de la chute (13 mars : 76 754 prises en charge, contre 102 054 le 12 mars) [`t7.3_mesures.txt` §4]. L'alerte part environ 1 minute réelle après le premier signal. Entre l'alerte et la décision de réentraîner, il s'écoule environ 6 minutes, dont 3 minutes pendant lesquelles personne n'a lancé le contrôle après la fin du rejeu. La promotion arrive environ 8 minutes après l'alerte, et le retour arrière prend 22,4 s.
