// State
let sessionId = localStorage.getItem('el_session') || null;
let currentCourseId = null;
let currentQuizId = null;
let currentAttemptId = null;
let currentQuestion = null;
let totalQuestions = 0;
let answeredCount = 0;
let quizTimer = null;
let quizSeconds = 0;
let coursesCache = [];

// Chat state
let chatMessages = [];
let isInterviewing = false;
let chatCurrentCourseId = null;
let chatCurrentTopic = "";
let chatCurrentRole = "";
let chatInterviewerName = "";
let chatInterviewerLinkedin = "";
let chatInterviewType = "";

// Init
document.addEventListener('DOMContentLoaded', async () => {
    await initSession();
    loadCourses();
});

async function initSession() {
    try {
        const resp = await fetch('/api/elearning/session/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_identifier: sessionId })
        });
        const data = await resp.json();
        sessionId = data.session_identifier;
        localStorage.setItem('el_session', sessionId);
    } catch (e) { console.error('Session init error:', e); }
}

// Tab navigation
function switchTab(tab) {
    document.querySelectorAll('.el-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.el-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    document.querySelectorAll('.el-tab')[
        ['generate', 'library', 'quiz', 'path'].indexOf(tab)
    ].classList.add('active');

    if (tab === 'library') loadCourses();
    if (tab === 'quiz') populateQuizCourseSelect();
    if (tab === 'path') populatePathCourseSelect();
}

// ==================
// MODE SELECTION
// ==================
let currentMode = 'free';

const modePlaceholders = {
    free: 'Ex: Introduction a Python, Machine Learning, Gestion de projet Agile...',
    interview: 'Ex: Data Engineer chez Google, Architecte Cloud AWS, Consultant SAP...',
    certification: 'Ex: AWS Solutions Architect, PMP, Scrum Master PSM I, Azure AZ-900...',
    training: 'Ex: Formation Docker pour devs, Atelier IA generative, Workshop Python...',
};

const modeLabels = {
    free: 'Sujet du cours',
    interview: 'Poste ou domaine de l\'entretien',
    certification: 'Nom de la certification',
    training: 'Sujet de la formation a donner',
};

function selectMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-card').forEach(c => c.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
    const input = document.getElementById('gen-topic');
    input.placeholder = modePlaceholders[mode] || modePlaceholders.free;
    document.getElementById('gen-topic-label').innerHTML =
        modeLabels[mode] + ' <span style="color:#6b7280;font-weight:400">(ou importer un document)</span>';

    // Hide audience field for certification (consultant is the only learner)
    const audienceGroup = document.getElementById('gen-audience-group');
    if (mode === 'certification') {
        audienceGroup.style.display = 'none';
        document.getElementById('gen-audience').value = 'Candidat a la certification';
    } else {
        audienceGroup.style.display = '';
        const sel = document.getElementById('gen-audience');
        if (sel.value === 'Candidat a la certification') {
            sel.value = 'Debutants sans experience';
        }
    }

    // Update file upload hint per mode
    const fileLabel = document.getElementById('gen-file-label');
    if (!document.getElementById('gen-file').files.length) {
        if (mode === 'certification') {
            fileLabel.textContent = 'Importer un support de certification (syllabus, exemples d\'examen...)';
        } else {
            fileLabel.textContent = 'Choisir un fichier PDF, PPTX, HTML ou Markdown';
        }
    }

    // Handle custom audience visibility when switching modes
    const audienceSel = document.getElementById('gen-audience');
    const customAudienceInput = document.getElementById('gen-audience-custom');
    if (mode === 'certification') {
        customAudienceInput.style.display = 'none';
    } else {
        if (audienceSel.value === 'custom') {
            customAudienceInput.style.display = '';
        }
    }

    // Show interviewer fields + interview type + consultant selector if in interview mode
    const interviewerGroup = document.getElementById('interviewer-group');
    const interviewTypeGroup = document.getElementById('interview-type-group');
    const consultantSelectGroup = document.getElementById('consultant-select-group');
    if (mode === 'interview') {
        interviewerGroup.style.display = 'block';
        interviewTypeGroup.style.display = '';
        consultantSelectGroup.style.display = 'block';
        loadSkillsMarketConsultants();
    } else {
        interviewerGroup.style.display = 'none';
        interviewTypeGroup.style.display = 'none';
        consultantSelectGroup.style.display = 'none';
        document.getElementById('gen-use-consultant').checked = false;
        document.getElementById('gen-consultant-select').style.display = 'none';
    }
}

async function loadSkillsMarketConsultants() {
    const sel = document.getElementById('gen-consultant-select');
    if (sel.dataset.loaded === 'true') return;
    try {
        const resp = await fetch('/api/skills-market/consultants');
        if (!resp.ok) return;
        const data = await resp.json();
        const consultants = data.consultants || data || [];
        sel.innerHTML = '<option value="0">-- Choisir un consultant --</option>';
        consultants.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = (c.name || '') + (c.title ? ' – ' + c.title : '');
            sel.appendChild(opt);
        });
        sel.dataset.loaded = 'true';
    } catch (e) {
        console.error('Erreur chargement consultants Skills Market:', e);
    }
}

