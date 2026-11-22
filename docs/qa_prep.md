# Préparation des questions de la soutenance

Le jury peut interroger n'importe quel membre sur n'importe quelle partie, et chacun défend un choix technique sans préparation, ce qui compte pour 10 % de la note (sujet p.2). Ce document donne les questions probables et une réponse courte pour chacune, avec sa source, pour que chacun puisse répondre sur les parties qu'il n'a pas faites.

Règle pour répondre : une phrase pour la réponse, une phrase pour la raison, puis le chiffre ou la preuve. Si on ne sait pas, on le dit et on renvoie au fichier qui contient la réponse.

## 1. Qui a fait quoi

D'après l'historique Git de `main` (auteurs des commits de chaque tâche). À corriger en séance si la répartition réelle diffère.

| Partie | Tâches | Fichiers | Commits |
| --- | --- | --- | --- |
| Données | 1.1, 1.2 | `download.py`, `build_dataset.py`, `data/*.dvc`, `docs/data.md` | Matis |
| Modèle | 2.1 | `train.py`, `register.py`, `evaluate.py` | Matis |
| API | 3.1 | `app/main.py` | Matis |
| Tests et CI | 3.2 | `tests/`, `.github/workflows/ci.yml` | Driss |
| Surveillance | 4.1, 4.2 | `monitoring/`, `replay.py` | Matis |
| Réaction | 5.1, 5.2 | `promote.py`, `rollback.py`, `docs/runbook.md`, `check_and_retrain.py` | Matis (5.1), Driss (5.2) |
| Incident | 7.1, 7.2, 7.3 | `docs/evidence/`, `docs/incident_report.md` | Driss (7.1, 7.2), Jérémy (7.3) |
| Rendu | 6.1, 8.1 | `README.md`, `docs/architecture.png`, `docs/demo_script.md`, `docs/soutenance.pdf` | Jérémy |

## 2. Séance de 45 minutes à quatre

Chaque partie est expliquée en 8 minutes par la personne qui l'a faite, en partant du fichier et de la preuve (tâche 8.2). Les 5 minutes restantes servent à tirer les questions de la section 5.

| Temps | Partie | Ce qu'il faut montrer |
| --- | --- | --- |
| 0:00 | Données | Le découpage temporel dans `params.yaml`, les 20 zones, une ligne de `features.parquet`, le pointeur DVC |
| 0:08 | Modèle | Le pipeline de `train.py`, la baseline `lag_168h`, un run dans MLflow et ses tags |
| 0:16 | API | Le contrat Pydantic, `/health`, `/v1/predict`, `/metrics`, le calcul du PSI glissant, un test |
| 0:24 | Surveillance | La règle `InputDrift`, le tableau de bord Grafana, `replay.py` |
| 0:32 | Réaction | `check_and_retrain.py` (décision, gate, cooldown), `promote.py`, `rollback.py`, le runbook |
| 0:40 | Questions | Chacun tire trois questions sur des parties qu'il n'a pas faites (section 5) |

## 3. Les six questions de la fiche

### Pourquoi un découpage temporel ?

Parce qu'en production le modèle prédit toujours le futur à partir du passé : la validation doit reproduire cette situation. Un découpage au hasard, comme le `train_test_split` des labs, mettrait des heures de fin février dans l'entraînement et laisserait fuir le futur par les variables décalées.

Nos périodes : entraînement du 8 janvier au 16 février 2020, validation du 17 au 29 février, mars rejoué comme période de dérive (`params.yaml`, DEC-02). L'écart au cours est noté (EC-3) ; le sujet demande un découpage temporel (sujet p.1).

### Pourquoi le PSI, et pourquoi 0,25 ?

Le PSI mesure à quel point la distribution d'une variable d'entrée s'éloigne de celle de l'entraînement, sans avoir besoin des vraies valeurs : c'est la couche 2, celle qui voit la dérive en premier. Il marche aussi bien sur des variables numériques que catégorielles (S5 p.13, p.16).

