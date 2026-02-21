# 🛠️ Guide Technique - WEnvision Agents IA

**Pour développeurs et contributeurs**

---

## 🏗️ Architecture du projet

```
wenvision-agents/
├── agents/               # Agents IA (logique métier)
│   ├── article_generator.py
│   ├── proposal_generator.py
│   ├── training_slides_generator.py
│   └── ...
├── utils/               # Modules utilitaires
│   ├── llm_client.py        # Client LLM (Claude/Gemini)
│   ├── pptx_generator.py    # Génération PPTX
│   ├── pdf_converter.py     # Conversion PDF
│   ├── document_parser.py   # Parsing DOCX/PDF
│   └── google_api.py        # API Google (Docs/Slides)
├── templates/           # Templates HTML (Jinja2)
├── static/             # CSS, JS, assets
├── data/               # Données statiques (références, CVs, etc.)
├── output/             # Fichiers générés
├── app.py              # Application FastAPI
└── requirements.txt    # Dépendances Python
```

---

## 🚀 Stack Technique

- **Backend** : FastAPI (Python 3.12+)
- **Frontend** : HTML/CSS/JS vanilla (pas de framework)
- **LLM** : Claude Opus 4.6 (via Anthropic API) ou Gemini 1.5 Pro (via Google API)
- **Documents** : python-pptx, PyPDF2, python-docx
- **Streaming** : Server-Sent Events (SSE)

---

## 🤖 Créer un nouvel agent

### Étape 1 : Créer le fichier agent

Créez `agents/mon_agent.py` :

```python
"""
Description de l'agent
"""
import os
from typing import Dict, Any
from pathlib import Path
from utils.llm_client import LLMClient


class MonAgent:
    """Description de la classe"""

    def __init__(self):
        self.llm = LLMClient(max_tokens=4096)
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def process(self, input_data: str) -> Dict[str, Any]:
        """
        Traite l'input et génère un résultat

        Args:
            input_data: Données d'entrée

        Returns:
            Résultat structuré
        """
        system_prompt = """Tu es un expert en..."""

        prompt = f"""Génère... à partir de :

{input_data}

Consignes:
- ...
"""

        result = self.llm.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )

        # Sauvegarder le résultat
        output_dir = self.base_dir / "output"
        output_dir.mkdir(exist_ok=True)
        # ...

        return {
            "result": result,
            "metadata": {...}
        }
```

### Étape 2 : Créer les routes API

Dans `app.py`, ajoutez :

```python
@app.get("/mon-agent", response_class=HTMLResponse)
async def mon_agent_page(request: Request):
    return templates.TemplateResponse("mon-agent.html", {
        "request": request,
        "active": "mon-agent",
        "consultant_name": CONSULTANT_NAME,
    })


@app.post("/api/mon-agent/generate")
@limiter.limit("5/minute")
async def api_mon_agent_generate(
    request: Request,
    input_text: str = Form(...),
):
    """Lance le traitement"""
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "mon-agent",
        "status": "running",
        "steps": [],
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_mon_agent,
        args=(job_id, input_text),
        daemon=True,
    )
    thread.start()

    return {"job_id": job_id}


def _run_mon_agent(job_id: str, input_text: str):
    """Exécute l'agent en background"""
    job = jobs[job_id]

    try:
        from agents.mon_agent import MonAgent
        agent = MonAgent()

        job["steps"].append({"step": "process", "status": "active", "progress": 50})

        result = agent.process(input_text)

        job["steps"].append({"step": "process", "status": "done", "progress": 100})

        job["status"] = "done"
        job["result"] = result

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.get("/api/mon-agent/stream/{job_id}")
async def api_mon_agent_stream(job_id: str):
    """SSE stream pour la progression"""
    async def event_generator():
        job = jobs.get(job_id)
        if not job:
            yield send_sse("error_msg", {"message": "Job non trouvé"})
            return

        last_step_idx = 0
        while True:
            while last_step_idx < len(job["steps"]):
                step = job["steps"][last_step_idx]
                yield send_sse("step", step)
                last_step_idx += 1

            if job["status"] == "done":
                yield send_sse("result", job["result"])
                return
            elif job["status"] == "error":
                yield send_sse("error_msg", {"message": job["error"]})
                return

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

### Étape 3 : Créer le template HTML

Créez `templates/mon-agent.html` :

```html
{% extends "base.html" %}

{% block title %}Mon Agent{% endblock %}

{% block content %}
<div class="card">
    <div class="card-header">
        <div class="card-icon">🤖</div>
        <div>
            <div class="card-title">Mon Agent</div>
            <div class="card-subtitle">Description de l'agent</div>
        </div>
    </div>

    <form id="mon-agent-form">
        <div class="form-group">
            <label class="form-label">Input</label>
            <textarea class="form-textarea" id="input-text"
                      placeholder="Entrez vos données..."></textarea>
        </div>

        <button type="submit" class="btn btn-primary" id="generate-btn">
            🚀 Générer
        </button>
    </form>

    <div class="progress-container" id="progress">
        <div class="progress-bar-wrapper">
            <div class="progress-bar" id="progress-bar"></div>
        </div>
        <ul class="progress-steps">
            <li class="progress-step pending" data-step="process">
                <span class="step-icon">1</span>
                <span>Traitement</span>
            </li>
        </ul>
    </div>

    <div id="error-container"></div>
