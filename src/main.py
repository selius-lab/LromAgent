import sys
import os
import asyncio
import logging

# Ensure modules in src/ can be imported easily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import Orchestrator

# Configure logging mapping to console output for demo readability
logging.basicConfig(level=logging.INFO, format='%(message)s')

async def main():
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: Please set the OPENROUTER_API_KEY environment variable.")
        return

    orchestrator = Orchestrator()
    print("=========================================")
    print(" LLM-ROM Architecture PoC v1.0 running")
    print("=========================================")
    print("Type 'exit' to quit.")
    
    while True:
        try:
            user_input = input("\nUser> ")
            if user_input.strip().lower() in ('exit', 'quit'):
                break
            if not user_input.strip():
                continue
            
            # Fire the orchestrator lifecycle
            await orchestrator.run(user_input)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Execution Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
