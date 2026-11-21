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
