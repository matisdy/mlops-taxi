# Rapport d'incident : dérive des entrées en mars 2020

Incident simulé, joué le samedi 21 novembre 2026 de 16:31 à 16:53 (heure de Paris, tâche 7.2), puis analysé en tâche 7.3. Il est écrit comme une revue sans reproche (S6 p.42) : on décrit ce qui a rendu l'incident possible et ce que nos contrôles ont vu, pas qui a fait quoi.

Chaque fait observé renvoie entre crochets à un fichier de `docs/evidence/` (liste en fin de rapport). Les valeurs de configuration (périodes, seuils, fenêtres) renvoient aux fichiers du contrat : `params.yaml`, `policy.yaml`, `docs/specifications.md` et le code cité. Ces fichiers n'ont pas changé depuis le commit de l'incident (`298cc99`, branche `t7-2-incident`).

## 1. Résumé

1. La v1 de `taxi-demand`, entraînée du 8 janvier au 16 février 2020, a reçu en rejeu mars 2020, quand la demande de taxis s'est effondrée (`params.yaml`) [`t7.3_mesures.txt` §4].
2. Le PSI des entrées a été le seul à donner l'alerte : seuil de 0,25 dépassé vers le 13-14 mars simulé, `InputDrift` en firing une minute réelle plus tard, sans action humaine [`incident/t7.2_psi_mars.png`, `incident/t7.2_inputdrift_firing.png`].
3. Le dommage est réel : la MAE de la v1 passe de 28,0 à 50,6 entre la semaine du 17 février et celle du 16 mars (+80 %) [`t7.3_mesures.txt` §2].
4. `check_and_retrain.py` a réentraîné : le candidat bat la production de 81,7 % (3,97 contre 21,68) et devient la v2 `@staging`, promue ensuite par une personne ; le rollback, exercé, prend 22,4 s [`incident/t7.2_check_and_retrain.png`, `incident/t7.2_rollback.png`].
5. À automatiser ensuite : la détection tourne seule, mais `check_and_retrain.py` se lance à la main ; il faut le lancer chaque nuit, comme le DAG Airflow du cours (S5 p.28–29).

## Contexte

