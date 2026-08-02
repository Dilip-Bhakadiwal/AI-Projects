import asyncio
import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.agents.query_agent.agent import stream_query_events

logging.basicConfig(level=logging.ERROR)

QUERIES = [
    # 1. Core Tooling Verification
    "Who is the current prime minister of the UK?",
    "What is the exact live price of AAPL right now?",
    "Use python to calculate the standard deviation of these numbers: 10, 12, 23, 23, 16, 23, 21, 16. Do NOT search the web.",
    
    # 2. Database & State Verification
    "Save the current live price of AAPL as a note in the database under the topic AAPL_INTERVIEW.",
    "What did I just save for AAPL_INTERVIEW?",
    
    # 3. Advanced Financial Analysis
    "Run live stats (z-score and RSI) for TSLA.",
    "Give me the raw price history of TSLA from the database."
]

async def run_tests():
    print("=" * 60)
    print("RUNNING MARKETPULSE INTERVIEW TEST SUITE")
    print("=" * 60)
    
    for i, query in enumerate(QUERIES, 1):
        print(f"\n[TEST {i}/{len(QUERIES)}] Query: '{query}'")
        print("-" * 60)
        
        final_answer = ""
        tool_traces = []
        
        try:
            async for chunk_raw in stream_query_events(query):
                chunk_str = chunk_raw.replace('data: ', '').strip()
                if not chunk_str:
                    continue
                    
                try:
                    data = json.loads(chunk_str)
                    if data["type"] == "tool_start":
                        print(f"Tool Started: {data['tool_name']} (Args: {data['tool_input']})")
                    elif data["type"] == "tool_end":
                        output = data["tool_output"]
                        # Truncate long tool outputs for readability
                        if len(output) > 100:
                            output = output[:100] + "..."
                        print(f"Tool Finished: {data['tool_name']} -> {output}")
                    elif data["type"] == "token":
                        final_answer += data["content"]
                        print(data["content"], end="", flush=True)
                    elif data["type"] == "done":
                        print("\n")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"\nFATAL ERROR in Test {i}: {e}")
            
    print("=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