Formule : somme de (part actuelle moins part de référence) multipliée par ln(part actuelle / part de référence), sur 10 classes tirées des déciles de l'entraînement (S5 p.8 et p.9). Les seuils sont la convention du cours : sous 0,10 stable, de 0,10 à 0,25 à surveiller, au-dessus de 0,25 on agit (S5 p.15, `policy.yaml`). Le cours précise que c'est « une règle empirique, pas un test » : nous l'avons vérifiée sur nos données, puisque février reste sous 0,10 en fin de fenêtre (0,035 et 0,077) alors que mars monte à 7,88 (`docs/evidence/t7.3_mesures.txt`).

Si on demande les détails : le PSI porte sur `lag_1h` et `lag_24h`, sur les 480 dernières prédictions (24 heures fois 20 zones), recalculé toutes les 20. La fenêtre de 24 heures couvre toutes les heures de la journée, pour que la variation normale entre la nuit et le jour ne passe pas pour une dérive (S5 p.20 et p.21, EC-7). Les parts de référence sont mesurées sur l'entraînement et non fixées à 10 % par classe, parce que les comptages ont des ex æquo (EC-8).

### Pourquoi la MAE ?

La cible est un nombre de prises en charge : c'est une régression, alors que le cours ne traite que la classification (EC-2). La MAE se lit directement en prises en charge par zone et par heure, et elle pèse moins que la RMSE sur quelques heures extrêmes ; c'est le choix DEC-07.

On la compare toujours à une baseline simple, la valeur de la même heure la semaine précédente (`lag_168h`), comme le demande le cours (S1-INTRO p.28). Sur la validation, la v1 fait 28,50 contre 47,89 pour la baseline (`docs/evidence/t7.3_mesures.txt`).

### Comment marche le gate ?

Le candidat est entraîné sur les 7 derniers jours rejoués, puis comparé à la production sur les 2 jours les plus récents, qu'il n'a jamais vus. Il ne passe que s'il réduit la MAE d'au moins 5 % (`policy.yaml`, DEC-07). Le cours le dit : « le gate décide, pas l'alarme », et on ne le mesure jamais sur les données d'entraînement (S5 p.31, WRAP p.15).

Pendant l'incident : 3,97 pour le candidat contre 21,68 pour la production, soit 81,7 % de mieux ; la v2 est passée en `@staging` (`docs/evidence/incident/decisions.jsonl`). Si le candidat avait échoué, l'ancien modèle restait en production (S5 p.24). Deux garde-fous l'entourent : au moins 3 jours de données et 7 jours de cooldown entre deux réentraînements (S5 p.32). Ensuite, une personne décide de la promotion avec `promote.py` : « le gate décide, une personne approuve » (WRAP p.15).

### Pourquoi un rollback par alias ?

Dans le Registry, l'API charge le modèle par son nom et son alias, `models:/taxi-demand@production`. Promouvoir, c'est déplacer l'alias ; l'ancienne version reste dans le Registry ; revenir en arrière, c'est remettre l'alias sur elle (WRAP p.7). Il n'y a rien à reconstruire ni à réentraîner.

`rollback.py` remet l'alias, puis on relance l'API, qui ne charge le modèle qu'au démarrage (S3 p.26 et p.41, EC-6). Pendant l'incident, `/health` a affiché la v1 après 22,4 s, pour un objectif de moins de 5 minutes (S6 p.36, `incident/t7.2_rollback.png`). Le chiffre à citer est 22,4 s ; les 6,1 s de la tâche 5.1 correspondent à une relance de l'API par un script, sur des modèles synthétiques.

### Pourquoi ni Kubernetes ni Airflow ?

Ni l'un ni l'autre n'est exigé par le sujet (DEC-17). Le cours les présente sans que nous les ayons pratiqués (S5 p.28 à 30, S6). Nous avons préféré mettre le temps dans la boucle complète, de la surveillance au rollback, et la prouver sur un vrai incident.

