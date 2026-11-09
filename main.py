import asyncio
import os
from ollama import AsyncClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from system_content import SYSTEM_CONTENT
from mcp_bridge import mcp_tool_to_ollama, tool_result_text

MODEL_NAME = ''
MCP_SERVER_URL = os.environ.get('MCP_SERVER_URL', 'http://127.0.0.1:8000/mcp')

client = AsyncClient()


async def stream_reply(messages):
    full_reply = ''
    try:
        stream = await client.chat(model=MODEL_NAME, messages=messages, stream=True)
        async for chunk in stream:
            piece = chunk['message']['content']
            print(piece, end='', flush=True)
            full_reply += piece
    except Exception as e:
        print(f"Error: {e}", end='')
    print()
    return full_reply


async def chat_loop(session, ollama_tools):
    messages = [
        {
            'role': 'system',
            'content': SYSTEM_CONTENT
        }
    ]
    print(f'{MODEL_NAME} MCP chat. Type "exit" to quit.')
    while True:
        user_input = await asyncio.to_thread(input, 'You: ')
        if user_input == 'exit':
            print('Bye')
            break
        messages.append({
            'role': 'user',
            'content': user_input
        })
        response = await client.chat(model=MODEL_NAME, messages=messages, stream=False, tools=ollama_tools)
        messages.append(response.message.model_dump(exclude_none=True))
        if response.message.tool_calls:
            for tool_call in response.message.tool_calls:
                result = await session.call_tool(tool_call.function.name, tool_call.function.arguments)
                messages.append({
                    'role': 'tool',
                    'name': tool_call.function.name,
                    'content': tool_result_text(result)
                })
            print('\nAgent: ', end='', flush=True)
            reply = await stream_reply(messages)
            messages.append({
                'role': 'assistant',
                'content': reply
            })
        else:
            print('\nAgent:', {response.message.content})

async def main():
    try:
        async with streamable_http_client(MCP_SERVER_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                mcp_tools = (await session.list_tools()).tools
                ollama_tools = [mcp_tool_to_ollama(tool) for tool in mcp_tools]
                await chat_loop(session, ollama_tools)
    except Exception as e:
        print(f'Connection error ({MCP_SERVER_URL}): {e}')

if __name__ == '__main__':
    asyncio.run(main())

