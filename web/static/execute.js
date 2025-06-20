class ExecutionInterface {
    constructor() {
        this.executionId = this.getExecutionIdFromUrl();
        this.eventSource = null;
        this.executionData = null;
        this.steps = new Map();
        this.startTime = null;
        
        this.initializeElements();
        this.loadExecution();
    }
    
    initializeElements() {
        this.statusBanner = document.getElementById('statusBanner');
        this.statusText = document.getElementById('statusText');
        this.executionInfo = document.getElementById('executionInfo');
        this.stepsContainer = document.getElementById('stepsContainer');
        this.currentStepCard = document.getElementById('currentStepCard');
        this.currentStepContent = document.getElementById('currentStepContent');
        this.finalResultCard = document.getElementById('finalResultCard');
        this.finalResultContent = document.getElementById('finalResultContent');
        this.errorCard = document.getElementById('errorCard');
        this.errorContent = document.getElementById('errorContent');
        
        // Summary elements
        this.totalSteps = document.getElementById('totalSteps');
        this.completedSteps = document.getElementById('completedSteps');
        this.remainingSteps = document.getElementById('remainingSteps');
        this.stepProgress = document.getElementById('stepProgress');
        
        // Info elements
        this.originalQuery = document.getElementById('originalQuery');
        this.startedAt = document.getElementById('startedAt');
        this.duration = document.getElementById('duration');
        
        // Initialize icons
        lucide.createIcons();
    }
    
    getExecutionIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('id');
    }
    
    async loadExecution() {
        if (!this.executionId) {
            this.showError('No execution ID provided');
            return;
        }
        
        try {
            // Get initial execution status
            const response = await fetch(`/api/execution/${this.executionId}/status`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load execution');
            }
            
            this.executionData = data;
            this.setupInitialDisplay();
            this.setupEventStream();
            
        } catch (error) {
            console.error('Error loading execution:', error);
            this.showError(error.message);
        }
    }
    
    setupInitialDisplay() {
        // Show execution info
        this.originalQuery.textContent = this.executionData.query || 'No query';
        this.startedAt.textContent = new Date(this.executionData.started_at).toLocaleString();
        this.executionInfo.classList.remove('hidden');
        
        // Setup steps
        if (this.executionData.plan && this.executionData.plan.plan) {
            this.setupSteps(this.executionData.plan.plan);
        }
        
        // Update status
        this.updateStatus(this.executionData.status);
        this.updateSummary();
    }
    
    setupSteps(planSteps) {
        this.totalSteps.textContent = planSteps.length;
        
        const stepsHtml = planSteps.map((step, index) => {
            const stepNumber = index + 1;
            this.steps.set(step.id, {
                ...step,
                status: 'pending',
                result: null,
                index: stepNumber
            });
            
            return this.createStepHtml(step, stepNumber);
        }).join('');
        
        this.stepsContainer.innerHTML = stepsHtml;
        lucide.createIcons();
    }
    
    createStepHtml(step, stepNumber) {
        const stepTypeColors = {
            'llm': 'bg-blue-50 border-blue-200 text-blue-800',
            'tool': 'bg-green-50 border-green-200 text-green-800',
            'if': 'bg-yellow-50 border-yellow-200 text-yellow-800',
            'goto': 'bg-purple-50 border-purple-200 text-purple-800',
            'end': 'bg-gray-50 border-gray-200 text-gray-800'
        };
        
        const stepTypeIcons = {
            'llm': 'brain',
            'tool': 'wrench',
            'if': 'git-branch',
            'goto': 'arrow-right',
            'end': 'flag'
        };
        
        const stepTypeColor = stepTypeColors[step.type] || 'bg-gray-50 border-gray-200 text-gray-800';
        const stepTypeIcon = stepTypeIcons[step.type] || 'circle';
        
        return `
            <div id="step-${step.id}" class="step-card border border-gray-200 rounded-lg p-4 mb-4 last:mb-0">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center">
                        <span class="step-number inline-flex items-center justify-center w-8 h-8 bg-gray-100 text-gray-700 rounded-full text-sm font-semibold mr-3">
                            ${stepNumber}
                        </span>
                        <div>
                            <div class="flex items-center mb-1">
                                <span class="text-sm font-mono font-semibold text-gray-900 mr-2">${step.id}</span>
                                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${stepTypeColor}">
                                    <i data-lucide="${stepTypeIcon}" class="w-3 h-3 mr-1"></i>
                                    ${step.type}
                                </span>
                            </div>
                            <p class="text-sm text-gray-600">${step.description || 'No description'}</p>
                        </div>
                    </div>
                    <div class="step-status flex items-center">
                        <span class="status-indicator inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                            <i data-lucide="clock" class="w-3 h-3 mr-1"></i>
                            pending
                        </span>
                    </div>
                </div>
                
                <div class="step-result hidden">
                    <div class="mt-3 p-3 bg-gray-50 rounded-lg">
                        <h4 class="text-sm font-semibold text-gray-700 mb-2">Result:</h4>
                        <div class="result-content text-sm text-gray-900"></div>
                    </div>
                </div>
            </div>
        `;
    }
    
    setupEventStream() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        console.log('Setting up event stream for execution:', this.executionId);
        this.eventSource = new EventSource(`/api/execution/${this.executionId}/stream`);
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('Raw SSE data received:', event.data);
                this.handleUpdate(data);
            } catch (error) {
                console.error('Error parsing event data:', error);
                console.error('Raw event data:', event.data);
            }
        };
        
        this.eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            console.error('EventSource state:', this.eventSource.readyState);
            
            // Handle connection errors
            this.handleConnectionError();
        };
        
        this.eventSource.onopen = () => {
            console.log('EventSource connection opened successfully');
        };
    }
    
    handleUpdate(data) {
        console.log('Received update:', data);
        
        // Add more detailed logging to debug the issue
        console.log('Update type:', data.type);
        console.log('Update data:', data);
        
        switch (data.type) {
            case 'execution_started':
                this.updateStatus('running');
                this.startTime = new Date();
                break;
                
            case 'step_started':
                this.updateStepStatus(data.step_id, 'running');
                this.updateCurrentStep(data);
                break;
                
            case 'step_completed':
                // Only update step status, not overall execution status
                this.updateStepStatus(data.step_id, data.success ? 'completed' : 'failed', data.result);
                this.updateSummary();
                
                // Check if this was the last step (END step) but don't assume execution is complete
                if (data.step_id && this.steps.has(data.step_id)) {
                    const step = this.steps.get(data.step_id);
                    if (step.type === 'end') {
                        console.log('END step completed, but waiting for execution_completed event');
                    }
                }
                break;
                
            case 'execution_completed':
                console.log('Execution completed event received');
                this.updateStatus('completed');
                this.showFinalResult(data.result);
                this.clearCurrentStep();
                if (this.eventSource) {
                    this.eventSource.close();
                }
                break;
                
            case 'execution_failed':
                console.log('Execution failed event received');
                this.updateStatus('failed');
                this.showError(data.error);
                this.clearCurrentStep();
                if (this.eventSource) {
                    this.eventSource.close();
                }
                break;
                
            case 'execution_stopped':
                console.log('Execution stopped event received');
                this.updateStatus('stopped');
                this.clearCurrentStep();
                if (this.eventSource) {
                    this.eventSource.close();
                }
                break;
                
            case 'heartbeat':
                // Just keep connection alive - don't log to reduce noise
                break;
                
            default:
                console.warn('Unknown event type received:', data.type);
                break;
        }
        
        this.updateDuration();
    }
    
    handleConnectionError() {
        console.error('Connection lost, attempting to reconnect...');
        this.updateStatus('connecting');
        
        // Try to reconnect after a delay
        setTimeout(() => {
            if (this.eventSource.readyState === EventSource.CLOSED) {
                this.setupEventStream();
            }
        }, 2000);
    }
    
    updateStepStatus(stepId, status, result = null) {
        const stepElement = document.getElementById(`step-${stepId}`);
        if (!stepElement) return;
        
        const statusIndicator = stepElement.querySelector('.status-indicator');
        const resultContainer = stepElement.querySelector('.step-result');
        const resultContent = stepElement.querySelector('.result-content');
        const stepNumber = stepElement.querySelector('.step-number');
        
        // Update step data
        if (this.steps.has(stepId)) {
            const stepData = this.steps.get(stepId);
            stepData.status = status;
            stepData.result = result;
        }
        
        // Update visual status
        switch (status) {
            case 'running':
                statusIndicator.innerHTML = '<i data-lucide="loader" class="w-3 h-3 mr-1 animate-spin"></i>running';
                statusIndicator.className = 'status-indicator inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-600';
                stepNumber.className = 'step-number inline-flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold mr-3';
                break;
                
            case 'completed':
                statusIndicator.innerHTML = '<i data-lucide="check" class="w-3 h-3 mr-1"></i>completed';
                statusIndicator.className = 'status-indicator inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-600';
                stepNumber.className = 'step-number inline-flex items-center justify-center w-8 h-8 bg-green-100 text-green-700 rounded-full text-sm font-semibold mr-3';
                
                // Show result if available
                if (result) {
                    resultContent.textContent = result.substring(0, 500) + (result.length > 500 ? '...' : '');
                    resultContainer.classList.remove('hidden');
                }
                break;
                
            case 'failed':
                statusIndicator.innerHTML = '<i data-lucide="x" class="w-3 h-3 mr-1"></i>failed';
                statusIndicator.className = 'status-indicator inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-600';
                stepNumber.className = 'step-number inline-flex items-center justify-center w-8 h-8 bg-red-100 text-red-700 rounded-full text-sm font-semibold mr-3';
                break;
        }
        
        lucide.createIcons();
    }
    
    updateCurrentStep(stepData) {
        this.currentStepContent.innerHTML = `
            <div class="space-y-2">
                <div class="flex items-center">
                    <span class="text-sm font-mono font-semibold text-gray-900">${stepData.step_id}</span>
                    <span class="ml-2 text-xs text-gray-500">${stepData.step_type}</span>
                </div>
                <p class="text-sm text-gray-700">${stepData.description || 'No description'}</p>
                <div class="flex items-center text-xs text-blue-600">
                    <i data-lucide="loader" class="w-3 h-3 mr-1 animate-spin"></i>
                    Executing...
                </div>
            </div>
        `;
        this.currentStepCard.classList.remove('hidden');
        lucide.createIcons();
    }
    
    clearCurrentStep() {
        this.currentStepCard.classList.add('hidden');
    }
    
    updateStatus(status) {
        const statusConfig = {
            'starting': {
                color: 'bg-yellow-50 text-yellow-700',
                icon: 'loader',
                text: 'Starting execution...',
                animate: true
            },
            'running': {
                color: 'bg-blue-50 text-blue-700',
                icon: 'play',
                text: 'Execution in progress...',
                animate: false
            },
            'completed': {
                color: 'bg-green-50 text-green-700',
                icon: 'check-circle',
                text: 'Execution completed successfully',
                animate: false
            },
            'failed': {
                color: 'bg-red-50 text-red-700',
                icon: 'alert-circle',
                text: 'Execution failed',
                animate: false
            },
            'stopped': {
                color: 'bg-gray-50 text-gray-700',
                icon: 'stop-circle',
                text: 'Execution stopped',
                animate: false
            },
            'connecting': {
                color: 'bg-purple-50 text-purple-700',
                icon: 'loader',
                text: 'Reconnecting...',
                animate: true
            }
        };
        
        const config = statusConfig[status] || statusConfig['starting'];
        const animateClass = config.animate ? 'animate-spin' : '';
        
        this.statusBanner.className = `mt-4 inline-flex items-center px-4 py-2 rounded-lg ${config.color}`;
        this.statusBanner.innerHTML = `
            <i data-lucide="${config.icon}" class="w-4 h-4 mr-2 ${animateClass}"></i>
            <span class="text-sm">${config.text}</span>
        `;
        
        lucide.createIcons();
    }
    
    updateSummary() {
        const completedCount = Array.from(this.steps.values()).filter(step => step.status === 'completed').length;
        const totalCount = this.steps.size;
        const remainingCount = totalCount - completedCount;
        
        this.completedSteps.textContent = completedCount;
        this.remainingSteps.textContent = remainingCount;
        this.stepProgress.textContent = `${completedCount}/${totalCount} steps completed`;
        
        // Add debug logging
        console.log(`Progress: ${completedCount}/${totalCount} steps completed`);
        
        // Don't automatically mark execution as complete just because all steps are done
        // Wait for the explicit execution_completed event from the backend
    }
    
    updateDuration() {
        if (this.startTime) {
            const now = new Date();
            const diff = now - this.startTime;
            const seconds = Math.floor(diff / 1000);
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            
            if (minutes > 0) {
                this.duration.textContent = `${minutes}m ${remainingSeconds}s`;
            } else {
                this.duration.textContent = `${remainingSeconds}s`;
            }
        }
    }
    
    showFinalResult(result) {
        this.finalResultContent.innerHTML = `
            <div class="prose prose-sm max-w-none">
                <pre class="whitespace-pre-wrap text-sm text-gray-900 bg-gray-50 p-3 rounded border">${result}</pre>
            </div>
        `;
        this.finalResultCard.classList.remove('hidden');
    }
    
    showError(errorMessage) {
        this.errorContent.innerHTML = `
            <div class="text-red-800">
                <p class="font-semibold mb-2">Error Details:</p>
                <p class="text-sm">${errorMessage}</p>
            </div>
        `;
        this.errorCard.classList.remove('hidden');
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new ExecutionInterface();
});