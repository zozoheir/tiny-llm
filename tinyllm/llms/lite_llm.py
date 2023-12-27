from typing import Optional, Any

from langchain.adapters import openai
from litellm import OpenAIError, acompletion

from tinyllm.function import Function
from tinyllm.tracing.langfuse_context import observation
from tinyllm.util.helpers import *
from tinyllm.validator import Validator

DEFAULT_LLM_MODEL = 'gpt-3.5-turbo'
DEFAULT_CONTEXT_FALLBACK_DICT = {"gpt-3.5-turbo": "gpt-3.5-turbo-16k"}
LLM_TOKEN_LIMITS = {
    "gpt-3.5-turbo-1106": 16385,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-16k": 16385,
    "gpt-3.5-turbo-instruct": 4096,
    "gpt-3.5-turbo-0613": 4096,
    "gpt-3.5-turbo-16k-0613": 16385,
    "gpt-3.5-turbo-0301": 4096,
    "text-davinci-003": 4096,
    "text-davinci-002": 4096,
    "code-davinci-002": 8001,
    "gpt-4-1106-preview": 4096,
    "gpt-4-vision-preview": 4096,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-0613": 8192,
    "gpt-4-32k-0613": 32768,
    "gpt-4-0314": 8192,
    "gpt-4-32k-0314": 32768
}


class LiteLLMChatInitValidator(Validator):
    system_role: str
    answer_format_prompt: Optional[str]


class LiteLLMChatInputValidator(Validator):
    messages: List[Dict]
    model: Optional[str] = 'gpt-3.5-turbo'
    temperature: Optional[float] = 0
    max_tokens: Optional[int] = 400
    n: Optional[int] = 1
    stream: Optional[bool] = True
    context_window_fallback_dict: Optional[Dict] = DEFAULT_CONTEXT_FALLBACK_DICT


class LiteLLMChatOutputValidator(Validator):
    type: str
    message: dict
    response: Any


class LiteLLM(Function):
    def __init__(self, **kwargs):
        super().__init__(input_validator=LiteLLMChatInputValidator,
                         **kwargs)
        self.generation = None

    @observation(observation_type='generation', input_mapping={'input': 'messages'},
                 output_mapping={'output': 'response'})
    async def run(self, **kwargs):
        tools_args = {}
        if kwargs.get('tools', None) is not None:
            tools_args = {}
            if 'tools' in kwargs:
                tools_args['tools'] = kwargs['tools']
                tools_args['tool_choice'] = kwargs.get('tool_choice', 'auto')

        api_result = await acompletion(
            messages=kwargs['messages'],
            model=kwargs.get('model', DEFAULT_LLM_MODEL),
            temperature=kwargs.get('temperature', 0),
            n=kwargs.get('n', 1),
            max_tokens=kwargs.get('max_tokens', 400),
            context_window_fallback_dict=kwargs.get('context_window_fallback_dict',
                                                    {"gpt-3.5-turbo": "gpt-3.5-turbo-16k"}),
            **tools_args
        )
        model_dump = api_result.model_dump()
        msg_type = 'tool' if model_dump['choices'][0]['finish_reason'] == 'tool_calls' else 'completion'
        message = model_dump['choices'][0]['message']
        return {
            "type": msg_type,
            "message": message,
            "response": model_dump,
            "completion": message['content'],
        }
