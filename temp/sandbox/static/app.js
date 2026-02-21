/* ===========================
   WEnvision Agents - Frontend JS
   =========================== */

// === GLOBAL MODEL SELECTOR ===

(function initModelSelector() {
    const selector = document.getElementById('model-selector');
    if (!selector) return;

    fetch('/api/settings/model')
        .then(r => r.json())
        .then(data => {
            if (data.current_model) {
                selector.value = data.current_model;
            }
        })
        .catch(() => {});
})();

function changeGeminiModel(model) {
    fetch('/api/settings/model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: model })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const selector = document.getElementById('model-selector');
            selector.style.borderColor = '#4CAF50';
            setTimeout(() => { selector.style.borderColor = ''; }, 1500);
        }
    })
    .catch(err => console.error('Model change error:', err));
}

// === PROPOSAL PAGE ===

function initProposalPage() {
    const form = document.getElementById('proposal-form');
    const fileUpload = document.getElementById('file-upload-zone');
    const fileInput = document.getElementById('tender-file');
    const fileNameEl = document.getElementById('file-name');

    // File upload handling
    fileUpload.addEventListener('click', () => fileInput.click());
    fileUpload.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileUpload.style.borderColor = 'var(--corail)';
    });
    fileUpload.addEventListener('dragleave', () => {
        fileUpload.style.borderColor = '';
    });
    fileUpload.addEventListener('drop', (e) => {
        e.preventDefault();
        fileUpload.style.borderColor = '';
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });
    fileInput.addEventListener('change', handleFileSelect);

    function handleFileSelect() {
        if (fileInput.files.length) {
            const name = fileInput.files[0].name;
            fileNameEl.textContent = name;
            fileUpload.classList.add('has-file');
        }
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const tenderText = document.getElementById('tender-text').value;
        const file = fileInput.files[0];

        if (!tenderText.trim() && !file) {
            showError('proposal', 'Veuillez coller un appel d\'offre ou uploader un fichier.');
            return;
        }

        const btn = document.getElementById('generate-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Generation en cours...';

        showProgress('proposal');
        clearError('proposal');

        const formData = new FormData();
        if (file) {
            formData.append('file', file);
        } else {
            formData.append('tender_text', tenderText);
        }

        try {
            const response = await fetch('/api/proposal/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.job_id) {
                currentJobId = data.job_id;
                connectSSE('/api/proposal/stream/' + data.job_id, 'proposal');
            } else if (data.error) {
                showError('proposal', data.error);
                resetButton(btn, 'Generer la proposition');
            }
        } catch (err) {
            showError('proposal', 'Erreur de connexion au serveur: ' + err.message);
            resetButton(btn, 'Generer la proposition');
        }
    });
}


// === LINKEDIN PAGE ===

function initLinkedInPage() {
    const form = document.getElementById('linkedin-form');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const postType = document.getElementById('post-type').value;
        const numPosts = document.getElementById('num-posts').value;

        const btn = document.getElementById('linkedin-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Veille en cours...';

        showProgress('linkedin');
        clearError('linkedin');

        try {
            const response = await fetch('/api/linkedin/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    post_type: postType,
                    num_posts: parseInt(numPosts)
                })
            });

            const data = await response.json();

            if (data.job_id) {
                currentJobId = data.job_id;
                connectSSE('/api/linkedin/stream/' + data.job_id, 'linkedin');
            } else if (data.error) {
                showError('linkedin', data.error);
                resetButton(btn, 'Lancer la veille + generation');
            }
        } catch (err) {
            showError('linkedin', 'Erreur de connexion: ' + err.message);
            resetButton(btn, 'Lancer la veille + generation');
        }
    });
}


// === ARTICLE PAGE ===

function initArticlePage() {
    const form = document.getElementById('article-form');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const url = document.getElementById('article-url').value.trim();
        const tone = document.getElementById('tone').value;

        if (!url) {
            showError('article', 'Veuillez saisir une URL d\'article.');
            return;
        }

        const btn = document.getElementById('article-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Generation en cours...';

        showProgress('article');
        clearError('article');

        try {
            const response = await fetch('/api/article/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, tone: tone })
            });

            const data = await response.json();

            if (data.job_id) {
                currentJobId = data.job_id;
                connectSSE('/api/article/stream/' + data.job_id, 'article');
            } else if (data.error) {
                showError('article', data.error);
                resetButton(btn, 'Generer le post');
            }
        } catch (err) {
            showError('article', 'Erreur de connexion: ' + err.message);
            resetButton(btn, 'Generer le post');
        }
    });
}


// === MEETING PAGE ===

function initMeetingPage() {
    const form = document.getElementById('meeting-form');
    const fileUpload = document.getElementById('file-upload-zone');
    const fileInput = document.getElementById('transcript-file');
    const fileNameEl = document.getElementById('file-name');

    // File upload handling
    if (fileUpload && fileInput) {
        fileUpload.addEventListener('click', () => fileInput.click());
        fileUpload.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileUpload.style.borderColor = 'var(--corail)';
        });
        fileUpload.addEventListener('dragleave', () => {
            fileUpload.style.borderColor = '';
        });
        fileUpload.addEventListener('drop', (e) => {
            e.preventDefault();
            fileUpload.style.borderColor = '';
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                handleMeetingFileSelect();
            }
        });
        fileInput.addEventListener('change', handleMeetingFileSelect);

        function handleMeetingFileSelect() {
            if (fileInput.files.length && fileNameEl) {
                fileNameEl.textContent = fileInput.files[0].name;
                fileUpload.classList.add('has-file');
            }
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const transcript = document.getElementById('transcript-text').value;
        const file = fileInput ? fileInput.files[0] : null;

        if (!transcript.trim() && !file) {
            alert('Veuillez coller un transcript ou uploader un fichier.');
            return;
        }

        const btn = form.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Generation en cours...';

        const progress = document.getElementById('progress');
        if (progress) progress.style.display = 'block';

        const formData = new FormData();
        if (file) {
            formData.append('file', file);
        } else {
            formData.append('transcript_text', transcript);
        }

        try {
            const response = await fetch('/api/meeting/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.job_id) {
                currentJobId = data.job_id;
                connectSSE('/api/meeting/stream/' + data.job_id, 'meeting');
            } else if (data.error) {
                alert('Erreur: ' + data.error);
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        } catch (err) {
            alert('Erreur de connexion: ' + err.message);
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });
}


// === SSE (Server-Sent Events) ===

