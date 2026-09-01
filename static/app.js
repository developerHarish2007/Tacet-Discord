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
            runPipelineBtn.querySelector('span').textContent = 'Evaluating 5 Agents...';

            let perceptionScore = null;

            try {
                // 1. Perception Step
                const formData = new FormData();
                if (selectedFile) {
                    formData.append('file', selectedFile);
                }

                const perceptRes = await fetch('/perceive', { method: 'POST', body: formData });
                if (perceptRes.ok) {
                    const perceptData = await perceptRes.json();
                    perceptionScore = perceptData.anomaly_score;
                    
                    document.getElementById('percept-score').textContent = perceptData.anomaly_score.toFixed(4);
                    document.getElementById('percept-confidence').textContent = (perceptData.mean_confidence * 100).toFixed(1) + '%';
                    document.getElementById('percept-uncertainty').textContent = `±${perceptData.variance.toFixed(6)}`;
                    document.getElementById('perception-status').textContent = 'Evaluated';

                    if (perceptData.heatmap_path) {
                        const heatmapContainer = document.getElementById('heatmap-container');
                        const heatmapImg = document.getElementById('heatmap-img');
                        heatmapImg.src = perceptData.heatmap_path;
                        heatmapContainer.style.display = 'block';
                    }
                }

                // 2. Correlation Step
                const selectedMode = telemetrySelect ? telemetrySelect.value : 'normal';
                const correlRes = await fetch('/correlate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        telemetry_mode: selectedMode,
                        perception_score: perceptionScore
                    })
                });

                if (correlRes.ok) {
                    const correlData = await correlRes.json();
                    document.getElementById('correl-rul').textContent = `${correlData.predicted_rul_hours} hrs`;
                    document.getElementById('correl-shap').textContent = correlData.top_contributing_feature;
                    document.getElementById('correlation-status').textContent = correlData.sensor_anomaly ? 'Anomaly' : 'Normal';

                    if (!correlData.agrees_with_perception) {
                        document.getElementById('verifier-notes').textContent = correlData.disagreement_reason;
                    }
                }

                // 3. Memory Step (Recall)
                const recallFormData = new FormData();
                if (selectedFile) {
                    recallFormData.append('file', selectedFile);
                }

                const recallRes = await fetch('/recall', { method: 'POST', body: recallFormData });
                if (recallRes.ok) {
                    const recallData = await recallRes.json();
                    document.getElementById('memory-similarity').textContent = `${(recallData.similarity_score * 100).toFixed(1)}% Cosine`;
                    
                    if (recallData.match) {
                        const tag = recallData.match.seeded ? " [Seeded Demo Data]" : " [Senior Confirmed]";
                        document.getElementById('memory-status').textContent = `Match ID #${recallData.match.id}${tag}`;
                    } else {
                        document.getElementById('memory-status').textContent = "No Match (<30%)";
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