</div>

<div class="result-container" id="result">
    <div class="card">
        <div class="card-header">
            <div class="card-icon">✅</div>
            <div>
                <div class="card-title">Résultat</div>
            </div>
        </div>

        <div class="result-content" id="result-content"></div>

        <div class="result-actions">
            <button class="btn btn-copy" onclick="copyResult()">Copier</button>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    initMonAgentPage();
</script>
{% endblock %}
```

### Étape 4 : Ajouter le JavaScript

Dans `static/app.js` :

```javascript
function initMonAgentPage() {
    const form = document.getElementById('mon-agent-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const inputText = document.getElementById('input-text').value.trim();

        if (!inputText) {
            alert('Veuillez entrer des données.');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Génération...';

        const progress = document.getElementById('progress');
        progress.style.display = 'block';

        const formData = new FormData();
        formData.append('input_text', inputText);

        try {
            const response = await fetch('/api/mon-agent/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (data.job_id) {
                connectSSE('/api/mon-agent/stream/' + data.job_id, 'mon-agent');
            } else if (data.error) {
                showError('mon-agent', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 Générer';
            }
        } catch (err) {
            showError('mon-agent', 'Erreur: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = '🚀 Générer';
        }
    });
}

function displayMonAgentResult(data) {
    const resultSection = document.getElementById('result');
    const resultContent = document.getElementById('result-content');
    const progress = document.getElementById('progress');

    if (progress) progress.style.display = 'none';

    // Afficher le résultat
    if (resultContent && data.result) {
        resultContent.innerHTML = marked.parse(data.result);
    }

    // Stocker pour copie
    window.currentMonAgentData = data;

    resultSection.classList.add('active');
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function copyResult() {
    if (!window.currentMonAgentData) {
        alert('Aucun résultat à copier.');
        return;
    }

    navigator.clipboard.writeText(window.currentMonAgentData.result)
        .then(() => {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '✅ Copié !';
            setTimeout(() => btn.textContent = originalText, 2000);
        })
        .catch(err => alert('Erreur: ' + err.message));
}

window.initMonAgentPage = initMonAgentPage;
window.copyResult = copyResult;
```

### Étape 5 : Mettre à jour connectSSE

Dans `static/app.js`, ajoutez le cas dans `connectSSE()` :

```javascript
} else if (pageType === 'mon-agent') {
    displayMonAgentResult(data);
    const form = document.getElementById('mon-agent-form');
    if (form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        resetButton(submitBtn, '🚀 Générer');
    }
```

### Étape 6 : Ajouter dans la navbar

Dans `templates/base.html`, ajoutez :

```html
<a href="/mon-agent" class="nav-link {% if active == 'mon-agent' %}active{% endif %}">Mon Agent</a>
```

---

## 📊 Génération de slides PPTX

### Utiliser le générateur PPTX

```python
from utils.pptx_generator import ProposalPPTXGenerator

gen = ProposalPPTXGenerator('WENVISION_Template_Palette 2026.pptx')

# Slide de couverture
gen.add_cover_slide(
    client_name="Client XYZ",
    project_title="Transformation Data",
    date="Février 2026",
    consultant_name="Jean-Sébastien Abessouguie"
)

# Slide de section
gen.add_section_slide("Contexte", section_number=1)

# Slide de contenu
gen.add_content_slide(
    title="Enjeux",
    bullet_points=["Enjeu 1", "Enjeu 2", "Enjeu 3"]
)

# Slide avec stat impactante
gen.add_stat_slide(
    stat_value="67%",
    stat_label="de ROI attendu",
    context="Source : étude interne"
)

# Slide avec citation
gen.add_quote_slide(
    quote_text="La donnée est le nouveau pétrole",
    author="Clive Humby"
)

# Slide highlight (points clés)
gen.add_highlight_slide(
    title="3 piliers",
    key_points=["Pilier 1", "Pilier 2", "Pilier 3"],
    highlight_color="corail"
)

# Slide diagramme
gen.add_diagram_slide(
    title="Notre démarche",
    diagram_type="flow",  # flow, cycle, pyramid, timeline, matrix
    elements=["Étape 1", "Étape 2", "Étape 3"]
)

# Slide de clôture
gen.add_closing_slide(
    consultant_name="Jean-Sébastien Abessouguie",
    company="Wenvision"
)

# Sauvegarder
gen.save('output/ma_presentation.pptx')
```

### Types de diagrammes disponibles

- **flow** : Flux linéaire horizontal
- **cycle** : Processus circulaire (cercle)
- **pyramid** : Hiérarchie pyramidale
- **timeline** : Timeline horizontale
- **matrix** : Grille 2x2 ou 2x3

### Palette de couleurs Wenvision

```python
COLORS = {
    'anthracite': RGBColor(0x3A, 0x3A, 0x3B),
    'noir_profond': RGBColor(0x1F, 0x1F, 0x1F),
    'gris_moyen': RGBColor(0x47, 0x47, 0x47),
    'gris_clair': RGBColor(0xEE, 0xEE, 0xEE),
    'rose_poudre': RGBColor(0xFB, 0xF0, 0xF4),
    'terracotta': RGBColor(0xC0, 0x50, 0x4D),
    'corail': RGBColor(0xFF, 0x6B, 0x58),
    'blanc': RGBColor(0xFF, 0xFF, 0xFF),
}
```

---

## 🤝 Client LLM

### Utilisation

```python
from utils.llm_client import LLMClient

# Initialiser (Claude par défaut)
llm = LLMClient(max_tokens=4096)

# Génération simple
response = llm.generate(
    prompt="Écris un article sur l'IA",
    system_prompt="Tu es un expert en IA",
    temperature=0.7
)

# Génération avec contexte (conversation)
messages = [
    {"role": "user", "content": "Bonjour"},
    {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"},
    {"role": "user", "content": "Parle-moi de l'IA"}
]

response = llm.generate_with_context(
    messages=messages,
    system_prompt="Tu es un expert en IA",
    temperature=0.7
)

# Extraction de données structurées (JSON)
data = llm.extract_structured_data(
    prompt="Extrais les infos de ce texte : ...",
    output_schema={"name": "str", "age": "int"}
)
```

### Changer de modèle LLM

Dans `.env` :

```env
# Utiliser Claude (par défaut)
USE_GEMINI=false
ANTHROPIC_API_KEY=your-claude-key

# OU utiliser Gemini
USE_GEMINI=true
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-1.5-pro
```

---

## 🔄 Conversion de formats

### PDF

```python
from utils.pdf_converter import pdf_converter

# PPTX → PDF
pdf_path = pdf_converter.pptx_to_pdf('output/ma_pres.pptx')

# Markdown → PDF
pdf_path = pdf_converter.markdown_to_pdf('output/article.md')

# Vérifier les capacités
capabilities = pdf_converter.is_pdf_conversion_available()
# {'pptx_to_pdf': True, 'markdown_to_pdf': False}
```

### Parsing de documents

```python
from utils.document_parser import document_parser

# Auto-détection du format
text = document_parser.parse_file('programme.docx')  # ou .pdf, .txt, .md

# Vérifier le support
is_supported = document_parser.is_format_supported('.docx')  # True

# Voir les bibliothèques nécessaires
status = document_parser.get_required_libraries()
# {'pdf': True, 'docx': False, 'txt': True, 'md': True}
```

---

## 🧪 Tests et Debugging

### Activer le mode debug

Dans `app.py`, changez :

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5678, reload=True)  # reload=True pour hot-reload
```

### Logs

Les logs sont affichés dans le terminal où vous avez lancé `python3.12 app.py`.

Ajoutez des prints pour debugger :

```python
print(f"🔍 Debug: {ma_variable}")
```

### Tester un agent isolément

```python
# test_mon_agent.py
from agents.mon_agent import MonAgent

agent = MonAgent()
result = agent.process("Test input")
print(result)
```

---

## 📦 Dépendances

### Ajouter une nouvelle dépendance

1. Installez : `pip install ma-bibliotheque`
2. Ajoutez dans `requirements.txt` : `ma-bibliotheque==1.2.3`
3. Committez le fichier

### Mettre à jour les dépendances

```bash
pip install --upgrade -r requirements.txt
```

---

## 🚢 Déploiement

### En local (développement)

```bash
python3.12 app.py
```

### Avec Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5678

CMD ["python", "app.py"]
```

Build et run :

```bash
docker build -t wenvision-agents .
docker run -p 5678:5678 -v $(pwd)/output:/app/output wenvision-agents
```

---

## 🛡️ Bonnes pratiques

### Sécurité

- ✅ Ne jamais committer les clés API (`.env` dans `.gitignore`)
- ✅ Valider les inputs utilisateur
- ✅ Limiter la taille des uploads (déjà en place)
- ✅ Rate limiting sur les routes API (déjà en place)

### Performance

- ✅ Utiliser le streaming SSE pour les tâches longues
- ✅ Exécuter les agents en background (threading)
- ✅ Nettoyer les fichiers temporaires
- ✅ Limiter la taille des prompts LLM (truncate si nécessaire)

### Code Quality

- ✅ Docstrings pour toutes les fonctions
- ✅ Type hints Python
- ✅ Noms de variables explicites
- ✅ Fonctions < 50 lignes
- ✅ DRY (Don't Repeat Yourself)

---

## 📚 Ressources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Google Gemini API](https://ai.google.dev/)
- [python-pptx Documentation](https://python-pptx.readthedocs.io/)

---

**Version** : 1.0
**Dernière mise à jour** : 17 février 2026
