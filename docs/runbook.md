# Runbook : rollback du modèle en production

À suivre dès qu'une promotion tourne mal, pour revenir à la version précédente en moins de 5 minutes (S6 p.36) ; cinq lignes, sur le modèle de S4 p.58.

1. **Symptôme** : dans `data/truth.csv`, depuis la promotion (`promote.py`), les prédictions de la nouvelle version (`model_version`) s'écartent plus de `y` que celles de l'ancienne (« Does it hurt? », S5 p.22), ou l'API ne sert pas la nouvelle version (`/health` répond 503 après la relance).
2. **Première vérification** : `curl localhost:8000/health` donne la version servie (`model_version`) ; `tail -n 1 data/promotions.jsonl` donne la dernière promotion (`from` → `to`).
3. **Commande** : dans le terminal 4, `uv run python rollback.py` pour revenir au `from` de la dernière promotion, ou `uv run python rollback.py VERSION` pour une version précise ; il remet l'alias `@production` sur cette version (S5 p.25 ; WRAP p.7), puis affiche « Relancer l'API ».
4. **Relance de l'API** : dans le terminal 2, pendant que `rollback.py` attend, Ctrl+C puis `uv run uvicorn app.main:app --port 8000` ; l'API ne charge `models:/taxi-demand@production` qu'au démarrage (S3 p.26, p.40 et p.41).
5. **Vérification de `/health`** : `rollback.py` interroge `/health` toutes les 2 s et affiche la durée dès que `model_version` est la version cible ; objectif : moins de 300 s (S6 p.36) ; s'il s'arrête en erreur au bout de 300 s, regarder les messages de l'API dans le terminal 2.