- **Périodes** (`params.yaml`) : entraînement du 8 janvier au 16 février 2020 ; validation du 17 au 29 février, rejouée comme période normale ; dérive du 1er au 31 mars 2020. 20 zones, 40 320 lignes « zone × heure », dont 19 200 d'entraînement, 6 240 de validation et 14 880 de rejeu [`t7.3_mesures.txt`].
- **Version servie au départ** : v1 en `@production` [`incident/chronologie.md`], run `vaunted-seal-31`, commit `c169bc4`, `data_md5` `335cc10a…` [`repetition/t7.1_run_mlflow_v1.png`]. Sur la validation, son erreur moyenne est de 28,50 prises en charge par zone et par heure, contre 47,89 pour la baseline `lag_168h`, qui reprend la même heure une semaine avant [`t7.3_mesures.txt` §1].
- **Dérive « injectée »** : mars 2020 est rejoué dans l'API en marche avec `replay.py`, sans modifier les données à la main (Spécifications §13) [`incident/chronologie.md`].
- **Seuils** (`policy.yaml` ; règle d'alerte : Spécifications §8) :
  - le PSI est recalculé toutes les 20 prédictions, sur les 480 dernières (24 h × 20 zones) ;
  - l'alerte part quand il reste au-dessus de 0,25 pendant 1 minute ;
  - le réentraînement regarde 7 jours, dont les 2 derniers sont réservés au gate ; il faut au moins 3 jours, 7 jours de cooldown et 5 % de gain minimal.
- **Point de départ propre** : `truth.csv`, `decisions.jsonl` et `promotions.jsonl` supprimés ; MLflow, l'API et la stack Prometheus, Alertmanager et Grafana lancés [`incident/chronologie.md`].

## 2. Chronologie, du premier signal à la fin du rollback

Les heures réelles sont celles du 21/11/2026, heure de Paris. Le rejeu avance de 2 heures simulées par seconde [`incident/chronologie.md`] : 12 s réelles font un jour simulé, et une minute réelle environ 5 jours simulés. Les heures marquées « ≈ » sont lues sur les graphiques ou déduites de cette vitesse. Les dates simulées sont des estimations.

| Heure réelle | Date simulée (estimée) | Événement | Couche | Preuve |
| --- | --- | --- | --- | --- |
| ≈ 16:33 → 16:35:30 | 17 → 29 février | Rejeu de février, période normale (le PSI bouge à partir de 16:34 environ) : PSI maximal de 0,07 (`lag_1h`) et 0,095 (`lag_24h`), loin de 0,25. Aucune alerte. Note 1. | 2 · entrées | `incident/t7.2_psi_fevrier.png` |
| ≈ 16:37 | 1er mars | Début du rejeu de mars. | | `incident/chronologie.md` |
| ≈ 16:38:50 → 16:39:00 | ≈ 10-11 mars | Pics brefs au-dessus de 0,25 : `lag_1h` à 0,55, puis `lag_24h` vers 0,4. Ils retombent avant la minute exigée par la règle : pas d'alerte. | 2 · entrées | `incident/t7.2_psi_mars.png` |
| ≈ 16:39:35 → 16:39:55 | ≈ 13-14 mars | **Premier signal** : `lag_1h`, puis `lag_24h`, passent durablement au-dessus de 0,25. Le 13 mars, les prises en charge des 20 zones tombent à 76 754 (102 054 la veille), puis à 48 608 le 14. | 2 · entrées | `incident/t7.2_psi_mars.png`, `t7.3_mesures.txt` §4 |
| ≈ 16:39:40 | ≈ 13-14 mars | `InputDrift` passe en pending. La capture de 16:45 montre l'alerte active depuis 5 min 34 s pour `lag_1h` et 5 min 24 s pour `lag_24h`. | 2 · entrées | `incident/t7.2_inputdrift_firing.png`, `incident/chronologie.md` |
| ≈ 16:40:40 | ≈ 18-19 mars | **`InputDrift` en firing**, après la minute de `for: 1m`. | 2 · entrées | `incident/t7.2_inputdrift_firing.png`, `incident/chronologie.md` |
| ≈ 16:43 | 31 mars, 23:00 | Fin du rejeu. Le PSI culmine vers 8 et finit à 7,88 (`lag_1h`) et 7,76 (`lag_24h`). | 2 · entrées | `incident/t7.2_psi_mars.png`, `incident/t7.2_inputdrift_firing.png` |
| 16:46:14 → 16:46:16 | 31 mars, 23:00 | `check_and_retrain.py`, lancé à la main, décide **retrain** : PSI de 7,70 et 7,64 sur les 7 derniers jours, 7 jours de données. Le candidat passe le gate (3,97 contre 21,68) et devient la **v2 `@staging`** à 16:46:16. | 4 · résultat (gate) | `incident/t7.2_check_and_retrain.png`, `incident/t7.2_v2_staging.png`, `incident/decisions.jsonl` |
| ≈ 16:48 | 31 mars, 23:00 | Second lancement aussitôt après : **cooldown**, pas de nouveau candidat. | | `incident/t7.2_cooldown.png`, `incident/decisions.jsonl` |
| 16:48:55 | | `promote.py`, sur décision humaine : `@production` passe de v1 à v2, puis l'API est relancée. | | `incident/promotions.jsonl` |
| ≈ 16:51 | | `/health` répond `{"status": "ok", "model_version": "2"}`. | 1 · infrastructure | `incident/t7.2_health_v2.png` |
| ≈ 16:52 | | **Exercice de rollback** : `rollback.py` remet v1 en `@production`. Après la relance de l'API, `/health` affiche v1 au bout de **22,4 s**, pour un objectif de moins de 300 s. État final : v1 en production. | 1 · infrastructure | `incident/t7.2_rollback.png`, `incident/chronologie.md` |

**Note 1.** `chronologie.md` fait commencer février à 16:31:30. Sur `incident/t7.2_psi_fevrier.png`, la jauge reste à 0 jusqu'à environ 16:34, et 13 jours à 2 heures par seconde ne durent que 2 min 36 s : le rejeu a donc commencé vers 16:33. Les heures de pending et de firing sont déduites de la durée d'activité affichée à 16:45 ; `chronologie.md` donne 16:40:30 pour le firing. L'heure de 16:31:30 correspond plutôt au démarrage de l'API, qui met la jauge à 0 (Spécifications §7).

**Durées clés**
- **Détection** : le seuil est franchi de 0 à 1 jour simulé après le début de la chute (13 mars).
- **Alerte** : elle part une minute réelle après le premier signal. Au rythme du rejeu, cela représente environ 5 jours simulés ; en production, ce serait une vraie minute.
- **Décision** : entre le firing et la décision de réentraîner, il s'écoule environ 5 min 30 s, dont environ 3 minutes entre la fin du rejeu et le lancement de `check_and_retrain.py`.
- **Promotion** : environ 8 min 15 s après le firing.
- **Rollback** : 22,4 s.

## 3. La couche qui a vu en premier, et pourquoi les autres n'ont rien vu

Le cours sépare la surveillance en quatre couches, chacune répondant à sa propre question (S4 p.11) : les couches rapides donnent l'alerte, la couche lente juge (S4 p.12).

- **Couche 2, les entrées : la première, et la seule à donner l'alerte.**
  - Ce qu'elle mesure : l'API garde les 480 dernières valeurs de `lag_1h` et `lag_24h` (24 h × 20 zones) et compare leur répartition à celle de l'entraînement avec le PSI. Les classes sont les déciles de l'entraînement : chacune contient environ 10 % des valeurs d'entraînement.
  - Ce qu'elle a vu : le dernier jour de mars, 99,4 % des valeurs de `lag_1h` tombent dans la classe la plus basse (moins de 34 prises en charge en une heure), contre 9,7 % à l'entraînement. Les huit classes au-dessus de 76 sont vides. D'où un PSI de 7,88, plus de trente fois le seuil [`t7.3_mesures.txt` §6].
  - Elle est restée calme quand il le fallait : fin février, chaque classe garde entre 7,9 et 14 % des valeurs de `lag_1h`, pour un PSI de 0,035 (0,077 pour `lag_24h`) [`t7.3_mesures.txt` §6, `incident/t7.2_psi_fevrier.png`]. Les pics brefs du 10-11 mars n'ont pas déclenché l'alerte, grâce au `for: 1m` [`incident/t7.2_psi_mars.png`].
- **Couche 1, l'infrastructure : rien à voir.** Une dérive des données ne casse pas la machine. Pendant la répétition sur les mêmes données (7.1), les 8 640 requêtes du 1er au 18 mars visibles sur la capture ont toutes reçu une réponse, sans erreur [`repetition/t7.1_rejeu_mars.png`]. Nous n'avons gardé ni la latence ni l'état d'`ApiDown` pendant l'incident.
- **Couche 3, les prédictions : pas instrumentée.**
  - L'API compte les prédictions par version (`taxi_predictions_total`), mais elle n'expose pas leur distribution, et aucune alerte ne la regarde (Spécifications §7 et §8).
  - Même instrumentée, elle n'aurait pas vu avant les entrées, puisque les prévisions en dépendent.
- **Couche 4, le résultat : elle a jugé, mais plus tard et à la demande.**
  - La vérité terrain `y` n'arrive qu'une heure après chaque prévision, et nous ne calculons pas l'erreur en continu.
  - L'erreur n'est calculée que lorsque `check_and_retrain.py` lit `truth.csv`, à 16:46, et seulement pour le gate, une fois la décision de réentraîner prise.
  - C'est elle qui confirme le dommage : 21,68 d'erreur moyenne pour 9,5 prises en charge par zone et par heure en moyenne [`incident/t7.2_check_and_retrain.png`, `t7.3_mesures.txt` §2].

## 4. La décision, au regard de l'arbre du cours (S5 p.22)

Le cours rappelle qu'une dérive n'est pas, à elle seule, une raison de réentraîner : il faut se poser trois questions dans l'ordre.

**Ce qui a réellement décidé.** Pendant l'incident, `decide()` n'a regardé que le PSI, le nombre de jours et le cooldown (`check_and_retrain.py`). La question « est-ce que ça fait mal ? » a été tranchée par le gate, puis vérifiée après coup sur toutes les semaines. Nous reprenons ici les trois questions avec ces preuves.

1. **Est-ce un bug ? Non.**
   - Le cours prévient qu'une panne en amont ressemble exactement à une dérive (S5 p.22). Notre raisonnement : une panne toucherait en général une zone ou une colonne, ou commencerait d'un coup.
   - Ici, les 20 zones baissent ensemble, de 90,3 % à 98,3 % entre fin février et la dernière semaine de mars [`t7.3_mesures.txt` §3].
   - La chute est progressive : entre 92 689 et 148 773 prises en charge par jour du 1er au 11 mars, 48 608 le 14, puis 5 430 le 22 [`t7.3_mesures.txt` §4].
   - Les données sont celles de la v1 (même md5, `335cc10a…`) [`t7.3_mesures.txt`].
   - Le rejeu de la répétition ne montre aucune erreur du 1er au 18 mars [`repetition/t7.1_rejeu_mars.png`].
   - Le sujet décrit d'ailleurs mars 2020 comme la période où la demande s'est effondrée (`project.pdf` p.1).
2. **Est-ce que ça fait mal ? Oui.** Erreur de la v1 par semaine, en prises en charge par zone et par heure [`t7.3_mesures.txt` §2] :

   | Semaine du | Prises en charge moyennes | MAE de la v1 | Erreur relative |
   | --- | --- | --- | --- |
   | 17 février | 256,5 | 28,0 | 11 % |
   | 24 février | 283,0 | 28,4 | 10 % |
   | 2 mars | 269,1 | 30,0 | 11 % |
   | 9 mars | 174,8 | 43,1 | 25 % |
   | 16 mars | 37,5 | 50,6 | 135 % |
   | 23 mars | 10,6 | 28,5 | 268 % |
   | 30 et 31 mars | 9,5 | 21,7 | 228 % |

   En valeur absolue, la MAE redescend en fin de mois parce qu'il n'y a presque plus de trajets. L'erreur relative montre que le modèle se trompe en réalité de deux à trois fois la demande réelle.
3. **Y a-t-il assez de nouvelles données ? Oui.** La fenêtre contient 7 jours rejoués, pour un minimum de 3 (`policy.yaml`) [`incident/decisions.jsonl`].

**Donc : réentraîner, puis passer le gate.**
- **Gate** : le candidat est entraîné du 25 au 29 mars, c'est-à-dire les 7 jours moins les 2 derniers (`check_and_retrain.py`, `policy.yaml`). Il est comparé à la production sur le 30 et le 31 mars : 3,97 contre 21,68, soit 81,7 % de mieux pour un minimum de 5 % [`incident/t7.2_check_and_retrain.png`].
- **Enregistrement** : il devient la v2 `@staging` [`incident/t7.2_v2_staging.png`].
- **Cooldown** : un second lancement immédiat répond « cooldown », il n'y a donc pas de réentraînement en boucle [`incident/t7.2_cooldown.png`].
- **Promotion** : elle reste une décision humaine (S5 p.24). `promote.py` est lancé à 16:48:55 [`incident/promotions.jsonl`], puis `/health` affiche la v2 [`incident/t7.2_health_v2.png`].

**Pourquoi pas un rollback ?**
- Revenir en arrière n'aide pas quand c'est le monde qui a changé. La v1 est justement le modèle qui se trompe, et il n'existe pas de version plus ancienne.
- Le rollback sert quand une nouvelle version fait pire que l'ancienne (`docs/runbook.md`).
- Nous l'avons exécuté ici comme exercice, pour mesurer la procédure : 22,4 s, bien sous l'objectif de 5 minutes (S6 p.36) [`incident/t7.2_rollback.png`].
- Dans un vrai incident, on aurait gardé la v2 en production. Après l'exercice, c'est la v1 qui sert de nouveau.

## 5. Ce qui a marché, ce qui a manqué, ce qu'on automatiserait ensuite

**Les contrôles qui existaient et ont joué leur rôle**
- le PSI des entrées et l'alerte `InputDrift`, qui ont détecté seuls, sans fausse alerte en février ;
- le gate : le candidat devait battre la production d'au moins 5 % ;
- le cooldown : pas de second réentraînement ;
- l'approbation humaine avant la promotion ;
- le runbook de rollback : 22,4 s.

**Ce qui a manqué, avec une action par constat (S6 p.42) et le rôle qui la porte**

| Constat | Action | Porteur | Source |
| --- | --- | --- | --- |
| La détection est automatique, mais `check_and_retrain.py` se lance à la main (choix déclaré, Spécifications §13). Pendant l'incident, il s'est écoulé 3 minutes entre la fin du rejeu et son lancement. En production, l'alerte peut tomber la nuit [`incident/chronologie.md`]. | **Lancer le contrôle chaque nuit** : un DAG Airflow `check_drift` → `decide` → `dispatch_retrain`, qui déclenche l'entraînement dans GitHub Actions par `workflow_dispatch`. La promotion reste humaine. | Réentraînement (5.2) | S5 p.24, p.28–30 |
| `decide()` décide de réentraîner sans mesurer le dommage (PSI, jours et cooldown seulement) ; le dommage n'est mesuré qu'ensuite, par le gate. | Garder l'enchaînement contrôle, entraînement, gate (S5 p.24), mais calculer la MAE de production avant d'entraîner, pour répondre à « Does it hurt? » d'abord (S5 p.22). | Réentraînement (5.2) | S5 p.22, p.24 |
| La couche 4 ne juge qu'à la demande. | Calculer l'erreur par heure dès que `y` arrive, en joignant prédictions et vérité terrain comme le fait `join_labels.py` au lab 4, puis l'afficher dans Grafana. | Surveillance (4.1) | S4 p.34, p.37–38 |
| La couche 3 n'est pas instrumentée. | Exposer la distribution des prédictions dans un histogramme Prometheus, comme le score au lab 4. | API (3.1) | S4 p.11, p.17 |
| Le gate ne compare le candidat qu'à la production. Or, sur le 30 et le 31 mars, la simple baseline `lag_168h` (4,88) battait déjà la v1 (21,68) [`t7.3_mesures.txt` §2]. | Ajouter une condition au gate : battre aussi la baseline. La v2 (3,97) l'aurait passée. | Réentraînement (5.2) | inspiré de S1-INTRO p.28 |
| Le modèle n'est chargé qu'au démarrage de l'API, il faut donc la relancer à la main après une promotion ou un rollback (S3 p.26, p.40–41). Cette relance manuelle compte dans les 22,4 s, contre 6,1 s quand un script relance l'API (5.1) [`incident/t7.2_rollback.png`, `t5.1_verification.txt`]. | Décider à l'avance qui relance, et sur quel signal. | Promotion et rollback (5.1) | S6 p.36 |
| La v2 n'a appris que sur 5 jours de confinement : elle dérivera à son tour quand la demande remontera. | Garder la surveillance du PSI contre la référence de la v2 (l'API charge le `reference.json` de la version servie, Spécifications §7) et réentraîner sur une fenêtre glissante. C'est notre proposition. | Réentraînement (5.2) | Spécifications §7 |
| Une partie des heures de la chronologie est lue sur des captures. | Exporter les heures exactes depuis l'API de Prometheus (`query_range` sur `taxi_input_psi` et `ALERTS`) au moment de rédiger les preuves. C'est notre proposition. | Surveillance (4.1) | Prometheus de S4 p.17 |
| En rejeu accéléré, la minute de `for: 1m` vaut environ 5 jours simulés à 2 h/s [`incident/chronologie.md`], et 25 jours à la vitesse de 10 h/s du §9 : l'alerte paraît tardive. | Le dire pendant la démo : c'est un effet du rejeu, pas de la règle. | Soutenance (8.1) | Spécifications §8 et §9 |