function connectSSE(url, pageType) {
    const evtSource = new EventSource(url);

    evtSource.addEventListener('step', (e) => {
        const data = JSON.parse(e.data);
        updateStep(data.step, data.status);
        updateProgressBar(data.progress || 0);
    });

    evtSource.addEventListener('result', (e) => {
        const data = JSON.parse(e.data);
        evtSource.close();

        // Store current result for feedback loop
        currentResult = data;

        if (pageType === 'proposal') {
            displayProposalResult(data);
            resetButton(document.getElementById('generate-btn'), 'Generer la proposition');
            resetButton(document.getElementById('regenerate-proposal-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'article') {
            displayArticleResult(data);
            resetButton(document.getElementById('article-btn'), 'Generer le post');
            resetButton(document.getElementById('regenerate-article-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'meeting') {
            displayMeetingResult(data);
        } else if (pageType === 'comment') {
            displayCommentResult(data);
            const form = document.getElementById('comment-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer les commentaires');
            }
            resetButton(document.getElementById('regenerate-comment-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'techwatch') {
            displayTechWatchResult(data);
            const form = document.getElementById('techwatch-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer le digest');
            }
            resetButton(document.getElementById('regenerate-techwatch-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'dataset') {
            displayDatasetResult(data);
            const form = document.getElementById('dataset-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Analyser le dataset');
            }
            resetButton(document.getElementById('regenerate-dataset-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'workshop') {
            displayWorkshopResult(data);
            const form = document.getElementById('workshop-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer le plan');
            }
            resetButton(document.getElementById('regenerate-workshop-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'rfp') {
            displayRFPResult(data);
            const form = document.getElementById('rfp-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer la réponse');
            }
            resetButton(document.getElementById('regenerate-rfp-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'proposal_section') {
            displayProposalSectionResult(data);
            // Progress is hidden in the display function
        } else if (pageType === 'formation') {
            displayFormationResult(data);
            const formForm = document.getElementById('formation-form');
            if (formForm) {
                const submitBtn = formForm.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer le programme');
            }
            resetButton(document.getElementById('regenerate-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'training_slides') {
            displayTrainingSlidesResult(data);
            const tsForm = document.getElementById('training-form');
            if (tsForm) {
                const submitBtn = tsForm.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer toutes les slides');
            }
        } else if (pageType === 'article-generator') {
            displayArticleGeneratorResult(data);
            const agForm = document.getElementById('article-form');
            if (agForm) {
                const submitBtn = agForm.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer l\'article');
            }
            resetButton(document.getElementById('regenerate-article-btn'), 'Regenerer avec feedback');
        } else if (pageType === 'doc-to-presentation') {
            displayDocToPresentationResult(data);
        } else {
            displayLinkedInResult(data);
            resetButton(document.getElementById('linkedin-btn'), 'Lancer la veille + generation');
            resetButton(document.getElementById('regenerate-linkedin-btn'), 'Regenerer avec feedback');
        }
    });

    evtSource.addEventListener('error_msg', (e) => {
        const data = JSON.parse(e.data);
        evtSource.close();
        showError(pageType, data.message);

        if (pageType === 'proposal') {
            resetButton(document.getElementById('generate-btn'), 'Generer la proposition');
        } else if (pageType === 'article') {
            resetButton(document.getElementById('article-btn'), 'Generer le post');
        } else if (pageType === 'meeting') {
            resetButton(document.getElementById('meeting-btn'), 'Generer le compte rendu');
        } else if (pageType === 'comment') {
            const form = document.getElementById('comment-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer les commentaires');
            }
        } else if (pageType === 'techwatch') {
            const form = document.getElementById('techwatch-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer le digest');
            }
        } else if (pageType === 'dataset') {
            const form = document.getElementById('dataset-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Analyser le dataset');
            }
        } else if (pageType === 'workshop') {
            const form = document.getElementById('workshop-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer le plan');
            }
        } else if (pageType === 'rfp') {
            const form = document.getElementById('rfp-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, 'Generer la réponse');
            }
        } else if (pageType === 'article-generator') {
            const form = document.getElementById('article-form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                resetButton(submitBtn, '✍️ Générer l\'article');
            }
        } else {
            resetButton(document.getElementById('linkedin-btn'), 'Lancer la veille + generation');
        }
    });

    evtSource.onerror = () => {
        evtSource.close();
    };
}


// === PROGRESS UI ===

function showProgress(pageType) {
    const container = document.getElementById('progress');
    container.classList.add('active');

    // Reset all steps
    container.querySelectorAll('.progress-step').forEach(step => {
        step.className = 'progress-step pending';
    });

    updateProgressBar(0);
}

function updateStep(stepName, status) {
    const step = document.querySelector(`[data-step="${stepName}"]`);
    if (step) {
        step.className = `progress-step ${status}`;
    }
}

function updateProgressBar(percent) {
    const bar = document.getElementById('progress-bar');
    if (bar) {
        bar.style.width = percent + '%';
    }
}


// === DISPLAY RESULTS ===

function displayProposalResult(data) {
    const container = document.getElementById('result');
    const content = document.getElementById('result-content');
    const title = document.getElementById('result-title');
    const subtitle = document.getElementById('result-subtitle');

    title.textContent = 'Proposition: ' + (data.client_name || 'Projet');
    subtitle.textContent = 'Generee le ' + new Date().toLocaleDateString('fr-FR');

    // Render markdown
    content.innerHTML = marked.parse(data.content || '');
    content.dataset.raw = data.content || '';

    // Download links
    if (data.md_path) {
        document.getElementById('download-md').href = '/api/download?path=' + encodeURIComponent(data.md_path);
    }
    if (data.json_path) {
        document.getElementById('download-json').href = '/api/download?path=' + encodeURIComponent(data.json_path);
    }
    if (data.pptx_path) {
        const pptxBtn = document.getElementById('download-pptx');
        pptxBtn.href = '/api/download?path=' + encodeURIComponent(data.pptx_path);
        pptxBtn.style.display = 'inline-block';
    }

    container.classList.add('active');
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayLinkedInResult(data) {
    const container = document.getElementById('result');
    const postsContainer = document.getElementById('posts-container');

    postsContainer.innerHTML = '';

    // Display posts
    const posts = data.posts || [];
    posts.forEach((post, index) => {
        const card = document.createElement('div');
        card.className = 'post-card';
        card.innerHTML = `
            <div class="post-card-header">
                <span class="post-type-badge ${post.post_type}">${post.post_type}</span>
                <button class="btn btn-copy" onclick="copyPost(this, ${index})">Copier</button>
            </div>
            <div class="post-content" id="post-${index}">${escapeHtml(post.main_post)}</div>
            ${post.source_articles && post.source_articles.length ? `
            <div style="font-size: 0.8rem; color: var(--gris-moyen); margin-top: 0.75rem;">
                <strong>Sources:</strong>
                ${post.source_articles.map(a => `<a href="${a.link}" target="_blank" style="color: var(--corail);">${a.title}</a>`).join(' | ')}
            </div>` : ''}
        `;
        postsContainer.appendChild(card);
    });

    // Display articles
    const articles = data.articles || [];
    if (articles.length > 0) {
        const section = document.getElementById('articles-section');
        section.style.display = 'block';
        document.getElementById('articles-count').textContent = articles.length + ' articles pertinents';

        const list = document.getElementById('articles-list');
        list.innerHTML = '';
        articles.slice(0, 15).forEach(article => {
            const item = document.createElement('div');
            item.className = 'article-item';
            item.innerHTML = `
                <div class="article-title">
                    <a href="${article.link}" target="_blank">${escapeHtml(article.title)}</a>
                </div>
                <span class="article-source">${escapeHtml(article.source || article.source_type || '')}</span>
                ${article.relevance_score ? `<span class="article-score"> &bull; Score: ${(article.relevance_score * 100).toFixed(0)}%</span>` : ''}
            `;
            list.appendChild(item);
        });
    }

    container.classList.add('active');
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


function displayArticleResult(data) {
    const container = document.getElementById('result');

    // Tone badge
    const toneBadge = document.getElementById('tone-badge');
    toneBadge.textContent = data.tone || 'expert';

    // Article title label
    const titleLabel = document.getElementById('article-title-label');
    titleLabel.textContent = data.article_title || '';

    // Main post
    document.getElementById('main-post-content').innerText = data.main_post || '';

    // Short post
    document.getElementById('short-post-content').innerText = data.short_version || '';

    // Article links
    const articleUrl = data.article_url || '#';
    const linkEl = document.getElementById('article-link');
    linkEl.href = articleUrl;
    linkEl.textContent = articleUrl;

    const linkShortEl = document.getElementById('article-link-short');
    linkShortEl.href = articleUrl;
    linkShortEl.textContent = articleUrl;

    container.classList.add('active');
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayMeetingResult(data) {
    const container = document.getElementById('result');
    const progress = document.getElementById('progress');

    if (progress) progress.style.display = 'none';

    // Afficher le compte rendu (en markdown converti en HTML)
    const minutesPreview = document.getElementById('minutes-preview');
    if (minutesPreview && data.minutes) {
        minutesPreview.innerHTML = marked.parse(data.minutes);
    }

    // Afficher l'email (objet et corps)
    const emailSubject = document.getElementById('email-subject');
    const emailBody = document.getElementById('email-body');

    if (data.email) {
        if (emailSubject) {
            emailSubject.textContent = data.email.subject || 'Compte rendu de réunion';
        }
        if (emailBody) {
            emailBody.innerHTML = marked.parse(data.email.body || '');
        }
    }

    // Lien de téléchargement
    const downloadBtn = document.getElementById('download-md');
    if (downloadBtn && data.md_path) {
        downloadBtn.href = '/api/download?path=' + encodeURIComponent(data.md_path);
        downloadBtn.style.display = 'inline-block';
    }

    // Afficher le résultat
    container.classList.add('active');
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Réinitialiser le bouton submit
    const form = document.getElementById('meeting-form');
    if (form) {
        const btn = form.querySelector('button[type="submit"]');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Générer le compte rendu';
        }
    }
}

function copyMinutes() {
    const content = document.getElementById('minutes-preview');
    if (content) {
        const text = content.innerText || content.textContent;
        navigator.clipboard.writeText(text).then(() => {
            alert('Compte rendu copié !');
        });
    }
}

function copyEmail() {
    const subject = document.getElementById('email-subject');
    const body = document.getElementById('email-body');
    if (subject && body) {
        const subjectText = subject.textContent || subject.innerText;
        const bodyText = body.textContent || body.innerText;
        const fullEmail = `Objet: ${subjectText}\n\n${bodyText}`;
        navigator.clipboard.writeText(fullEmail).then(() => {
            alert('Email copié !');
        });
    }
}

function shareByEmail() {
    const content = document.getElementById('email-content').innerText;

    // Extraire l'objet et le corps du mail
    let subject = 'Compte rendu de réunion';
    let body = content;

    // Le format typique est : "**Objet :** ..." ou "Objet: ..." suivi du corps
    const lines = content.split('\n');

    // Trouver la ligne de l'objet
    for (let i = 0; i < Math.min(lines.length, 5); i++) {
        const line = lines[i].trim();
        // Matcher "**Objet :**", "Objet:", "Subject:", etc.
        const match = line.match(/^\*?\*?(Objet|Subject)\s*:?\*?\*?\s*(.+)$/i);
        if (match) {
            subject = match[2].trim();
            // Le corps commence après l'objet (sauter les lignes vides)
            let bodyStartIdx = i + 1;
            while (bodyStartIdx < lines.length && lines[bodyStartIdx].trim() === '') {
                bodyStartIdx++;
            }
            body = lines.slice(bodyStartIdx).join('\n').trim();
            break;
        }
    }

    // Nettoyer le corps : enlever les séparateurs markdown
    body = body.replace(/^---+$/gm, '').trim();

    // Encoder pour mailto
    const mailtoLink = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

    // Ouvrir le client mail
    window.location.href = mailtoLink;
}

function copyMainPost() {
    const content = document.getElementById('main-post-content').innerText;
    const link = document.getElementById('article-link').href;
    navigator.clipboard.writeText(content + '\n\n' + link).then(() => {
        const btn = document.querySelector('#main-post-card .btn-copy');
        btn.textContent = 'Copie !';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Copier'; btn.classList.remove('copied'); }, 2000);
    });
}

function copyShortPost() {
    const content = document.getElementById('short-post-content').innerText;
    const link = document.getElementById('article-link-short').href;
    navigator.clipboard.writeText(content + '\n\n' + link).then(() => {
        const btn = document.querySelector('#short-post-card .btn-copy');
        btn.textContent = 'Copie !';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Copier'; btn.classList.remove('copied'); }, 2000);
    });
}


// === UTILITY FUNCTIONS ===

function copyResult() {
    const content = document.getElementById('result-content');
    const raw = content.dataset.raw || content.innerText;
    navigator.clipboard.writeText(raw).then(() => {
        const btn = content.closest('.card').querySelector('.btn-copy');
        btn.textContent = 'Copie !';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = 'Copier le texte';
            btn.classList.remove('copied');
        }, 2000);
    });
}

function copyPost(btn, index) {
    const post = document.getElementById('post-' + index);
    navigator.clipboard.writeText(post.innerText).then(() => {
        btn.textContent = 'Copie !';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = 'Copier';
            btn.classList.remove('copied');
        }, 2000);
    });
}

function showError(pageType, message) {
    const container = document.getElementById('error-container');
    container.innerHTML = `<div class="alert alert-error">${escapeHtml(message)}</div>`;
}

function clearError(pageType) {
    const container = document.getElementById('error-container');
    container.innerHTML = '';
}

function resetButton(btn, text) {
    btn.disabled = false;
    btn.innerHTML = text;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// === FEEDBACK LOOP ===

let currentJobId = null;
let currentResult = null;

function submitFeedback(pageType) {
    const feedbackTextarea = document.getElementById(`${pageType}-feedback`);
    const feedback = feedbackTextarea.value.trim();

    if (!feedback) {
        showError(pageType, 'Veuillez saisir un feedback.');
        return;
    }

    if (!currentResult) {
        showError(pageType, 'Aucun resultat a regenerer.');
        return;
    }

    const btn = document.getElementById(`regenerate-${pageType}-btn`);
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Regeneration en cours...';

    showProgress(pageType);
    clearError(pageType);

    if (pageType === 'proposal') {
        regenerateProposal(feedback);
    } else if (pageType === 'linkedin') {
        regenerateLinkedIn(feedback);
    } else if (pageType === 'article') {
        regenerateArticle(feedback);
    } else if (pageType === 'meeting') {
        regenerateMeeting(feedback);
    } else if (pageType === 'comment') {
        regenerateComment(feedback);
    } else if (pageType === 'techwatch') {
        regenerateTechWatch(feedback);
    } else if (pageType === 'dataset') {
        regenerateDataset(feedback);
    } else if (pageType === 'workshop') {
        regenerateWorkshop(feedback);
    } else if (pageType === 'rfp') {
        regenerateRFP(feedback);
    } else if (pageType === 'article-generator') {
        regenerateArticleGenerator(feedback);
    }
}

async function regenerateProposal(feedback) {
    try {
        const response = await fetch('/api/proposal/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_content: currentResult.content || '',
                job_id: currentJobId,
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/proposal/stream/' + data.job_id, 'proposal');
        } else if (data.error) {
            showError('proposal', data.error);
            resetButton(document.getElementById('regenerate-proposal-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('proposal', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-proposal-btn'), 'Regenerer avec feedback');
    }
}

async function regenerateLinkedIn(feedback) {
    try {
        const response = await fetch('/api/linkedin/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_posts: currentResult.posts || [],
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/linkedin/stream/' + data.job_id, 'linkedin');
        } else if (data.error) {
            showError('linkedin', data.error);
            resetButton(document.getElementById('regenerate-linkedin-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('linkedin', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-linkedin-btn'), 'Regenerer avec feedback');
    }
}

async function regenerateArticle(feedback) {
    try {
        const response = await fetch('/api/article/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_main: currentResult.main_post || '',
                previous_short: currentResult.short_version || '',
                article_url: currentResult.article_url || '',
                tone: currentResult.tone || 'expert',
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/article/stream/' + data.job_id, 'article');
        } else if (data.error) {
            showError('article', data.error);
            resetButton(document.getElementById('regenerate-article-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('article', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-article-btn'), 'Regenerer avec feedback');
    }
}

async function regenerateMeeting(feedback) {
    try {
        const response = await fetch('/api/meeting/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_minutes: currentResult.minutes || '',
                previous_email: currentResult.email || '',
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/meeting/stream/' + data.job_id, 'meeting');
        } else if (data.error) {
            showError('meeting', data.error);
            resetButton(document.getElementById('regenerate-meeting-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('meeting', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-meeting-btn'), 'Regenerer avec feedback');
    }
}

async function regenerateComment(feedback) {
    try {
        const response = await fetch('/api/comment/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_short: currentResult.short || '',
                previous_medium: currentResult.medium || '',
                previous_long: currentResult.long || '',
                post_preview: currentResult.post_preview || '',
                style: currentResult.style || 'insightful',
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/comment/stream/' + data.job_id, 'comment');
        } else if (data.error) {
            showError('comment', data.error);
            resetButton(document.getElementById('regenerate-comment-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('comment', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-comment-btn'), 'Regenerer avec feedback');
    }
}

// === COMMENT PAGE ===

function initCommentPage() {
    const form = document.getElementById('comment-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const postInput = document.getElementById('post-input').value.trim();
        const style = document.getElementById('comment-style').value;

        if (!postInput) {
            alert('Veuillez fournir un post LinkedIn.');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Génération...';

        try {
            const response = await fetch('/api/comment/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    post_input: postInput,
                    style: style
                })
            });

            const data = await response.json();

            if (data.job_id) {
                connectSSE('/api/comment/stream/' + data.job_id, 'comment');
            } else if (data.error) {
                showError('comment', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Générer les commentaires';
            }
        } catch (err) {
            showError('comment', 'Erreur de connexion: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Générer les commentaires';
        }
    });
}

function displayCommentResult(data) {
    const resultSection = document.getElementById('result-section');
    const progressSection = document.getElementById('progress-section');

    progressSection.style.display = 'none';
    resultSection.style.display = 'block';

    // Post preview
    document.getElementById('post-preview').textContent = data.post_preview || '';

    // Short comment
    const shortBox = document.getElementById('comment-short');
    shortBox.textContent = data.short || '';
    document.getElementById('count-short').textContent = (data.short || '').length;

    // Medium comment
    const mediumBox = document.getElementById('comment-medium');
    mediumBox.textContent = data.medium || '';
    document.getElementById('count-medium').textContent = (data.medium || '').length;

    // Long comment
    const longBox = document.getElementById('comment-long');
    longBox.textContent = data.long || '';
    document.getElementById('count-long').textContent = (data.long || '').length;

    // Reset form
    const form = document.getElementById('comment-form');
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Générer les commentaires';

    // Scroll to result
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function copyComment(variant) {
    const commentBox = document.getElementById('comment-' + variant);
    const text = commentBox.textContent;

    navigator.clipboard.writeText(text).then(() => {
        // Visual feedback
        const btn = event.target.closest('button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '✅ Copié !';
        btn.style.backgroundColor = '#22c55e';

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.backgroundColor = '';
        }, 2000);
    }).catch(err => {
        alert('Erreur lors de la copie: ' + err);
    });
}

// === TECH WATCH PAGE ===

function initTechWatchPage() {
    const form = document.getElementById('techwatch-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const keywords = document.getElementById('keywords').value.trim();
        const days = document.getElementById('days').value;
        const periodType = document.getElementById('period-type').value;

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Génération...';

        // Show progress
        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('result-section').style.display = 'none';

        try {
            const response = await fetch('/api/techwatch/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    keywords: keywords,
                    days: parseInt(days),
                    period_type: periodType
                })
            });

            const data = await response.json();

            if (data.job_id) {
                connectSSE('/api/techwatch/stream/' + data.job_id, 'techwatch');
            } else if (data.error) {
                showError('techwatch', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Générer le digest';
            }
        } catch (err) {
            showError('techwatch', 'Erreur de connexion: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Générer le digest';
        }
    });
}

function displayTechWatchResult(data) {
    const resultSection = document.getElementById('result-section');
    const progressSection = document.getElementById('progress-section');

    progressSection.style.display = 'none';
    resultSection.style.display = 'block';

    // Stats
    document.getElementById('stat-articles').textContent = data.num_articles || 0;
    document.getElementById('stat-period').textContent = data.period === 'weekly' ? 'Hebdomadaire' : 'Mensuel';
    document.getElementById('stat-date').textContent = new Date().toLocaleString('fr-FR');

    // Digest content (render markdown)
    const digestContent = document.getElementById('digest-content');
    if (typeof marked !== 'undefined') {
        digestContent.innerHTML = marked.parse(data.digest || '');
    } else {
        digestContent.textContent = data.digest || '';
    }

    // Reset form
    const form = document.getElementById('techwatch-form');
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Générer le digest';

    // Scroll to result
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function copyDigest() {
    const content = document.getElementById('digest-content').innerText;

    navigator.clipboard.writeText(content).then(() => {
        // Visual feedback
        const btn = event.target.closest('button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '✅ Copié !';
        btn.style.backgroundColor = '#22c55e';

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.backgroundColor = '';
        }, 2000);
    }).catch(err => {
        alert('Erreur lors de la copie: ' + err);
    });
}

async function regenerateTechWatch(feedback) {
    try {
        const response = await fetch('/api/techwatch/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_digest: document.getElementById('digest-content').innerText || '',
                num_articles: parseInt(document.getElementById('stat-articles').textContent) || 0,
                period: document.getElementById('stat-period').textContent === 'Hebdomadaire' ? 'weekly' : 'monthly',
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/techwatch/stream/' + data.job_id, 'techwatch');
        } else if (data.error) {
            showError('techwatch', data.error);
            resetButton(document.getElementById('regenerate-techwatch-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('techwatch', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-techwatch-btn'), 'Regenerer avec feedback');
    }
}

// === DATASET ANALYZER PAGE ===

function initDatasetPage() {
    const form = document.getElementById('dataset-form');
    if (!form) return;

    const fileInput = document.getElementById('dataset-file');
    const uploadZone = document.getElementById('dataset-file-upload-zone');
    const fileNameDisplay = document.getElementById('dataset-file-name');

    // Click to upload
    uploadZone.addEventListener('click', () => fileInput.click());

    // File selected
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            fileNameDisplay.textContent = `📄 ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        }
    });

    // Drag & drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--corail)';
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = 'var(--gris-clair)';
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--gris-clair)';

        const file = e.dataTransfer.files[0];
        if (file) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = `📄 ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        }
    });

    // Form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            alert('Veuillez sélectionner un fichier.');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Analyse en cours...';

        // Show progress
        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('result-section').style.display = 'none';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/dataset/analyze', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.job_id) {
                connectSSE('/api/dataset/stream/' + data.job_id, 'dataset');
            } else if (data.error) {
                showError('dataset', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Analyser le dataset';
            }
        } catch (err) {
            showError('dataset', 'Erreur de connexion: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Analyser le dataset';
        }
    });
}

function displayDatasetResult(data) {
    const resultSection = document.getElementById('result-section');
    const progressSection = document.getElementById('progress-section');

    progressSection.style.display = 'none';
    resultSection.style.display = 'block';

    // Stats
    document.getElementById('stat-filename').textContent = data.filename || '-';
    document.getElementById('stat-rows').textContent = (data.num_rows || 0).toLocaleString('fr-FR');
    document.getElementById('stat-columns').textContent = data.num_columns || 0;
    document.getElementById('stat-memory').textContent = (data.memory_mb || 0) + ' MB';

    // Report content (render markdown)
    const reportContent = document.getElementById('report-content');
    if (typeof marked !== 'undefined') {
        reportContent.innerHTML = marked.parse(data.report || '');
    } else {
        reportContent.textContent = data.report || '';
    }

    // Reset form
    const form = document.getElementById('dataset-form');
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Analyser le dataset';

    // Scroll to result
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function copyReport() {
    const content = document.getElementById('report-content').innerText;

    navigator.clipboard.writeText(content).then(() => {
        // Visual feedback
        const btn = event.target.closest('button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '✅ Copié !';
        btn.style.backgroundColor = '#22c55e';

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.backgroundColor = '';
        }, 2000);
    }).catch(err => {
        alert('Erreur lors de la copie: ' + err);
    });
}

async function regenerateDataset(feedback) {
    try {
        const response = await fetch('/api/dataset/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_report: document.getElementById('report-content').innerText || '',
                filename: document.getElementById('stat-filename').textContent || 'dataset',
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/dataset/stream/' + data.job_id, 'dataset');
        } else if (data.error) {
            showError('dataset', data.error);
            resetButton(document.getElementById('regenerate-dataset-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('dataset', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-dataset-btn'), 'Regenerer avec feedback');
    }
}

// === WORKSHOP PLANNER PAGE ===

function initWorkshopPage() {
    const form = document.getElementById('workshop-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const topic = document.getElementById('topic').value.trim();
        const duration = document.getElementById('duration').value;
        const audience = document.getElementById('audience').value.trim() || 'Professionnels';
        const objectives = document.getElementById('objectives').value.trim();

        if (!topic) {
            alert('Veuillez saisir un sujet.');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Génération...';

        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('result-section').style.display = 'none';

        try {
            const response = await fetch('/api/workshop/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic: topic,
                    duration: duration,
                    audience: audience,
                    objectives: objectives
                })
            });

            const data = await response.json();

            if (data.job_id) {
                connectSSE('/api/workshop/stream/' + data.job_id, 'workshop');
            } else if (data.error) {
                showError('workshop', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Générer le plan';
            }
        } catch (err) {
            showError('workshop', 'Erreur de connexion: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Générer le plan';
        }
    });
}

function displayWorkshopResult(data) {
    const resultSection = document.getElementById('result-section');
    const progressSection = document.getElementById('progress-section');

    progressSection.style.display = 'none';
    resultSection.style.display = 'block';

    document.getElementById('stat-topic').textContent = data.topic || '-';
    document.getElementById('stat-duration').textContent = data.duration || '-';
    document.getElementById('stat-audience').textContent = data.audience || '-';

    const planContent = document.getElementById('plan-content');
    if (typeof marked !== 'undefined') {
        planContent.innerHTML = marked.parse(data.plan || '');
    } else {
        planContent.textContent = data.plan || '';
    }

    const form = document.getElementById('workshop-form');
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Générer le plan';

    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function copyWorkshopPlan() {
    const content = document.getElementById('plan-content').innerText;
    navigator.clipboard.writeText(content).then(() => {
        const btn = event.target.closest('button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '✅ Copié !';
        btn.style.backgroundColor = '#22c55e';
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.backgroundColor = '';
        }, 2000);
    }).catch(err => {
        alert('Erreur lors de la copie: ' + err);
    });
}

async function regenerateWorkshop(feedback) {
    try {
        const response = await fetch('/api/workshop/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_plan: document.getElementById('plan-content').innerText || '',
                topic: document.getElementById('stat-topic').textContent || 'Workshop',
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/workshop/stream/' + data.job_id, 'workshop');
        } else if (data.error) {
            showError('workshop', data.error);
            resetButton(document.getElementById('regenerate-workshop-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('workshop', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-workshop-btn'), 'Regenerer avec feedback');
    }
}

// === RFP RESPONDER PAGE ===

function initRFPPage() {
    const form = document.getElementById('rfp-form');
    if (!form) return;

    const fileInput = document.getElementById('rfp-file');
    const uploadZone = document.getElementById('rfp-file-upload-zone');
    const fileNameDisplay = document.getElementById('rfp-file-name');
    const textArea = document.getElementById('rfp-text');

    // Click to upload
    uploadZone.addEventListener('click', () => fileInput.click());

    // File selected
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            fileNameDisplay.textContent = `📄 ${file.name}`;
            textArea.value = '';  // Clear textarea if file is selected
        }
    });

    // Drag & drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--corail)';
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = 'var(--gris-clair)';
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--gris-clair)';

        const file = e.dataTransfer.files[0];
        if (file) {
            fileInput.files = e.dataTransfer.files;
            fileNameDisplay.textContent = `📄 ${file.name}`;
            textArea.value = '';
        }
    });

    // Form submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const rfpText = textArea.value.trim();
        const file = fileInput.files[0];

        if (!rfpText && !file) {
            alert('Veuillez fournir un RFP (texte ou fichier).');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Analyse en cours...';

        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('result-section').style.display = 'none';

        const formData = new FormData();
        if (file) {
            formData.append('file', file);
        } else {
            formData.append('rfp_text', rfpText);
        }

        try {
            const response = await fetch('/api/rfp/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.job_id) {
                connectSSE('/api/rfp/stream/' + data.job_id, 'rfp');
            } else if (data.error) {
                showError('rfp', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Générer la réponse';
            }
        } catch (err) {
            showError('rfp', 'Erreur de connexion: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = 'Générer la réponse';
        }
    });
}