Pour la réaction, `check_and_retrain.py` est lancé à la main, comme le script unique du lab (S5 p.33) ; l'alerte, elle, se déclenche seule (EC-10). Avec un mois de plus, Airflow lancerait ce contrôle chaque nuit, et Kubernetes ferait le rollback avec `kubectl rollout undo` (S6 p.36).

## 4. Autres questions probables

### Sur l'incident

**Quelle couche a vu le problème en premier ?** La couche 2, celle des entrées : le PSI a dépassé 0,25 et `InputDrift` est passée en firing sans personne. La couche 1 (infrastructure) n'avait rien à voir, l'API répondait normalement. La couche 3 (prédictions) n'est pas instrumentée. La couche 4 (résultats) a jugé plus tard, au gate. Le cours le résume : « les couches rapides préviennent, la couche lente juge » (S4 p.11 et p.12, `docs/incident_report.md`).

**Pourquoi le PSI monte-t-il autant (7,88) ?** Le dernier jour de mars, 99,4 % des valeurs de `lag_1h` tombent dans la classe la plus basse, contre 9,7 % à l'entraînement, et les huit classes au-dessus sont vides. Le PSI est plus de trente fois au-dessus du seuil (`docs/evidence/t7.3_mesures.txt` §6).

**Pourquoi avoir réentraîné ?** On suit l'arbre du cours (S5 p.22). Est-ce un bug ? Non : les 20 zones baissent toutes, de 90,3 % à 98,3 %, progressivement du 12 au 22 mars. Est-ce que ça fait mal ? Oui : la MAE par semaine passe de 28,0 à 50,6, et l'erreur relative monte jusqu'à 268 %. Assez de données ? Oui : 7 jours rejoués, il en faut 3. Donc on réentraîne, puis le gate décide (`docs/incident_report.md`).

**Quel type de dérive ?** Une dérive des données, sur P(X) : les variables décalées s'effondrent avec le confinement (S5 p.6 et p.7). Le PSI seul dit que quelque chose a changé, jamais que le modèle se trompe (WRAP p.31) : c'est la MAE sur les vraies valeurs qui le montre.

**Février a eu un pic de PSI à 0,55 : pourquoi pas d'alerte ?** Pendant la répétition 7.1, le PSI de `lag_24h` a fait un pic au démarrage, puis il est retombé. La règle demande que le PSI reste au-dessus de 0,25 pendant 1 minute (`for: 1m`), donc rien n'est parti. C'est exactement son rôle : ne pas sonner sur un pic (S4 p.43). On dit « aucune fausse alerte », pas « aucun pic » (`repetition/t7.1_psi_fevrier.png`).

**La baseline fait mieux que la v1 sur la fin de mars : pourquoi ne pas la servir ?** Sur les 2 derniers jours, `lag_168h` fait 4,88 contre 21,68 pour la v1, mais le candidat v2 fait encore mieux (3,97). Le gate du cours compare le candidat à la production (S5 p.31). Ajouter la baseline au gate fait partie du mois de plus (`docs/incident_report.md`).

### Sur la reproductibilité

**Comment sait-on d'où vient une version ?** On versionne trois choses (WRAP p.4 et p.5) : le code (le run MLflow garde `git_commit` et `git_dirty`), les données (`data_md5`, le hash DVC de `features.parquet`) et le modèle (le run et sa version dans le Registry). Preuve : la v1 reconstruite depuis le même code et les mêmes données redonne la même MAE au gate, 21,6775 (`docs/evidence/t7.3_mesures.txt`, `repetition/t7.1_run_mlflow_v1.png`).

