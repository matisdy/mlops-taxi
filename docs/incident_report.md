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

## 3. La couche qui a vu en premier, et pourquoi les autres n'ont rien vu

Le cours sépare la surveillance en quatre couches qui répondent chacune à une question (S4 p.11) ; les couches rapides donnent l'alerte, la couche lente juge (S4 p.12).

- **Couche 2, les entrées : elle a vu en premier, et seule.** L'API garde les 480 dernières valeurs de `lag_1h` et `lag_24h` (24 h × 20 zones) et compare leur répartition à celle de l'entraînement (`reference.json`) avec le PSI. Quand la demande s'effondre, les nombres de prises en charge de l'heure précédente et de la veille tombent dans les plus petites classes, presque vides à l'entraînement : le PSI monte jusqu'à 7,88, plus de trente fois le seuil [`InputDriftFiring.png`]. Le contrôle est aussi resté calme quand il le fallait : 0,095 au plus en février [`Feb Retrain.png`], et le pic isolé à 0,55 du 11 mars n'a pas déclenché d'alerte grâce au `for: 1m` [`March retrain.png`].
- **Couche 1, l'infrastructure : rien à voir.** Le service est resté en marche et rapide : pendant la répétition sur les mêmes données (7.1), les 8 640 requêtes du 1er au 18 mars visibles sur la capture ont toutes reçu une réponse, sans erreur [`Date over 0.25 March.png`], et `ApiDown` ne s'est pas déclenchée. Une dérive des données ne casse pas la machine.
- **Couche 3, les prédictions : pas instrumentée.** L'API compte les prédictions par version (`taxi_predictions_total`) mais n'expose pas leur distribution, et aucune alerte ne la regarde (Spécifications §7 et §8). Elle aurait pu voir la chute des prévisions, mais pas avant les entrées, dont les prévisions dépendent.
- **Couche 4, le résultat : elle a jugé, mais plus tard et à la demande.** La vérité terrain `y` n'est connue qu'une heure après chaque prévision ; nous ne calculons pas la MAE en continu (pas de `join_labels.py`, roadmap §6). La MAE n'apparaît que lorsque `check_and_retrain.py` lit `truth.csv`, à 16:46, six minutes après l'alerte [`action retrain.png`]. C'est elle qui confirme le dommage : 21,68 de MAE pour une moyenne de 9,5 prises en charge par heure [`t7.3_mesures.txt` §2].

## 4. La décision, selon l'arbre du cours (S5 p.22)

Le cours rappelle qu'une dérive n'est pas en soi une raison de réentraîner : on se pose trois questions dans l'ordre.

1. **Est-ce un bug ? Non.** Une panne de pipeline en amont ressemble à une dérive (S5 p.22), mais elle touche en général une zone, une colonne, ou commence d'un coup. Ici, les 20 zones baissent ensemble, de 90,3 % à 98,3 % entre la fin février et la dernière semaine de mars [`t7.3_mesures.txt` §3], et la chute est progressive : environ 110 000 prises en charge par jour jusqu'au 11 mars, 48 608 le 14, 5 430 le 22 [`t7.3_mesures.txt` §4]. Les données sont celles de la v1 (même md5 `335cc10a…`) et le rejeu de la répétition n'affiche aucune erreur [`t7.3_mesures.txt`, `Date over 0.25 March.png`]. Le sujet décrit d'ailleurs mars 2020 comme la période où la demande s'est effondrée (`project.pdf` p.1).
2. **Est-ce que ça fait mal ? Oui.** La MAE par semaine de la v1 [`t7.3_mesures.txt` §2] :

   | Semaine du | Prises en charge moyennes par heure | MAE de la v1 | Erreur relative |
   | --- | --- | --- | --- |
   | 17 février | 256,5 | 28,0 | 11 % |
   | 24 février | 283,0 | 28,4 | 10 % |
   | 2 mars | 269,1 | 30,0 | 11 % |
   | 9 mars | 174,8 | 43,1 | 25 % |
   | 16 mars | 37,5 | 50,6 | 135 % |
   | 23 mars | 10,6 | 28,5 | 268 % |
   | 30 et 31 mars | 9,5 | 21,7 | 228 % |

   La MAE en valeur absolue redescend en fin de mois parce qu'il n'y a presque plus de trajets ; l'erreur relative montre que le modèle se trompe en fait de deux à trois fois la demande réelle.
3. **Y a-t-il assez de nouvelles données ? Oui.** La fenêtre contient 7 jours rejoués, pour un minimum de 3 (`min_new_days`) [`incident/decisions.jsonl`].

**Donc : réentraîner, puis passer le gate.** Le candidat est entraîné sur le 25 au 29 mars (fenêtre de 7 jours moins les 2 derniers), puis comparé à la production sur le 30 et le 31 mars : MAE de 3,97 contre 21,68, soit 81,7 % de mieux pour un minimum de 5 % [`action retrain.png`]. Il est enregistré en v2 `@staging` [`MLFlow Staging.png`]. Un second lancement immédiat répond « cooldown » : pas de réentraînement en boucle [`Cooldown.png`]. La promotion reste une décision humaine (S5 p.24) : `promote.py` à 16:48:55 [`incident/promotions.jsonl`], puis `/health` affiche la v2 [`Curl new version.png`].

