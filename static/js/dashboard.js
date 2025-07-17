class OptimizationDashboard {
    constructor() {
        this.websocket = null;
        this.state = {
            phase: 'idle',
            progress: 0,
            data_points: [],
            model_results: {},
            optimization_results: {}
        };
        
        this.scatterPlot = null;
        this.surfacePlot = null;
        this.currentPlotTab = '2d';
        
        // Plot data storage
        this.doePoints = [];
        this.refinementPoints = [];
        this.optimumPoint = null;
        
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.initializeUI();
        this.initializePlots();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            this.addLogEntry('Connected to server', 'success');
        };
        
        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
        };
        
        this.websocket.onclose = () => {
            this.addLogEntry('Disconnected from server', 'warning');
            // Try to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.websocket.onerror = (error) => {
            this.addLogEntry('Connection error', 'error');
        };
    }

    setupEventListeners() {
        document.getElementById('startBtn').addEventListener('click', () => {
            this.startOptimization();
        });
        
        document.getElementById('resetBtn').addEventListener('click', () => {
            this.resetSystem();
        });
        
        // Plot tab switching
        document.getElementById('tab2d').addEventListener('click', () => {
            this.switchPlotTab('2d');
        });
        
        document.getElementById('tab3d').addEventListener('click', () => {
            this.switchPlotTab('3d');
        });
        
        // Handle window resize for plots
        window.addEventListener('resize', () => {
            setTimeout(() => {
                Plotly.Plots.resize('scatterPlot');
                Plotly.Plots.resize('surfacePlot');
            }, 100);
        });
    }

    initializeUI() {
        this.updatePhaseIndicators();
        this.updateProgress(0);
    }

    initializePlots() {
        // Initialize 2D scatter plot with Plotly
        this.initialize2DPlot();
        
        // Initialize 3D surface plot placeholder
        this.initializeSurfacePlot();
    }

    initialize2DPlot() {
        const layout = {
            title: 'Design Space Exploration',
            xaxis: {
                title: 'Variable 1 (x1)',
                range: [0, 1],
                showgrid: true,
                zeroline: false
            },
            yaxis: {
                title: 'Variable 2 (x2)',
                range: [0, 1],
                showgrid: true,
                zeroline: false,
                scaleanchor: 'x', // Keep square aspect ratio
                scaleratio: 1
            },
            showlegend: true,
            legend: { x: 0, y: 1 },
            margin: { l: 50, r: 20, t: 40, b: 40 },
            plot_bgcolor: 'white',
            paper_bgcolor: '#f8f9fa'
        };

        const config = {
            displayModeBar: false,
            responsive: true
        };

        // Initial empty traces
        const traces = [
            {
                x: [],
                y: [],
                mode: 'markers',
                type: 'scatter',
                name: 'DoE Points',
                marker: {
                    color: 'rgba(102, 126, 234, 0.8)',
                    size: 8,
                    line: { color: 'rgba(102, 126, 234, 1)', width: 1 }
                }
            },
            {
                x: [],
                y: [],
                mode: 'markers',
                type: 'scatter',
                name: 'Refinement Points',
                marker: {
                    color: 'rgba(40, 167, 69, 0.8)',
                    size: 8,
                    line: { color: 'rgba(40, 167, 69, 1)', width: 1 }
                }
            },
            {
                x: [],
                y: [],
                mode: 'markers',
                type: 'scatter',
                name: 'Predicted Optimum',
                marker: {
                    color: 'rgba(220, 53, 69, 0.9)',
                    size: 15,
                    symbol: 'star',
                    line: { color: 'rgba(220, 53, 69, 1)', width: 2 }
                }
            }
        ];

        Plotly.newPlot('scatterPlot', traces, layout, config);
    }

    initializeSurfacePlot() {
        // Initial empty 3D plot
        const layout = {
            title: 'Response Surface (Available after modeling)',
            scene: {
                xaxis: { title: 'Variable 1 (x1)', range: [0, 1] },
                yaxis: { title: 'Variable 2 (x2)', range: [0, 1] },
                zaxis: { title: 'Response' }
            },
            margin: { l: 0, r: 0, t: 30, b: 0 }
        };

        Plotly.newPlot('surfacePlot', [], layout, {
            displayModeBar: false,
            responsive: true
        });
    }

    switchPlotTab(tab) {
        // Update tab buttons
        document.querySelectorAll('.plot-tab').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.plot-content').forEach(content => content.classList.remove('active'));
        
        if (tab === '2d') {
            document.getElementById('tab2d').classList.add('active');
            document.getElementById('plot2d').classList.add('active');
        } else {
            document.getElementById('tab3d').classList.add('active');
            document.getElementById('plot3d').classList.add('active');
        }
        
        this.currentPlotTab = tab;
        
        // Resize plots when switching tabs
        setTimeout(() => {
            if (tab === '2d') {
                Plotly.Plots.resize('scatterPlot');
            } else if (tab === '3d') {
                Plotly.Plots.resize('surfacePlot');
            }
        }, 100);
    }

    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'state_update':
                this.state = message.state;
                this.updateUI();
                break;
                
            case 'phase_change':
                this.state.phase = message.phase;
                this.updatePhaseIndicators();
                this.addLogEntry(message.message, 'info');
                break;
                
            case 'doe_generated':
                this.addLogEntry(message.message, 'info');
                break;
                
            case 'data_collection':
                this.updateDataCollection(message);
                break;
                
            case 'data_collected':
                this.addDataPoint(message);
                this.updateScatterPlot();
                break;
                
            case 'model_fitted':
                this.updateModelResults(message.model);
                this.updateSurfacePlot(message.model);
                this.addLogEntry(message.message, 'success');
                break;
                
            case 'optimization_complete':
                this.updateOptimizationResults(message.result);
                this.updateOptimumPoint(message.result);
                this.addLogEntry(message.message, 'success');
                break;
                
            case 'refinement_complete':
                this.addLogEntry(message.message, 'success');
                break;
                
            case 'workflow_complete':
                this.state.phase = 'complete';
                this.updatePhaseIndicators();
                this.updateProgress(100);
                this.displayFinalSummary(message.summary);
                this.addLogEntry(message.message, 'success');
                this.enableStartButton();
                break;
                
            case 'error':
                this.addLogEntry(message.message, 'error');
                this.enableStartButton();
                break;
                
            case 'reset_complete':
                this.resetUI();
                this.addLogEntry(message.message, 'info');
                break;
        }
    }

    startOptimization() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                action: 'start_optimization'
            }));
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('startBtn').textContent = 'Running...';
            this.addLogEntry('Starting optimization workflow...', 'info');
        }
    }

    resetSystem() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                action: 'reset'
            }));
        }
    }

    enableStartButton() {
        const startBtn = document.getElementById('startBtn');
        startBtn.disabled = false;
        startBtn.textContent = 'Start Optimization';
    }

    updateUI() {
        this.updatePhaseIndicators();
        this.updateProgress(this.state.progress);
        
        if (this.state.data_points.length > 0) {
            this.displayDataPoints();
        }
        
        if (Object.keys(this.state.model_results).length > 0) {
            this.updateModelResults(this.state.model_results);
        }
        
        if (Object.keys(this.state.optimization_results).length > 0) {
            this.updateOptimizationResults(this.state.optimization_results);
        }
    }

    updatePhaseIndicators() {
        const phases = ['doe', 'modeling', 'optimization', 'refinement'];
        const currentPhase = this.state.phase;
        
        // Update current phase display
        const phaseElement = document.getElementById('currentPhase');
        phaseElement.textContent = this.getPhaseDisplayName(currentPhase);
        phaseElement.className = `phase-${currentPhase}`;
        
        // Update phase indicators
        phases.forEach(phase => {
            const indicator = document.getElementById(`phase-${phase}`);
            indicator.classList.remove('active', 'completed');
            
            if (phase === currentPhase) {
                indicator.classList.add('active');
            } else if (this.isPhaseCompleted(phase, currentPhase)) {
                indicator.classList.add('completed');
            }
        });
    }

    getPhaseDisplayName(phase) {
        const names = {
            'idle': 'Idle',
            'starting': 'Starting',
            'doe': 'Design of Experiments',
            'modeling': 'Response Surface Modeling',
            'optimization': 'Model-Based Optimization',
            'refinement': 'Local Refinement',
            'complete': 'Complete',
            'error': 'Error'
        };
        return names[phase] || phase;
    }

    isPhaseCompleted(phase, currentPhase) {
        const phaseOrder = ['doe', 'modeling', 'optimization', 'refinement'];
        const currentIndex = phaseOrder.indexOf(currentPhase);
        const phaseIndex = phaseOrder.indexOf(phase);
        
        return currentIndex > phaseIndex || currentPhase === 'complete';
    }

    updateProgress(percentage) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        progressFill.style.width = `${percentage}%`;
        progressText.textContent = `${Math.round(percentage)}%`;
    }

    updateDataCollection(message) {
        this.addLogEntry(message.message, 'info');
        
        // Calculate progress based on data collection
        if (message.total_points > 0) {
            const progress = (message.point_index / message.total_points) * 25; // 25% per phase
            const phaseProgress = {
                'doe': progress,
                'refinement': 75 + progress
            };
            
            if (phaseProgress[this.state.phase]) {
                this.updateProgress(phaseProgress[this.state.phase]);
            }
        }
    }

    addDataPoint(message) {
        const dataContainer = document.getElementById('dataPoints');
        
        // Remove "no data" message if it exists
        const noDataMsg = dataContainer.querySelector('.no-data');
        if (noDataMsg) {
            noDataMsg.remove();
        }
        
        const dataPoint = document.createElement('div');
        dataPoint.className = 'data-point collected';
        dataPoint.innerHTML = `
            <strong>Point:</strong> [${message.point.map(p => p.toFixed(3)).join(', ')}]<br>
            <strong>Measurement:</strong> ${message.measurement.toFixed(4)}
        `;
        
        dataContainer.appendChild(dataPoint);
        dataContainer.scrollTop = dataContainer.scrollHeight;
    }

    displayDataPoints() {
        const dataContainer = document.getElementById('dataPoints');
        dataContainer.innerHTML = '';
        
        this.state.data_points.forEach(point => {
            const dataPoint = document.createElement('div');
            dataPoint.className = 'data-point collected';
            dataPoint.innerHTML = `
                <strong>Point:</strong> [${point.vars.map(p => p.toFixed(3)).join(', ')}]<br>
                <strong>Measurement:</strong> ${point.measurement.toFixed(4)}
            `;
            dataContainer.appendChild(dataPoint);
        });
    }

    updateModelResults(model) {
        const modelContainer = document.getElementById('modelResults');
        
        if (model && model.status) {
            modelContainer.innerHTML = `
                <h3>${model.status}</h3>
                <div style="margin-top: 15px;">
                    <strong>R² (Goodness of Fit):</strong> ${(model.r_squared || 0).toFixed(4)}<br>
                    <strong>Data Points Used:</strong> ${model.num_data_points || 0}<br>
                    <strong>Model:</strong> ${model.model_equation || 'N/A'}
                </div>
                <div style="margin-top: 15px;">
                    <strong>Coefficients:</strong>
                    <ul style="margin-top: 5px; padding-left: 20px;">
                        ${(model.coefficient_names || []).map((name, i) => 
                            `<li>${name}: ${(model.model_coefficients[i] || 0).toFixed(4)}</li>`
                        ).join('')}
                    </ul>
                </div>
            `;
            
            // Update progress for modeling phase
            if (this.state.phase === 'modeling') {
                this.updateProgress(50);
            }
        }
    }

    updateOptimizationResults(result) {
        const optContainer = document.getElementById('optimizationResults');
        
        if (result && result.status) {
            optContainer.innerHTML = `
                <h3>${result.status}</h3>
                <div style="margin-top: 15px;">
                    <strong>Optimal Point:</strong> [${result.optimal_point.map(p => p.toFixed(4)).join(', ')}]<br>
                    <strong>Optimal Value:</strong> ${result.optimal_value.toFixed(4)}<br>
                    <strong>Iterations:</strong> ${result.iterations}<br>
                    <strong>Converged:</strong> ${result.converged ? 'Yes' : 'No'}
                </div>
            `;
            
            // Update progress for optimization phase
            if (this.state.phase === 'optimization') {
                this.updateProgress(75);
            }
        }
    }

    displayFinalSummary(summary) {
        const optContainer = document.getElementById('optimizationResults');
        
        let summaryHTML = `
            <h3>🎯 Optimization Workflow Complete</h3>
            <div style="margin-top: 15px;">
                <strong>Total Data Points:</strong> ${summary.total_points}<br>
                <strong>Model R²:</strong> ${(summary.r_squared || 0).toFixed(4)}<br>
        `;
        
        if (summary.predicted_optimum) {
            summaryHTML += `
                <strong>Model-Predicted Optimum:</strong> [${summary.predicted_optimum.map(p => p.toFixed(4)).join(', ')}]<br>
                <strong>Model-Predicted Value:</strong> ${summary.predicted_value.toFixed(4)}<br>
            `;
        }
        
        if (summary.experimental_optimum) {
            summaryHTML += `
                <strong>Experimentally Verified Optimum:</strong> [${summary.experimental_optimum.map(p => p.toFixed(4)).join(', ')}]<br>
                <strong>Experimentally Verified Value:</strong> ${summary.experimental_value.toFixed(4)}<br>
            `;
        }
        
        summaryHTML += '</div>';
        optContainer.innerHTML = summaryHTML;
    }

    resetUI() {
        // Reset state
        this.state = {
            phase: 'idle',
            progress: 0,
            data_points: [],
            model_results: {},
            optimization_results: {}
        };
        
        // Reset UI elements
        this.updatePhaseIndicators();
        this.updateProgress(0);
        this.enableStartButton();
        
        // Clear data displays
        document.getElementById('dataPoints').innerHTML = '<p class="no-data">No data points collected yet</p>';
        document.getElementById('modelResults').innerHTML = '<p class="no-data">No model fitted yet</p>';
        document.getElementById('optimizationResults').innerHTML = '<p class="no-data">No optimization results yet</p>';
        
        // Clear log except for reset message
        const logContainer = document.getElementById('activityLog');
        logContainer.innerHTML = '<p class="log-entry">System ready</p>';
    }

    addLogEntry(message, type = 'info') {
        const logContainer = document.getElementById('activityLog');
        const timestamp = new Date().toLocaleTimeString();
        
        const logEntry = document.createElement('p');
        logEntry.className = `log-entry ${type}`;
        logEntry.textContent = `[${timestamp}] ${message}`;
        
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Keep only last 50 entries
        const entries = logContainer.querySelectorAll('.log-entry');
        if (entries.length > 50) {
            entries[0].remove();
        }
    }

    updateScatterPlot() {
        // Separate DoE and refinement points
        const doeX = [];
        const doeY = [];
        const refinementX = [];
        const refinementY = [];
        
        this.state.data_points.forEach((point, index) => {
            // Assume first 16 points are DoE, rest are refinement
            if (index < 16) {
                doeX.push(point.vars[0]);
                doeY.push(point.vars[1]);
            } else {
                refinementX.push(point.vars[0]);
                refinementY.push(point.vars[1]);
            }
        });
        
        // Update plot data
        const update = {
            x: [doeX, refinementX, this.optimumPoint ? [this.optimumPoint[0]] : []],
            y: [doeY, refinementY, this.optimumPoint ? [this.optimumPoint[1]] : []]
        };
        
        Plotly.restyle('scatterPlot', update, [0, 1, 2]);
    }

    updateOptimumPoint(optimizationResult) {
        if (!optimizationResult.optimal_point) return;
        
        this.optimumPoint = optimizationResult.optimal_point;
        
        // Update optimum point in 2D plot
        const update = {
            x: [[this.optimumPoint[0]]],
            y: [[this.optimumPoint[1]]]
        };
        
        Plotly.restyle('scatterPlot', update, [2]);
    }

    updateSurfacePlot(modelResults) {
        if (!modelResults.model_coefficients) return;
        
        const coeffs = modelResults.model_coefficients;
        
        // Generate grid for surface plot
        const size = 20;
        const x = [];
        const y = [];
        const z = [];
        
        for (let i = 0; i < size; i++) {
            const xi = i / (size - 1);
            const xRow = [];
            const yRow = [];
            const zRow = [];
            
            for (let j = 0; j < size; j++) {
                const yj = j / (size - 1);
                
                // Quadratic model: z = a*x^2 + b*y^2 + c*x*y + d*x + e*y + f
                const zi = coeffs[0] * xi * xi + 
                           coeffs[1] * yj * yj + 
                           coeffs[2] * xi * yj + 
                           coeffs[3] * xi + 
                           coeffs[4] * yj + 
                           coeffs[5];
                
                xRow.push(xi);
                yRow.push(yj);
                zRow.push(zi);
            }
            
            x.push(xRow);
            y.push(yRow);
            z.push(zRow);
        }
        
        // Create surface trace
        const surfaceTrace = {
            type: 'surface',
            x: x,
            y: y,
            z: z,
            colorscale: 'Viridis',
            opacity: 0.8,
            name: 'Response Surface'
        };
        
        // Add data points as scatter
        const scatterTrace = {
            type: 'scatter3d',
            mode: 'markers',
            x: this.state.data_points.map(p => p.vars[0]),
            y: this.state.data_points.map(p => p.vars[1]),
            z: this.state.data_points.map(p => p.measurement),
            marker: {
                size: 6,
                color: 'red',
                symbol: 'circle'
            },
            name: 'Data Points'
        };
        
        const layout = {
            title: `Response Surface (R² = ${modelResults.r_squared.toFixed(3)})`,
            scene: {
                xaxis: { title: 'Variable 1 (x1)', range: [0, 1] },
                yaxis: { title: 'Variable 2 (x2)', range: [0, 1] },
                zaxis: { title: 'Response' }
            },
            margin: { l: 0, r: 0, t: 30, b: 0 }
        };
        
        // Add optimum point if available
        const traces = [surfaceTrace, scatterTrace];
        if (this.state.optimization_results && this.state.optimization_results.optimal_point) {
            const optimumTrace = {
                type: 'scatter3d',
                mode: 'markers',
                x: [this.state.optimization_results.optimal_point[0]],
                y: [this.state.optimization_results.optimal_point[1]],
                z: [this.state.optimization_results.optimal_value],
                marker: {
                    size: 12,
                    color: 'gold',
                    symbol: 'diamond',
                    line: { color: 'black', width: 2 }
                },
                name: 'Predicted Optimum'
            };
            traces.push(optimumTrace);
        }
        
        Plotly.react('surfacePlot', traces, layout, {
            displayModeBar: false,
            responsive: true
        });
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new OptimizationDashboard();
});