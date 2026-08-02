import asyncio, os, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
from app.agents.query_agent.agent import stream_query_events, _memory

async def run_test(prompt, session_id):
    print(f'\n=== Testing Prompt: "{prompt}" ===')
    async for event_str in stream_query_events(prompt, session_id):
        if not event_str.startswith('data: '):
            continue
        try:
            data = json.loads(event_str[6:].strip())
            if data['type'] == 'tool_start':
                print(f"[TOOL_START] {data['tool_name']} input: {data['tool_input']}")
            elif data['type'] == 'tool_end':
                print(f"[TOOL_END] {data['tool_name']} output: {data['tool_output']}")
            elif data['type'] == 'token':
                print(data['content'], end='', flush=True)
            elif data['type'] == 'widget':
                print(f"[WIDGET] (Artifact attached)")
            elif data['type'] == 'done':
                print("\n[DONE]")
        except json.JSONDecodeError:
            pass

async def main():
    await run_test('find and tell me top 10 most expensive stocks', 'test_session_1')
    await run_test('update all values of database', 'test_session_2')

if __name__ == '__main__':
    asyncio.run(main())