function toggleConsultantSelect() {
    const checked = document.getElementById('gen-use-consultant').checked;
    const sel = document.getElementById('gen-consultant-select');
    const audienceSel = document.getElementById('gen-audience');
    sel.style.display = checked ? 'block' : 'none';
    audienceSel.style.display = checked ? 'none' : '';
}

function toggleAutoDuration() {
    const checked = document.getElementById('gen-auto-duration').checked;
    const durationInput = document.getElementById('gen-duration');
    durationInput.disabled = checked;
    durationInput.style.opacity = checked ? '0.4' : '1';
}

// ==================
// FILE UPLOAD
// ==================
let elDocumentContent = '';

async function handleElearningFileUpload(input) {
    const file = input.files[0];
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    const label = document.getElementById('gen-file-label');
    const clearBtn = document.getElementById('gen-file-clear');

    if (['txt', 'md', 'markdown'].includes(ext)) {
        elDocumentContent = await file.text();
        label.textContent = file.name + ' (' + (elDocumentContent.length / 1000).toFixed(1) + 'k car.)';
        clearBtn.style.display = 'inline-block';
        return;
    }

    label.textContent = 'Extraction en cours...';
    try {
        const formData = new FormData();
        formData.append('file', file);
        const resp = await fetch('/api/elearning/course/upload-document', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.error) { alert('Erreur: ' + data.error); label.textContent = 'Choisir un fichier'; return; }
        elDocumentContent = data.text;
        label.textContent = data.filename + ' (' + (data.length / 1000).toFixed(1) + 'k car.)';
        clearBtn.style.display = 'inline-block';
    } catch (e) {
        alert('Erreur: ' + e.message);
        label.textContent = 'Choisir un fichier PDF, PPTX, HTML ou Markdown';
    }
}

function clearElearningFile() {
    elDocumentContent = '';
    document.getElementById('gen-file').value = '';
    document.getElementById('gen-file-label').textContent = 'Choisir un fichier PDF, PPTX, HTML ou Markdown';
    document.getElementById('gen-file-clear').style.display = 'none';
}

function toggleCustomAudience(selectElement) {
    const customInput = document.getElementById('gen-audience-custom');
    if (selectElement.value === 'custom') {
        customInput.style.display = '';
        customInput.focus();
    } else {
        customInput.style.display = 'none';
    }
}

// ==================
// COURSE GENERATION
// ==================

async function generateCourse() {
    const topic = document.getElementById('gen-topic').value.trim();
    if (!topic && !elDocumentContent) return alert('Veuillez entrer un sujet ou importer un document');

    let audience = document.getElementById('gen-audience').value;
    if (audience === 'custom') {
        audience = document.getElementById('gen-audience-custom').value.trim();
        if (!audience) return alert('Veuillez preciser le public cible personnalisé');
    }
    const duration = document.getElementById('gen-duration').value;
    const difficulty = document.querySelector('input[name="gen-difficulty"]:checked').value;

    const btn = document.getElementById('btn-generate');
    btn.disabled = true;
    btn.textContent = elDocumentContent ? 'Analyse du document...' : 'Generation en cours...';

    const progress = document.getElementById('gen-progress');
    progress.style.display = 'block';
    document.getElementById('gen-steps').innerHTML = '';
    document.getElementById('gen-progress-bar').style.width = '10%';

    const autoDuration = document.getElementById('gen-auto-duration').checked;
    const form = new FormData();
    form.append('topic', topic);
    form.append('target_audience', audience);
    form.append('duration_hours', autoDuration ? '0' : duration);
    form.append('difficulty', difficulty);
    form.append('mode', currentMode);
    form.append('auto_duration', autoDuration ? 'true' : 'false');

    if (currentMode === 'interview') {
        form.append('interviewer_name', document.getElementById('gen-interviewer-name').value.trim());
        form.append('interviewer_linkedin', document.getElementById('gen-interviewer-linkedin').value.trim());
        const interviewTypeChecked = document.querySelector('input[name="interview-type"]:checked');
        form.append('interview_type', interviewTypeChecked ? interviewTypeChecked.value : '');
        const useConsultant = document.getElementById('gen-use-consultant').checked;
        if (useConsultant) {
            const consultantId = document.getElementById('gen-consultant-select').value;
            form.append('consultant_id', consultantId || '0');
        }
    }

    if (elDocumentContent) form.append('document_content', elDocumentContent);

    try {
        const resp = await fetch('/api/elearning/course/generate', { method: 'POST', body: form });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        await streamJob(data.job_id, 'gen-progress-bar', 'gen-steps', (result) => {
            btn.disabled = false;
            btn.textContent = 'Generer le cours';
            if (result.course_id) {
                currentCourseId = result.course_id;
                loadCourseDetail(result.course_id, 'gen');
            }
        });
    } catch (e) {
        alert('Erreur: ' + e.message);
        btn.disabled = false;
        btn.textContent = 'Generer le cours';
    }
}

