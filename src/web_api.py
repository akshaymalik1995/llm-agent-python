from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from src.agent.agent_core import AgentCore
from src.llm_interface.openai_interface import OpenAIInterface
from src.tooling.tool_registry import ToolRegistry
from src.tooling.tools import GetCurrentTimeTool, ListFilesTool, BrightnessControlTool, LocalLLMTool
from src.config import settings
import json


app = Flask(__name__, template_folder='../web', static_folder='../web/static')
CORS(app)

# Global agent instance for planning
agent_instance = None

def initialize_agent():
    global agent_instance
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found")
    
    llm_interface = OpenAIInterface(
        model_name=settings.DEFAULT_OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY
    )
    
    tool_registry = ToolRegistry()
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

        # Create execution plan only (don't execute)
        plan_data = agent_instance._create_execution_plan(query)

        if not plan_data:
            return jsonify({'error': 'Failed to create execution plan'}), 500
        
        return jsonify({
            'success': True,
            'plan': plan_data,
            'query': query
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/tools')
def get_available_tools():
    if not agent_instance:
        initialize_agent()
    
    tools = agent_instance.tool_registry.get_all_tools_info()
    return jsonify({'tools': tools})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)