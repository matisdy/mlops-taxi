# Données

## Source

NYC Taxi and Limousine Commission (TLC), Trip Record Data : https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page (taxis jaunes, un fichier Parquet par mois).

## Fichiers

Mois utilisés (`data.months` de `params.yaml`) : 2020-01, 2020-02 et 2020-03. Chaque fichier est téléchargé depuis le gabarit `data.url`, `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{month}.parquet`, vers `data/raw/yellow_tripdata_{month}.parquet`.

| Mois | Fichier | Taille | Lignes |
| --- | --- | --- | --- |
| 2020-01 | `yellow_tripdata_2020-01.parquet` | 93,6 Mo (93 562 858 octets) | 6 405 008 |
| 2020-02 | `yellow_tripdata_2020-02.parquet` | 92,1 Mo (92 134 881 octets) | 6 299 367 |
| 2020-03 | `yellow_tripdata_2020-03.parquet` | 44,4 Mo (44 442 590 octets) | 3 007 687 |
| Total | | 230,1 Mo | 15 712 062 |

Mesures du 21/11/2026 ; l'en-tête `Last-Modified` des trois fichiers sur le CDN de la TLC indique le 30/06/2022.

## Colonnes lues

Chaque fichier a 19 colonnes ; on n'en lit que deux (`pd.read_parquet(chemin, columns=[...])`) :

- `tpep_pickup_datetime` : date et heure de prise en charge, `datetime64[us]` sans fuseau, en heure locale de New York, sans conversion ;
- `PULocationID` : zone TLC de prise en charge, `int64`, de 1 à 265.

Aucune valeur manquante dans ces deux colonnes. 275 trajets ont une date avant le 2020-01-01 00:00 ou à partir du 2020-04-01 00:00 (177 dans le fichier de janvier, 44 dans celui de février, 54 dans celui de mars ; extrêmes : 2003-01-01 et 2021-01-02). La section 4 des Spécifications ne garde que les trajets du 2020-01-01 00:00 au 2020-03-31 23:59, dernière minute comprise (3 trajets ont lieu entre 23:59:00 et minuit le 31 mars).

## Reproduire

- `uv run python download.py` télécharge les fichiers absents de `data/raw/`, ne retélécharge pas un fichier présent et affiche la taille de chaque fichier.
- Les fichiers bruts ne sont jamais commités : DVC les suit, avec le pointeur `data/raw.dvc` et le remote local `../dvc-store`, un dossier à côté du dépôt. Le `.gitignore` les écarte avec `data/?*` et non `data/*` : avec `data/*`, DVC considère le dossier `data/` lui-même comme ignoré et ne trouve plus les pointeurs `data/*.dvc` (écart au §3 accepté le 21/11, tâche 1.1).
- Sur la machine qui a le dossier `dvc-store` à côté du dépôt, `uv run dvc pull` récupère les fichiers ; `uv run dvc status -c` répond alors « Cache and remote 'local' are in sync. ».
- Sur une autre machine, ce dossier n'existe pas (DEC-09) : `uv run python download.py`, puis `uv run dvc add data/raw` pour remplir le cache, vide sur un clone neuf (sans cela, `dvc status` affiche « not in cache », que les fichiers soient identiques ou non). La preuve est le pointeur : `git status --short data/raw.dvc` ne doit rien afficher (mêmes empreintes, donc mêmes octets) ; ne pas suivre le conseil « git add data/raw.dvc » que `dvc add` affiche toujours. `uv run dvc status data/raw.dvc` répond ensuite « Data and pipelines are up to date. » ; sans argument, `uv run dvc status` signale aussi `data/features.parquet` et `data/zones.json` « not in cache » : `build_dataset.py` les reconstruit, `dvc add` ne les a pas mis dans le cache. Si `data/raw.dvc` apparaît modifié, les fichiers de la TLC ont changé : ne pas le commiter, prévenir l'équipe.