function displayRFPResult(data) {
    const resultSection = document.getElementById('result-section');
    const progressSection = document.getElementById('progress-section');

    progressSection.style.display = 'none';
    resultSection.style.display = 'block';

    // Analysis
    const analysisContent = document.getElementById('analysis-content');
    if (data.analysis) {
        const analysis = data.analysis;
        let analysisHtml = '';
        if (analysis.client) analysisHtml += `<p><strong>Client:</strong> ${analysis.client}</p>`;
        if (analysis.context) analysisHtml += `<p><strong>Contexte:</strong> ${analysis.context}</p>`;
        if (analysis.key_requirements && analysis.key_requirements.length > 0) {
            analysisHtml += '<p><strong>Exigences clés:</strong></p><ul>';
            analysis.key_requirements.forEach(req => {
                analysisHtml += `<li>${req}</li>`;
            });
            analysisHtml += '</ul>';
        }
        analysisContent.innerHTML = analysisHtml;
    }

    // Response
    const responseContent = document.getElementById('response-content');
    if (typeof marked !== 'undefined') {
        responseContent.innerHTML = marked.parse(data.response || '');
    } else {
        responseContent.textContent = data.response || '';
    }

    const form = document.getElementById('rfp-form');
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Générer la réponse';

    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function copyRFPResponse() {
    const content = document.getElementById('response-content').innerText;
    navigator.clipboard.writeText(content).then(() => {
        const btn = event.target.closest('button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '✅ Copié !';
        btn.style.backgroundColor = '#22c55e';
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.backgroundColor = '';
        }, 2000);
    }).catch(err => {
        alert('Erreur lors de la copie: ' + err);
    });
}