async function loadCourseDetail(courseId, target) {
    const resp = await fetch('/api/elearning/course/' + courseId);
    const data = await resp.json();
    if (!data.course) return;

    const c = data.course;

    if (target === 'gen') {
        document.getElementById('gen-result').style.display = 'block';
        document.getElementById('gen-result-title').textContent = c.title;
        document.getElementById('gen-result-desc').textContent = c.description;

        let objHtml = '<h4>Objectifs d\'apprentissage</h4><ul>';
        (c.learning_objectives || []).forEach(o => objHtml += '<li>' + o + '</li>');
        objHtml += '</ul>';
        document.getElementById('gen-result-objectives').innerHTML = objHtml;

        document.getElementById('gen-result-modules').innerHTML = renderModules(c.modules, c);
    } else if (target === 'modal') {
        document.getElementById('modal-title').textContent = c.title;
        document.getElementById('modal-desc').textContent = c.description;

        let objHtml = '<h4>Objectifs</h4><ul>';
        (c.learning_objectives || []).forEach(o => objHtml += '<li>' + o + '</li>');
        objHtml += '</ul>';
        document.getElementById('modal-objectives').innerHTML = objHtml;

        document.getElementById('modal-modules').innerHTML = renderModules(c.modules, c);

        // Toggle interview button
        const interviewBtn = document.getElementById('btn-modal-interview');
        if (c.mode === 'interview') {
            interviewBtn.style.display = 'block';
        } else {
            interviewBtn.style.display = 'none';
        }
    }
}

function renderExercise(e, sid) {
    let html = '<div style="padding: 0.5rem; background: #eff6ff; border-radius: 6px; margin: 0.3rem 0;">';
    html += '<strong>' + (e.title || '') + '</strong>';
    html += '<p style="margin: 0.2rem 0; font-size: 0.85rem;">' + (e.description || '') + '</p>';
    if (e.hints && e.hints.length) {
        html += '<p style="margin: 0.2rem 0; font-size: 0.8rem; color: #6b7280;"><em>Indices : ' + e.hints.join(' · ') + '</em></p>';
    }
    if (e.solution) {
        html += '<div style="margin-top: 0.4rem;">';
        html += '<button onclick="toggleSolution(\'' + sid + '\')" style="font-size: 0.78rem; padding: 0.15rem 0.5rem; background: #fff; border: 1px solid #93c5fd; border-radius: 4px; cursor: pointer; color: #1d4ed8;">Voir la reponse</button>';
        html += '<div id="' + sid + '" style="display:none; margin-top: 0.4rem; padding: 0.5rem; background: #f0fdf4; border-left: 3px solid #22c55e; border-radius: 4px; font-size: 0.85rem; white-space: pre-wrap;">';
        html += e.solution.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        html += '</div></div>';
    }
    html += '</div>';
    return html;
}

function renderModules(modules, course) {
    return (modules || []).map((m, i) => {
        const mNum = m.module_number || (i + 1);
        let lessonsHtml = (m.lessons || []).map(l => {
            const mdContent = typeof marked !== 'undefined' ? marked.parse(l.content_markdown || '') : (l.content_markdown || '');
            let takeaways = '';
            if ((l.key_takeaways || []).length) {
                takeaways = '<div style="margin-top: 0.5rem;"><strong>Points cles:</strong><ul>' +
                    l.key_takeaways.map(k => '<li>' + k + '</li>').join('') + '</ul></div>';
            }
            const exList = l.practical_exercises || [];
            const hasMissingSolution = exList.some(e => !e.solution);
            let exercises = '';
            if (exList.length) {
                const exHtml = exList.map((e, ei) => {
                    const sid = 'sol-' + mNum + '-' + l.lesson_number + '-' + ei;
                    return renderExercise(e, sid);
                }).join('');
                const genBtn = hasMissingSolution && l.id && course
                    ? '<button id="gen-sol-btn-' + l.id + '" onclick="generateLessonSolutions(' + l.id + ', ' + (course.id || 0) + ', \'' + (course.topic || '').replace(/'/g, "\\'") + '\')" style="font-size: 0.78rem; padding: 0.2rem 0.6rem; background: #fff7ed; border: 1px solid #fb923c; border-radius: 4px; cursor: pointer; color: #c2410c; margin-top: 0.4rem;">Generer les reponses</button>'
                    : '';
                exercises = '<div id="exercises-' + l.id + '" style="margin-top: 0.5rem;"><strong>Exercices :</strong>' + exHtml + genBtn + '</div>';
            }
            return '<div class="lesson-item">' +
                '<h5>Lecon ' + l.lesson_number + ': ' + l.title + '</h5>' +
                '<div class="markdown-content">' + mdContent + '</div>' +
                takeaways + exercises +
                '</div>';
        }).join('');

        return '<div class="module-item">' +
            '<div class="module-header" onclick="this.nextElementSibling.classList.toggle(\'open\')">' +
            '<span>Module ' + mNum + ': ' + m.title + '</span>' +
            '<span style="font-size: 0.8rem; color: #6b7280;">' + (m.estimated_duration_minutes || 30) + ' min</span>' +
            '</div>' +
            '<div class="module-body">' +
            '<p style="color: #6b7280; font-size: 0.85rem;">' + (m.description || '') + '</p>' +
            lessonsHtml +
            '</div></div>';
    }).join('');
}

async function generateLessonSolutions(lessonId, courseId, topic) {
    const btn = document.getElementById('gen-sol-btn-' + lessonId);
    if (btn) { btn.textContent = 'Generation...'; btn.disabled = true; }

    // Collect current exercises from the rendered DOM is not reliable;
    // re-fetch the course to get the lesson data
    try {
        const courseResp = await fetch('/api/elearning/course/' + courseId);
        const courseData = await courseResp.json();
        let lesson = null;
        for (const mod of (courseData.course?.modules || [])) {
            for (const les of (mod.lessons || [])) {
                if (les.id === lessonId) { lesson = les; break; }
            }
            if (lesson) break;
        }
        if (!lesson) throw new Error('Lecon introuvable');

        const resp = await fetch('/api/elearning/lesson/' + lessonId + '/solutions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: courseId,
                topic: topic,
                lesson_title: lesson.title,
                exercises: lesson.practical_exercises || [],
                consultant_id: 0,
            }),
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        // Re-render only the exercises section for this lesson
        const container = document.getElementById('exercises-' + lessonId);
        if (container) {
            const updatedExHtml = (data.exercises || []).map((e, ei) => {
                const sid = 'sol-gen-' + lessonId + '-' + ei;
                return renderExercise(e, sid);
            }).join('');
            container.innerHTML = '<strong>Exercices :</strong>' + updatedExHtml;
        }
    } catch (err) {
        if (btn) { btn.textContent = 'Erreur – Reessayer'; btn.disabled = false; }
        console.error('generateLessonSolutions error:', err);
    }
}

