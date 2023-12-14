from tinyllm.functions.agent.agent import Agent
from tinyllm.functions.agent.toolkit import Toolkit
from tinyllm.functions.llms.llm_store import LLMStore, LLMs

from tinyllm.functions.agent.tool import Tool
from tinyllm.functions.eval.evaluator import Evaluator
from tinyllm.functions.memory.memory import Memory

import asyncio

loop = asyncio.get_event_loop()


class AnswerCorrectnessEvaluator(Evaluator):

    async def run(self, **kwargs):
        completion = kwargs['output']['response']['choices'][0]['message']['content']
        evals = {
            "evals": {
                "correct_answer": 1 if 'january 1st' in completion.lower() else 0
            },
            "metadata": {}
        }
        return evals


def get_user_property(asked_property):
    if asked_property == "name":
        return "Elias"
    elif asked_property == "birthday":
        return "January 1st"


tools = [
    Tool(
        name="get_user_property",
        description="This is the tool you use retrieve ANY information about the user. Use it to answer questions about his birthday and any personal info",
        python_lambda=get_user_property,
        parameters={
            "type": "object",
            "properties": {
                "asked_property": {
                    "type": "string",
                    "enum": ["birthday", "name"],
                    "description": "The specific property the user asked about",
                },
            },
            "required": ["asked_property"],
        },
        is_traced=False,
    )
]
toolkit = Toolkit(
    name='Toolkit',
    tools=tools,
    is_traced=False,
)

llm_store = LLMStore()
manager_llm = llm_store.get_llm_function(
    llm_library=LLMs.LITE_LLM,
    system_role="You are a helpful agent that can answer questions about the user's profile using available tools.",
    name='Manager',
    is_traced=False,
    debug=False
)
tiny_agent = Agent(name='Test: agent stream',
                   manager_llm=manager_llm,
                   toolkit=toolkit,
                   memory=Memory(name='Agent memory', is_traced=False),
                   evaluators=[
                       AnswerCorrectnessEvaluator(
                           name="Eval: correct user info",
                           is_traced=False,
                       ),
                   ],
                   debug=True)

# Run
result = loop.run_until_complete(tiny_agent(user_input="What is the user's birthday?"))