async function regenerateRFP(feedback) {
    try {
        const response = await fetch('/api/rfp/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_response: document.getElementById('response-content').innerText || '',
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/rfp/stream/' + data.job_id, 'rfp');
        } else if (data.error) {
            showError('rfp', data.error);
            resetButton(document.getElementById('regenerate-rfp-btn'), 'Regenerer avec feedback');
        }
    } catch (err) {
        showError('rfp', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-rfp-btn'), 'Regenerer avec feedback');
    }
}

async function regenerateArticleGenerator(feedback) {
    if (!window.currentArticleData) {
        showError('article-generator', 'Aucun article à régénérer.');
        return;
    }

    try {
        const ideaText = document.getElementById('idea-text').value.trim();

        const response = await fetch('/api/article-generator/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_content: window.currentArticleData.content || '',
                previous_idea: ideaText,
            })
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/article-generator/stream/' + data.job_id, 'article-generator');
        } else if (data.error) {
            showError('article-generator', data.error);
            resetButton(document.getElementById('regenerate-article-btn'), 'Régénérer avec feedback');
        }
    } catch (err) {
        showError('article-generator', 'Erreur de connexion: ' + err.message);
        resetButton(document.getElementById('regenerate-article-btn'), 'Régénérer avec feedback');
    }
}


// ====================================
// PROPOSAL MODULAR PAGE
// ====================================

function initProposalModularPage() {
    console.log('Init proposal modular page');

    // File upload
    const fileZone = document.getElementById('file-upload-zone');
    const fileInput = document.getElementById('tender-file');
    const fileName = document.getElementById('file-name');

    if (!fileZone || !fileInput || !fileName) {
        console.error('Proposal modular: Elements not found', { fileZone, fileInput, fileName });
        return;
    }

    fileZone.addEventListener('click', () => fileInput.click());

    fileZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileZone.style.borderColor = 'var(--corail)';
        fileZone.style.background = 'var(--rose-poudre)';
    });

    fileZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileZone.style.borderColor = '';
        fileZone.style.background = '';
    });

    fileZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileZone.style.borderColor = '';
        fileZone.style.background = '';

        const files = e.dataTransfer.files;
        console.log('Files dropped:', files.length);

        if (files.length > 0) {
            // Use DataTransfer to properly set files
            const dt = new DataTransfer();
            dt.items.add(files[0]);
            fileInput.files = dt.files;

            fileName.textContent = files[0].name;
            console.log('File set:', files[0].name);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            fileName.textContent = fileInput.files[0].name;
        }
    });

    // Section buttons
    const sectionButtons = document.querySelectorAll('.section-btn');
    sectionButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const section = btn.dataset.section;
            generateProposalSection(section);
        });
    });
}

// Expose globally for template
window.initProposalModularPage = initProposalModularPage;

async function generateProposalSection(section) {
    const tenderText = document.getElementById('tender-text').value.trim();
    const fileInput = document.getElementById('tender-file');

    if (!tenderText && fileInput.files.length === 0) {
        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            errorContainer.innerHTML = '<div class="error-message">⚠️ Veuillez fournir un appel d\'offre (texte ou fichier).</div>';
        }
        return;
    }

    // Store tender_text for later use in feedback
    window.currentTenderText = tenderText;

    // Disable all buttons
    document.querySelectorAll('.section-btn').forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = '0.5';
    });

    // Show progress
    const progress = document.getElementById('progress');
    const progressBar = document.getElementById('progress-bar');
    const errorContainer = document.getElementById('error-container');

    progress.style.display = 'block';
    errorContainer.innerHTML = '';
    progressBar.style.width = '0%';

    // Reset steps
    document.querySelectorAll('.progress-step').forEach(step => {
        step.classList.remove('active', 'done');
        step.classList.add('pending');
    });

    // Prepare form data
    const formData = new FormData();
    formData.append('section', section);

    if (fileInput.files.length > 0) {
        formData.append('file', fileInput.files[0]);
    } else {
        formData.append('tender_text', tenderText);
    }

    try {
        // Submit generation request
        const response = await fetch('/api/proposal/generate-section', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erreur lors de la génération');
        }

        const { job_id } = await response.json();

        // Connect to SSE for progress
        connectSSE(`/api/proposal/stream/${job_id}`, 'proposal_section');

    } catch (error) {
        console.error('Erreur:', error);

        const errorContainer = document.getElementById('error-container');
        if (errorContainer) {
            errorContainer.innerHTML = `<div class="error-message">⚠️ ${error.message}</div>`;
        }

        // Re-enable buttons
        document.querySelectorAll('.section-btn').forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '';
        });

        const progress = document.getElementById('progress');
        if (progress) {
            progress.style.display = 'none';
        }
    }
}

function displayProposalSectionResult(data) {
    const resultSection = document.getElementById('result');
    const sectionName = document.getElementById('section-name');
    const slidesCount = document.getElementById('slides-count');
    const resultTitle = document.getElementById('result-title');
    const resultSubtitle = document.getElementById('result-subtitle');

    // Store data for feedback (use tender_text from backend, not from form)
    // This ensures we have the text even if user uploaded a PDF file
    window.currentSectionData = {
        ...data,
        tender_text: data.tender_text || window.currentTenderText || ''
    };

    // Update content
    sectionName.textContent = data.section_name;
    slidesCount.textContent = data.slides_count;
    resultTitle.textContent = `Section générée : ${data.section_name}`;
    resultSubtitle.textContent = `${data.slides_count} slide(s) créée(s)`;

    // Hide progress
    const progress = document.getElementById('progress');
    if (progress) {
        progress.style.display = 'none';
    }

    // Download button
    const pptxBtn = document.getElementById('download-pptx');
    if (pptxBtn && data.pptx_path) {
        pptxBtn.href = '/api/download?path=' + encodeURIComponent(data.pptx_path);
        pptxBtn.style.display = 'inline-block';
    }

    // Show result
    resultSection.classList.add('active');
    resultSection.scrollIntoView({ behavior: 'smooth' });

    // Re-enable buttons
    document.querySelectorAll('.section-btn').forEach(btn => {
        btn.disabled = false;
        btn.style.opacity = '';
    });
}

// === PREVIEW & FEEDBACK FUNCTIONS FOR MODULAR ===

async function showPreview() {
    console.log('showPreview called');
    console.log('currentSectionData:', window.currentSectionData);

    if (!window.currentSectionData || !window.currentSectionData.slides_data) {
        alert('Aucune présentation à prévisualiser');
        return;
    }

    const previewSection = document.getElementById('preview-section');
    const previewContainer = document.getElementById('slides-preview-container');

    previewSection.style.display = 'block';

    const slides = window.currentSectionData.slides_data;

    if (!slides || slides.length === 0) {
        previewContainer.innerHTML = '<div style="padding: 2rem;">Aucune slide à afficher</div>';
        return;
    }

    // Render all slides as HTML cards directly from the data
    previewContainer.innerHTML = '';

    slides.forEach((slide, index) => {
        const slideDiv = document.createElement('div');
        slideDiv.style.cssText = 'border: 2px solid var(--gris-clair); border-radius: 8px; overflow: hidden; cursor: pointer; transition: all 0.2s; background: var(--blanc);';

        // Build slide content HTML
        const title = slide.title || `Slide ${index + 1}`;
        const slideType = slide.type || 'content';
        const bullets = slide.bullets || [];
        const visual = slide.visual || null;

        // Color based on slide type
        const typeColors = {
            'cover': '#FF6B58',
            'section': '#2D3748',
            'content': '#1a1a2e',
            'context': '#2c5282',
            'approach': '#2f855a',
            'diagram': '#6b46c1',
            'closing': '#FF6B58'
        };
        const bgColor = typeColors[slideType] || '#1a1a2e';

        let bulletsHtml = '';
        if (bullets.length > 0) {
            bulletsHtml = '<ul style="margin: 0.5rem 0; padding-left: 1.2rem; font-size: 0.75rem; color: rgba(255,255,255,0.85);">';
            bullets.forEach(b => {
                bulletsHtml += `<li style="margin-bottom: 0.2rem;">${b}</li>`;
            });
            bulletsHtml += '</ul>';
        }

        let visualBadge = '';
        if (visual && visual.type) {
            visualBadge = `<span style="display:inline-block; background: rgba(255,255,255,0.2); color: white; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.65rem; margin-top: 0.3rem;">📊 ${visual.type}</span>`;
        }

        slideDiv.innerHTML = `
            <div style="background: ${bgColor}; padding: 1rem; min-height: 120px; display: flex; flex-direction: column; justify-content: ${slideType === 'cover' ? 'center' : 'flex-start'}; ${slideType === 'cover' ? 'text-align: center;' : ''}">
                <div style="color: white; font-weight: 600; font-size: 0.85rem; ${slideType === 'cover' ? 'font-size: 1rem;' : ''}">${title}</div>
                ${bulletsHtml}
                ${visualBadge}
            </div>
            <div style="padding: 0.5rem; text-align: center; font-size: 0.85rem; color: var(--gris-moyen); display: flex; justify-content: space-between; align-items: center;">
                <span>Slide ${index + 1}</span>
                <span style="font-size: 0.7rem; text-transform: uppercase; opacity: 0.6;">${slideType}</span>
            </div>
        `;

        slideDiv.addEventListener('mouseenter', () => {
            slideDiv.style.borderColor = 'var(--corail)';
            slideDiv.style.boxShadow = '0 4px 12px rgba(255,107,88,0.2)';
        });
        slideDiv.addEventListener('mouseleave', () => {
            slideDiv.style.borderColor = 'var(--gris-clair)';
            slideDiv.style.boxShadow = 'none';
        });
        slideDiv.addEventListener('click', () => {
            openSlideEditor(index);
        });
        previewContainer.appendChild(slideDiv);
    });
}

function togglePreview() {
    showPreview();
}

