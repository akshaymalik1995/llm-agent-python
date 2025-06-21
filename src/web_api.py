from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from src.agent.agent_core import AgentCore
from src.llm_interface.openai_interface import OpenAIInterface
from src.tooling.tool_registry import ToolRegistry
from src.tooling.tools import GetCurrentTimeTool, ListFilesTool, BrightnessControlTool, LocalLLMTool
from src.config import settings
import threading
import uuid
from datetime import datetime
from typing import Dict, Any
import queue
import time
import json





app = Flask(__name__, template_folder='../web', static_folder='../web/static')
CORS(app)

# Global agent instance for planning
agent_instance = None

# Global execution state management
execution_states: Dict[str, Dict[str, Any]] = {}
execution_queues: Dict[str, queue.Queue] = {}

def initialize_agent():
    global agent_instance
    if not settings.OPENAI_API_KEY: # TODO: Perhaps, we does not need to check it here.
        raise ValueError("OPENAI_API_KEY not found")
    
    llm_interface = OpenAIInterface(
        model_name=settings.DEFAULT_OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY
    )
    
    tool_registry = ToolRegistry()
    # TODO: I shall find a way to make the tools get registered automatically or at once
    tool_registry.register_tool(GetCurrentTimeTool())
    tool_registry.register_tool(ListFilesTool())
    tool_registry.register_tool(BrightnessControlTool())
    tool_registry.register_tool(LocalLLMTool())
    
    agent_instance = AgentCore(llm_interface=llm_interface, tool_registry=tool_registry)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/plan', methods=['POST'])
