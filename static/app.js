document.addEventListener('DOMContentLoaded', () => {
    const backendStatus = document.getElementById('backend-status');
    const factoryStateBadge = document.getElementById('factory-state-badge');
    const factoryModeText = document.getElementById('factory-mode-text');
    const factoryIncidentCount = document.getElementById('factory-incident-count');

    const runPipelineBtn = document.getElementById('run-pipeline-btn');
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const telemetrySelect = document.getElementById('telemetry-select');

    // Preset Buttons
    const presetTier1 = document.getElementById('preset-tier1');
    const presetTier2 = document.getElementById('preset-tier2');
    const presetTier3 = document.getElementById('preset-tier3');
    const allPresets = [presetTier1, presetTier2, presetTier3];

    // Tabs
    const tabJunior = document.getElementById('tab-junior');
    const tabSenior = document.getElementById('tab-senior');
    const juniorPanel = document.getElementById('junior-view-panel');
    const seniorPanel = document.getElementById('senior-view-panel');

    // Senior Controls
    const seniorConfirmBtn = document.getElementById('senior-confirm-btn');
    const seniorCorrectBtn = document.getElementById('senior-correct-btn');
    const seniorSaveBtn = document.getElementById('senior-save-btn');
    const seniorCorrectionForm = document.getElementById('senior-correction-form');
    const seniorStatusMsg = document.getElementById('senior-status-msg');

    // Investigation Controls
    const investigationCard = document.getElementById('investigation-card');
    const sufficiencyBadge = document.getElementById('sufficiency-badge');
    const hypothesesList = document.getElementById('hypotheses-list');
    const nextEvidenceLabel = document.getElementById('next-evidence-label');
    const nextEvidenceReason = document.getElementById('next-evidence-reason');
    const acquireEvidenceBtn = document.getElementById('acquire-evidence-btn');
    const investigationTransitionBox = document.getElementById('investigation-transition-box');
    const transitionSummaryText = document.getElementById('transition-summary-text');

    let selectedFile = null;
    let currentImagePath = "data/mvtec/bottle/test/broken_large/000.png";
    let lastPipelineResult = null;

    function setActivePreset(activeBtn) {
        allPresets.forEach(btn => {
            if (btn) btn.classList.remove('active');
        });
        if (activeBtn) activeBtn.classList.add('active');
    }

    // Tab Switching
    if (tabJunior && tabSenior) {
        tabJunior.addEventListener('click', () => {
            tabJunior.classList.add('active');
            tabSenior.classList.remove('active');
            juniorPanel.style.display = 'block';
            seniorPanel.style.display = 'none';
        });

        tabSenior.addEventListener('click', () => {
            tabSenior.classList.add('active');
            tabJunior.classList.remove('active');
            seniorPanel.style.display = 'block';
            juniorPanel.style.display = 'none';
            populateSeniorPanel();
        });
    }

    // File Drop Zone
    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedFile = e.target.files[0];
                setActivePreset(null);
                document.getElementById('file-label').textContent = `Uploaded Custom File: ${selectedFile.name}`;
            }
        });
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'var(--accent-blue)';
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.style.borderColor = 'var(--border-color)';
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            if (e.dataTransfer.files.length > 0) {
                selectedFile = e.dataTransfer.files[0];
                fileInput.files = e.dataTransfer.files;
                setActivePreset(null);
                document.getElementById('file-label').textContent = `Uploaded Custom File: ${selectedFile.name}`;
            }
        });
    }

    // Check Backend Health & Factory Onboarding State
    async function checkHealthAndFactoryState() {
        try {
            const res = await fetch('/health');
            if (res.ok) {
                const data = await res.json();
                backendStatus.textContent = `Online: ${data.system}`;
                backendStatus.previousElementSibling.classList.add('online');
            } else {
                backendStatus.textContent = 'Backend Offline';
            }

            const stateRes = await fetch('/factory-state');
            if (stateRes.ok) {
                const stateData = await stateRes.json();
                factoryModeText.textContent = stateData.factory_mode_label;
                factoryIncidentCount.textContent = `${stateData.confirmed_factory_incidents} Confirmed Precedents`;
            }
        } catch (e) {
            backendStatus.textContent = 'Backend Offline';
        }
    }

    checkHealthAndFactoryState();

    // Preset Handlers
    if (presetTier1) {
        presetTier1.addEventListener('click', () => {
            selectedFile = null;
            currentImagePath = "data/mvtec/bottle/test/broken_large/000.png";
            setActivePreset(presetTier1);
            document.getElementById('file-label').textContent = "Scenario 1: Defect + Spiking Telemetry";
            telemetrySelect.value = "degraded";
            runPipeline();
        });
    }

    if (presetTier2) {
        presetTier2.addEventListener('click', () => {
            selectedFile = null;
            currentImagePath = "data/mvtec/bottle/test/broken_large/001.png";
            setActivePreset(presetTier2);
            document.getElementById('file-label').textContent = "Scenario 2: Visual Scratch vs Flat Baseline";
            telemetrySelect.value = "normal";
            runPipeline();
        });
    }

    if (presetTier3) {
        presetTier3.addEventListener('click', () => {
            selectedFile = null;
            currentImagePath = "data/mvtec/bottle/test/good/001.png";
            setActivePreset(presetTier3);
            document.getElementById('file-label').textContent = "Scenario 3: Cold Start / Low Confidence";
            telemetrySelect.value = "normal";
            runPipeline();
        });
    }

    if (runPipelineBtn) {
        runPipelineBtn.addEventListener('click', () => runPipeline());
    }

    // Main Pipeline Execution Call (/ask)
    async function runPipeline() {
        runPipelineBtn.disabled = true;
        runPipelineBtn.querySelector('span').textContent = 'Executing Coordinator Pipeline (/ask)...';

        try {
            const selectedMode = telemetrySelect ? telemetrySelect.value : 'normal';
            const formData = new FormData();
            
            if (selectedFile) {
                formData.append('file', selectedFile);
            } else {
                formData.append('image_path', currentImagePath);
            }
            formData.append('telemetry_mode', selectedMode);

            const askRes = await fetch('/ask', { method: 'POST', body: formData });
            if (askRes.ok) {
                const data = await askRes.json();
                console.log("[NETWORK RESP] POST /ask returned:", data);
                
                if (data.image_path) {
                    currentImagePath = data.image_path;
                }

                lastPipelineResult = data;
                renderJuniorView(data);
                populateSeniorPanel();
            }
        } catch (err) {
            console.error("Pipeline request failed:", err);
        } finally {
            runPipelineBtn.disabled = false;
            runPipelineBtn.querySelector('span').textContent = '⚡ Run 5-Agent Pipeline (/ask)';
        }
    }

    // Render Junior View, High-Impact Trace, and Active Evidence Gathering Card
    function renderJuniorView(data) {
        const trace = data.reasoning_trace || {};
        const pTrace = trace.perception || {};
        const cTrace = trace.correlation || {};
        const mTrace = trace.memory || {};
        const vTrace = trace.verifier || {};
        const traceCard = document.querySelector('.trace-card');
        const investigation = data.investigation || {};

        // Check if conflict occurred
        const isConflict = cTrace.agrees === false;
        if (traceCard) {
            if (isConflict) {
                traceCard.classList.add('conflict-active');
            } else {
                traceCard.classList.remove('conflict-active');
            }
        }

        // 1. Update Prominent Live Reasoning Trace Panel
        document.getElementById('trace-percept-score').textContent = `Score: ${(pTrace.score || 0).toFixed(4)}`;
        document.getElementById('trace-percept-desc').textContent = pTrace.summary || '--';

        const correlHead = document.getElementById('trace-correl-rul');
        if (cTrace.agrees === false) {
            correlHead.innerHTML = `${cTrace.predicted_rul || 0} hrs <span class="conflict-badge">DISAGREES ❌</span>`;
        } else {
            correlHead.textContent = `${cTrace.predicted_rul || 0} hrs`;
        }
        document.getElementById('trace-correl-desc').textContent = cTrace.summary || '--';

        document.getElementById('trace-memory-sim').textContent = `${((mTrace.similarity || 0)*100).toFixed(1)}%`;
        document.getElementById('trace-memory-desc').textContent = mTrace.summary || '--';

        const verifierHead = document.getElementById('trace-verifier-tier');
        if (data.tier === 2 && isConflict) {
            verifierHead.innerHTML = `TIER ${data.tier} <span class="conflict-badge">DOWNGRADE ⚡</span>`;
        } else {
            verifierHead.textContent = `TIER ${data.tier}`;
        }
        document.getElementById('trace-verifier-desc').textContent = vTrace.reasoning || data.verifier_reasoning;

        // 2. Render Active Evidence Gathering Engine Card
        if (investigationCard) {
            investigationCard.style.display = 'block';
            investigationTransitionBox.style.display = 'none';

            const sufficiency = investigation.evidence_sufficiency || "LOW";
            sufficiencyBadge.textContent = `Sufficiency: ${sufficiency}`;
            if (sufficiency === "HIGH") {
                sufficiencyBadge.className = "sufficiency-badge high";
            } else {
                sufficiencyBadge.className = "sufficiency-badge";
            }

            // Hypotheses List
            const hypotheses = investigation.hypotheses || [];
            hypothesesList.innerHTML = hypotheses.map(h => `
                <div class="hypothesis-item">
                    <span>${h.cause}</span>
                    <div class="hypo-bar-bg">
                        <div class="hypo-bar-fill" style="width: ${(h.probability*100).toFixed(0)}%"></div>
                    </div>
                    <strong>${(h.probability*100).toFixed(0)}%</strong>
                </div>
            `).join('');

            // Next-Best Evidence Recommendation
            const topRec = investigation.top_recommendation || {};
            nextEvidenceLabel.textContent = topRec.label || "10-Second Vibration Sample (Bearing Accelerometer)";
            nextEvidenceReason.textContent = `Expected Uncertainty Reduction: ${(topRec.expected_uncertainty_reduction || 0.45)*100}% | Relevance: ${(topRec.relevance || 0.9)*100}%`;
        }

        // 3. Verdict Banner
        const verdictBanner = document.getElementById('verdict-banner');
        const verdictTier = document.getElementById('verdict-tier');
        const verdictTitle = document.getElementById('verdict-title');
        const verdictDesc = document.getElementById('verdict-desc');

        verdictBanner.className = `verdict-banner tier-${data.tier}`;
        verdictTier.textContent = `TIER ${data.tier}`;
        verdictTitle.textContent = data.tier_label;
        verdictDesc.textContent = data.verifier_reasoning;

        // 4. Hide all tier container views first
        document.getElementById('tier1-container').style.display = 'none';
        document.getElementById('tier2-container').style.display = 'none';
        document.getElementById('tier3-container').style.display = 'none';

        // 5. Render specified Tier container view
        if (data.tier === 1) {
            document.getElementById('tier1-container').style.display = 'block';
            document.getElementById('t1-diagnosis').textContent = data.confirmed_diagnosis || '--';
            document.getElementById('t1-fix-steps').textContent = data.fix_steps || '--';

            if (data.voice_note_path) {
                document.getElementById('t1-voice-text').textContent = `Audio Note: ${data.voice_note_path}`;
                document.getElementById('t1-audio-box').style.display = 'block';
            } else {
                document.getElementById('t1-audio-box').style.display = 'none';
            }
        } else if (data.tier === 2) {
            document.getElementById('tier2-container').style.display = 'block';
            document.getElementById('t2-tentative').textContent = data.tentative_diagnosis || 'TENTATIVE DIAGNOSIS';
            document.getElementById('t2-who-to-ask').textContent = `Recommended Action: ${data.who_to_ask}`;
        } else if (data.tier === 3) {
            document.getElementById('tier3-container').style.display = 'block';
            document.getElementById('t3-redirect-msg').textContent = data.redirect_message || "Not confident enough — escalate to a senior technician";
        }

        // Heatmap Preview
        if (data.heatmap_path) {
            const heatmapContainer = document.getElementById('heatmap-container');
            const heatmapImg = document.getElementById('heatmap-img');
            heatmapImg.src = data.heatmap_path;
            heatmapContainer.style.display = 'block';
        }
    }

    // Active Evidence Acquisition Handler (POST /acquire)
    if (acquireEvidenceBtn) {
        acquireEvidenceBtn.addEventListener('click', async () => {
            acquireEvidenceBtn.disabled = true;
            acquireEvidenceBtn.querySelector('span').textContent = 'Acquiring Target Evidence & Re-Evaluating...';

            try {
                const res = await fetch('/acquire', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image_path: currentImagePath,
                        evidence_id: 'vibration_sample_10s'
                    })
                });

                if (res.ok) {
                    const data = await res.json();
                    console.log("[NETWORK RESP] POST /acquire returned:", data);

                    // Render Investigation Transition
                    investigationTransitionBox.style.display = 'block';
                    transitionSummaryText.textContent = data.transition_summary;

                    sufficiencyBadge.textContent = "Sufficiency: HIGH";
                    sufficiencyBadge.className = "sufficiency-badge high";

                    // Re-run full ask pipeline with degraded telemetry to show upgraded tier live
                    telemetrySelect.value = "degraded";
                    runPipeline();
                }
            } catch (err) {
                console.error("Acquire evidence failed:", err);
            } finally {
                acquireEvidenceBtn.disabled = false;
                acquireEvidenceBtn.querySelector('span').textContent = '⚡ ACQUIRE NEXT BEST EVIDENCE (Execute Investigation Loop)';
            }
        });
    }

    // Populate Senior Handoff Panel
    function populateSeniorPanel() {
        if (!lastPipelineResult) return;
        
        const data = lastPipelineResult;
        const draftHeader = document.getElementById('senior-draft-diag');
        const draftTier = document.getElementById('senior-draft-tier');

        let draftText = "No Anomaly Detected";
        if (data.tier === 1) {
            draftText = data.confirmed_diagnosis;
        } else if (data.tier === 2) {
            draftText = data.tentative_diagnosis;
        } else {
            draftText = "Unconfirmed Low-Confidence Reading";
        }

        draftHeader.textContent = draftText;
        draftTier.textContent = `Tier ${data.tier}`;
        seniorCorrectionForm.style.display = 'none';
        seniorSaveBtn.style.display = 'none';
        seniorStatusMsg.style.display = 'none';
    }

    // Senior Confirm Handler
    if (seniorConfirmBtn) {
        seniorConfirmBtn.addEventListener('click', async () => {
            seniorCorrectionForm.style.display = 'none';
            seniorSaveBtn.style.display = 'block';
            
            let diag = "Confirmed Defect Pattern";
            let steps = "Standard resolution steps.";

            if (lastPipelineResult) {
                diag = lastPipelineResult.confirmed_diagnosis || lastPipelineResult.tentative_diagnosis || "Confirmed Defect Pattern";
                steps = lastPipelineResult.fix_steps || "1. Perform visual inspection\n2. Clean conveyor guide.";
            }

            document.getElementById('senior-input-diag').value = diag;
            document.getElementById('senior-input-steps').value = steps;
            
            saveSeniorIncident(diag, steps);
        });
    }

    // Senior Correct Handler
    if (seniorCorrectBtn) {
        seniorCorrectBtn.addEventListener('click', () => {
            seniorCorrectionForm.style.display = 'block';
            seniorSaveBtn.style.display = 'block';
            
            document.getElementById('senior-input-diag').value = "";
            document.getElementById('senior-input-steps').value = "";
        });
    }

    if (seniorSaveBtn) {
        seniorSaveBtn.addEventListener('click', () => {
            const diag = document.getElementById('senior-input-diag').value || "Senior Corrected Defect Pattern";
            const steps = document.getElementById('senior-input-steps').value || "1. Manual resolution steps.";
            saveSeniorIncident(diag, steps);
        });
    }

    // Save Senior Incident to Incident Memory via /remember
    async function saveSeniorIncident(confirmedDiag, fixSteps) {
        const noteText = document.getElementById('senior-input-note').value || "";
        
        console.log(`[NETWORK REQ] POST /remember with image_path: ${currentImagePath}`);

        try {
            const res = await fetch('/remember', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image_path: currentImagePath,
                    confirmed_diagnosis: confirmedDiag,
                    fix_steps: fixSteps,
                    voice_note_path: noteText ? `/audio/${noteText.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.mp3` : null,
                    confidence_at_capture: 0.98
                })
            });

            if (res.ok) {
                const data = await res.json();
                console.log("[NETWORK RESP] POST /remember returned:", data);
                seniorStatusMsg.textContent = `✅ Saved to incident memory! (Incident Record ID #${data.id}, seeded: false)`;
                seniorStatusMsg.style.display = 'block';
                seniorSaveBtn.style.display = 'none';

                // Refresh factory state badge
                checkHealthAndFactoryState();
            }
        } catch (err) {
            console.error("Save senior incident failed:", err);
        }
    }
});
