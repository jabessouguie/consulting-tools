# Consulting Tools — Project Guidelines

## Commands

```bash
# Tests (toujours utiliser le venv)
.venv/bin/python3 -m pytest tests/ -q --tb=short

# Vérifier import app sans erreur
.venv/bin/python3 -c "from app import app; print('OK')"

# Lancer le serveur
.venv/bin/python3 -m uvicorn app:app --reload

# Linter / pre-commit
.venv/bin/python3 -m pre_commit run --all-files
```

## Baseline tests

**1578 passing, 66 pre-existing failures** — ne pas régresser.

Les 66 failures sont des problèmes connus (routes 404 dans test_settings + test_microsoft_api, openpyxl manquant dans test_tender_scout). Ne pas tenter de les corriger.

## Architecture — règles impératives

- **Toutes les nouvelles routes** vont dans `routers/<domain>.py`, jamais dans `app.py`
- **`routers/shared.py`** est la seule source pour : `jobs`, `limiter`, `templates`, `BASE_DIR`, `CONSULTANT_NAME`, `COMPANY_NAME`, `safe_error_message`, `safe_traceback`, `send_sse`
- **SSE streaming** : `send_sse(event, data)` de shared.py + `StreamingResponse`
- **Background jobs** : `threading.Thread(target=fn, daemon=True)` + `jobs[job_id]` dict
- **Auth** : `get_current_user(request)` depuis `utils/auth.py` — routes meeting-capture et elearning exigent ce guard

## Style de code

- **Venv obligatoire** : Python 3.13 dans `.venv/` — jamais `python3` système
- Pas de `except:` nu — toujours `except Exception as e:` ou exception spécifique
- `safe_error_message(e)` pour les réponses erreur client — jamais exposer le message brut
- `@limiter.limit("N/minute")` sur tous les endpoints de mutation
- Messages d'erreur UI en **français**

## Tests

- `asyncio_mode=auto` dans pytest.ini — pas besoin de `@pytest.mark.asyncio`
- `conftest.py` auto-mock `app.get_current_user` → `"test_admin"` pour tous les tests
- Tests non-authentifiés : re-patcher `app.get_current_user` à `None` dans le corps du test
- Quand on déplace du code vers un router : **mettre à jour les patches** `app.X` → `routers.<module>.X`
- La cible du patch = là où le nom est importé (pas où il est défini)

## Git / PR

- Branches : `feature/phase<N><lettre>-<description>` (ex: `feature/phase7b-routers-groupB`)
- PRs ciblent `dev` (pas `main`)
- Commits : message clair + `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`

## Gotchas

- `utils/__init__.py` et `agents/__init__.py` ré-exportent tout — une erreur de syntaxe dans n'importe quel module casse tous les tests
- `static/photos/` est créé au démarrage (upload de photos)
- Skills Market DB : patcher `routers.shared.skills_market_db` (plus `app.skills_market_db`)
- Meeting Capture : patcher `routers.meeting_capture.MeetingGmailClient` (plus `app.MeetingGmailClient`)
- LinkedIn : patcher `routers.linkedin.LinkedInClient` et `routers.linkedin.has_linkedin_access_token`