function toggleSolution(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const btn = el.previousElementSibling;
    if (el.style.display === 'none') {
        el.style.display = 'block';
        if (btn) btn.textContent = 'Masquer la reponse';
    } else {
        el.style.display = 'none';
        if (btn) btn.textContent = 'Voir la reponse';
    }
}

function showRegenerateForm() {
    document.getElementById('regenerate-form').style.display =
        document.getElementById('regenerate-form').style.display === 'none' ? 'block' : 'none';
}

async function regenerateCourse() {
    if (!currentCourseId) return;
    const feedback = document.getElementById('regen-feedback').value.trim();
    if (!feedback) return alert('Veuillez entrer du feedback');

    const form = new FormData();
    form.append('feedback', feedback);

    const resp = await fetch('/api/elearning/course/' + currentCourseId + '/regenerate', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.job_id) {
        document.getElementById('gen-progress').style.display = 'block';
        await streamJob(data.job_id, 'gen-progress-bar', 'gen-steps', (result) => {
            if (result.course_id) {
                currentCourseId = result.course_id;
                loadCourseDetail(result.course_id, 'gen');
                document.getElementById('regenerate-form').style.display = 'none';
            }
        });
    }
}

// ==================
// LIBRARY
// ==================

async function loadCourses() {
    try {
        const resp = await fetch('/api/elearning/courses');
        const data = await resp.json();
        coursesCache = data.courses || [];
        renderCourseGrid(coursesCache);
    } catch (e) { console.error('Load courses error:', e); }
}

function renderCourseGrid(courses) {
    const grid = document.getElementById('library-grid');
    const empty = document.getElementById('library-empty');

    if (!courses.length) {
        grid.innerHTML = '';
        empty.style.display = 'block';
        return;
    }
    empty.style.display = 'none';

    grid.innerHTML = courses.map(c => `
    <div class="course-card" onclick="openCourseModal(${c.id})">
        <h4>${c.title}</h4>
        <div class="meta">
            <span class="badge badge-${c.difficulty_level}">${c.difficulty_level}</span>
            <span>${c.duration_hours}h</span>
            <span>${c.modules_count} modules</span>
            <span>${c.lessons_count} lecons</span>
        </div>
        <p style="font-size: 0.85rem; color: #6b7280; margin: 0;">${c.topic}</p>
    </div>
`).join('');
}

function openCourseModal(courseId) {
    currentCourseId = courseId;
    loadCourseDetail(courseId, 'modal');
    document.getElementById('course-modal').classList.add('open');
}

function closeCourseModal() {
    document.getElementById('course-modal').classList.remove('open');
}

async function deleteCourse() {
    if (!currentCourseId) return;
    if (!confirm('Supprimer ce cours et toutes ses donnees?')) return;

    await fetch('/api/elearning/course/' + currentCourseId, { method: 'DELETE' });
    closeCourseModal();
    loadCourses();
}

function generateQuizForCourse() {
    closeCourseModal();
    switchTab('quiz');
    setTimeout(() => {
        document.getElementById('quiz-course').value = currentCourseId;
        loadQuizLessons();
    }, 100);
}

function startLearningPath() {
    closeCourseModal();
    switchTab('path');
    setTimeout(() => {
        document.getElementById('path-course').value = currentCourseId;
    }, 100);
}

