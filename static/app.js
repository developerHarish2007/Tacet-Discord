document.addEventListener('DOMContentLoaded', () => {
    const backendStatus = document.getElementById('backend-status');
    const runPipelineBtn = document.getElementById('run-pipeline-btn');
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const telemetrySelect = document.getElementById('telemetry-select');
    let selectedFile = null;

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedFile = e.target.files[0];
                dropZone.querySelector('p').textContent = `Selected: ${selectedFile.name}`;
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
                dropZone.querySelector('p').textContent = `Selected: ${selectedFile.name}`;
            }
        });
    }

    async function checkHealth() {
        try {
            const res = await fetch('/health');
            if (res.ok) {
                const data = await res.json();
                backendStatus.textContent = `Online: ${data.system}`;
                backendStatus.previousElementSibling.classList.add('online');
            } else {
                backendStatus.textContent = 'Backend Offline';
            }
        } catch (e) {
            backendStatus.textContent = 'Backend Offline';
        }
    }

    checkHealth();

    if (runPipelineBtn) {
        runPipelineBtn.addEventListener('click', async () => {
            runPipelineBtn.disabled = true;
            runPipelineBtn.querySelector('span').textContent = 'Evaluating 5-Agent Cross-Verification...';

            try {
                const selectedMode = telemetrySelect ? telemetrySelect.value : 'normal';
                const formData = new FormData();
                if (selectedFile) {
                    formData.append('file', selectedFile);
                }
                formData.append('telemetry_mode', selectedMode);

                const verifyRes = await fetch('/verify', { method: 'POST', body: formData });
                if (verifyRes.ok) {
                    const verifyData = await verifyRes.json();
                    const outputs = verifyData.agent_outputs || {};
                    const percept = outputs.perception || {};
                    const correl = outputs.correlation || {};
                    const memory = outputs.memory || {};

                    // 1. Update Perception UI Panel
                    if (percept.anomaly_score !== undefined) {
                        document.getElementById('percept-score').textContent = percept.anomaly_score.toFixed(4);
                        document.getElementById('percept-confidence').textContent = (percept.mean_confidence * 100).toFixed(1) + '%';
                        document.getElementById('percept-uncertainty').textContent = `±${percept.variance.toFixed(6)}`;
                        document.getElementById('perception-status').textContent = 'Evaluated';

                        if (percept.heatmap_path) {
                            const heatmapContainer = document.getElementById('heatmap-container');
                            const heatmapImg = document.getElementById('heatmap-img');
                            heatmapImg.src = percept.heatmap_path;
                            heatmapContainer.style.display = 'block';
                        }
                    }

                    // 2. Update Correlation UI Panel
                    if (correl.predicted_rul_hours !== undefined) {
                        document.getElementById('correl-rul').textContent = `${correl.predicted_rul_hours} hrs`;
                        document.getElementById('correl-shap').textContent = correl.top_contributing_feature || '--';
                        document.getElementById('correlation-status').textContent = correl.sensor_anomaly ? 'Anomaly' : 'Normal';
                    }

                    // 3. Update Memory UI Panel
                    if (memory.similarity_score !== undefined) {
                        document.getElementById('memory-similarity').textContent = `${(memory.similarity_score * 100).toFixed(1)}% Cosine`;
                        if (memory.match) {
                            const tag = memory.match.seeded ? " [Seeded Demo Data]" : " [Senior Confirmed]";
                            document.getElementById('memory-status').textContent = `Match ID #${memory.match.id}${tag}`;
                        } else {
                            document.getElementById('memory-status').textContent = "No Match (<30%)";
                        }
                    }

                    // 4. Update Skeptical Verifier Ruling Card
                    const verdictBanner = document.getElementById('verdict-banner');
                    const verdictTier = document.getElementById('verdict-tier');
                    const verdictTitle = document.getElementById('verdict-title');
                    const verdictDesc = document.getElementById('verdict-desc');
                    const verifierNotes = document.getElementById('verifier-notes');
                    const seniorNoteBox = document.getElementById('senior-note-box');

                    verdictBanner.className = `verdict-banner tier-${verifyData.tier}`;
                    verdictTier.textContent = `TIER ${verifyData.tier}`;
                    verdictTitle.textContent = verifyData.tier_label;
                    verdictDesc.textContent = verifyData.reasoning;
                    
                    let auditText = `Auditable Values:\n` +
                        `• Visual Confidence: ${(verifyData.auditable_values.mean_confidence * 100).toFixed(1)}%\n` +
                        `• Dropout Variance: ±${verifyData.auditable_values.variance.toFixed(6)}\n` +
                        `• Sensor Agreement: ${verifyData.auditable_values.agrees_with_perception}\n` +
                        `• Memory Similarity: ${(verifyData.auditable_values.similarity_score * 100).toFixed(1)}%\n`;

                    if (verifyData.stage_b_tiebreaker && verifyData.stage_b_tiebreaker.negotiation_needed) {
                        auditText += `\n${verifyData.stage_b_tiebreaker.tiebreaker_summary}`;
                    }

                    verifierNotes.textContent = auditText;

                    // Display senior voice note / diagnosis if available
                    if (memory.match && (memory.match.confirmed_diagnosis || memory.match.voice_note_path)) {
                        document.getElementById('senior-audio-text').textContent = 
                            `"${memory.match.confirmed_diagnosis}"\nSteps: ${memory.match.fix_steps}`;
                        seniorNoteBox.style.display = 'block';
                    } else {
                        seniorNoteBox.style.display = 'none';
                    }
                }
            } catch (err) {
                console.error("Pipeline trigger failed:", err);
            } finally {
                runPipelineBtn.disabled = false;
                runPipelineBtn.querySelector('span').textContent = '⚡ Run 5-Agent Cross-Verification';
            }
        });
    }
});
