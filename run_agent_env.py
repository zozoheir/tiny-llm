import asyncio
import os

import openai
from langfuse.model import CreateScore

from tinyllm.functions.environment.environment import TinyEnvironment
from tinyllm.functions.environment.llm_store import LLMStore
from tinyllm.functions.environment.tool_store import ToolStore
from tinyllm.functions.eval.evaluator import Evaluator

openai.api_key = os.environ['OPENAI_API_KEY']


class AnswerCorrectnessEvaluator(Evaluator):

    async def run(self, **kwargs):

        evals = {
            "evals": {
            },
            "metadata": {}
        }
        completion = kwargs['output']['completion']
        if kwargs['processed_output']['type'] == 'tool':
            evals = {
                "evals": {
                    "functional_call": 1 if completion['name'] == 'get_user_property' else 0,
                },
                "metadata": {}
            }

        return evals


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_user_property",
            "description": "This is the tool you use retrieve ANY information about the user. Use it to answer questions about his birthday and any personal info",
            "parameters": {
                "type": "object",
                "properties": {
                    "asked_property": {
                        "type": "string",
                        "enum": ["birthday", "name"],
                        "description": "The specific property the user asked about",
                    },
                },
                "required": ["asked_property"],
            }
        }
    },
]


def get_user_property(asked_property):
    if asked_property == "name":
        return "Elias"
    elif asked_property == "birthday":
        return "January 1st"


tools_callables = {'get_user_property': get_user_property}
tool_store = ToolStore(tools=tools,
                       tools_callables=tools_callables)
llm_store = LLMStore(tool_store=tool_store)
# An environment = 1 manager for user interactions, 1 tool store, 1 llm store
tiny_env = TinyEnvironment(name='TinyLLM Environment',
                           llm_store=llm_store,
                           tool_store=tool_store,
                           manager_llm='lite_llm_stream',
                           manager_args={
                               'name': 'manager',
                               'debug': False,
                               'evaluators': [
                                   AnswerCorrectnessEvaluator(
                                       name="Answer Correctness Evaluator",
                                       is_traced=False,
                                   ),
                               ]
                           },
                           debug=True)


async def run_env():
    msgs = []
    async for message in tiny_env(user_input="What is the user's birthday?"):
        msgs.append(message)


result = asyncio.run(run_env())
print(result)
