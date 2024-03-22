import os

from tinyllm.examples.example_manager import ExampleManager
from tinyllm.llms.lite_llm import DEFAULT_LLM_MODEL, LLM_TOKEN_LIMITS, DEFAULT_CONTEXT_FALLBACK_DICT
from tinyllm.memory.memory import Memory
from tinyllm.util.helpers import get_openai_message, count_tokens, OPENAI_MODELS_CONTEXT_SIZES
import datetime as dt

from tinyllm.util.message import SystemMessage, UserMessage, Text, AssistantMessage


class PromptManager:
    """
    This class is responsible for formatting the prompt for the LLM and managing:
    - model (to avoid exceeding the token limit)
    - max_tokens (based on the expected completion size)
    """

    def __init__(self,
                 system_role: str,
                 example_manager: ExampleManager,
                 memory: Memory,
                 answer_formatting_prompt: str = None,
                 is_time_aware: bool = True, ):
        self.system_role = system_role
        self.example_manager = example_manager
        self.memory = memory
        self.answer_formatting_prompt = answer_formatting_prompt.strip() if answer_formatting_prompt is not None else None
        self.is_time_aware = is_time_aware

    async def format_messages(self, message):
        system_content = self.system_role if self.is_time_aware is False else self.system_role + '\n\n\n<Current time: ' + \
                                                                              str(dt.datetime.utcnow()).split('.')[
                                                                                  0] + '>'
        system_msg = SystemMessage(system_content)
        memories = [] if self.memory is None else await self.memory.get_memories()
        examples = []

        if self.example_manager is not None:
            examples += self.example_manager.constant_examples
            if self.example_manager.example_selector is not None and message['role'] == 'user':
                best_examples = await self.example_manager.example_selector(input=message['content'])
                for good_example in best_examples['output']['best_examples']:
                    examples.append(UserMessage(good_example['user']))
                    examples.append(AssistantMessage(good_example['assistant']))

        answer_format_msg = [UserMessage(self.answer_formatting_prompt).to_dict()] if self.answer_formatting_prompt is not None else []

        messages = [system_msg] + memories + examples + answer_format_msg + [message]
        return messages

    async def prepare_llm_request(self,
                                  message,
                                  **kwargs):

        messages = await self.format_messages(message)
        prompt_to_completion_multiplier = kwargs.pop('prompt_to_completion_multiplier', 1)
        input_size = count_tokens(messages)
        max_tokens, model = self.get_run_config(model=kwargs.get('model', DEFAULT_LLM_MODEL),
                                                prompt_to_completion_multiplier=prompt_to_completion_multiplier,
                                                input_size=input_size)

        kwargs['messages'] = messages
        kwargs['max_tokens'] = max_tokens
        kwargs['model'] = model
        return kwargs

    async def add_memory(self,
                         message):
        if self.memory is not None:
            await self.memory(message=message)

    @property
    async def size(self):
        messages = await self.prepare_llm_request(message=get_openai_message(role='user', content=''))
        return count_tokens(messages)

    def get_run_config(self, input_size, prompt_to_completion_multiplier, model):
        model_token_limit = LLM_TOKEN_LIMITS[model]
        context_size_available = model_token_limit - input_size

        max_tokens = min(max(500, input_size * prompt_to_completion_multiplier), 4096)
        expected_total_size = input_size + max_tokens
        if expected_total_size / context_size_available > 0.9:
            model = DEFAULT_CONTEXT_FALLBACK_DICT[model]

        return int(max_tokens), model