function openSlideModal(imgPath, slideNumber) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.9); z-index: 9999;
        display: flex; align-items: center; justify-content: center;
        cursor: pointer;
    `;
    modal.innerHTML = `
        <div style="max-width: 90%; max-height: 90%; text-align: center;">
            <div style="color: white; margin-bottom: 1rem; font-size: 1.2rem;">Slide ${slideNumber}</div>
            <img src="/api/download?path=${encodeURIComponent(imgPath)}"
                 style="max-width: 100%; max-height: 80vh; border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,0.5);">
            <div style="color: white; margin-top: 1rem; font-size: 0.9rem;">Cliquez n'importe où pour fermer</div>
        </div>
    `;
    modal.onclick = () => document.body.removeChild(modal);
    document.body.appendChild(modal);
}

async function submitSectionFeedback() {
    const feedback = document.getElementById('section-feedback').value.trim();

    if (!feedback) {
        alert('Veuillez saisir un feedback');
        return;
    }

    if (!window.currentSectionData) {
        alert('Aucune section à régénérer');
        return;
    }

    const btn = document.getElementById('regenerate-section-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Régénération...';

    // Show progress
    const progress = document.getElementById('progress');
    progress.style.display = 'block';
    document.querySelectorAll('.progress-step').forEach(step => {
        step.classList.remove('active', 'done');
        step.classList.add('pending');
    });

    try {
        // Prepare form data for regeneration
        const formData = new FormData();
        formData.append('section', window.currentSectionData.section);
        formData.append('feedback', feedback);
        formData.append('tender_text', window.currentSectionData.tender_text || '');

        // Send previous slides as JSON string
        if (window.currentSectionData.slides_data) {
            formData.append('previous_slides', JSON.stringify(window.currentSectionData.slides_data));
        }

        const response = await fetch('/api/proposal/regenerate-section', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.job_id) {
            connectSSE('/api/proposal/stream/' + data.job_id, 'proposal_section');
        } else if (data.error) {
            alert('Erreur: ' + data.error);
            btn.disabled = false;
            btn.innerHTML = '🔄 Régénérer avec feedback';
        }
    } catch (error) {
        alert('Erreur de connexion: ' + error.message);
        btn.disabled = false;
        btn.innerHTML = '🔄 Régénérer avec feedback';
    }
}

// === SLIDE EDITOR FUNCTIONS ===

function openSlideEditor(slideIndex) {
    console.log('Opening editor for slide:', slideIndex);

    if (!window.currentSectionData || !window.currentSectionData.slides_data) {
        alert('Données de slides non disponibles');
        return;
    }

    const slides = window.currentSectionData.slides_data;
    if (slideIndex < 0 || slideIndex >= slides.length) {
        alert('Index de slide invalide');
        return;
    }

    const slide = slides[slideIndex];
    window.currentEditingSlide = { index: slideIndex, data: slide };

    // Show editor panel
    const editor = document.getElementById('slide-editor');
    editor.style.display = 'block';

    // Update slide number
    document.getElementById('edit-slide-number').textContent = `${slideIndex + 1}`;

    // Populate title
    document.getElementById('edit-slide-title').value = slide.title || '';

    // Populate content (bullets)
    const contentTextarea = document.getElementById('edit-slide-content');
    if (slide.bullets && Array.isArray(slide.bullets)) {
        contentTextarea.value = slide.bullets.map(b => `• ${b}`).join('\n');
    } else {
        contentTextarea.value = '';
    }

    // Show/hide diagram selector
    const diagramGroup = document.getElementById('edit-diagram-group');
    const diagramSelect = document.getElementById('edit-diagram-type');

    if (slide.visual && slide.visual.type) {
        diagramGroup.style.display = 'block';
        diagramSelect.value = slide.visual.type || 'flow';
    } else {
        diagramGroup.style.display = 'none';
    }

    // Scroll editor into view
    editor.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeSlideEditor() {
    const editor = document.getElementById('slide-editor');
    editor.style.display = 'none';
    window.currentEditingSlide = null;
}

async function regenerateSlide() {
    if (!window.currentEditingSlide) {
        alert('Aucune slide en cours d\'édition');
        return;
    }

    const slideIndex = window.currentEditingSlide.index;
    const title = document.getElementById('edit-slide-title').value.trim();
    const contentText = document.getElementById('edit-slide-content').value.trim();
    const diagramType = document.getElementById('edit-diagram-type').value;

    if (!title) {
        alert('Le titre est requis');
        return;
    }

    // Parse bullets (remove leading bullets if present)
    const bullets = contentText
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .map(line => line.replace(/^[•\-*]\s*/, ''));

    if (bullets.length === 0) {
        alert('Le contenu est requis');
        return;
    }

    // Prepare regeneration request
    const formData = new FormData();
    formData.append('section', window.currentSectionData.section);
    formData.append('slide_index', slideIndex);
    formData.append('slide_title', title);
    formData.append('slide_bullets', JSON.stringify(bullets));
    formData.append('diagram_type', diagramType);
    formData.append('tender_text', window.currentSectionData.tender_text || '');

    // Show loading state
    const regenerateBtn = document.querySelector('#slide-editor .btn-primary');
    const originalText = regenerateBtn.innerHTML;
    regenerateBtn.disabled = true;
    regenerateBtn.innerHTML = '<span class="spinner"></span> Régénération...';

    try {
        const response = await fetch('/api/proposal/regenerate-slide', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            alert('Erreur: ' + data.error);
            return;
        }

        if (data.pptx_path) {
            // Update current section data with new PPTX
            window.currentSectionData.pptx_path = data.pptx_path;
            window.currentSectionData.slides_data = data.slides_data;

            // Update download link
            const pptxBtn = document.getElementById('download-pptx');
            if (pptxBtn) {
                pptxBtn.href = '/api/download?path=' + encodeURIComponent(data.pptx_path);
            }

            // Close editor
            closeSlideEditor();

            // Refresh preview
            await showPreview();

            alert('✅ Slide régénérée avec succès !');
        }
    } catch (error) {
        alert('Erreur de connexion: ' + error.message);
    } finally {
        regenerateBtn.disabled = false;
        regenerateBtn.innerHTML = originalText;
    }
}

// Expose functions globally for onclick handlers
window.showPreview = showPreview;
window.togglePreview = togglePreview;
window.openSlideModal = openSlideModal;
window.openSlideEditor = openSlideEditor;
window.closeSlideEditor = closeSlideEditor;
window.regenerateSlide = regenerateSlide;
window.submitSectionFeedback = submitSectionFeedback;

// === GOOGLE SLIDES EXPORT ===

async function exportToGoogleSlides() {
    if (!window.currentSectionData || !window.currentSectionData.slides_data) {
        alert('Aucune section à exporter');
        return;
    }

    const exportBtn = event.target;
    const originalText = exportBtn.innerHTML;
    exportBtn.disabled = true;
    exportBtn.innerHTML = '<span class="spinner"></span> Export en cours...';

    try {
        const formData = new FormData();
        formData.append('section', window.currentSectionData.section);
        formData.append('tender_text', window.currentSectionData.tender_text || '');
        formData.append('slides_data', JSON.stringify(window.currentSectionData.slides_data));

        const response = await fetch('/api/proposal/export-to-slides', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            if (data.setup_required) {
                alert('⚠️ Configuration Google requise\n\n' + data.error + '\n\nConsultez la documentation pour configurer l\'API Google.');
            } else {
                alert('Erreur: ' + data.error);
            }
            return;
        }

        if (data.presentation_url) {
            // Afficher un message de succès avec le lien
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.8); z-index: 9999;
                display: flex; align-items: center; justify-content: center;
            `;
            modal.innerHTML = `
                <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 500px; text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
                    <h2 style="color: var(--noir-profond); margin-bottom: 1rem;">Présentation créée !</h2>
                    <p style="color: var(--gris-moyen); margin-bottom: 1.5rem;">
                        Votre présentation a été exportée vers Google Slides avec succès.
                    </p>
                    <div style="display: flex; gap: 1rem; justify-content: center;">
                        <button onclick="window.open('${data.presentation_url}', '_blank')"
                                class="btn btn-primary" style="padding: 0.75rem 1.5rem;">
                            🔗 Ouvrir dans Google Slides
                        </button>
                        <button onclick="this.closest('div[style*=fixed]').remove()"
                                class="btn btn-secondary" style="padding: 0.75rem 1.5rem;">
                            Fermer
                        </button>
                    </div>
                    <div style="margin-top: 1rem; padding: 1rem; background: var(--gris-clair); border-radius: 8px;">
                        <small style="color: var(--gris-moyen); word-break: break-all;">${data.presentation_url}</small>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Copier le lien dans le presse-papier
            try {
                await navigator.clipboard.writeText(data.presentation_url);
                console.log('Lien copié dans le presse-papier');
            } catch (err) {
                console.log('Impossible de copier le lien');
            }
        }

    } catch (error) {
        alert('Erreur de connexion: ' + error.message);
    } finally {
        exportBtn.disabled = false;
        exportBtn.innerHTML = originalText;
    }
}

window.exportToGoogleSlides = exportToGoogleSlides;

async function downloadProposalPDF() {
    if (!window.currentSectionData || !window.currentSectionData.pptx_path) {
        alert('Aucun PPTX à convertir. Générez d\'abord les slides.');
        return;
    }

    await downloadAsPDF(
        window.currentSectionData.pptx_path,
        'pptx',
        'download-pdf'
    );
}

window.downloadProposalPDF = downloadProposalPDF;


// ====================================
// FORMATION PAGE
// ====================================

function initFormationPage() {
    console.log('Init formation page');

    const form = document.getElementById('formation-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const clientNeeds = document.getElementById('client-needs').value.trim();
        if (!clientNeeds) {
            alert('Veuillez décrire le besoin de formation.');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Génération en cours...';

        const progress = document.getElementById('progress');
        progress.style.display = 'block';
        document.querySelectorAll('.progress-step').forEach(step => {
            step.classList.remove('active', 'done');
            step.classList.add('pending');
        });

        const formData = new FormData();
        formData.append('client_needs', clientNeeds);

        try {
            const response = await fetch('/api/formation/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (data.job_id) {
                connectSSE('/api/formation/stream/' + data.job_id, 'formation');
            } else if (data.error) {
                showError('formation', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = '📋 Générer le programme';
            }
        } catch (err) {
            showError('formation', 'Erreur de connexion: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = '📋 Générer le programme';
        }
    });
}

function displayFormationResult(data) {
    const resultSection = document.getElementById('result');
    const resultTitle = document.getElementById('result-title');
    const resultSubtitle = document.getElementById('result-subtitle');
    const preview = document.getElementById('programme-preview');
    const progress = document.getElementById('progress');

    if (progress) progress.style.display = 'none';

    // Store for feedback
    window.currentFormationData = data;

    const title = data.metadata ? data.metadata.title || 'Programme de formation' : 'Programme de formation';
    resultTitle.textContent = `Programme : ${title}`;
    resultSubtitle.textContent = data.metadata && data.metadata.duration ? `Durée : ${data.metadata.duration}` : '';

    // Render markdown
    if (typeof marked !== 'undefined') {
        preview.innerHTML = marked.parse(data.content || '');
    } else {
        preview.textContent = data.content || '';
    }

    resultSection.classList.add('active');
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function copyProgramme() {
    if (!window.currentFormationData) return;
    navigator.clipboard.writeText(window.currentFormationData.content).then(() => {
        alert('✅ Markdown copié dans le presse-papier !');
    }).catch(err => {
        alert('Erreur lors de la copie: ' + err);
    });
}

function downloadProgramme() {
    if (!window.currentFormationData || !window.currentFormationData.md_path) return;
    window.location.href = '/api/download?path=' + encodeURIComponent(window.currentFormationData.md_path);
}

async function exportToGoogleDocs() {
    if (!window.currentFormationData || !window.currentFormationData.content) {
        alert('Aucun programme à exporter');
        return;
    }

    const title = window.currentFormationData.metadata ? window.currentFormationData.metadata.title || 'Programme de Formation' : 'Programme de Formation';

    try {
        const formData = new FormData();
        formData.append('content', window.currentFormationData.content);
        formData.append('title', title);

        const response = await fetch('/api/formation/export-gdocs', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            if (data.setup_required) {
                alert('⚠️ Configuration Google requise\n\n' + data.error);
            } else {
                alert('Erreur: ' + data.error);
            }
            return;
        }

        if (data.doc_url) {
            window.open(data.doc_url, '_blank');
            alert('✅ Document Google Docs créé ! Le lien a été ouvert dans un nouvel onglet.');
        }
    } catch (error) {
        alert('Erreur de connexion: ' + error.message);
    }
}

async function regenerateFormation() {
    const feedback = document.getElementById('formation-feedback').value.trim();
    if (!feedback) {
        alert('Veuillez saisir un feedback');
        return;
    }
    if (!window.currentFormationData) {
        alert('Aucun programme à régénérer');
        return;
    }

    const btn = document.getElementById('regenerate-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Régénération...';

    const progress = document.getElementById('progress');
    progress.style.display = 'block';

    try {
        const response = await fetch('/api/formation/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                feedback: feedback,
                previous_content: window.currentFormationData.content || ''
            })
        });

        const data = await response.json();
        if (data.job_id) {
            connectSSE('/api/formation/stream/' + data.job_id, 'formation');
        } else if (data.error) {
            alert('Erreur: ' + data.error);
            btn.disabled = false;
            btn.innerHTML = '🔄 Régénérer avec feedback';
        }
    } catch (err) {
        alert('Erreur: ' + err.message);
        btn.disabled = false;
        btn.innerHTML = '🔄 Régénérer avec feedback';
    }
}

window.initFormationPage = initFormationPage;
window.copyProgramme = copyProgramme;
window.downloadProgramme = downloadProgramme;
window.exportToGoogleDocs = exportToGoogleDocs;
window.regenerateFormation = regenerateFormation;


// ====================================
// TRAINING SLIDES PAGE
// ====================================

function initTrainingSlidesPage() {
    console.log('Init training slides page');

    // File upload
    const fileZone = document.getElementById('file-upload-zone');
    const fileInput = document.getElementById('programme-file');
    const fileName = document.getElementById('file-name');

    if (fileZone) {
        fileZone.addEventListener('click', () => fileInput.click());
        fileZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileZone.style.borderColor = 'var(--corail)';
        });
        fileZone.addEventListener('dragleave', () => {
            fileZone.style.borderColor = '';
        });
        fileZone.addEventListener('drop', (e) => {
            e.preventDefault();
            fileZone.style.borderColor = '';
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileName.textContent = files[0].name;
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                fileName.textContent = fileInput.files[0].name;
            }
        });
    }

    // Form submit
    const form = document.getElementById('training-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const programmeText = document.getElementById('programme-text').value.trim();
        const file = fileInput.files[0];

        if (!programmeText && !file) {
            alert('Veuillez fournir un programme de formation (texte ou fichier).');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Génération en cours...';

        const progress = document.getElementById('progress');
        progress.style.display = 'block';
        document.querySelectorAll('.progress-step').forEach(step => {
            step.classList.remove('active', 'done');
            step.classList.add('pending');
        });

        const formData = new FormData();
        if (file) {
            formData.append('file', file);
        } else {
            formData.append('programme_text', programmeText);
        }

        try {
            const response = await fetch('/api/training-slides/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (data.job_id) {
                connectSSE('/api/training-slides/stream/' + data.job_id, 'training_slides');
            } else if (data.error) {
                showError('training_slides', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = '🎓 Générer toutes les slides';
            }
        } catch (err) {
            showError('training_slides', 'Erreur de connexion: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = '🎓 Générer toutes les slides';
        }
    });
}

function displayTrainingSlidesResult(data) {
    const resultSection = document.getElementById('result');
    const resultTitle = document.getElementById('result-title');
    const resultSubtitle = document.getElementById('result-subtitle');
    const modulesList = document.getElementById('modules-list');
    const progress = document.getElementById('progress');
    const resultActions = document.getElementById('result-actions');
    const previewSection = document.getElementById('preview-section');
    const previewContainer = document.getElementById('slides-preview-container');

    if (progress) progress.style.display = 'none';

    // Store data
    window.currentTrainingSlidesData = data;

    const title = data.programme_data ? data.programme_data.title || 'Formation' : 'Formation';
    resultTitle.textContent = `Slides : ${title}`;
    resultSubtitle.textContent = `${data.total_slides} slides générées pour ${Object.keys(data.modules_slides || {}).length} modules`;

    // Build modules list
    let modulesHtml = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">';
    const pptxPaths = data.pptx_paths || {};

    for (const [moduleName, slides] of Object.entries(data.modules_slides || {})) {
        const pptxPath = pptxPaths[moduleName];
        modulesHtml += `
            <div style="border: 1px solid var(--gris-clair); border-radius: 8px; padding: 1rem; background: var(--blanc);">
                <div style="font-weight: 600; margin-bottom: 0.5rem;">${moduleName}</div>
                <div style="font-size: 0.85rem; color: var(--gris-moyen); margin-bottom: 0.75rem;">${slides.length} slides</div>
                ${pptxPath ? `<a href="/api/download?path=${encodeURIComponent(pptxPath)}" class="btn btn-secondary" style="font-size: 0.85rem; padding: 0.4rem 0.8rem;" download>📥 Télécharger</a>` : ''}
            </div>
        `;
    }
    modulesHtml += '</div>';
    modulesList.innerHTML = modulesHtml;

    // Actions
    let actionsHtml = '';
    if (data.all_pptx_path) {
        actionsHtml += `<a href="/api/download?path=${encodeURIComponent(data.all_pptx_path)}" class="btn btn-primary" style="font-size: 1.1rem;" download>📥 Télécharger tout (.pptx)</a>`;
    }
    actionsHtml += `<button class="btn btn-secondary" onclick="previewTrainingSlides()" style="font-size: 1rem;">👁️ Prévisualiser</button>`;
    actionsHtml += `<button class="btn btn-secondary" onclick="exportTrainingSlidesToGoogle()" style="font-size: 1rem;">📤 Google Slides</button>`;
    resultActions.innerHTML = actionsHtml;

    // Show result
    resultSection.classList.add('active');
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function previewTrainingSlides() {
    if (!window.currentTrainingSlidesData || !window.currentTrainingSlidesData.all_slides) return;

    const previewSection = document.getElementById('preview-section');
    const previewContainer = document.getElementById('slides-preview-container');
    previewSection.style.display = 'block';
    previewContainer.innerHTML = '';

    const slides = window.currentTrainingSlidesData.all_slides;

    slides.forEach((slide, index) => {
        const slideDiv = document.createElement('div');
        slideDiv.style.cssText = 'border: 2px solid var(--gris-clair); border-radius: 8px; overflow: hidden; background: var(--blanc); transition: all 0.2s;';

        const title = slide.title || `Slide ${index + 1}`;
        const slideType = slide.type || 'content';
        const bullets = slide.bullets || [];
        const visual = slide.visual || null;

        const typeColors = {
            'cover': '#FF6B58', 'section': '#2D3748', 'content': '#1a1a2e',
            'diagram': '#6b46c1', 'closing': '#FF6B58'
        };
        const bgColor = typeColors[slideType] || '#1a1a2e';

        let bulletsHtml = '';
        if (bullets.length > 0) {
            bulletsHtml = '<ul style="margin: 0.5rem 0; padding-left: 1.2rem; font-size: 0.75rem; color: rgba(255,255,255,0.85);">';
            bullets.forEach(b => { bulletsHtml += `<li style="margin-bottom: 0.2rem;">${b}</li>`; });
            bulletsHtml += '</ul>';
        }

        let visualBadge = '';
        if (visual && visual.type) {
            visualBadge = `<span style="display:inline-block; background: rgba(255,255,255,0.2); color: white; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.65rem; margin-top: 0.3rem;">📊 ${visual.type}</span>`;
        }

        slideDiv.innerHTML = `
            <div style="background: ${bgColor}; padding: 1rem; min-height: 100px; display: flex; flex-direction: column; justify-content: ${slideType === 'cover' ? 'center' : 'flex-start'}; ${slideType === 'cover' ? 'text-align: center;' : ''}">
                <div style="color: white; font-weight: 600; font-size: 0.85rem;">${title}</div>
                ${bulletsHtml}
                ${visualBadge}
            </div>
            <div style="padding: 0.4rem; text-align: center; font-size: 0.8rem; color: var(--gris-moyen);">
                Slide ${index + 1} · ${slideType}
            </div>
        `;
        previewContainer.appendChild(slideDiv);
    });

    previewSection.scrollIntoView({ behavior: 'smooth' });
}

async function exportTrainingSlidesToGoogle() {
    if (!window.currentTrainingSlidesData || !window.currentTrainingSlidesData.all_slides) {
        alert('Aucune slide à exporter');
        return;
    }

    const title = window.currentTrainingSlidesData.programme_data ? window.currentTrainingSlidesData.programme_data.title || 'Support de Formation' : 'Support de Formation';

    try {
        const formData = new FormData();
        formData.append('slides_data', JSON.stringify(window.currentTrainingSlidesData.all_slides));
        formData.append('title', title);

        const response = await fetch('/api/training-slides/export-slides', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            alert('Erreur: ' + data.error);
            return;
        }

        if (data.presentation_url) {
            window.open(data.presentation_url, '_blank');
            alert('✅ Présentation Google Slides créée !');
        }
    } catch (error) {
        alert('Erreur: ' + error.message);
    }
}

window.initTrainingSlidesPage = initTrainingSlidesPage;
window.previewTrainingSlides = previewTrainingSlides;
window.exportTrainingSlidesToGoogle = exportTrainingSlidesToGoogle;

// ====================================
// ARTICLE GENERATOR
// ====================================

function initArticleGeneratorPage() {
    console.log('Init article generator page');

    const form = document.getElementById('article-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const ideaText = document.getElementById('idea-text').value.trim();

        if (!ideaText || ideaText.length < 20) {
            alert('Veuillez fournir une idée d\'article (minimum 20 caractères).');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Génération en cours...';

        const progress = document.getElementById('progress');
        progress.style.display = 'block';
        document.querySelectorAll('.progress-step').forEach(step => {
            step.classList.remove('active', 'done');
            step.classList.add('pending');
        });

        const formData = new FormData();
        formData.append('idea_text', ideaText);

        try {
            const response = await fetch('/api/article-generator/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (data.job_id) {
                connectSSE('/api/article-generator/stream/' + data.job_id, 'article-generator');
            } else if (data.error) {
                showError('article-generator', data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = '✍️ Générer l\'article';
            }
        } catch (err) {
            showError('article-generator', 'Erreur de connexion: ' + err.message);
            submitBtn.disabled = false;
            submitBtn.textContent = '✍️ Générer l\'article';
        }
    });
}

function displayArticleGeneratorResult(data) {
    const resultSection = document.getElementById('result');
    const resultContent = document.getElementById('result-content');
    const wordCount = document.getElementById('word-count');
    const downloadLink = document.getElementById('download-md');
    const progress = document.getElementById('progress');

    if (progress) progress.style.display = 'none';

    // Store data for copy/feedback
    window.currentArticleData = data;

    // Display article using markdown renderer
    if (resultContent && data.content) {
        resultContent.innerHTML = marked.parse(data.content);
    }

    // Word count
    if (wordCount && data.word_count) {
        wordCount.textContent = data.word_count;
    }

    // Download link
    if (downloadLink && data.md_path) {
        downloadLink.href = `/api/download?path=${encodeURIComponent(data.md_path)}`;
    }

    // LinkedIn post
    const linkedinCard = document.getElementById('linkedin-post-card');
    const linkedinContent = document.getElementById('linkedin-post-content');
    if (linkedinCard && data.linkedin_post) {
        linkedinContent.textContent = data.linkedin_post;
        linkedinCard.style.display = 'block';
    }

    // Illustration
    const illustrationCard = document.getElementById('illustration-card');
    const illustrationImg = document.getElementById('illustration-img');
    if (illustrationCard && data.image_path) {
        illustrationImg.src = `/api/download?path=${encodeURIComponent(data.image_path)}`;
        illustrationCard.style.display = 'block';
    }

    // Sources
    const sourcesCard = document.getElementById('sources-card');
    const sourcesContent = document.getElementById('sources-content');
    if (sourcesCard && data.sources && data.sources.length > 0) {
        let html = '<ul style="list-style: none; padding: 0;">';
        data.sources.forEach(s => {
            html += `<li style="margin-bottom: 1rem; padding: 1rem; background: var(--gris-clair); border-radius: 8px;">
                <strong>${s.title || 'Source'}</strong><br>
                ${s.url ? `<a href="${s.url}" target="_blank" style="color: var(--corail);">${s.url}</a><br>` : ''}
                <em>${s.excerpt || ''}</em>
                ${s.related_point ? `<br><small style="color: var(--gris-moyen);">Point : ${s.related_point}</small>` : ''}
            </li>`;
        });
        html += '</ul>';
        sourcesContent.innerHTML = html;
        sourcesCard.style.display = 'block';
    }

    // Show result
    resultSection.classList.add('active');
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function copyLinkedinPost() {
    if (!window.currentArticleData || !window.currentArticleData.linkedin_post) {
        alert('Aucun post LinkedIn a copier.');
        return;
    }
    navigator.clipboard.writeText(window.currentArticleData.linkedin_post)
        .then(() => {
            const btn = event.target;
            const orig = btn.textContent;
            btn.textContent = 'Copie !';
            setTimeout(() => { btn.textContent = orig; }, 2000);
        });
}

function copyArticle() {
    if (!window.currentArticleData || !window.currentArticleData.content) {
        alert('Aucun article à copier.');
        return;
    }

    navigator.clipboard.writeText(window.currentArticleData.content)
        .then(() => {
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '✅ Copié !';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 2000);
        })
        .catch(err => {
            alert('Erreur lors de la copie: ' + err.message);
        });
}

window.initArticleGeneratorPage = initArticleGeneratorPage;
window.copyArticle = copyArticle;

// ====================================
// PDF CONVERSION & DOWNLOAD
// ====================================

async function convertToPDF(filePath, fileType = 'pptx') {
    /**
     * Convertit un fichier (PPTX ou Markdown) en PDF
     *
     * @param {string} filePath - Chemin relatif du fichier
     * @param {string} fileType - Type de fichier ('pptx' ou 'markdown')
     * @returns {Promise<string|null>} - Chemin du PDF ou null si échec
     */
    try {
        const response = await fetch('/api/convert-to-pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                file_path: filePath,
                file_type: fileType
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            return data.pdf_path;
        } else {
            console.error('Conversion PDF échouée:', data.error || data.message);
            alert(data.error || 'Conversion PDF échouée. Vérifiez que LibreOffice est installé.');
            return null;
        }
    } catch (error) {
        console.error('Erreur lors de la conversion PDF:', error);
        alert('Erreur lors de la conversion PDF: ' + error.message);
        return null;
    }
}

async function downloadAsPDF(filePath, fileType = 'pptx', buttonId = null) {
    /**
     * Convertit et télécharge un fichier en PDF
     *
     * @param {string} filePath - Chemin relatif du fichier
     * @param {string} fileType - Type de fichier ('pptx' ou 'markdown')
     * @param {string|null} buttonId - ID du bouton à désactiver pendant la conversion
     */
    const btn = buttonId ? document.getElementById(buttonId) : null;
    const originalText = btn ? btn.textContent : '';

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Conversion en cours...';
    }

    try {
        const pdfPath = await convertToPDF(filePath, fileType);

        if (pdfPath) {
            // Télécharger le PDF
            window.location.href = `/api/download?path=${encodeURIComponent(pdfPath)}`;

            if (btn) {
                btn.textContent = '✅ PDF téléchargé !';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.disabled = false;
                }, 2000);
            }
        } else {
            if (btn) {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        }
    } catch (error) {
        console.error('Erreur:', error);
        if (btn) {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }
}

async function checkPDFCapabilities() {
    /**
     * Vérifie les capacités de conversion PDF disponibles
     *
     * @returns {Promise<Object>} - Objet avec les capacités disponibles
     */
    try {
        const response = await fetch('/api/pdf-capabilities');
        const data = await response.json();
        return data.capabilities || {};
    } catch (error) {
        console.error('Erreur lors de la vérification des capacités PDF:', error);
        return {};
    }
}

window.convertToPDF = convertToPDF;
window.downloadAsPDF = downloadAsPDF;
window.checkPDFCapabilities = checkPDFCapabilities;

// ====================================
// PROPOSAL CANVA PAGE (Gemini Mode)
// ====================================

let conversationHistory = [];
let currentProposal = null;
let uploadedFile = null;
let tenderText = '';

function initProposalCanvaPage() {
    console.log('Init proposal canva page');

    const form = document.getElementById('canva-form');
    const textarea = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const fileZone = document.getElementById('file-upload-zone');
    const fileInput = document.getElementById('tender-file');
    const fileName = document.getElementById('file-name');
    const sectionsPanel = document.getElementById('sections-panel');

    // === FILE UPLOAD ===
    fileZone.addEventListener('click', () => fileInput.click());

    fileZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileZone.style.borderColor = 'var(--corail)';
        fileZone.style.background = 'var(--rose-poudre)';
    });

    fileZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileZone.style.borderColor = '';
        fileZone.style.background = '';
    });

    fileZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileZone.style.borderColor = '';
        fileZone.style.background = '';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadedFile = files[0];
            fileName.textContent = files[0].name;
            fileZone.classList.add('has-file');

            // Read file content
            await readTenderFile(files[0]);

            // Show sections panel
            sectionsPanel.style.display = 'block';
            addMessage('assistant', `✅ Fichier chargé : ${files[0].name}<br>Cliquez sur une section pour commencer la génération.`);
        }
    });

    fileInput.addEventListener('change', async () => {
        if (fileInput.files.length > 0) {
            uploadedFile = fileInput.files[0];
            fileName.textContent = fileInput.files[0].name;
            fileZone.classList.add('has-file');

            // Read file content
            await readTenderFile(fileInput.files[0]);

            // Show sections panel
            sectionsPanel.style.display = 'block';
            addMessage('assistant', `✅ Fichier chargé : ${fileInput.files[0].name}<br>Cliquez sur une section pour commencer la génération.`);
        }
    });

    // === SECTION BUTTONS ===
    const sectionButtons = document.querySelectorAll('.section-btn');
    sectionButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const section = btn.dataset.section;
            generateSection(section);
        });
    });

    // Auto-resize textarea
    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    });

    // Submit form
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userMessage = textarea.value.trim();

        if (!userMessage) return;

        // Add user message to conversation
        addMessage('user', userMessage);
        textarea.value = '';
        textarea.style.height = 'auto';

        // Disable input while processing
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<span class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></span>';

        try {
            // Prepare request data
            const requestData = {
                message: userMessage,
                conversation_history: conversationHistory,
                current_proposal: currentProposal,
                tender_text: tenderText
            };

            // Send to backend
            const response = await fetch('/api/proposal-canva/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            if (data.error) {
                addMessage('assistant', '❌ Erreur: ' + data.error);
            } else {
                // Add assistant response
                addMessage('assistant', data.response);

                // Update conversation history
                conversationHistory = data.conversation_history;

                // Update canvas with slides
                if (data.slides && data.slides.length > 0) {
                    currentProposal = data;
                    updateCanvas(data.slides);
                    showDownloadButtons(data.pptx_path);
                }
            }
        } catch (error) {
            console.error('Error:', error);
            addMessage('assistant', '❌ Erreur de connexion: ' + error.message);
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = 'Envoyer';
        }
    });
}

async function readTenderFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            tenderText = e.target.result;
            resolve();
        };
        reader.onerror = reject;
        reader.readAsText(file);
    });
}

async function generateSection(section) {
    if (!tenderText) {
        addMessage('assistant', '❌ Veuillez d\'abord uploader un appel d\'offres.');
        return;
    }

    addMessage('user', `Génère la section : ${section}`);

    try {
        const response = await fetch('/api/proposal-canva/generate-section', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section: section,
                tender_text: tenderText,
                current_proposal: currentProposal
            })
        });

        const data = await response.json();

        if (data.error) {
            addMessage('assistant', '❌ Erreur: ' + data.error);
        } else {
            addMessage('assistant', data.response || `✅ Section "${section}" générée !`);

            // Update canvas with new slides
            if (data.slides && data.slides.length > 0) {
                // Append to existing proposal or create new
                if (currentProposal && currentProposal.slides) {
                    currentProposal.slides = [...currentProposal.slides, ...data.slides];
                } else {
                    currentProposal = data;
                }

                updateCanvas(currentProposal.slides);
                showDownloadButtons(data.pptx_path);
            }
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage('assistant', '❌ Erreur de connexion: ' + error.message);
    }
}

function addMessage(role, content) {
    const messagesContainer = document.getElementById('conversation-messages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = content.replace(/\n/g, '<br>');

    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

    messageDiv.appendChild(bubble);
    messageDiv.appendChild(time);
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Store in conversation history
    conversationHistory.push({ role, content });
}

function updateCanvas(slides) {
    const canvasContent = document.getElementById('canvas-content');
    const slidesCount = document.getElementById('slides-count');

    // Update count
    slidesCount.textContent = `${slides.length} slide${slides.length > 1 ? 's' : ''}`;

    // Clear canvas
    canvasContent.innerHTML = '';

    // Add slides
    slides.forEach((slide, index) => {
        const slideDiv = createSlidePreview(slide, index);
        canvasContent.appendChild(slideDiv);
    });
}

function createSlidePreview(slide, index) {
    const slideDiv = document.createElement('div');
    slideDiv.className = 'slide-preview';

    const slideType = slide.type || 'content';
    const slideTypeLabel = {
        'cover': 'Couverture',
        'section': 'Section',
        'content': 'Contenu',
        'diagram': 'Diagramme',
        'stat': 'Statistique',
        'quote': 'Citation',
        'highlight': 'Points clés',
        'closing': 'Clôture'
    }[slideType] || 'Contenu';

    slideDiv.innerHTML = `
        <div class="slide-preview-header">
            <div class="slide-number">Slide ${index + 1}</div>
            <div class="slide-type-badge">${slideTypeLabel}</div>
        </div>
        <div class="slide-preview-content">
            ${generateSlideHTML(slide)}
        </div>
    `;

    return slideDiv;
}

function generateSlideHTML(slide) {
    const type = slide.type || 'content';

    switch(type) {
        case 'cover':
            return `
                <h4>${slide.title || ''}</h4>
                <p style="color: var(--gris-moyen); margin-top: 0.5rem;">${slide.subtitle || ''}</p>
            `;

        case 'section':
            return `
                <h4>${slide.title || ''}</h4>
            `;

        case 'content':
            const bullets = slide.bullets || [];
            return `
                <h4>${slide.title || ''}</h4>
                <ul>
                    ${bullets.map(b => `<li>${b}</li>`).join('')}
                </ul>
            `;

        case 'stat':
            return `
                <h4 style="font-size: 3rem; color: var(--corail); margin: 1rem 0;">${slide.stat_value || ''}</h4>
                <h4 style="font-size: 1.3rem; margin: 0.5rem 0;">${slide.stat_label || ''}</h4>
                <p style="color: var(--gris-moyen); margin-top: 1rem;">${slide.context || ''}</p>
            `;

        case 'quote':
            return `
                <div style="font-size: 1.5rem; color: var(--corail); margin-bottom: 1rem;">"</div>
                <h4 style="font-style: italic; font-weight: normal;">${slide.quote_text || ''}</h4>
                ${slide.author ? `<p style="margin-top: 1rem; color: var(--gris-moyen);">— ${slide.author}</p>` : ''}
            `;

        case 'highlight':
            const keyPoints = slide.key_points || [];
            return `
                <h4>${slide.title || ''}</h4>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-top: 1rem;">
                    ${keyPoints.map((point, i) => `
                        <div style="background: var(--rose-poudre); padding: 1rem; border-radius: 8px;">
                            <div style="font-weight: bold; color: var(--corail); margin-bottom: 0.5rem;">${i + 1}</div>
                            <div>${point}</div>
                        </div>
                    `).join('')}
                </div>
            `;

        case 'diagram':
            const elements = slide.elements || [];
            return `
                <h4>${slide.title || ''}</h4>
                <div style="background: var(--gris-clair); padding: 2rem; border-radius: 8px; margin-top: 1rem; text-align: center;">
                    <div style="color: var(--gris-moyen); font-size: 0.9rem;">Diagramme: ${slide.diagram_type || 'flow'}</div>
                    <div style="margin-top: 1rem; display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
                        ${elements.map(el => `
                            <div style="background: var(--blanc); padding: 0.75rem 1.5rem; border-radius: 8px; border: 2px solid var(--corail);">
                                ${el}
                            </div>
                        `).join(' → ')}
                    </div>
                </div>
            `;

        default:
            return `<h4>${slide.title || 'Slide'}</h4>`;
    }
}

function showDownloadButtons(pptxPath) {
    const downloadPptx = document.getElementById('download-pptx-btn');
    const downloadPdf = document.getElementById('download-pdf-btn');
    const regenerateBtn = document.getElementById('regenerate-btn');

    if (pptxPath) {
        downloadPptx.style.display = 'flex';
        downloadPdf.style.display = 'flex';
        regenerateBtn.style.display = 'flex';

        downloadPptx.onclick = () => {
            window.location.href = '/api/download?path=' + encodeURIComponent(pptxPath);
        };
    }
}

function useSuggestion(text) {
    const textarea = document.getElementById('user-input');
    textarea.value = text;
    textarea.focus();
}

function downloadPPTX() {
    if (currentProposal && currentProposal.pptx_path) {
        window.location.href = '/api/download?path=' + encodeURIComponent(currentProposal.pptx_path);
    }
}

async function downloadPDF() {
    if (currentProposal && currentProposal.pptx_path) {
        await downloadAsPDF(currentProposal.pptx_path, 'pptx', 'download-pdf-btn');
    }
}

async function regenerateAll() {
    const userMessage = "Régénère toutes les slides en améliorant la qualité et le style";
    document.getElementById('user-input').value = userMessage;
    document.getElementById('canva-form').dispatchEvent(new Event('submit'));
}

// Expose globally
window.initProposalCanvaPage = initProposalCanvaPage;
window.useSuggestion = useSuggestion;
window.downloadPPTX = downloadPPTX;
window.downloadPDF = downloadPDF;
window.regenerateAll = regenerateAll;

// === LOADING & PROGRESS FUNCTIONS ===
let currentPptxPath = null;

function showLoading() {
    const loadingState = document.getElementById('loading-state');
    const emptyCanvas = document.getElementById('empty-canvas');
    const slidesContainer = document.getElementById('slides-container');
    
    if (loadingState) loadingState.style.display = 'flex';
    if (emptyCanvas) emptyCanvas.style.display = 'none';
    if (slidesContainer) slidesContainer.style.display = 'none';
    
    // Reset all steps to pending
    const steps = document.querySelectorAll('.progress-step');
    steps.forEach(step => {
        step.classList.remove('active', 'done');
        step.classList.add('pending');
        const icon = step.querySelector('.step-icon');
        if (icon) icon.textContent = step.querySelector('.step-icon').dataset.number || icon.textContent;
    });
}

function hideLoading() {
    const loadingState = document.getElementById('loading-state');
    const emptyCanvas = document.getElementById('empty-canvas');
    const slidesContainer = document.getElementById('slides-container');
    
    if (loadingState) loadingState.style.display = 'none';
    
    // Show slides container if there are slides, otherwise show empty state
    const hasSlides = currentProposal && currentProposal.slides && currentProposal.slides.length > 0;
    if (slidesContainer) slidesContainer.style.display = hasSlides ? 'flex' : 'none';
    if (emptyCanvas) emptyCanvas.style.display = hasSlides ? 'none' : 'flex';
}

function updateProgress(stepName, status) {
    const step = document.querySelector(`.progress-step[data-step="${stepName}"]`);
    if (!step) return;
    
    step.classList.remove('pending', 'active', 'done');
    step.classList.add(status);
    
    const icon = step.querySelector('.step-icon');
    if (status === 'done' && icon) {
        // Store original number
        if (!icon.dataset.number) {
            icon.dataset.number = icon.textContent;
        }
        icon.textContent = '';
    }
}

function setLoadingText(text) {
    const loadingText = document.getElementById('loading-text');
    if (loadingText) loadingText.textContent = text;
}

// === DOWNLOAD & EXPORT FUNCTIONS ===
async function downloadFile(format) {
    if (!currentPptxPath) {
        alert('Aucun fichier à télécharger. Générez d\'abord une proposition.');
        return;
    }
    
    try {
        const response = await fetch('/api/proposal-canva/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pptx_path: currentPptxPath,
                format: format,
                slides: currentProposal.slides
            })
        });
        
        if (!response.ok) {
            throw new Error('Erreur lors du téléchargement');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        const extensions = { pptx: 'pptx', pdf: 'pdf', md: 'md', odt: 'odt' };
        a.download = `proposition_${Date.now()}.${extensions[format] || format}`;
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Download error:', error);
        alert('Erreur lors du téléchargement: ' + error.message);
    }
}

async function exportToGoogleSlides() {
    if (!currentProposal || !currentProposal.slides) {
        alert('Aucune slide à exporter. Générez d\'abord une proposition.');
        return;
    }
    
    try {
        const response = await fetch('/api/proposal-canva/export-google-slides', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                slides: currentProposal.slides,
                pptx_path: currentPptxPath
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            alert('Erreur: ' + data.error);
        } else if (data.url) {
            window.open(data.url, '_blank');
            addMessage('assistant', `✅ Exporté vers Google Slides: <a href="${data.url}" target="_blank">Ouvrir</a>`);
        }
    } catch (error) {
        console.error('Export error:', error);
        alert('Erreur lors de l\'export vers Google Slides: ' + error.message);
    }
}

function downloadPPTX() {
    downloadFile('pptx');
}

function downloadPDF() {
    downloadFile('pdf');
}

function regenerateAll() {
    if (!currentProposal) {
        alert('Aucune proposition à régénérer.');
        return;
    }
    
    if (confirm('Voulez-vous régénérer toute la proposition ?')) {
        currentProposal = null;
        const textarea = document.getElementById('user-input');
        if (textarea) {
            textarea.value = 'Régénère toute la proposition avec les mêmes informations mais de manière améliorée.';
            document.getElementById('canva-form').dispatchEvent(new Event('submit'));
        }
    }
}

// === DOCUMENT TO PRESENTATION PAGE ===

function initDocToPresentationPage() {
    const form = document.getElementById('doc-presentation-form');
    const fileZone = document.getElementById('doc-upload-zone');
    const fileInput = document.getElementById('doc-files');
    const fileList = document.getElementById('file-list');

    if (!form) return;

    // File upload handling
    fileZone.addEventListener('click', () => fileInput.click());

    fileZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileZone.style.borderColor = 'var(--corail)';
        fileZone.style.background = 'var(--rose-poudre)';
    });

    fileZone.addEventListener('dragleave', () => {
        fileZone.style.borderColor = '';
        fileZone.style.background = '';
    });

    fileZone.addEventListener('drop', (e) => {
        e.preventDefault();
        fileZone.style.borderColor = '';
        fileZone.style.background = '';
        const dt = new DataTransfer();
        for (const file of e.dataTransfer.files) {
            dt.items.add(file);
        }
        fileInput.files = dt.files;
        updateFileList(fileInput.files);
    });

    fileInput.addEventListener('change', () => {
        updateFileList(fileInput.files);
    });

    function updateFileList(files) {
        fileList.innerHTML = '';
        for (const file of files) {
            const div = document.createElement('div');
            div.style.cssText = 'padding: 0.5rem; background: var(--gris-clair); border-radius: 6px; margin-bottom: 0.25rem; font-size: 0.85rem;';
            div.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} Ko)`;
            fileList.appendChild(div);
        }
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const files = fileInput.files;
        const targetAudience = document.getElementById('target-audience').value.trim();
        const objective = document.getElementById('presentation-objective').value.trim();

        if (!files.length) {
            alert('Veuillez ajouter au moins un document.');
            return;
        }
        if (!targetAudience || !objective) {
            alert('Veuillez remplir le public cible et l\'objectif.');
            return;
        }

        const formData = new FormData();
        formData.append('target_audience', targetAudience);
        formData.append('objective', objective);
        for (const file of files) {
            formData.append('files', file);
        }

        // Show progress
        const progress = document.getElementById('progress');
        const generateBtn = document.getElementById('generate-btn');
        progress.style.display = 'block';
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generation en cours...';

        try {
            const response = await fetch('/api/doc-to-presentation/generate', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.error) {
                showError('doc-to-presentation', data.error);
                return;
            }

            // Connect to SSE stream
            connectSSE(`/api/doc-to-presentation/stream/${data.job_id}`, 'doc-to-presentation');
        } catch (error) {
            showError('doc-to-presentation', error.message);
        }
    });
}

