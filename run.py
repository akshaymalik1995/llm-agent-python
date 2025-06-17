from src.main import run_agent
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the AI Agent for a single query via run.py.")
    parser.add_argument("query", type=str, help="The query to send to the agent.")
    args = parser.parse_args()

    run_agent(args.query)