**Pourquoi DVC alors que les données sont publiques ?** Pour pouvoir répondre à « sur quelles données ce modèle a-t-il été entraîné ? » (S1-MLF p.41) : le pointeur `data/raw.dvc` garde l'empreinte des fichiers. Si la TLC changeait un fichier, `dvc status` le verrait (`docs/data.md`).

**Et l'environnement ?** `uv.lock` est commité, et la CI lance `uv sync --locked`, qui échoue si `pyproject.toml` ne correspond plus (WRAP p.10).

### Sur l'API

**Que se passe-t-il si la requête est fausse ?** Le contrat Pydantic la refuse avec un 422 : champ inconnu, zone hors de 1 à 265 ou décalage négatif. Une mauvaise requête est refusée, pas notée (WRAP p.19 et p.20, Spécifications §7).

**Et s'il n'y a pas de modèle ?** `/health` répond 503, pour qu'un répartiteur de charge arrête de lui envoyer du trafic (S3 p.27). Chaque réponse porte `model_version`, ce qui permet de savoir quelle version a répondu (S3 p.26).

**On déplace `@staging` pendant que l'API tourne : quelle version répondent les requêtes suivantes ?** Toujours la même : l'API a chargé `@production` au démarrage et ne relit pas le Registry. Il faut la relancer, d'où la relance après `promote.py` et `rollback.py` (S3 p.41, EC-6).

**L'API répondait 200 pendant tout mars : est-ce que tout allait bien ?** Non, c'est la panne silencieuse du cours : « tableau de bord vert, mauvais modèle » (S4 p.6 et p.7). C'est pour ça qu'on surveille aussi les entrées et pas seulement la disponibilité.

### Sur la surveillance

**Pourquoi une jauge pour le PSI ?** Le PSI monte et descend, donc c'est une jauge ; un compteur ne fait que monter (S4 p.14 et p.15).

**Pourquoi `for: 1m` et pas 10 minutes ?** Le cours met 10 minutes en production et 1 minute au lab (S4 p.43) ; nous rejouons un mois en quelques minutes, donc la minute du lab suffit.

**Où est le runbook ?** `docs/runbook.md`, en cinq lignes sur le modèle du cours (S4 p.58) : symptôme, première vérification, commande, relance de l'API, vérification de `/health`.

### Sur ce qu'on n'a pas fait

**Pourquoi pas de canary ou de blue/green ?** L'API tourne sur une seule machine, sans Kubernetes (DEC-11, DEC-17). Notre retour arrière, c'est l'alias du Registry. Avec Kubernetes, on ferait un canary surveillé sur la latence, le taux d'erreur et le PSI (S6 p.34).

**Pourquoi l'API n'est-elle pas dans un conteneur ?** Elle tourne sur la machine, comme dans le lab 4 ; seule la stack de surveillance est en Docker Compose (DEC-11).

**Que feriez-vous avec un mois de plus ?** Lancer le contrôle chaque nuit (Airflow), instrumenter la couche 4 dès que les vraies valeurs arrivent, mettre la baseline dans le gate, et surveiller la v2 quand la demande reviendra entre avril et juin (`docs/soutenance.pdf`, slide 9).

## 5. Entraînement croisé et vérification

Chacun s'entraîne sur deux choix qu'il n'a pas faits lui-même (tâche 8.2). Proposition, à ajuster en séance :

| Membre | Choix 1 | Choix 2 |
| --- | --- | --- |
| Driss | Le découpage temporel | Le rollback par alias |
| Elimane | La MAE et la baseline | Pourquoi ni Kubernetes ni Airflow |
| Jérémy | Le PSI et le seuil de 0,25 | Le contrat de l'API |
| Matis | Le gate et le cooldown | L'arbre de décision appliqué à l'incident |

Vérification : chacun répond à trois questions tirées de la section 4, sur des parties qu'il n'a pas faites. On note le résultat ici.

| Membre | Questions tirées | Réponses justes |
| --- | --- | --- |
| Driss | | |
| Elimane | | |
| Jérémy | | |
| Matis | | |
