import asyncio

from tinyllm.functions.agent.agent_stream import AgentStream
from tinyllm.functions.agent.toolkit import Toolkit
from tinyllm.functions.llms.llm_store import LLMStore, LLMs

from tinyllm.functions.agent.tool import Tool
from tinyllm.functions.eval.evaluator import Evaluator

loop = asyncio.get_event_loop()

class AnswerCorrectnessEvaluator(Evaluator):
    async def run(self, **kwargs):
        completion = kwargs['output']['output']['completion']

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
    )
]
toolkit = Toolkit(
    name='Toolkit',
    tools=tools
)

llm_store = LLMStore()

async def run_agent_stream():
    manager_llm_stream = llm_store.get_llm_function(
        llm_library=LLMs.LITE_LLM_STREAM,
        system_role="You are a helpful agent that can answer questions about the user's profile using available tools.",
        name='Tinyllm manager',
        debug=False,
    )

    tiny_agent = AgentStream(name='Test: agent stream',
                             manager_llm=manager_llm_stream,
                             toolkit=toolkit,
                             evaluators=[
                                 AnswerCorrectnessEvaluator(
                                     name="Functional call corrector",
                                     is_traced=False,
                                 ),
                             ],
                             debug=True)

    msgs = []
    async for message in tiny_agent(user_input="What is the user's birthday?"):
        msgs.append(message)
    return msgs

result = loop.run_until_complete(run_agent_stream())
