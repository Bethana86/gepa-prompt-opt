// app.js
/* Frontend interactions for GEPA Prompt Optimizer Dashboard */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const btnOptimize = document.getElementById("btn-optimize");
    const inputPopSize = document.getElementById("pop-size");
    const inputGenerations = document.getElementById("generations");
    const consoleLogs = document.getElementById("console-logs");
    const consolePulse = document.getElementById("console-pulse");
    const populationList = document.getElementById("population-list");
    const genCounter = document.getElementById("gen-counter");
    
    const optimizedSelect = document.getElementById("optimized-select");
    const customerQuery = document.getElementById("customer-query");
    const btnRunAgent = document.getElementById("btn-run-agent");
    
    const origLatency = document.getElementById("metrics-orig-latency");
    const origCost = document.getElementById("metrics-orig-cost");
    const origResponse = document.getElementById("agent-orig-response");
    const origTraceTree = document.getElementById("trace-orig-tree");
    
    const optLatency = document.getElementById("metrics-opt-latency");
    const optCost = document.getElementById("metrics-opt-cost");
    const optResponse = document.getElementById("agent-opt-response");
    const optTraceTree = document.getElementById("trace-opt-tree");
    
    // Modal Elements
    const spanModal = document.getElementById("span-modal");
    const modalClose = document.getElementById("close-modal");
    const modalName = document.getElementById("modal-span-name");
    const modalSpanId = document.getElementById("modal-span-id");
    const modalParentId = document.getElementById("modal-parent-id");
    const modalDuration = document.getElementById("modal-duration");
    const modalAttributes = document.getElementById("modal-attributes");

    // Detect if running on GitHub Pages (static demo mode)
    const IS_GITHUB_PAGES = window.location.hostname.endsWith('github.io') || window.location.protocol === 'file:';

    if (IS_GITHUB_PAGES) {
        document.getElementById("system-status").innerHTML = `
            <span class="dot yellow"></span>
            <span class="status-text">Static Demo Mode</span>
        `;
    }

    // Default seed prompt for "Before" comparison
    const SEED_PROMPT = {
        base: "Classify review sentiment.",
        formatting: "Output only the label: Positive, Negative, or Neutral.",
        reasoning: "Do not write any explanation, just print the label."
    };
    document.getElementById("prompt-orig-text").textContent = 
        `${SEED_PROMPT.base}\n\nFormatting: ${SEED_PROMPT.formatting}\n\nConstraint: ${SEED_PROMPT.reasoning}`;

    let paretoCandidates = [];
    let selectedCandidate = null;

    // 1. Chart.js Configuration
    const ctx = document.getElementById("paretoChart").getContext("2d");
    let paretoChart = new Chart(ctx, {
        type: "scatter",
        data: {
            datasets: [
                {
                    label: "All Prompts (Evolving)",
                    data: [],
                    backgroundColor: "rgba(54, 162, 235, 0.4)",
                    borderColor: "rgba(54, 162, 235, 0.8)",
                    pointRadius: 5
                },
                {
                    label: "Pareto Front (Rank 0)",
                    data: [],
                    backgroundColor: "rgba(142, 71, 45, 0.9)",
                    borderColor: "hsl(142, 71, 45)",
                    pointRadius: 8,
                    pointStyle: "rectRot",
                    showLine: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Token Cost per Run",
                        color: "hsl(215, 20%, 65%)"
                    },
                    grid: { color: "rgba(217, 30, 25, 0.1)" },
                    ticks: { color: "hsl(215, 20%, 65%)" }
                },
                y: {
                    title: {
                        display: true,
                        text: "Evaluation Accuracy",
                        color: "hsl(215, 20%, 65%)"
                    },
                    min: 0,
                    max: 1.05,
                    grid: { color: "rgba(217, 30, 25, 0.1)" },
                    ticks: {
                        color: "hsl(215, 20%, 65%)",
                        callback: function(value) {
                            return (value * 100) + "%";
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    labels: { color: "hsl(210, 40%, 96%)" }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += `Accuracy: ${(context.parsed.y * 100).toFixed(1)}%, Cost: ${context.parsed.x} tokens`;
                            return label;
                        }
                    }
                }
            }
        }
    });

    // Logger Helpers
    function appendLog(message, type = "info") {
        const span = document.createElement("span");
        span.className = `log-${type}`;
        span.innerHTML = `[${new Date().toLocaleTimeString()}] ${message}`;
        consoleLogs.appendChild(span);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Modal Helpers
    modalClose.addEventListener("click", () => {
        spanModal.classList.remove("show");
    });
    window.addEventListener("click", (e) => {
        if (e.target === spanModal) {
            spanModal.classList.remove("show");
        }
    });

    function showSpanDetails(span) {
        modalName.textContent = span.name;
        modalSpanId.textContent = span.span_id;
        modalParentId.textContent = span.parent_id || "None (Root)";
        modalDuration.textContent = `${span.duration_ms.toFixed(2)} ms`;
        modalAttributes.textContent = JSON.stringify(span.attributes, null, 2);
        spanModal.classList.add("show");
    }

    // 2. Telemetry Trace Tree Renderer
    function renderTraceTree(container, node) {
        container.innerHTML = "";
        if (!node || !node.name) {
            container.innerHTML = `<span class="log-info">No trace spans available.</span>`;
            return;
        }

        function createNodeEl(span) {
            const wrapper = document.createElement("div");
            wrapper.className = "trace-node";

            const summary = document.createElement("div");
            summary.className = "trace-node-summary";
            summary.innerHTML = `
                <i class="fa-solid fa-angle-right"></i> 
                <span class="span-name">${span.name}</span> 
                <span class="span-duration">(${span.duration_ms.toFixed(1)}ms)</span>
            `;
            
            summary.addEventListener("click", (e) => {
                e.stopPropagation();
                showSpanDetails(span);
            });

            wrapper.appendChild(summary);

            if (span.children && span.children.length > 0) {
                span.children.forEach(child => {
                    wrapper.appendChild(createNodeEl(child));
                });
            }

            return wrapper;
        }

        const rootEl = createNodeEl(node);
        rootEl.style.marginLeft = "0px";
        rootEl.style.borderLeft = "none";
        container.appendChild(rootEl);
    }

    // 3. Client-Side Simulation Mode for GitHub Pages
    function runStaticOptimization(popSize, gens) {
        let currentGen = 0;
        let population = [];

        const bases = [
            "Classify review sentiment.",
            "Analyze the product review and determine its sentiment.",
            "You are a helpful assistant. Classify the user feedback into Positive, Negative, or Neutral.",
            "Categorize review sentiment as Positive, Negative, or Neutral."
        ];
        const formats = [
            "Output only the label: Positive, Negative, or Neutral.",
            "Respond in JSON format: {'sentiment': label}",
            "Provide a single-word response.",
            "Begin your response with the word: Sentiment:"
        ];
        const reasonings = [
            "Do not write any explanation, just print the label.",
            "Explain your reasoning step-by-step before deciding.",
            "Think carefully before answering.",
            "Output directly the final classification."
        ];

        function generateMetrics(base, formatting, reasoning) {
            const has_reasoning = reasoning.includes("step-by-step") || reasoning.includes("carefully");
            const has_brief = formatting.includes("single-word") || reasoning.includes("directly") || reasoning.includes("just print");
            const has_json = formatting.includes("JSON");
            const has_prefix = formatting.includes("Sentiment:");

            let quality = 0.55;
            if (has_reasoning) quality += 0.25;
            if (has_json || has_prefix || formatting.includes("only")) quality += 0.15;
            if (has_reasoning && has_brief) quality -= 0.35;

            const accuracy = Math.max(0.10, Math.min(1.0, quality));
            const input_tokens = base.split(" ").length + formatting.split(" ").length + reasoning.split(" ").length + 20;
            const output_tokens = has_reasoning ? 50 : (has_json ? 15 : 2);
            const latency = 0.05 + (input_tokens * 0.001) + (output_tokens * 0.008);

            return {
                accuracy: accuracy,
                latency: latency,
                tokens: input_tokens + output_tokens
            };
        }

        // Initialize Population
        appendLog("Initializing local starting population (Simulation Mode)...", "status");
        
        for (let i = 0; i < popSize; i++) {
            const b = bases[i % bases.length];
            const f = formats[Math.floor(Math.random() * formats.length)];
            const r = reasonings[Math.floor(Math.random() * reasonings.length)];
            population.push({
                base: b,
                formatting: f,
                reasoning: r,
                metrics: generateMetrics(b, f, r),
                rank: i < 3 ? 0 : (i < 6 ? 1 : 2)
            });
        }

        function executeGenerationStep() {
            if (currentGen > gens) {
                // Complete
                appendLog("Optimization Completed Successfully! (Static Demo Front Cached)", "success");
                consolePulse.classList.add("hide");
                btnOptimize.disabled = false;

                // Build Pareto Front dropdown
                paretoCandidates = population.filter(c => c.rank === 0).sort((a,b) => b.metrics.accuracy - a.metrics.accuracy);
                
                optimizedSelect.innerHTML = "";
                paretoCandidates.forEach((cand, idx) => {
                    const opt = document.createElement("option");
                    opt.value = idx;
                    opt.textContent = `Candidate #${idx + 1} (Acc: ${(cand.metrics.accuracy*100).toFixed(0)}%, Lat: ${cand.metrics.latency.toFixed(2)}s, Cost: ${cand.metrics.tokens.toFixed(0)} t)`;
                    optimizedSelect.appendChild(opt);
                });
                optimizedSelect.disabled = false;
                selectedCandidate = paretoCandidates[0];
                updateOptimizedPromptPreview();
                return;
            }

            genCounter.textContent = `Gen: ${currentGen}`;
            if (currentGen === 0) {
                appendLog(`Initial population evaluated. Pareto Front size: 3`, "status");
            } else {
                appendLog(`Generation ${currentGen} completed. Pareto Front size: 3`, "status");
            }

            // Redraw table
            populationList.innerHTML = "";
            population.forEach((cand, idx) => {
                const m = cand.metrics;
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${idx + 1}</td>
                    <td title="${cand.base}">${cand.base.substring(0, 30)}...</td>
                    <td title="${cand.formatting}">${cand.formatting.substring(0, 30)}...</td>
                    <td title="${cand.reasoning}">${cand.reasoning.substring(0, 30)}...</td>
                    <td>${(m.accuracy * 100).toFixed(1)}%</td>
                    <td>${m.latency.toFixed(3)}s</td>
                    <td>${m.tokens.toFixed(0)}</td>
                    <td><span class="badge ${cand.rank === 0 ? 'green' : 'red'}">${cand.rank}</span></td>
                `;
                populationList.appendChild(row);
            });

            // Update Chart
            const allPoints = [];
            const paretoPoints = [];
            population.forEach(cand => {
                const pt = { x: parseFloat(cand.metrics.tokens.toFixed(1)), y: cand.metrics.accuracy };
                allPoints.push(pt);
                if (cand.rank === 0) {
                    paretoPoints.push(pt);
                }
            });

            paretoChart.data.datasets[0].data = allPoints;
            paretoChart.data.datasets[1].data = paretoPoints;
            paretoChart.update();

            // Mutate population for next step
            if (currentGen < gens) {
                population = population.map((cand, idx) => {
                    if (cand.rank > 0 || Math.random() < 0.4) {
                        // Mutate
                        const b = bases[Math.floor(Math.random() * bases.length)];
                        const f = formats[Math.floor(Math.random() * formats.length)];
                        const r = reasonings[Math.floor(Math.random() * reasonings.length)];
                        return {
                            base: b,
                            formatting: f,
                            reasoning: r,
                            metrics: generateMetrics(b, f, r),
                            rank: Math.random() < 0.45 ? 0 : (Math.random() < 0.7 ? 1 : 2)
                        };
                    }
                    return cand;
                });
            }

            currentGen++;
            // Setup next generation delay simulating evaluation
            let step = 1;
            function runSubStep() {
                if (step <= popSize) {
                    appendLog(`Evaluating candidate offspring ${step}/${popSize} in Gen ${currentGen}...`, "info");
                    step++;
                    setTimeout(runSubStep, 250);
                } else {
                    setTimeout(executeGenerationStep, 300);
                }
            }
            if (currentGen <= gens) {
                runSubStep();
            } else {
                setTimeout(executeGenerationStep, 500);
            }
        }

        executeGenerationStep();
    }

    function simulateAgentExecution(base, formatting, reasoning, query) {
        // Evaluate expected responses and metrics
        const isOptimized = base.includes("Classify") && reasoning.includes("Think carefully");
        const has_json = formatting.includes("JSON");
        
        let actual_sentiment = "Neutral";
        if (/billing|refund|cancel|charge/i.test(query)) {
            actual_sentiment = "Negative";
        } else if (/perfect|great|exceptional|best/i.test(query)) {
            actual_sentiment = "Positive";
        }

        const response_text = has_json 
            ? `{\n  "sentiment": "${actual_sentiment}"\n}`
            : (formatting.includes("Sentiment:") ? `Sentiment: ${actual_sentiment}` : actual_sentiment);

        const input_tokens = base.split(" ").length + formatting.split(" ").length + reasoning.split(" ").length + 20;
        const output_tokens = reasoning.includes("step-by-step") ? 45 : (has_json ? 12 : 2);
        const latency = isOptimized ? 0.158 : 0.122;

        const duration_ms = latency * 1000;
        
        // OpenTelemetry Span Tree
        const span_tree = {
            name: "invocation",
            span_id: "0000000000000001",
            parent_id: null,
            duration_ms: duration_ms + 15.2,
            attributes: {},
            children: [
                {
                    name: "invoke_agent customer_support_agent",
                    span_id: "0000000000000002",
                    parent_id: "0000000000000001",
                    duration_ms: duration_ms + 12.1,
                    attributes: {
                        "gen_ai.operation.name": "invoke_agent",
                        "gen_ai.agent.name": "customer_support_agent"
                    },
                    children: [
                        {
                            name: "call_llm",
                            span_id: "0000000000000003",
                            parent_id: "0000000000000002",
                            duration_ms: duration_ms,
                            attributes: {
                                "gen_ai.system": "gcp.vertex.agent",
                                "gen_ai.request.model": "mock-model",
                                "gen_ai.usage.input_tokens": input_tokens,
                                "gen_ai.usage.output_tokens": output_tokens
                            },
                            children: [
                                {
                                    name: "generate_content mock-model",
                                    span_id: "0000000000000004",
                                    parent_id: "0000000000000003",
                                    duration_ms: duration_ms - 2.5,
                                    attributes: {
                                        "gen_ai.system": "gemini",
                                        "gen_ai.operation.name": "generate_content",
                                        "gen_ai.usage.input_tokens": input_tokens,
                                        "gen_ai.usage.output_tokens": output_tokens
                                    },
                                    children: []
                                }
                            ]
                        }
                    ]
                }
            ]
        };

        return {
            response_text: response_text,
            latency_s: latency,
            tokens: input_tokens + output_tokens,
            trace_tree: span_tree
        };
    }

    // 4. Optimization trigger (handles SSE vs Demo simulation)
    btnOptimize.addEventListener("click", () => {
        const popSize = parseInt(inputPopSize.value);
        const gens = parseInt(inputGenerations.value);

        if (IS_GITHUB_PAGES) {
            btnOptimize.disabled = true;
            consolePulse.classList.remove("hide");
            consoleLogs.innerHTML = "";
            runStaticOptimization(popSize, gens);
            return;
        }

        btnOptimize.disabled = true;
        consolePulse.classList.remove("hide");
        consoleLogs.innerHTML = "";
        appendLog("Connecting to ADK Optimization Engine...", "status");
        
        // SSE Connection
        const sse = new EventSource(`/api/optimize/stream?pop_size=${popSize}&generations=${gens}`);

        sse.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.event === "status") {
                appendLog(data.message, "info");
            } 
            else if (data.event === "generation") {
                genCounter.textContent = `Gen: ${data.gen}`;
                appendLog(`Generation ${data.gen} completed. Pareto Front size: ${data.front_size}`, "status");
                
                // Redraw table
                populationList.innerHTML = "";
                data.population.forEach((cand, idx) => {
                    const m = cand.metrics;
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${idx + 1}</td>
                        <td title="${cand.base}">${cand.base.substring(0, 30)}...</td>
                        <td title="${cand.formatting}">${cand.formatting.substring(0, 30)}...</td>
                        <td title="${cand.reasoning}">${cand.reasoning.substring(0, 30)}...</td>
                        <td>${(m.accuracy * 100).toFixed(1)}%</td>
                        <td>${m.latency.toFixed(3)}s</td>
                        <td>${m.tokens.toFixed(0)}</td>
                        <td><span class="badge ${cand.rank === 0 ? 'green' : 'red'}">${cand.rank}</span></td>
                    `;
                    populationList.appendChild(row);
                });

                // Update Chart
                const allPoints = [];
                const paretoPoints = [];
                data.population.forEach(cand => {
                    const pt = { x: parseFloat(cand.metrics.tokens.toFixed(1)), y: cand.metrics.accuracy };
                    allPoints.push(pt);
                    if (cand.rank === 0) {
                        paretoPoints.push(pt);
                    }
                });

                paretoChart.data.datasets[0].data = allPoints;
                paretoChart.data.datasets[1].data = paretoPoints;
                paretoChart.update();
            } 
            else if (data.event === "complete") {
                appendLog("Optimization Completed Successfully!", "success");
                consolePulse.classList.add("hide");
                btnOptimize.disabled = false;
                sse.close();

                paretoCandidates = data.pareto_front;
                selectedCandidate = paretoCandidates[0]; 

                // Populate Playground Options
                optimizedSelect.innerHTML = "";
                paretoCandidates.forEach((cand, idx) => {
                    const opt = document.createElement("option");
                    opt.value = idx;
                    opt.textContent = `Candidate #${idx + 1} (Acc: ${(cand.metrics.accuracy*100).toFixed(0)}%, Lat: ${cand.metrics.latency.toFixed(2)}s, Cost: ${cand.metrics.tokens.toFixed(0)} t)`;
                    optimizedSelect.appendChild(opt);
                });
                optimizedSelect.disabled = false;
                updateOptimizedPromptPreview();
            }
            else if (data.event === "error") {
                appendLog(`Optimization error: ${data.message}`, "error");
                consolePulse.classList.add("hide");
                btnOptimize.disabled = false;
                sse.close();
            }
        };

        sse.onerror = (err) => {
            appendLog("Server-Sent Events connection failed. Reconnecting or server down.", "error");
            consolePulse.classList.add("hide");
            btnOptimize.disabled = false;
            sse.close();
        };
    });

    function updateOptimizedPromptPreview() {
        if (!selectedCandidate) return;
        const text = `${selectedCandidate.base}\n\nFormatting: ${selectedCandidate.formatting}\n\nConstraint: ${selectedCandidate.reasoning}`;
        document.getElementById("prompt-opt-text").textContent = text;
    }

    optimizedSelect.addEventListener("change", (e) => {
        const val = e.target.value;
        if (val !== "") {
            selectedCandidate = paretoCandidates[parseInt(val)];
            updateOptimizedPromptPreview();
        }
    });

    // 5. Run Agent (Playground)
    btnRunAgent.addEventListener("click", async () => {
        const query = customerQuery.value.trim();
        if (!query) {
            alert("Please input a customer query first.");
            return;
        }

        btnRunAgent.disabled = true;
        btnRunAgent.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Running...`;

        origResponse.innerHTML = `<span class="log-info"><i class="fa-solid fa-spinner fa-spin"></i> Querying agent...</span>`;
        optResponse.innerHTML = `<span class="log-info"><i class="fa-solid fa-spinner fa-spin"></i> Querying agent...</span>`;
        origTraceTree.innerHTML = `<span class="log-info"><i class="fa-solid fa-spinner fa-spin"></i> Awaiting telemetry...</span>`;
        optTraceTree.innerHTML = `<span class="log-info"><i class="fa-solid fa-spinner fa-spin"></i> Awaiting telemetry...</span>`;

        if (IS_GITHUB_PAGES) {
            // Client-Side Simulated Playground execution
            setTimeout(() => {
                const dataOrig = simulateAgentExecution(SEED_PROMPT.base, SEED_PROMPT.formatting, SEED_PROMPT.reasoning, query);
                origLatency.innerHTML = `<i class="fa-regular fa-clock"></i> Latency: ${dataOrig.latency_s.toFixed(3)}s`;
                origCost.innerHTML = `<i class="fa-solid fa-coins"></i> Tokens: ${dataOrig.tokens}`;
                origResponse.textContent = dataOrig.response_text;
                renderTraceTree(origTraceTree, dataOrig.trace_tree);

                if (selectedCandidate) {
                    const dataOpt = simulateAgentExecution(selectedCandidate.base, selectedCandidate.formatting, selectedCandidate.reasoning, query);
                    optLatency.innerHTML = `<i class="fa-regular fa-clock"></i> Latency: ${dataOpt.latency_s.toFixed(3)}s`;
                    optCost.innerHTML = `<i class="fa-solid fa-coins"></i> Tokens: ${dataOpt.tokens}`;
                    optResponse.textContent = dataOpt.response_text;
                    renderTraceTree(optTraceTree, dataOpt.trace_tree);
                } else {
                    optResponse.innerHTML = `<span class="log-error">No optimized prompt selected. Complete GA run.</span>`;
                    optTraceTree.innerHTML = "";
                }

                btnRunAgent.disabled = false;
                btnRunAgent.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Run Agent`;
            }, 600);
            return;
        }

        try {
            // Run Original Prompt (FastAPI)
            const resOrig = await fetch("/api/run-agent", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    base: SEED_PROMPT.base,
                    formatting: SEED_PROMPT.formatting,
                    reasoning: SEED_PROMPT.reasoning,
                    query: query
                })
            });
            const dataOrig = await resOrig.json();
            
            origLatency.innerHTML = `<i class="fa-regular fa-clock"></i> Latency: ${dataOrig.latency_s.toFixed(3)}s`;
            origCost.innerHTML = `<i class="fa-solid fa-coins"></i> Tokens: ${dataOrig.tokens}`;
            origResponse.textContent = dataOrig.response_text;
            renderTraceTree(origTraceTree, dataOrig.trace_tree);

            // Run Optimized Prompt (FastAPI)
            if (selectedCandidate) {
                const resOpt = await fetch("/api/run-agent", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        base: selectedCandidate.base,
                        formatting: selectedCandidate.formatting,
                        reasoning: selectedCandidate.reasoning,
                        query: query
                    })
                });
                const dataOpt = await resOpt.json();
                
                optLatency.innerHTML = `<i class="fa-regular fa-clock"></i> Latency: ${dataOpt.latency_s.toFixed(3)}s`;
                optCost.innerHTML = `<i class="fa-solid fa-coins"></i> Tokens: ${dataOpt.tokens}`;
                optResponse.textContent = dataOpt.response_text;
                renderTraceTree(optTraceTree, dataOpt.trace_tree);
            } else {
                optResponse.innerHTML = `<span class="log-error">No optimized prompt selected. Complete GA run.</span>`;
                optTraceTree.innerHTML = "";
            }

        } catch (err) {
            console.error(err);
            origResponse.textContent = `Failed: ${err}`;
            optResponse.textContent = `Failed: ${err}`;
        } finally {
            btnRunAgent.disabled = false;
            btnRunAgent.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Run Agent`;
        }
    });
});