## Preuves

**Faits observés**, tous dans `docs/evidence/` :

| Fichier | Ce qu'il prouve | Tâche |
| --- | --- | --- |
| `incident/chronologie.md` | Heures réelles, dates simulées, état de départ et façon dont chaque heure a été établie | 7.2 |
| `incident/decisions.jsonl` | Décisions `retrain` (PSI, jours, MAE, run, version), puis `cooldown` | 7.2 |
| `incident/promotions.jsonl` | Promotion de v1 à v2 à 15:48:55 UTC, soit 16:48:55 à Paris | 7.2 |
| `incident/t7.2_psi_fevrier.png` | PSI de février : 0,095 au plus | 7.2 |
| `incident/t7.2_psi_mars.png` | PSI de mars : pics brefs, puis dépassement durable de 0,25 jusqu'à environ 8 | 7.2 |
| `incident/t7.2_inputdrift_firing.png` | Règle `InputDrift` dans Prometheus : firing pour `lag_1h` (7,88) et `lag_24h` (7,76), avec la durée d'activité | 7.2 |
| `incident/t7.2_check_and_retrain.png` | Sortie de `check_and_retrain.py` : retrain, gate à 3,97 contre 21,68, v2 `@staging` | 7.2 |
| `incident/t7.2_v2_staging.png` | v2 enregistrée à 16:46:16 avec l'alias `@staging` | 7.2 |
| `incident/t7.2_cooldown.png` | Second lancement : cooldown | 7.2 |
| `incident/t7.2_health_v2.png` | `/health` sert la v2 après la promotion | 7.2 |
| `incident/t7.2_rollback.png` | `rollback.py` : `/health` affiche v1 après 22,4 s | 7.2 |
| `repetition/t7.1_run_mlflow_v1.png` | Run de la v1 : commit, `data_md5`, version 1 | 7.1 |
| `repetition/t7.1_rejeu_mars.png` | Répétition du rejeu de mars : requêtes sans erreur du 1er au 18 mars | 7.1 |
| `repetition/t7.1_psi_fevrier.png`, `repetition/t7.1_psi_mars.png`, `repetition/t7.1_alerte_firing.png` | Répétition de 7.1 : en février, deux pics brefs de `lag_24h` au-dessus de 0,25 (≈ 0,55 et 0,26) sans alerte grâce au `for: 1m` ; mars au-dessus du seuil ; alerte en firing aux mêmes valeurs (7,88 et 7,76) | 7.1 |
| `t5.1_verification.txt` | Rollback de la 5.1 avec relance de l'API par script : 6,1 s | 5.1 |
| `t7.3_mesures.txt` | v1 refaite sur les mêmes données, contrôlée par la MAE du gate et le PSI de la règle `InputDrift`. Contient la MAE par semaine, la baisse par zone, les prises en charge par jour et la répartition par classe du PSI. | 7.3 |

**Contrat**, pour les valeurs de configuration : `params.yaml`, `policy.yaml`, `docs/specifications.md` (§7, §8, §9, §13), `check_and_retrain.py`, `docs/runbook.md`.
