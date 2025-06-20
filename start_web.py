#!/usr/bin/env python3
"""
Web interface startup script for LLM Agent Planning Interface
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.web_api import app

if __name__ == '__main__':
    print("Starting LLM Agent Planning Interface...")
    print("Open your browser to: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)