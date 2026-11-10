from types import SimpleNamespace

from mcp_bridge import mcp_tool_to_ollama, tool_result_text


def test_mcp_tool_to_ollama_preserves_tool_metadata():
    schema = {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
    tool = SimpleNamespace(name="get_weather", description="Get weather", inputSchema=schema)

    assert mcp_tool_to_ollama(tool) == {
        "type": "function",
        "function": {"name": "get_weather", "description": "Get weather", "parameters": schema},
    }


def test_tool_result_text_joins_only_text_blocks():
    result = SimpleNamespace(content=[
        SimpleNamespace(text="first"),
        SimpleNamespace(data="image"),
        SimpleNamespace(text="second"),
    ])

    assert tool_result_text(result) == "first\nsecond"


def test_tool_result_text_without_text_blocks():
    assert tool_result_text(SimpleNamespace(content=[SimpleNamespace(data="image")])) == ""