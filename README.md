# LienSérieux

Application de rencontres sérieuses — **100 % gratuite**.

https://github.com/oussamabbass/lienserieux

## Déployer sur Render

1. https://render.com → compte GitHub
2. **New** → **Web Service** → repo **lienserieux**
3. Réglages :
   - **Build** : `pip install -r requirements.txt`
   - **Start** : `gunicorn bootstrap_google:app`
4. Variables d’environnement (optionnel, pour Google) :
   - `SECRET_KEY` = une longue chaîne secrète
   - `GOOGLE_CLIENT_ID` = ton ID client Google
   - `GOOGLE_CLIENT_SECRET` = ton secret Google
5. Create → URL publique

## Connexion Google (configurer)

1. https://console.cloud.google.com/
2. Crée un projet → APIs & Services → Credentials
3. **OAuth client ID** → type **Web application**
4. Authorized redirect URIs :
   `https://TON-APP.onrender.com/login/google/callback`
5. Copie Client ID et Client Secret dans Render (variables d’environnement)
6. Redeploy

Sans ces clés, le bouton Google n’apparaît pas (connexion classique reste dispo).

## Local

```bash
pip install -r requirements.txt
export GOOGLE_CLIENT_ID=...
export GOOGLE_CLIENT_SECRET=...
python app.py
```
