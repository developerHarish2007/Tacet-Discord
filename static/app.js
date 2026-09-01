document.addEventListener('DOMContentLoaded', () => {
    const backendStatus = document.getElementById('backend-status');
    const factoryModeText = document.getElementById('factory-mode-text');
    const factoryIncidentCount = document.getElementById('factory-incident-count');

    // Navigation Tabs
    const tabJuniorAsk = document.getElementById('tab-junior-ask');
    const tabSeniorAdd = document.getElementById('tab-senior-add');
    const tabClassicAsk = document.getElementById('tab-classic-ask');
    
    const panelJuniorAsk = document.getElementById('panel-junior-ask');
    const panelSeniorAdd = document.getElementById('panel-senior-add');
    const panelClassic = document.getElementById('panel-classic');

    // Demo Presets
    const presetQuery1 = document.getElementById('preset-query-1');
    const presetQuery2 = document.getElementById('preset-query-2');
    const presetQuery3 = document.getElementById('preset-query-3');

    // Junior Ask Form Controls
    const askFileInput = document.getElementById('ask-file-input');
    const askDropZone = document.getElementById('ask-drop-zone');
    const askFileLabel = document.getElementById('ask-file-label');
    const askQuestionInput = document.getElementById('ask-question-input');
    const askJuniorBtn = document.getElementById('ask-junior-btn');

    // Junior Ask Output Controls
    const jaskWarningBanner = document.getElementById('jask-warning-banner');
    const jaskVerdictBox = document.getElementById('jask-verdict-box');
    const jaskTierBadge = document.getElementById('jask-tier-badge');
    const jaskTierTitle = document.getElementById('jask-tier-title');
    const jaskTierReasoning = document.getElementById('jask-tier-reasoning');
    const jaskAnswerBox = document.getElementById('jask-answer-box');
    const jaskAnswerText = document.getElementById('jask-answer-text');
    const jaskSourcesList = document.getElementById('jask-sources-list');
    const jaskRecordsBox = document.getElementById('jask-records-box');
    const jaskRecordsList = document.getElementById('jask-records-list');
    const jaskHallucinationBox = document.getElementById('jask-hallucination-box');
    const jaskClaimsList = document.getElementById('jask-claims-list');

    // Senior Add Record Form Controls
    const seniorAddFileInput = document.getElementById('senior-add-file-input');
    const seniorAddDropZone = document.getElementById('senior-add-drop-zone');
    const seniorAddFileLabel = document.getElementById('senior-add-file-label');
    const seniorAddDiag = document.getElementById('senior-add-diag');
    const seniorAddSteps = document.getElementById('senior-add-steps');
    const seniorAddVoice = document.getElementById('senior-add-voice');
    const seniorAddSubmitBtn = document.getElementById('senior-add-submit-btn');
    const seniorAddStatusMsg = document.getElementById('senior-add-status-msg');

    // Classic Controls
    const classicDropZone = document.getElementById('classic-drop-zone');
    const classicFileInput = document.getElementById('classic-file-input');
    const classicFileLabel = document.getElementById('classic-file-label');
    const classicTelemetry = document.getElementById('classic-telemetry');
    const classicRunBtn = document.getElementById('classic-run-btn');
    const classicTraceBox = document.getElementById('classic-trace-box');

    let askSelectedFile = null;
    let seniorSelectedFile = null;
    let classicSelectedFile = null;

    // Tab Switching
    function switchTab(activeTab, activePanel) {
        [tabJuniorAsk, tabSeniorAdd, tabClassicAsk].forEach(t => t && t.classList.remove('active'));
        [panelJuniorAsk, panelSeniorAdd, panelClassic].forEach(p => p && (p.style.display = 'none'));

        if (activeTab) activeTab.classList.add('active');
        if (activePanel) activePanel.style.display = 'block';
    }

    if (tabJuniorAsk) tabJuniorAsk.addEventListener('click', () => switchTab(tabJuniorAsk, panelJuniorAsk));
    if (tabSeniorAdd) tabSeniorAdd.addEventListener('click', () => switchTab(tabSeniorAdd, panelSeniorAdd));
    if (tabClassicAsk) tabClassicAsk.addEventListener('click', () => switchTab(tabClassicAsk, panelClassic));

    // Preset Clicks
    if (presetQuery1) {
        presetQuery1.addEventListener('click', () => {
            switchTab(tabJuniorAsk, panelJuniorAsk);
            askQuestionInput.value = "Tool wear reached limit, what fix is needed?";
            handleJuniorAskSubmit();
        });
    }
    if (presetQuery2) {
        presetQuery2.addEventListener('click', () => {
            switchTab(tabJuniorAsk, panelJuniorAsk);
            askQuestionInput.value = "Heat dissipation problem at 1350 RPM";
            handleJuniorAskSubmit();
        });
    }
    if (presetQuery3) {
        presetQuery3.addEventListener('click', () => {
            switchTab(tabJuniorAsk, panelJuniorAsk);
            askQuestionInput.value = "Unknown alien quantum flux error on conveyor 9";
            handleJuniorAskSubmit();
        });
    }

    // Drop Zone Setup
    function setupDropZone(dropZone, fileInput, label, onFileSelect) {
        if (!dropZone || !fileInput) return;
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                label.textContent = `Selected: ${file.name}`;
                onFileSelect(file);
            }
        });
    }

    setupDropZone(askDropZone, askFileInput, askFileLabel, f => askSelectedFile = f);
    setupDropZone(seniorAddDropZone, seniorAddFileInput, seniorAddFileLabel, f => seniorSelectedFile = f);
    setupDropZone(classicDropZone, classicFileInput, classicFileLabel, f => classicSelectedFile = f);

    // Health & Factory State Polling
    async function updateHealth() {
        try {
            const r = await fetch('/health');
            if (r.ok) {
                backendStatus.textContent = "Backend Online (1,000+ AI4I Dataset Records)";
                document.querySelector('.status-indicator').classList.add('online');
            }
        } catch (e) {
            backendStatus.textContent = "Backend Offline";
        }
        try {
            const fs = await fetch('/factory-state');
            if (fs.ok) {
                const data = await fs.json();
                factoryModeText.textContent = data.factory_mode_label || "ASSISTED MODE (1,000+ AI4I Records)";
                factoryIncidentCount.textContent = `${data.confirmed_factory_incidents || 1000} Records`;
            }
        } catch (e) {}
    }
    updateHealth();

    // -------------------------------------------------------------
    // SUBMIT JUNIOR ASK (Photo + Question)
    // -------------------------------------------------------------
    async function handleJuniorAskSubmit() {
        const question = askQuestionInput.value.trim();
        if (!question) {
            alert("Please enter a question or issue description.");
            return;
        }

        askJuniorBtn.disabled = true;
        askJuniorBtn.innerHTML = "<span>⌛ Processing Grounded Query & Verification Gate...</span>";

        const formData = new FormData();
        formData.append("question", question);
        if (askSelectedFile) {
            formData.append("file", askSelectedFile);
        }

        try {
            const response = await fetch('/junior/ask', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const data = await response.json();
            renderJuniorAskResult(data);
        } catch (err) {
            alert(`Error querying copilot: ${err.message}`);
        } finally {
            askJuniorBtn.disabled = false;
            askJuniorBtn.innerHTML = "<span>⚡ Submit Grounded Query (/junior/ask)</span>";
        }
    }

    if (askJuniorBtn) {
        askJuniorBtn.addEventListener('click', handleJuniorAskSubmit);
    }

    function renderJuniorAskResult(data) {
        const tier = data.tier;
        const warning = data.warning_banner;

        // Render Tier Badge & Warning Banner
        if (warning) {
            jaskWarningBanner.style.display = 'block';
            jaskWarningBanner.textContent = warning;
        } else {
            jaskWarningBanner.style.display = 'none';
        }

        jaskVerdictBox.style.display = 'block';
        jaskTierBadge.textContent = data.tier_label;
        jaskTierTitle.textContent = `Verdict: ${data.tier_label}`;
        jaskTierReasoning.textContent = data.verifier_reasoning;

        if (tier === 1) {
            jaskTierBadge.style.background = 'rgba(74, 222, 128, 0.2)';
            jaskTierBadge.style.color = 'var(--accent-green)';
        } else if (tier === 2) {
            jaskTierBadge.style.background = 'rgba(251, 191, 36, 0.2)';
            jaskTierBadge.style.color = 'var(--accent-amber)';
        } else {
            jaskTierBadge.style.background = 'rgba(248, 113, 113, 0.2)';
            jaskTierBadge.style.color = 'var(--accent-red)';
        }

        // Grounded Verified Answer
        jaskAnswerBox.style.display = 'block';
        jaskAnswerText.textContent = data.answer;

        // Sources List
        jaskSourcesList.innerHTML = '';
        (data.grounded_sources || []).forEach(src => {
            const li = document.createElement('li');
            li.textContent = src;
            jaskSourcesList.appendChild(li);
        });

        // Retrieved Evidence Cards (1-3)
        jaskRecordsBox.style.display = 'block';
        jaskRecordsList.innerHTML = '';

        const records = data.retrieved_records || [];
        if (records.length === 0) {
            jaskRecordsList.innerHTML = '<p class="subtitle">No matching evidence records found in incident database.</p>';
        } else {
            records.forEach(rec => {
                const card = document.createElement('div');
                card.className = 'record-card';
                const simPct = (rec.similarity_score * 100).toFixed(0);
                card.innerHTML = `
                    <div class="record-card-head">
                        <strong>Record #${rec.id} — ${rec.confirmed_diagnosis}</strong>
                        <span class="provenance-tag">Source: ${rec.provenance || 'seeded_dataset'} (Match ${simPct}%)</span>
                    </div>
                    <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:0.3rem;">
                        <strong>Fix Steps:</strong> ${rec.fix_steps.replace(/\n/g, ' ')}
                    </p>
                `;
                jaskRecordsList.appendChild(card);
            });
        }

        // Explicit Hallucination Check Gate Trace
        jaskHallucinationBox.style.display = 'block';
        jaskClaimsList.innerHTML = '';
        const htrace = (data.reasoning_trace && data.reasoning_trace.hallucination_check) || {};
        
        (htrace.passed_claims || []).forEach(c => {
            const d = document.createElement('div');
            d.className = 'claim-passed';
            d.textContent = `✅ ${c}`;
            jaskClaimsList.appendChild(d);
        });

        (htrace.failed_claims || []).forEach(c => {
            const d = document.createElement('div');
            d.className = 'claim-failed';
            d.textContent = `🛑 ${c}`;
            jaskClaimsList.appendChild(d);
        });

        // 5-Agent Live Pipeline Trace & ResNet-18 Heatmap Accordion Drawer
        const wrapper = document.getElementById('jask-pipeline-trace-wrapper');
        const toggleBtn = document.getElementById('toggle-pipeline-trace-btn');
        const traceContent = document.getElementById('pipeline-trace-content');
        const icon = document.getElementById('trace-accordion-icon');
        const heatmapContainer = document.getElementById('jask-heatmap-container');
        const heatmapImg = document.getElementById('jask-heatmap-img');

        if (wrapper) wrapper.style.display = 'block';

        if (toggleBtn && !toggleBtn.dataset.bound) {
            toggleBtn.dataset.bound = 'true';
            toggleBtn.addEventListener('click', () => {
                const isHidden = traceContent.style.display === 'none';
                traceContent.style.display = isHidden ? 'flex' : 'none';
                if (icon) icon.textContent = isHidden ? '▲' : '▼';
            });
        }

        // Render ResNet-18 Anomaly Heatmap if image was uploaded
        if (data.heatmap_path && heatmapContainer && heatmapImg) {
            heatmapContainer.style.display = 'block';
            heatmapImg.src = data.heatmap_path;
        } else if (heatmapContainer) {
            heatmapContainer.style.display = 'none';
        }

        // Populate Agent visual cards
        const rtrace = data.reasoning_trace || {};
        const ptrace = rtrace.perception || {};
        const mtrace = rtrace.memory || {};

        const tracePerceptScore = document.getElementById('trace-percept-score');
        const tracePerceptConf = document.getElementById('trace-percept-conf');
        const tracePerceptOcr = document.getElementById('trace-percept-ocr');
        const traceMemoryCount = document.getElementById('trace-memory-count');
        const traceMemorySim = document.getElementById('trace-memory-sim');
        const traceVerifierTier = document.getElementById('trace-verifier-tier');
        const traceVerifierHallucination = document.getElementById('trace-verifier-hallucination');
        const crossModalBox = document.getElementById('jask-cross-modal-box');
        const crossModalText = document.getElementById('jask-cross-modal-text');
        const rawJsonPre = document.getElementById('jask-raw-json-trace');

        if (tracePerceptScore) tracePerceptScore.textContent = ptrace.score !== null && ptrace.score !== undefined ? ptrace.score.toFixed(4) : 'N/A';
        if (tracePerceptConf) tracePerceptConf.textContent = ptrace.confidence !== null && ptrace.confidence !== undefined ? ptrace.confidence.toFixed(4) : 'N/A';
        if (tracePerceptOcr) tracePerceptOcr.textContent = ptrace.extracted_ocr || 'None detected';
        if (traceMemoryCount) traceMemoryCount.textContent = mtrace.retrieved_count || 0;
        if (traceMemorySim) traceMemorySim.textContent = mtrace.top_similarity ? `${(mtrace.top_similarity * 100).toFixed(0)}%` : '0%';
        if (traceVerifierTier) traceVerifierTier.textContent = data.tier_label;
        if (traceVerifierHallucination) traceVerifierHallucination.textContent = rtrace.hallucination_check && rtrace.hallucination_check.has_hallucination ? '🛑 Flagged' : '✅ Passed';

        if (rtrace.cross_modal_note && crossModalBox && crossModalText) {
            crossModalBox.style.display = 'block';
            crossModalText.textContent = rtrace.cross_modal_note;
        } else if (crossModalBox) {
            crossModalBox.style.display = 'none';
        }

        if (rawJsonPre) {
            rawJsonPre.textContent = JSON.stringify(rtrace, null, 2);
        }
    }

    // -------------------------------------------------------------
    // SUBMIT SENIOR ADD RECORD (/records/add)
    // -------------------------------------------------------------
    // Microphone recording state for Senior Add
    const seniorAddAudioFile = document.getElementById('senior-add-audio-file');
    const seniorVoiceRecBtn = document.getElementById('senior-voice-rec-btn');
    const seniorVoiceStatus = document.getElementById('senior-voice-status');

    let mediaRecorder = null;
    let audioChunks = [];
    let recordedAudioBlob = null;

    if (seniorVoiceRecBtn) {
        seniorVoiceRecBtn.addEventListener('click', async () => {
            if (!mediaRecorder || mediaRecorder.state === 'inactive') {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];

                    mediaRecorder.ondataavailable = (event) => {
                        if (event.data.size > 0) audioChunks.push(event.data);
                    };

                    mediaRecorder.onstop = () => {
                        recordedAudioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        if (seniorVoiceStatus) {
                            seniorVoiceStatus.textContent = "🎙️ Voice note recorded successfully! (Ready for submission)";
                            seniorVoiceStatus.style.color = "#3fb950";
                        }
                    };

                    mediaRecorder.start();
                    seniorVoiceRecBtn.textContent = "🛑 Stop Recording";
                    seniorVoiceRecBtn.classList.remove('btn-primary');
                    seniorVoiceRecBtn.classList.add('btn-danger');
                    if (seniorVoiceStatus) {
                        seniorVoiceStatus.textContent = "🔴 Recording voice note... Speak clearly into your mic.";
                        seniorVoiceStatus.style.color = "#f85149";
                    }
                } catch (err) {
                    alert("Microphone access failed: " + err.message);
                }
            } else if (mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                seniorVoiceRecBtn.textContent = "🎙️ Record Mic";
                seniorVoiceRecBtn.classList.remove('btn-danger');
                seniorVoiceRecBtn.classList.add('btn-primary');
            }
        });
    }

    async function handleSeniorAddSubmit() {
        const diag = seniorAddDiag.value.trim();
        const steps = seniorAddSteps.value.trim();
        const voice = seniorAddVoice.value.trim();
        const audioFileInput = seniorAddAudioFile && seniorAddAudioFile.files.length > 0 ? seniorAddAudioFile.files[0] : null;

        if (!diag && !steps && !audioFileInput && !recordedAudioBlob) {
            alert("Please provide diagnosis & fix steps, or record/upload a voice note.");
            return;
        }

        seniorAddSubmitBtn.disabled = true;
        seniorAddSubmitBtn.innerHTML = "<span>⌛ Adding Record & Processing Voice LM / Gemma 4...</span>";

        const formData = new FormData();
        formData.append("confirmed_diagnosis", diag || "");
        formData.append("fix_steps", steps || "");
        formData.append("voice_note_path", voice || "");
        if (seniorSelectedFile) formData.append("file", seniorSelectedFile);

        if (audioFileInput) {
            formData.append("voice_file", audioFileInput);
        } else if (recordedAudioBlob) {
            formData.append("voice_file", recordedAudioBlob, "mic_recording.wav");
        }

        try {
            const response = await fetch('/records/add', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const data = await response.json();
            seniorAddStatusMsg.style.display = 'block';
            
            let msgText = `✅ Record #${data.id} added to trusted memory store (provenance: ${data.provenance || 'senior_manual_entry'})!`;
            if (data.raw_transcript) {
                msgText += ` Transcribed voice note: "${data.raw_transcript.substring(0, 80)}..."`;
            }
            msgText += ` Instantly searchable by junior technicians.`;
            
            seniorAddStatusMsg.textContent = msgText;
            
            seniorAddDiag.value = '';
            seniorAddSteps.value = '';
            seniorAddVoice.value = '';
            if (seniorAddAudioFile) seniorAddAudioFile.value = '';
            recordedAudioBlob = null;
            seniorSelectedFile = null;
            if (seniorAddFileLabel) seniorAddFileLabel.textContent = "Click or Drag & Drop Image File";
            if (seniorVoiceStatus) {
                seniorVoiceStatus.textContent = "Upload an audio file (.wav, .mp3, .m4a) or speak directly into your mic. Voice notes are automatically transcribed & cleaned by Gemma 4 into structured records.";
                seniorVoiceStatus.style.color = "#8b949e";
            }

            updateHealth();
        } catch (err) {
            alert(`Error adding record: ${err.message}`);
        } finally {
            seniorAddSubmitBtn.disabled = false;
            seniorAddSubmitBtn.innerHTML = "<span>💾 Save to Trusted Memory Store (/records/add)</span>";
        }
    }

    if (seniorAddSubmitBtn) {
        seniorAddSubmitBtn.addEventListener('click', handleSeniorAddSubmit);
    }

    // -------------------------------------------------------------
    // SUBMIT CLASSIC PIPELINE TRACE (/ask)
    // -------------------------------------------------------------
    if (classicRunBtn) {
        classicRunBtn.addEventListener('click', async () => {
            classicRunBtn.disabled = true;
            classicRunBtn.textContent = "⌛ Running 5-Agent Pipeline...";
            classicTraceBox.innerHTML = "<p class='trace-subtitle'>Executing Perception, Correlation, Memory & Verifier agents...</p>";

            const formData = new FormData();
            formData.append("telemetry_mode", classicTelemetry ? classicTelemetry.value : "normal");
            if (classicSelectedFile) formData.append("file", classicSelectedFile);

            try {
                const resp = await fetch('/ask', { method: 'POST', body: formData });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                
                const trace = data.reasoning_trace || {};
                const percept = trace.perception || {};
                const correl = trace.correlation || {};
                const memory = trace.memory || {};
                const verifier = trace.verifier || {};

                classicTraceBox.innerHTML = `
                    <div class="result-box">
                        <div class="tier-tag">${data.tier_label || 'Verdict'}</div>
                        <h3>${data.confirmed_diagnosis || data.tentative_diagnosis || 'Inspection Result'}</h3>
                        <p><strong>Verifier Reasoning:</strong> ${data.verifier_reasoning || ''}</p>
                    </div>
                    <div class="trace-panel">
                        <div class="trace-step"><strong>👁️ Perception:</strong> ${percept.summary || 'Score computed'}</div>
                        <div class="trace-step"><strong>📈 Correlation:</strong> ${correl.summary || 'RUL computed'}</div>
                        <div class="trace-step"><strong>🧠 Memory:</strong> ${memory.summary || 'Vector match evaluated'}</div>
                        <div class="trace-step verifier-step"><strong>⚖️ Verifier:</strong> Tier ${verifier.tier || data.tier} - ${verifier.reasoning || ''}</div>
                    </div>
                `;
            } catch (err) {
                classicTraceBox.innerHTML = `<p class="warning-text">Error executing pipeline: ${err.message}</p>`;
            } finally {
                classicRunBtn.disabled = false;
                classicRunBtn.textContent = "⚡ Run Pipeline (/ask)";
            }
        });
    }
});
