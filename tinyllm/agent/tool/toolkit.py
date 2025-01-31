import asyncio
from typing import List, Dict

from tinyllm.agent.tool.tool import Tool
from tinyllm.function import Function
from tinyllm.tracing.langfuse_context import observation
from tinyllm.validator import Validator


class ToolkitInputValidator(Validator):
    tool_calls: List[Dict]


class ToolkitOutputValidator(Validator):
    tool_results: List[Dict]


class Toolkit(Function):

    def __init__(self,
                 tools: List[Tool],
                 **kwargs):
        super().__init__(
            input_validator=ToolkitInputValidator,
            **kwargs)
        self.tools = tools

    @observation(observation_type='span', input_mapping={'input': 'tool_calls'})
    async def run(self,
                  **kwargs):
        tasks = []

        for tool_call in kwargs['tool_calls']:
            name = tool_call['name']
            tool = [tool for tool in self.tools if tool.name == name][0]
            tasks.append(tool(**tool_call['arguments']))

        results = await asyncio.gather(*tasks)
        tool_results = [result['output']['response'] for result in results]
        return {'tool_results': tool_results,
                'tool_calls': kwargs['tool_calls']}

    def as_dict_list(self):
        return [tool.as_dict() for tool in self.tools]