function startInterviewSimulation() {
    closeCourseModal();
    const course = coursesCache.find(c => c.id === currentCourseId);
    if (!course) return;

    chatCurrentCourseId = course.id;
    chatCurrentTopic = course.topic;
    chatCurrentRole = course.title;
    chatInterviewerName = "";
    chatInterviewerLinkedin = "";
    chatInterviewType = course.interview_type || "";

    // Reset chat
    chatMessages = [];
    isInterviewing = true;

    switchTab('quiz'); // Chat is in the quiz tab
    document.getElementById('quiz-setup').style.display = 'none';
    document.getElementById('quiz-active').style.display = 'none';
    document.getElementById('quiz-results').style.display = 'none';
    document.getElementById('interview-chat-active').style.display = 'block';

    document.getElementById('chat-messages').innerHTML = '';
    addChatMessage('interviewer', "Bonjour ! Je suis ravi de vous rencontrer pour cet entretien concernant le poste de **" + chatCurrentRole + "**. Nous allons discuter de vos competences en **" + chatCurrentTopic + "**. Pour commencer, pourriez-vous vous presenter brievement ?");
}

function addChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-message ' + role;
    msgDiv.innerHTML = typeof marked !== 'undefined' ? marked.parse(text) : text;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;

    if (role === 'candidate') {
        chatMessages.push({ role: 'user', content: text });
    } else {
        chatMessages.push({ role: 'assistant', content: text });
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text || !isInterviewing) return;

    input.value = '';
    input.style.height = 'auto';
    addChatMessage('candidate', text);

    const thinking = document.getElementById('chat-thinking');
    thinking.style.display = 'flex';
    document.getElementById('chat-btn-send').disabled = true;

    try {
        const chatBody = {
            topic: chatCurrentTopic,
            role: chatCurrentRole,
            messages: chatMessages,
            interviewer_name: chatInterviewerName,
            interviewer_linkedin: chatInterviewerLinkedin,
            interview_type: chatInterviewType,
        };
        const resp = await fetch('/api/elearning/interview/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(chatBody),
        });
        const data = await resp.json();

        thinking.style.display = 'none';
        document.getElementById('chat-btn-send').disabled = false;

        if (data.message) {
            addChatMessage('interviewer', data.message);
        } else if (data.error) {
            alert('Erreur: ' + data.error);
        }
    } catch (e) {
        thinking.style.display = 'none';
        document.getElementById('chat-btn-send').disabled = false;
        alert('Erreur: ' + e.message);
    }
}

function handleChatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
}

async function endInterview() {
    if (!confirm('Souhaitez-vous terminer l\'entretien et recevoir votre analyse ?')) return;

    isInterviewing = false;
    document.getElementById('interview-chat-active').style.display = 'none';
    document.getElementById('quiz-results').style.display = 'block';
    document.getElementById('quiz-results-title').textContent = "Analyse de l'entretien";
    document.getElementById('quiz-score').textContent = "Analyse...";
    document.getElementById('quiz-stats').innerHTML = "";
    document.getElementById('quiz-breakdown').innerHTML = "";

    const analysisArea = document.getElementById('interview-analysis-area');
    const analysisContent = document.getElementById('interview-analysis-content');
    analysisArea.style.display = 'block';
    analysisContent.innerHTML = '<p>Analyse en cours par l\'IA...</p>';

    try {
        const analyzeBody = {
            topic: chatCurrentTopic,
            role: chatCurrentRole,
            messages: chatMessages,
            interviewer_name: chatInterviewerName,
            interviewer_linkedin: chatInterviewerLinkedin,
            interview_type: chatInterviewType,
        };
        const resp = await fetch('/api/elearning/interview/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(analyzeBody),
        });
        const data = await resp.json();

        if (data.analysis) {
            document.getElementById('quiz-score').textContent = "Termine";
            analysisContent.innerHTML = typeof marked !== 'undefined' ? marked.parse(data.analysis) : data.analysis;
        } else {
            analysisContent.innerHTML = '<p>Erreur lors de l\'analyse.</p>';
        }
    } catch (e) {
        analysisContent.innerHTML = '<p>Erreur: ' + e.message + '</p>';
    }
}

// ==================
// QUIZ
// ==================

function populateQuizCourseSelect() {
    const sel = document.getElementById('quiz-course');
    const current = sel.value;
    sel.innerHTML = '<option value="">Selectionner un cours...</option>';
    coursesCache.forEach(c => {
        sel.innerHTML += `<option value="${c.id}">${c.title}</option>`;
    });
    if (current) sel.value = current;
}