def create_plan():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if not agent_instance:
            initialize_agent()

        # Create execution plan only
        plan_data = agent_instance._create_execution_plan(query)

        if not plan_data:
            return jsonify({'error': 'Failed to create execution plan'}), 500
        
        # Include tool information in the response
        relevant_tools = plan_data.get('tools', [])
        tools_info = {
            tool_name: agent_instance.tool_registry.get_tool(tool_name).get_tool_info()
            for tool_name in relevant_tools
        }
        
        return jsonify({
            'plan': plan_data,
            'tools': tools_info
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/tools')
def get_available_tools():
    if not agent_instance:
        initialize_agent()
    
    tools = agent_instance.tool_registry.get_all_tools_info()
    return jsonify({'tools': tools})

@app.route('/execute.html')
def execute_page():
    """Serve the execution interface page"""
    return render_template('execute.html')

@app.route('/api/execute', methods=['POST'])
def start_execution():
    """Start executing a plan and return execution ID"""
    try:
        data = request.get_json()
        plan_data = data.get('plan')
        query = data.get('query', '')
        
        if not plan_data:
            return jsonify({'error': 'Plan data is required'}), 400
        
        if not agent_instance:
            initialize_agent()
        
        # Generate unique execution ID
        execution_id = str(uuid.uuid4())
        
        # Initialize execution state
        execution_states[execution_id] = {
            'id': execution_id,
            'query': query,
            'plan': plan_data,
            'status': 'starting',
            'started_at': datetime.now().isoformat(),
            'current_step': None,
            'completed_steps': [],
            'step_results': {},
            'error': None
        }
        
        # Create event queue for this execution
        execution_queues[execution_id] = queue.Queue()
        
        # Start execution in background thread
        thread = threading.Thread(
            target=execute_plan_with_updates,
            args=(execution_id, plan_data),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'success': True,
            'execution_id': execution_id,
            'status': 'started'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/execution/<execution_id>/status')
def get_execution_status(execution_id):
    """Get current execution status and step results"""
    if execution_id not in execution_states:
        return jsonify({'error': 'Execution not found'}), 404
    
    return jsonify(execution_states[execution_id])

@app.route('/api/execution/<execution_id>/stream')
def stream_execution_updates(execution_id):
    """Server-Sent Events stream for real-time execution updates"""
    if execution_id not in execution_queues:
        return jsonify({'error': 'Execution not found'}), 404
    
    def event_stream():
        event_queue = execution_queues[execution_id]
        
        # Send initial state
        if execution_id in execution_states:
            yield f"data: {json.dumps(execution_states[execution_id])}\n\n"
        
        # Stream updates
        while execution_id in execution_queues:
            try:
                # Wait for new updates with timeout
                update = event_queue.get(timeout=1.0)
                yield f"data: {json.dumps(update)}\n\n"
                
                # Clean up completed executions
                if update.get('status') in ['completed', 'failed']:
                    break
                    
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        }
    )

@app.route('/api/execution/<execution_id>', methods=['DELETE'])
def stop_execution(execution_id):
    """Stop a running execution"""
    if execution_id in execution_states:
        execution_states[execution_id]['status'] = 'stopped'
        _send_update(execution_id, {
            'type': 'execution_stopped',
            'status': 'stopped',
            'stopped_at': datetime.now().isoformat()
        })
    
    return jsonify({'success': True})

def execute_plan_with_updates(execution_id: str, plan_data: dict):
    """Execute plan with real-time updates"""
    try:
        # Update status to running
        execution_states[execution_id]['status'] = 'running'
        _send_update(execution_id, {
            'type': 'execution_started',
            'status': 'running'
        })
        
        # Create callback function
        def step_callback(step_id: str, event_type: str, data: dict):
            if step_id == 'execution':
                # Handle execution-level events
                if event_type == 'started':
                    execution_states[execution_id]['status'] = 'running'
                elif event_type == 'completed':
                    execution_states[execution_id]['status'] = 'completed'
                    execution_states[execution_id]['result'] = data.get('result')
                    execution_states[execution_id]['completed_at'] = data.get('completed_at')
                elif event_type == 'failed':
                    execution_states[execution_id]['status'] = 'failed'
                    execution_states[execution_id]['error'] = data.get('error')
                    execution_states[execution_id]['failed_at'] = data.get('failed_at')
                
                _send_update(execution_id, {
                    'type': f'execution_{event_type}',
                    **data
                })
            else:
                # Handle step-level events
                if event_type == 'started':
                    execution_states[execution_id]['current_step'] = step_id
                    _send_update(execution_id, {
                        'type': 'step_started',
                        'step_id': step_id,
                        'current_step': step_id,
                        **data
                    })
                elif event_type in ['completed', 'failed']:
                    # On completion or failed, the status of all steps needs to be updated
                    step_result = {
                        'step_id': step_id,
                        'success': data.get('success', False),
                        'result': data.get('result'),
                        'executed': data.get('executed', False)
                    }
                    
                    execution_states[execution_id]['step_results'][step_id] = step_result
                    if data.get('success'):
                        execution_states[execution_id]['completed_steps'].append(step_id)
                    
                    _send_update(execution_id, {
                        'type': 'step_completed',
                        **step_result
                    })
        
        # Create agent and execute with callback
        agent = AgentCore(
            llm_interface=agent_instance.llm_interface,
            tool_registry=agent_instance.tool_registry
        )
        
        # Execute the plan with callback
        result = agent.execute_plan_with_callback(plan_data, step_callback)
        
    except Exception as e:
        # Error handling remains the same
        error_msg = str(e)
        execution_states[execution_id]['status'] = 'failed'
        execution_states[execution_id]['error'] = error_msg
        execution_states[execution_id]['failed_at'] = datetime.now().isoformat()
        
        _send_update(execution_id, {
            'type': 'execution_failed',
            'status': 'failed',
            'error': error_msg,
            'failed_at': execution_states[execution_id]['failed_at']
        })
    
    finally:
        # Cleanup remains the same
        def cleanup():
            time.sleep(60)
            if execution_id in execution_states:
                del execution_states[execution_id]
            if execution_id in execution_queues:
                del execution_queues[execution_id]
        
        threading.Thread(target=cleanup, daemon=True).start()

def _send_update(execution_id: str, update_data: dict):
    """Send update to execution queue"""
    if execution_id in execution_queues:
        try:
            # Update the main state
            for key, value in update_data.items():
                if key not in ['type']:  # Don't store the 'type' field in state
                    execution_states[execution_id][key] = value
            
            # Send to queue for streaming
            execution_queues[execution_id].put(update_data)
        except Exception as e:
            print(f"Error sending update for execution {execution_id}: {e}")