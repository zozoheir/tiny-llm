from datetime import datetime
from typing import Optional
import copy

import openai
from langfuse.model import Usage

from tinyllm.functions.function import Function
from tinyllm.functions.llms.open_ai.util.helpers import get_assistant_message, get_user_message, get_openai_api_cost, \
    count_openai_messages_tokens, count_tokens, OPENAI_MODELS_CONTEXT_SIZES
from tinyllm.functions.llms.open_ai.openai_memory import OpenAIMemory
from tinyllm.functions.llms.open_ai.openai_prompt_template import OpenAIPromptTemplate
from tinyllm.functions.validator import Validator
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type
import openai

# Define which exceptions to retry on
def retry_on_openai_exceptions(exception):
    return isinstance(exception,
                      (openai.error.RateLimitError,
                       openai.error.Timeout,
                       openai.error.ServiceUnavailableError,
                       openai.error.APIError))


class OpenAIChatInitValidator(Validator):
    prompt_template: OpenAIPromptTemplate  # Prompt template TYPES are validated on a model by model basis
    with_memory: bool


class OpenAIChatInputValidator(Validator):
    message: str
    llm_name: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]
    call_metadata: Optional[dict]


class OpenAIChatOutputValidator(Validator):
    response: str


class OpenAIChat(Function):
    def __init__(self,
                 prompt_template=OpenAIPromptTemplate(name="standard_prompt_template",
                                                      is_traced=False),
                 llm_name='gpt-3.5-turbo',
                 temperature=0,
                 with_memory=False,
                 max_tokens=400,
                 **kwargs):
        val = OpenAIChatInitValidator(llm_name=llm_name,
                                      temperature=temperature,
                                      prompt_template=prompt_template,
                                      max_tokens=max_tokens,
                                      with_memory=with_memory,
                                      )
        super().__init__(input_validator=OpenAIChatInputValidator,
                         **kwargs)
        self.llm_name = llm_name
        self.temperature = temperature
        self.n = 1
        if 'memory' not in kwargs.keys():
            self.memory = OpenAIMemory(name=f"{self.name}_memory",
                                       is_traced=False)
        else:
            self.memory = kwargs['memory']
        self.prompt_template = prompt_template
        self.with_memory = with_memory
        self.max_tokens = max_tokens
        self.total_cost = 0

    async def add_memory(self, new_memory):
        if self.with_memory is True:
            await self.memory(openai_message=new_memory)

    async def run(self, **kwargs):
        message = kwargs.pop('message')
        llm_name = kwargs['llm_name'] if kwargs['llm_name'] is not None else self.llm_name
        temperature = kwargs['temperature'] if kwargs['temperature'] is not None else self.temperature
        max_tokens = kwargs['max_tokens'] if kwargs['max_tokens'] is not None else self.max_tokens
        call_metadata = kwargs['call_metadata'] if kwargs['call_metadata'] is not None else {}

        messages = await self.process_input_message(openai_message=get_user_message(message))

        api_result = await self.get_completion(
            messages=messages['messages'],
            llm_name=llm_name,
            temperature=temperature,
            n=self.n,
            max_tokens=max_tokens,
            call_metadata=call_metadata,
            generation_name=kwargs.get('generation_name', "Assistant response")
        )
        assistant_response = api_result['choices'][0]['message']['content']
        return {'response': assistant_response}

    async def process_input_message(self,
                                    openai_message,
                                    **kwargs):
        # Format messages into list of dicts for OpenAI
        messages = await self.prompt_template(openai_msg=openai_message,
                                              memories=self.memory.memories)
        # add new memory
        await self.add_memory(new_memory=openai_message)
        return messages

    async def process_output(self, **kwargs):
        await self.add_memory(get_assistant_message(content=kwargs['response']))
        return kwargs

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(min=1, max=30),
        retry=retry_if_exception_type(
            (openai.error.RateLimitError, openai.error.Timeout, openai.error.ServiceUnavailableError))
    )
    async def get_completion(self,
                             llm_name,
                             temperature,
                             n,
                             max_tokens,
                             messages,
                             call_metadata={},
                             generation_name="Assistant response",
                             **kwargs):
        try:
            # Create tracing generation
            self.llm_trace.create_generation(
                name=generation_name,
                model=llm_name,
                prompt=messages,
                startTime=datetime.now(),
            )
            # Call OpenAI API
            api_result = await openai.ChatCompletion.acreate(
                model=llm_name,
                temperature=temperature,
                n=n,
                max_tokens=max_tokens,
                messages=messages,
                **kwargs
            )
            model_parameters = {
                "model": llm_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "n": n,
            }
            # Update tracing generation
            self._update_generation(api_result=api_result, model_parameters=model_parameters,
                                    call_metadata=call_metadata)
            return api_result

        except Exception as e:
            cost = get_openai_api_cost(model=self.llm_name,
                                       completion_tokens=0,
                                       prompt_tokens=count_openai_messages_tokens(messages))
            self.llm_trace.update_generation(
                completion=str({"error": str(e)}),
                metadata={"error": str(e)},
            )
            raise e

    def _update_generation(self,
                           api_result,
                           model_parameters,
                           call_metadata
                           ):
        # We remove message content to properly visualise the API result in metadata
        # api_result_to_log = api_result.copy()
        # api_result_to_log['choices'][0]['message']['content'] = "..."
        dict_to_log = copy.deepcopy(api_result['choices'][0])
        dict_to_log['message']['content'] = "..."

        # Enrich the api result with metadata
        call_metadata['api_result'] = dict_to_log
        call_metadata['cost_summary'] = get_openai_api_cost(model=self.llm_name,
                                                            completion_tokens=api_result["usage"]['completion_tokens'],
                                                            prompt_tokens=api_result["usage"]['prompt_tokens'])
        # call_metadata['api_result'] = api_result_to_log
        call_metadata['cost_summary']['total_cost'] = self.total_cost

        # Extract completion from API result
        if api_result['choices'][0]['finish_reason'] == 'function_call':
            completion = str(api_result['choices'][0]['message']['function_call'])
        else:
            completion = str(api_result['choices'][0]['message']['content'])

        self.llm_trace.update_generation(
            endTime=datetime.now(),
            modelParameters=model_parameters,
            completion=completion,
            metadata=call_metadata,
            usage=Usage(promptTokens=call_metadata['cost_summary']['prompt_tokens'],
                        completionTokens=call_metadata['cost_summary']['completion_tokens'])
        )
        self.total_cost += call_metadata['cost_summary']['request_cost']

    @property
    def available_token_size(self):
        memories_size = count_tokens(self.memory.memories,
                                     header='',
                                     ignore_keys=[])
        prompt_template_size = count_tokens(self.prompt_template.messages,
                                            header='',
                                            ignore_keys=[])
        return OPENAI_MODELS_CONTEXT_SIZES[self.llm_name] - prompt_template_size - memories_size - self.max_tokens - 10


class OpenAIChatStream(OpenAIChat):

    async def run(self, **kwargs):
        message = kwargs.pop('message')
        llm_name = kwargs.get('llm_name', self.llm_name)
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        call_metadata = kwargs.get('call_metadata', {})

        messages = await self.process_input_message(openai_message=get_user_message(message))
        # Create tracing generation
        self.llm_trace.create_generation(
            name=kwargs.get('generation_name', "Assistant response"),
            model=llm_name,
            prompt=messages,
            startTime=datetime.now(),
        )

        response = openai.ChatCompletion.create(
            model=self.llm_name,
            messages=messages['messages'],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True  # this time, we set stream=True
        )

        assistant_response = ""
        for chunk in response:
            if len(chunk['choices']) > 0:
                if 'content' in chunk['choices'][0]['delta']:
                    delta = chunk['choices'][0]['delta']['content']
                    assistant_response += delta
                    yield {'delta': delta}

        self.llm_trace.update_generation(
            completion=assistant_response,
            endTime=datetime.now(),
        )

        yield {'final_message': assistant_response}
