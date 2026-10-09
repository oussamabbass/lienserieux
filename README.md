# LienSérieux

Application de rencontres sérieuses — **100 % gratuite**.

Repo: https://github.com/oussamabbass/lienserieux

## Déployer sur Render (gratuit)

1. Va sur https://render.com et connecte ton GitHub
2. **New** → **Web Service**
3. Sélectionne le repo **lienserieux**
4. Réglages :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:app`
5. **Create Web Service**
6. Attends 2–5 min → tu reçois une URL publique

Ouvre cette URL sur ton téléphone.

## Lancer en local

```bash
pip install -r requirements.txt
python app.py
```

http://127.0.0.1:5000

## Fonctionnalités

- Inscription / connexion
- Découverte de profils
- Chat texte, vocal, photo, vidéo
- Suppression de messages
- Mode sombre
- Bouton Partager
- Premium (affichage seulement, tout est gratuit)
