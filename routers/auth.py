"""Router: Authentication — GET/POST /login, GET /logout, GET /auth/linkedin, GET /auth/linkedin/callback"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from routers.shared import limiter, safe_error_message, templates
from utils.auth import authenticate_user, get_current_user

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Page de connexion"""
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authentification"""
    if authenticate_user(username, password):
        request.session["user"] = username
        return {"success": True, "redirect": "/"}
    else:
        return JSONResponse(
            {"detail": "Nom d'utilisateur ou mot de passe incorrect"}, status_code=401
        )


@router.get("/logout")
async def logout(request: Request):
    """Déconnexion"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/auth/linkedin")
async def linkedin_auth_start():
    """Demarre le flux OAuth LinkedIn"""
    from utils.linkedin_client import LinkedInClient, is_linkedin_configured

    if not is_linkedin_configured():
        return HTMLResponse(
            """
            <h1>LinkedIn OAuth non configure</h1>
            <p>Veuillez configurer les variables suivantes dans votre .env :</p>
            <ul>
                <li>LINKEDIN_CLIENT_ID</li>
                <li>LINKEDIN_CLIENT_SECRET</li>
                <li>LINKEDIN_REDIRECT_URI</li>
            </ul>
            <p>Consultez <a href="https://www.linkedin.com/developers/apps">LinkedIn Developers</a> pour créer une app.</p>
        """,
            status_code=400,
        )

    try:
        client = LinkedInClient()
        auth_url = client.get_auth_url()
        return RedirectResponse(auth_url)
    except Exception as e:
        return HTMLResponse(f"<h1>Erreur</h1><p>{safe_error_message(e)}</p>", status_code=500)


@router.get("/auth/linkedin/callback")
async def linkedin_auth_callback(
    code: str = None, error: str = None, error_description: str = None
):
    """Gere le callback OAuth LinkedIn"""
    from utils.linkedin_client import LinkedInClient

    if error:
        return HTMLResponse(
            f"""
            <h1>Erreur OAuth LinkedIn</h1>
            <p><strong>Erreur :</strong> {error}</p>
            <p><strong>Description :</strong> {error_description or 'N/A'}</p>
            <p><a href="/">Retour au dashboard</a></p>
        """,
            status_code=400,
        )

    if not code:
        return HTMLResponse(
            """
            <h1>Erreur OAuth LinkedIn</h1>
            <p>Code d autorisation manquant</p>
            <p><a href="/">Retour au dashboard</a></p>
        """,
            status_code=400,
        )

    try:
        client = LinkedInClient()
        token_data = client.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", "N/A")

        return HTMLResponse(
            f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>LinkedIn Connected!</title>
                <style>
                    body {{
                        font-family: 'Inter', sans-serif;
                        max-width: 800px;
                        margin: 50px auto;
                        padding: 20px;
                        background: #f8f9fa;
                    }}
                    .success {{
                        background: white;
                        padding: 30px;
                        border-radius: 12px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }}
                    h1 {{ color: #0a66c2; }}
                    code {{
                        background: #f0f0f0;
                        padding: 15px;
                        display: block;
                        border-radius: 8px;
                        margin: 15px 0;
                        font-family: monospace;
                        word-break: break-all;
                    }}
                    .btn {{
                        background: #0a66c2;
                        color: white;
                        padding: 12px 24px;
                        text-decoration: none;
                        border-radius: 8px;
                        display: inline-block;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="success">
                    <h1>✅ LinkedIn connecté avec succès !</h1>
                    <p>Votre application est maintenant autorisée à publier sur LinkedIn.</p>
                    <p><strong>Expire dans :</strong> {expires_in} secondes</p>

                    <h2>Configuration</h2>
                    <p>Ajoutez cette ligne à votre fichier <code>.env</code> :</p>
                    <code>LINKEDIN_ACCESS_TOKEN={access_token}</code>

                    <p><strong>Important :</strong> Ce token expire. Vous devrez répéter le processus OAuth lorsqu il expirera.</p>

                    <a href="/" class="btn">Retour au dashboard</a>
                </div>
            </body>
            </html>
        """
        )

    except Exception as e:
        return HTMLResponse(
            f"""
            <h1>Erreur lors de l echange du code</h1>
            <p>{safe_error_message(e)}</p>
            <p><a href="/">Retour au dashboard</a></p>
        """,
            status_code=500,
        )