function displayDocToPresentationResult(data) {
    const progress = document.getElementById('progress');
    const resultSection = document.getElementById('result');
    const slideCount = document.getElementById('slide-count');
    const slidesPreview = document.getElementById('slides-preview');
    const downloadBtn = document.getElementById('download-pptx');
    const generateBtn = document.getElementById('generate-btn');

    if (progress) progress.style.display = 'none';
    if (generateBtn) {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generer la presentation';
    }

    // Slide count
    if (slideCount) slideCount.textContent = data.slide_count || 0;

    // Slides preview
    if (slidesPreview && data.slides) {
        let html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; padding: 1rem;">';
        data.slides.forEach((slide, i) => {
            const typeLabel = {
                'cover': 'Couverture', 'section': 'Section', 'content': 'Contenu',
                'stat': 'Statistique', 'highlight': 'Points cles', 'diagram': 'Diagramme', 'closing': 'Cloture'
            }[slide.type] || 'Slide';

            html += `<div style="background: white; border: 1px solid var(--gris-clair); border-radius: 8px; padding: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <small style="color: var(--gris-moyen);">Slide ${i + 1}</small>
                    <small style="background: var(--rose-poudre); padding: 2px 8px; border-radius: 4px; color: var(--corail);">${typeLabel}</small>
                </div>
                <strong>${slide.title || ''}</strong>
                ${slide.bullets ? '<ul style="font-size: 0.85rem; margin-top: 0.5rem;">' + slide.bullets.map(b => `<li>${b}</li>`).join('') + '</ul>' : ''}
                ${slide.stat_value ? `<div style="font-size: 2rem; color: var(--corail); font-weight: bold;">${slide.stat_value}</div>` : ''}
                ${slide.subtitle ? `<div style="color: var(--gris-moyen); font-size: 0.9rem;">${slide.subtitle}</div>` : ''}
            </div>`;
        });
        html += '</div>';
        slidesPreview.innerHTML = html;
    }

    // Download button
    if (downloadBtn && data.pptx_path) {
        downloadBtn.href = `/api/download?path=${encodeURIComponent(data.pptx_path)}`;
        downloadBtn.style.display = 'inline-flex';
    }

    resultSection.classList.add('active');
    resultSection.scrollIntoView({ behavior: 'smooth' });
}
