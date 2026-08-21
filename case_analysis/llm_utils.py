import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from uipath_langchain.chat import UiPathChat

llm = UiPathChat(model="anthropic.claude-sonnet-4-5-20250929-v1:0")

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]+?)\s*```")


def strip_json_fence(content: str) -> str:
    content = content.strip()
    fence = _JSON_FENCE_RE.search(content)
    return fence.group(1) if fence else content


def extract_json(content: str) -> dict:
    return json.loads(strip_json_fence(content))


async def llm_call(system_prompt: str, case_data: str, instruction: str) -> dict:
    human_msg = (
        f"{instruction}\n\nCase Data:\n{case_data}\n\n"
        "Return ONLY valid JSON. No markdown fences, no explanation."
    )
    response = await llm.ainvoke([SystemMessage(system_prompt), HumanMessage(human_msg)])
    return extract_json(response.content)


def make_analysis_node(prompt: str, instruction: str, result_key: str):
    """Build a graph node that runs one analysis prompt over the raw case data."""

    async def node(state) -> dict:
        if state.error:
            return {}
        try:
            result = await llm_call(prompt, state.raw_case_data, instruction)
            return {result_key: result}
        except Exception as exc:
            return {result_key: {"_error": str(exc)}}

    return node