**Pourquoi pas un rollback ?** Revenir en arrière n'aide pas quand c'est le monde qui a changé : la v1 est justement le modèle qui se trompe, et il n'y a pas de version plus ancienne. Le rollback sert quand une nouvelle version fait pire que l'ancienne (`docs/runbook.md`). Nous l'avons exécuté ici comme exercice, pour mesurer la procédure : 22,4 s, bien sous l'objectif de 5 minutes (S6 p.36) [`Rollback.png`]. Dans un vrai incident, on aurait gardé la v2 en production.

## 5. Ce qui a marché, ce qui a manqué, ce qu'on automatiserait ensuite

**Les contrôles qui existaient et ont joué leur rôle** : le PSI des entrées et l'alerte `InputDrift` (détection seule, sans fausse alerte en février) ; le gate (le candidat devait battre la production d'au moins 5 %) ; le cooldown (pas de second réentraînement) ; l'approbation humaine avant la promotion ; le runbook de rollback (22,4 s).

**Ce qui a manqué, et une action par constat** (S6 p.42), avec le rôle qui la porte :

| Constat | Action | Porteur | Source |
| --- | --- | --- | --- |
| Le contrôle et le réentraînement se lancent à la main : 3 minutes de rejeu terminé sans que personne ne lance `check_and_retrain.py` ; en production, l'alerte pourrait tomber la nuit sans personne pour réagir [`incident/chronologie.md`]. | **Lancer le contrôle chaque nuit** : un DAG Airflow `check_drift` → `decide` → `dispatch_retrain`, qui déclenche l'entraînement dans GitHub Actions par `workflow_dispatch`. La promotion reste humaine. | Réentraînement (5.2) | S5 p.24, p.28–30 |
| La couche 4 ne juge qu'à la demande : la MAE n'existe qu'au lancement de `check_and_retrain.py`. | Calculer la MAE par heure dès que `y` arrive, en joignant prédictions et vérité terrain comme `join_labels.py` du lab 4, et l'afficher dans Grafana. | Surveillance (4.1) | S4 p.33–38 |
| La couche 3 n'est pas instrumentée. | Exposer la distribution des prédictions (histogramme Prometheus), comme le score du lab 4. | API (3.1) | S4 p.11, p.17 |
| Le gate ne compare le candidat qu'à la production. Or sur le 30 et le 31 mars, la simple baseline `lag_168h` (MAE 4,88) battait déjà la v1 (21,68) [`t7.3_mesures.txt` §2]. | Ajouter au gate une seconde condition : le candidat doit aussi battre la baseline. Ici la v2 (3,97) l'aurait passée. | Réentraînement (5.2) | S1-INTRO p.28 |
| Promotion et rollback demandent de relancer l'API à la main, parce que le modèle n'est chargé qu'au démarrage (S3 p.41) : la relance à la main compte dans les 22,4 s, contre 6,1 s quand un script relance l'API (5.1) [`Rollback.png`, `t5.1_verification.txt`]. | Décider à l'avance qui relance et sur quel signal, comme le demande le cours pour tout rollback. | Promotion et rollback (5.1) | S6 p.36 |
| La v2 a appris sur 5 jours de confinement : elle dérivera à son tour quand la demande remontera. | Garder la surveillance du PSI contre la référence de la v2 (l'API charge le `reference.json` de la version servie) et réentraîner sur une fenêtre glissante. | Réentraînement (5.2) | S5 p.24 |

## Preuves

Tous les fichiers sont dans `docs/evidence/`.

| Fichier | Ce qu'il prouve | Tâche |
| --- | --- | --- |
| `incident/chronologie.md` | Heures réelles, dates simulées et façon dont chaque heure a été établie | 7.2 |
| `incident/decisions.jsonl` | Décisions `retrain` (PSI, jours, MAE, run, version) puis `cooldown` | 7.2 |
| `incident/promotions.jsonl` | Promotion de v1 à v2 à 15:48:55 UTC (16:48:55 à Paris) | 7.2 |
| `Feb Retrain.png` | PSI de février, au plus 0,095 | 7.2 |
| `March retrain.png` | PSI de mars : pic bref à 0,55, puis dépassement durable de 0,25 jusqu'à environ 8 | 7.2 |
| `InputDriftFiring.png` | `InputDrift` en firing pour `lag_1h` (PSI 7,88) et `lag_24h` (PSI 7,76) | 7.2 |
| `action retrain.png` | Sortie de `check_and_retrain.py` : retrain, gate 3,97 contre 21,68, v2 `@staging` | 7.2 |
| `MLFlow Staging.png` | v2 enregistrée à 16:46:16 avec l'alias `@staging` | 7.2 |
| `Cooldown.png` | Second lancement : cooldown | 7.2 |
| `Curl new version.png` | `/health` sert la v2 après la promotion | 7.2 |
| `Rollback.png` | `rollback.py` : `/health` affiche v1 après 22,4 s | 7.2 |
| `MLFlow run.png` | Run de la v1 : commit, `data_md5`, version 1 | 7.1 |
| `Date over 0.25 March.png` | Répétition du rejeu de mars : requêtes sans erreur, PSI au-dessus du seuil | 7.1 |
| `t5.1_verification.txt` | Rollback de la 5.1 avec relance de l'API par script : 6,1 s | 5.1 |
| `t7.3_mesures.txt` | v1 refaite sur les mêmes données (contrôlée par la MAE du gate et le PSI d'Alertmanager), MAE par semaine, baisse par zone, prises en charge par jour | 7.3 |