async function loadQuizLessons() {
    const courseId = document.getElementById('quiz-course').value;
    const sel = document.getElementById('quiz-lesson');
    sel.innerHTML = '<option value="">Tout le cours</option>';

    if (!courseId) return;

    const resp = await fetch('/api/elearning/course/' + courseId);
    const data = await resp.json();
    if (!data.course) return;

    (data.course.modules || []).forEach(m => {
        (m.lessons || []).forEach(l => {
            sel.innerHTML += `<option value="${l.id}">M${m.module_number} - ${l.title}</option>`;
        });
    });

    // Load existing quizzes
    const qResp = await fetch('/api/elearning/quizzes/' + courseId);
    const qData = await qResp.json();
    const quizzes = qData.quizzes || [];

    const container = document.getElementById('existing-quizzes');
    const list = document.getElementById('quiz-list');

    if (quizzes.length) {
        container.style.display = 'block';
        list.innerHTML = quizzes.map(q => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 0.5rem;">
            <div>
                <strong>${q.title}</strong>
                <span class="badge badge-${q.difficulty_level}" style="margin-left: 0.5rem;">${q.difficulty_level}</span>
                <span style="color: #6b7280; font-size: 0.8rem; margin-left: 0.5rem;">${q.questions_count} questions</span>
            </div>
            <button class="el-btn el-btn-primary" style="padding: 0.3rem 0.8rem; font-size: 0.8rem;" onclick="startQuiz(${q.id})">Commencer</button>
        </div>
    `).join('');
    } else {
        container.style.display = 'none';
    }
}

async function generateQuiz() {
    const courseId = document.getElementById('quiz-course').value;
    if (!courseId) return alert('Selectionner un cours');

    const lessonId = document.getElementById('quiz-lesson').value || '';
    const difficulty = document.querySelector('input[name="quiz-difficulty"]:checked').value;

    const btn = document.getElementById('btn-gen-quiz');
    btn.disabled = true;

    const progress = document.getElementById('quiz-gen-progress');
    progress.style.display = 'block';

    const form = new FormData();
    form.append('course_id', courseId);
    if (lessonId) form.append('lesson_id', lessonId);
    form.append('difficulty', difficulty);
    form.append('mode', currentMode);

    try {
        const resp = await fetch('/api/elearning/quiz/generate', { method: 'POST', body: form });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        await streamJob(data.job_id, 'quiz-gen-bar', 'quiz-gen-steps', (result) => {
            btn.disabled = false;
            if (result.quiz_id) {
                startQuiz(result.quiz_id);
            }
        });
    } catch (e) {
        alert('Erreur: ' + e.message);
        btn.disabled = false;
    }
}

async function startQuiz(quizId) {
    currentQuizId = quizId;
    answeredCount = 0;

    const form = new FormData();
    form.append('quiz_id', quizId);
    form.append('session_identifier', sessionId);

    const resp = await fetch('/api/elearning/quiz/start', { method: 'POST', body: form });
    const data = await resp.json();

    if (data.error) return alert(data.error);

    currentAttemptId = data.attempt_id;
    totalQuestions = data.total_questions;
    currentQuestion = data.first_question;

    document.getElementById('quiz-setup').style.display = 'none';
    document.getElementById('quiz-active').style.display = 'block';
    document.getElementById('quiz-results').style.display = 'none';

    // Start timer
    quizSeconds = 0;
    if (quizTimer) clearInterval(quizTimer);
    quizTimer = setInterval(() => {
        quizSeconds++;
        const m = Math.floor(quizSeconds / 60).toString().padStart(2, '0');
        const s = (quizSeconds % 60).toString().padStart(2, '0');
        document.getElementById('quiz-timer').textContent = m + ':' + s;
    }, 1000);

    renderQuestion(currentQuestion);
}

function renderQuestion(q) {
    if (!q) return showQuizResults();

    document.getElementById('quiz-counter').textContent = `Question ${answeredCount + 1}/${totalQuestions}`;
    document.getElementById('quiz-q-text').textContent = q.question_text;

    const feedbackEl = document.getElementById('quiz-feedback-area');
    feedbackEl.style.display = 'none';
    feedbackEl.className = 'quiz-feedback';

    document.getElementById('btn-submit-answer').style.display = 'inline-block';
    document.getElementById('btn-next-question').style.display = 'none';

    const optionsEl = document.getElementById('quiz-options');
    const textEl = document.getElementById('quiz-text-input');

    if (q.question_type === 'mcq' || q.question_type === 'true_false') {
        optionsEl.style.display = 'block';
        textEl.style.display = 'none';
        optionsEl.innerHTML = (q.options || []).map((opt, i) =>
            `<div class="quiz-option" data-value="${opt}" onclick="selectOption(this)">${opt}</div>`
        ).join('');
    } else {
        optionsEl.style.display = 'none';
        textEl.style.display = 'block';
        document.getElementById('quiz-answer-text').value = '';
    }
}

function selectOption(el) {
    document.querySelectorAll('.quiz-option').forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
}

async function submitAnswer() {
    if (!currentQuestion || !currentAttemptId) return;

    let answer = '';
    if (currentQuestion.question_type === 'mcq' || currentQuestion.question_type === 'true_false') {
        const selected = document.querySelector('.quiz-option.selected');
        if (!selected) return alert('Selectionnez une reponse');
        answer = selected.dataset.value;
    } else {
        answer = document.getElementById('quiz-answer-text').value.trim();
        if (!answer) return alert('Entrez votre reponse');
    }

    document.getElementById('btn-submit-answer').disabled = true;

    const form = new FormData();
    form.append('attempt_id', currentAttemptId);
    form.append('question_id', currentQuestion.id);
    form.append('answer', answer);
    form.append('time_spent', quizSeconds);

    try {
        const resp = await fetch('/api/elearning/quiz/answer', { method: 'POST', body: form });
        const data = await resp.json();

        answeredCount++;

        // Show feedback
        const feedbackEl = document.getElementById('quiz-feedback-area');
        feedbackEl.style.display = 'block';
        feedbackEl.className = 'quiz-feedback ' + (data.is_correct ? 'correct' : 'wrong');
        feedbackEl.innerHTML = `
        <strong>${data.is_correct ? 'Correct !' : 'Incorrect'}</strong>
        <p style="margin: 0.3rem 0 0;">${data.explanation || data.feedback || ''}</p>
        ${data.difficulty_changed ? '<p style="margin: 0.3rem 0 0; font-size: 0.85rem; color: #6b7280;">Difficulte ajustee: <strong>' + data.current_difficulty + '</strong></p>' : ''}
    `;

        // Update difficulty badge
        const badgeEl = document.getElementById('quiz-difficulty-badge');
        badgeEl.textContent = data.current_difficulty;
        badgeEl.className = 'badge badge-' + data.current_difficulty;

        // Highlight correct/wrong options
        if (currentQuestion.question_type === 'mcq' || currentQuestion.question_type === 'true_false') {
            document.querySelectorAll('.quiz-option').forEach(o => {
                if (o.classList.contains('selected') && !data.is_correct) o.classList.add('wrong');
                if (o.classList.contains('selected') && data.is_correct) o.classList.add('correct');
            });
        }

        currentQuestion = data.next_question;

        document.getElementById('btn-submit-answer').style.display = 'none';
        document.getElementById('btn-submit-answer').disabled = false;
        document.getElementById('btn-next-question').style.display = 'inline-block';

        if (!data.next_question) {
            document.getElementById('btn-next-question').textContent = 'Voir les resultats';
        }
    } catch (e) {
        document.getElementById('btn-submit-answer').disabled = false;
        alert('Erreur: ' + e.message);
    }
}

function nextQuestion() {
    if (currentQuestion) {
        renderQuestion(currentQuestion);
    } else {
        showQuizResults();
    }
}

async function showQuizResults() {
    if (quizTimer) clearInterval(quizTimer);

    const resp = await fetch('/api/elearning/quiz/results/' + currentAttemptId);
    const data = await resp.json();
    const r = data.results;

    document.getElementById('quiz-active').style.display = 'none';
    document.getElementById('quiz-results').style.display = 'block';

    const score = r.score_percentage || 0;
    document.getElementById('quiz-score').textContent = Math.round(score) + '%';
    document.getElementById('quiz-score').style.color = score >= 70 ? '#10b981' : score >= 40 ? '#f59e0b' : '#ef4444';

    document.getElementById('quiz-stats').innerHTML = `
    <div><strong>${r.correct_answers}</strong><br><span style="font-size: 0.8rem; color: #6b7280;">Correctes</span></div>
    <div><strong>${r.total_questions}</strong><br><span style="font-size: 0.8rem; color: #6b7280;">Questions</span></div>
    <div><strong>${Math.floor(quizSeconds / 60)}m ${quizSeconds % 60}s</strong><br><span style="font-size: 0.8rem; color: #6b7280;">Temps</span></div>
`;

    // Breakdown
    const answers = r.answers || [];
    document.getElementById('quiz-breakdown').innerHTML = '<h4>Detail des reponses</h4>' +
        answers.map((a, i) => `
        <div style="padding: 0.5rem; border-left: 3px solid ${a.is_correct ? '#10b981' : '#ef4444'}; margin: 0.3rem 0; background: ${a.is_correct ? '#f0fdf4' : '#fef2f2'}; border-radius: 0 6px 6px 0;">
            <strong>Q${i + 1}:</strong> ${a.question_text}
            <br><span style="font-size: 0.85rem;">Votre reponse: ${a.student_answer} ${a.is_correct ? '&#10003;' : '&#10007; (Attendu: ' + a.correct_answer + ')'}</span>
        </div>
    `).join('');
}

function resetQuiz() {
    document.getElementById('quiz-setup').style.display = 'block';
    document.getElementById('quiz-active').style.display = 'none';
    document.getElementById('quiz-results').style.display = 'none';
    currentAttemptId = null;
    currentQuestion = null;
}

function createPathFromQuiz() {
    const courseId = document.getElementById('quiz-course').value;
    if (courseId) currentCourseId = parseInt(courseId);
    switchTab('path');
    setTimeout(() => {
        if (currentCourseId) document.getElementById('path-course').value = currentCourseId;
    }, 100);
}

// ==================
// LEARNING PATH
// ==================

function populatePathCourseSelect() {
    const sel = document.getElementById('path-course');
    const current = sel.value;
    sel.innerHTML = '<option value="">Selectionner un cours...</option>';
    coursesCache.forEach(c => {
        sel.innerHTML += `<option value="${c.id}">${c.title}</option>`;
    });
    if (current) sel.value = current;
}

async function generatePath() {
    const courseId = document.getElementById('path-course').value;
    if (!courseId) return alert('Selectionner un cours');

    const goalsText = document.getElementById('path-goals').value.trim();
    const goals = goalsText ? goalsText.split('\n').filter(g => g.trim()) : ['Completer le cours'];

    const btn = document.getElementById('btn-gen-path');
    btn.disabled = true;

    const progress = document.getElementById('path-gen-progress');
    progress.style.display = 'block';

    const form = new FormData();
    form.append('session_identifier', sessionId);
    form.append('course_id', courseId);
    form.append('goals', JSON.stringify(goals));

    try {
        const resp = await fetch('/api/elearning/learning-path/create', { method: 'POST', body: form });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        await streamJob(data.job_id, 'path-gen-bar', 'path-gen-steps', (result) => {
            btn.disabled = false;
            loadLearningPath(courseId);
        });
    } catch (e) {
        alert('Erreur: ' + e.message);
        btn.disabled = false;
    }
}

async function loadLearningPath(courseId) {
    try {
        const resp = await fetch('/api/elearning/learning-path/' + sessionId + '/' + courseId);
        if (!resp.ok) return;

        const data = await resp.json();
        const path = data.path;
        if (!path) return;

        document.getElementById('path-dashboard').style.display = 'block';

        // Progress
        const pct = path.current_progress_percentage || 0;
        document.getElementById('path-progress-pct').textContent = Math.round(pct) + '%';
        document.getElementById('path-progress-bar').style.width = pct + '%';

        // Gaps
        const gaps = path.knowledge_gaps || [];
        document.getElementById('path-gaps').innerHTML = gaps.length ?
            '<h4 style="color: #dc2626;">Lacunes identifiees</h4>' +
            gaps.map(g => `<div style="padding: 0.5rem; background: #fef2f2; border-radius: 6px; margin: 0.3rem 0; font-size: 0.9rem;">
            <strong>${g.title || 'Module ' + g.module_id}</strong>: ${g.reason || ''}
        </div>`).join('') : '';

        // Recommendations
        const recs = path.recommendations || [];
        document.getElementById('path-recommendations').innerHTML = recs.length ?
            '<h4>Recommandations</h4>' +
            recs.map(r => `<div class="path-step">
            <div style="flex: 1;">
                <strong>${r.type || 'Etude'}</strong> - Module ${r.module_id || ''}
                <p style="margin: 0.2rem 0 0; font-size: 0.85rem; color: #6b7280;">${r.reason || ''}</p>
            </div>
        </div>`).join('') : '';

        // Module progress
        const modProgress = path.module_progress || [];
        document.getElementById('path-modules').innerHTML = modProgress.length ?
            modProgress.map(mp => `
            <div style="display: flex; align-items: center; gap: 1rem; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 8px; margin: 0.5rem 0;">
                <div style="flex: 1;">
                    <div style="font-weight: 500;">Module ${mp.module_id}</div>
                    <div class="el-progress" style="margin-top: 0.3rem;">
                        <div class="el-progress-fill" style="width: ${mp.completion_percentage || 0}%;"></div>
                    </div>
                </div>
                <span class="badge badge-${mp.mastery_level || 'none'}">${mp.mastery_level || 'none'}</span>
                <span style="font-size: 0.85rem; color: #6b7280;">${Math.round(mp.completion_percentage || 0)}%</span>
            </div>
        `).join('') :
            '<p style="color: #6b7280; font-size: 0.85rem;">Commencez des quiz pour suivre votre progression.</p>';

    } catch (e) { console.error('Load path error:', e); }
}

// ==================
// SSE STREAMING
// ==================

async function streamJob(jobId, barId, stepsId, onDone) {
    const bar = document.getElementById(barId);
    const stepsEl = document.getElementById(stepsId);
    let progress = 20;

    return new Promise((resolve) => {
        const es = new EventSource('/api/elearning/course/stream/' + jobId);

        // Try quiz and path streams too
        let stream = null;
        try {
            stream = new EventSource(getStreamUrl(jobId));
        } catch (e) {
            stream = es;
        }

        function handleEvent(event) {
            try {
                const data = JSON.parse(event.data);

                if (data.status === 'done') {
                    bar.style.width = '100%';
                    stepsEl.innerHTML += '<div class="step-log" style="color: #10b981;">&#10003; Termine</div>';
                    if (onDone) onDone(data.result || {});
                    this.close();
                    resolve();
                } else if (data.status === 'error') {
                    stepsEl.innerHTML += '<div class="step-log" style="color: #ef4444;">&#10007; Erreur: ' + (data.error || '') + '</div>';
                    this.close();
                    resolve();
                } else if (data.step) {
                    progress = Math.min(progress + 15, 90);
                    bar.style.width = progress + '%';
                    stepsEl.innerHTML += '<div class="step-log">' + (data.detail || data.step) + '</div>';
                }
            } catch (e) { }
        }

        es.onmessage = handleEvent;
        es.onerror = () => { es.close(); resolve(); };
    });
}

function getStreamUrl(jobId) {
    // The stream endpoints all follow the same pattern
    return '/api/elearning/course/stream/' + jobId;
}
