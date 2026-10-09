# LienSérieux

Application de rencontres sérieuses — 100 % gratuite.

## Lancer en local

```bash
pip install -r requirements.txt
python app.py
```

Ouvre http://127.0.0.1:5000

## Déployer sur Render

1. New → Web Service
2. Connecte ce repo
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn app:app`
5. Create

## Fonctionnalités

- Profils & découverte
- Chat texte, vocal, photo, vidéo
- Suppression de messages
- Mode sombre
- Partage
