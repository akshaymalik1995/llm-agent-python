class PlanningInterface {
    constructor() {
        this.initializeElements();
        this.loadAvailableTools();
        this.setupEventListeners();
        
        // Add these properties to store current plan
        this.currentPlan = null;
        this.currentQuery = null;
    }

    initializeElements() {
        this.queryInput = document.getElementById('query');
        this.generateBtn = document.getElementById('generateBtn');
        this.executeBtn = document.getElementById('executeBtn');
        this.executeButtonContainer = document.getElementById('executeButtonContainer');
        this.planContainer = document.getElementById('planContainer');
        this.toolsContainer = document.getElementById('toolsContainer');
        this.metadataCard = document.getElementById('metadataCard');
        this.metadataContent = document.getElementById('metadataContent');

        // Initialize Lucide icons
        lucide.createIcons();
    }

    setupEventListeners() {
        this.generateBtn.addEventListener('click', () => this.generatePlan());
        
        // Add execute button event listener
        this.executeBtn.addEventListener('click', () => this.startExecution());
        
        // Example query buttons
        document.querySelectorAll('.example-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.queryInput.value = btn.dataset.query;
                // Hide execute button when changing query
                this.executeButtonContainer.classList.add('hidden');
            });
        });

        // Enter key support
        this.queryInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.generatePlan();
            }
        });
        
        // Hide execute button when user starts typing new query
        this.queryInput.addEventListener('input', () => {
            this.executeButtonContainer.classList.add('hidden');
        });
    }

    async loadAvailableTools() {
        try {
            const response = await fetch('/api/tools');
            const data = await response.json();
            this.displayTools(data.tools);
        } catch (error) {
            console.error('Error loading tools:', error);
            this.toolsContainer.innerHTML = `
                <div class="text-center text-red-500 py-4">
                    <i data-lucide="alert-circle" class="w-6 h-6 mx-auto mb-2"></i>
                    <p class="text-sm">Error loading tools</p>
                </div>
            `;
            lucide.createIcons();
        }
    }

    displayTools(tools) {
        const toolsHtml = tools.map(tool => `
            <div class="bg-gray-50 rounded-lg p-4 mb-3 last:mb-0">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <h4 class="font-semibold text-gray-900 text-sm">${tool.name}</h4>
                        <p class="text-gray-600 text-xs mt-1 leading-relaxed">${tool.description}</p>
                    </div>
                    <span class="inline-block bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded ml-2 flex-shrink-0">
                        ${Object.keys(tool.input_schema?.properties || {}).length} params
                    </span>
                </div>
            </div>
        `).join('');

        this.toolsContainer.innerHTML = toolsHtml;
    }

    async generatePlan() {
        const query = this.queryInput.value.trim();
        if (!query) {
            this.showError('Please enter a query');
            return;
        }

        this.generateBtn.disabled = true;
        this.generateBtn.innerHTML = '<i data-lucide="loader" class="inline w-5 h-5 mr-2 animate-spin"></i>Generating Plan...';
        
        // Hide execute button while generating new plan
        this.executeButtonContainer.classList.add('hidden');
        
        this.planContainer.innerHTML = `
            <div class="text-center text-blue-600 py-12">
                <i data-lucide="brain-circuit" class="w-16 h-16 mx-auto mb-4 animate-pulse"></i>
                <p class="text-lg mb-2">Creating execution plan...</p>
                <p class="text-sm text-gray-500">This may take a few moments</p>
            </div>
        `;
        lucide.createIcons();

        try {
            const response = await fetch('/api/plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });

            const data = await response.json();

            if (data.success) {
                // Store the plan and query for execution
                this.currentPlan = data.plan;
                this.currentQuery = query;
                
                this.displayPlan(data.plan, query);
                this.displayMetadata(data.plan);
                
                // Show execute button after successful plan generation
                this.executeButtonContainer.classList.remove('hidden');
                
                // Add a subtle notification that plan is ready for execution
                this.showPlanReadyNotification();
            } else {
                this.showError(data.error || 'Failed to generate plan');
            }
        } catch (error) {
            console.error('Error generating plan:', error);
            this.showError('Network error occurred');
        } finally {
            this.generateBtn.disabled = false;
            this.generateBtn.innerHTML = '<i data-lucide="brain-circuit" class="inline w-5 h-5 mr-2"></i>Generate Execution Plan';
            lucide.createIcons();
        }
    }

    displayPlan(planData, originalQuery) {
        const steps = planData.plan || [];
        
        const stepsHtml = steps.map((step, index) => {
            const stepNumber = index + 1;
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
                <div class="border border-gray-200 rounded-lg p-4 mb-4 last:mb-0">
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center">
                            <span class="inline-flex items-center justify-center w-8 h-8 bg-gray-100 text-gray-700 rounded-full text-sm font-semibold mr-3">
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
                    </div>
                    
                    ${this.renderStepDetails(step)}
                </div>
            `;
        }).join('');

        this.planContainer.innerHTML = `
            <div class="mb-6">
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                    <h3 class="font-semibold text-blue-900 mb-2 flex items-center">
                        <i data-lucide="target" class="w-4 h-4 mr-2"></i>
                        Original Query
                    </h3>
                    <p class="text-blue-800 text-sm">${originalQuery}</p>
                </div>
                
                <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                    <h3 class="font-semibold text-green-900 mb-2 flex items-center">
                        <i data-lucide="lightbulb" class="w-4 h-4 mr-2"></i>
                        Planning Reasoning
                    </h3>
                    <p class="text-green-800 text-sm">${planData.reasoning || 'No reasoning provided'}</p>
                </div>
            </div>
            
            <div class="space-y-0">
                <h3 class="font-semibold text-gray-900 mb-4 flex items-center">
                    <i data-lucide="list-ordered" class="w-4 h-4 mr-2"></i>
                    Execution Steps (${steps.length})
                </h3>
                ${stepsHtml}
            </div>
        `;
        
        lucide.createIcons();
    }

    renderStepDetails(step) {
        let details = '';
        
        if (step.type === 'llm' && step.prompt) {
            details += `
                <div class="mt-3 p-3 bg-blue-50 rounded-md">
                    <h5 class="text-xs font-semibold text-blue-900 mb-2">LLM Prompt:</h5>
                    <pre class="text-xs text-blue-800 whitespace-pre-wrap">${step.prompt}</pre>
                </div>
            `;
        }
        
        if (step.type === 'tool') {
            details += `
                <div class="mt-3 p-3 bg-green-50 rounded-md">
                    <h5 class="text-xs font-semibold text-green-900 mb-2">Tool: ${step.tool_name}</h5>
                    <pre class="text-xs text-green-800">${JSON.stringify(step.arguments || {}, null, 2)}</pre>
                </div>
            `;
        }
        
        if (step.type === 'if') {
            details += `
                <div class="mt-3 p-3 bg-yellow-50 rounded-md">
                    <h5 class="text-xs font-semibold text-yellow-900 mb-2">Condition:</h5>
                    <pre class="text-xs text-yellow-800">${step.condition}</pre>
                    <p class="text-xs text-yellow-700 mt-1">Jump to: <span class="font-mono">${step.goto_id}</span></p>
                </div>
            `;
        }
        
        if (step.type === 'goto') {
            details += `
                <div class="mt-3 p-3 bg-purple-50 rounded-md">
                    <h5 class="text-xs font-semibold text-purple-900 mb-2">Jump to:</h5>
                    <span class="text-xs text-purple-800 font-mono">${step.goto_id}</span>
                </div>
            `;
        }
        
        if (step.output_name) {
            details += `
                <div class="mt-3 p-3 bg-gray-50 rounded-md">
                    <h5 class="text-xs font-semibold text-gray-900 mb-1">Output Variable:</h5>
                    <span class="text-xs text-gray-700 font-mono bg-white px-2 py-1 rounded border">${step.output_name}</span>
                </div>
            `;
        }
        
        if (step.input_refs && step.input_refs.length > 0) {
            details += `
                <div class="mt-3 p-3 bg-gray-50 rounded-md">
                    <h5 class="text-xs font-semibold text-gray-900 mb-2">Input References:</h5>
                    <div class="flex flex-wrap gap-1">
                        ${step.input_refs.map(ref => `
                            <span class="text-xs text-gray-700 font-mono bg-white px-2 py-1 rounded border">${ref}</span>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        return details;
    }

    displayMetadata(planData) {
        const steps = planData.plan || [];
        const stepTypes = {};
        steps.forEach(step => {
            stepTypes[step.type] = (stepTypes[step.type] || 0) + 1;
        });

        const metadataHtml = `
            <div class="space-y-4">
                <div>
                    <h4 class="text-sm font-semibold text-gray-900 mb-2">Plan Statistics</h4>
                    <div class="grid grid-cols-2 gap-2 text-sm">
                        <div class="bg-gray-50 p-2 rounded">
                            <span class="text-gray-600">Total Steps:</span>
                            <span class="font-semibold text-gray-900">${steps.length}</span>
                        </div>
                        <div class="bg-gray-50 p-2 rounded">
                            <span class="text-gray-600">Max Iterations:</span>
                            <span class="font-semibold text-gray-900">${planData.max_iterations || 'Not set'}</span>
                        </div>
                    </div>
                </div>
                
                <div>
                    <h4 class="text-sm font-semibold text-gray-900 mb-2">Step Types</h4>
                    <div class="space-y-1">
                        ${Object.entries(stepTypes).map(([type, count]) => `
                            <div class="flex justify-between text-xs">
                                <span class="text-gray-600 capitalize">${type}:</span>
                                <span class="font-semibold">${count}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        this.metadataContent.innerHTML = metadataHtml;
        this.metadataCard.classList.remove('hidden');
    }

    showError(message) {
        this.planContainer.innerHTML = `
            <div class="text-center text-red-600 py-12">
                <i data-lucide="alert-circle" class="w-16 h-16 mx-auto mb-4"></i>
                <p class="text-lg mb-2">Error</p>
                <p class="text-sm text-gray-600">${message}</p>
            </div>
        `;
        this.metadataCard.classList.add('hidden');
        lucide.createIcons();
    }

    showPlanReadyNotification() {
        // Create a temporary notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg shadow-lg z-50';
        notification.innerHTML = `
            <div class="flex items-center">
                <i data-lucide="check-circle" class="w-5 h-5 mr-2"></i>
                <span>Plan ready for execution!</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        lucide.createIcons();
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    async startExecution() {
        if (!this.currentPlan) {
            this.showError('No plan available for execution');
            return;
        }

        // Confirm execution with user
        const confirmed = confirm('Are you ready to execute this plan? This will start the actual execution process.');
        if (!confirmed) {
            return;
        }

        this.executeBtn.disabled = true;
        this.executeBtn.innerHTML = '<i data-lucide="loader" class="inline w-4 h-4 mr-2 animate-spin"></i>Starting...';

        try {
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    plan: this.currentPlan,
                    query: this.currentQuery
                })
            });

            const data = await response.json();

            if (data.success) {
                // Redirect to execution page with execution ID
                window.location.href = `/execute.html?id=${data.execution_id}`;
            } else {
                this.showError(data.error || 'Failed to start execution');
            }
        } catch (error) {
            console.error('Error starting execution:', error);
            this.showError('Network error occurred while starting execution');
        } finally {
            this.executeBtn.disabled = false;
            this.executeBtn.innerHTML = '<i data-lucide="play" class="inline w-4 h-4 mr-2"></i>Execute Plan';
            lucide.createIcons();
        }
    }
}

// Initialize the interface when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new PlanningInterface();
});