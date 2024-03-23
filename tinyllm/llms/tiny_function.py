import functools
from textwrap import dedent

from pydantic import BaseModel, create_model
from typing import Type, Dict, Any, Union, List

from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

from tinyllm.agent.agent import Agent
from tinyllm.exceptions import MissingBlockException
from tinyllm.llms.lite_llm import json_mode_models, DEFAULT_LLM_MODEL
from tinyllm.util.message import AssistantMessage, Text
from tinyllm.util.parse_util import *


def model_to_string(model) -> str:
    fields = model.__fields__
    field_defs = []
    for field_name, field in fields.items():
        field_type = field.annotation.__name__
        description = getattr(field, 'description', None)
        description = f" | Description: {field.description}" if description else ""
        field_defs.append(
            f"    {field_name}: {field_type}" + description)
    model_prompt = "Model:\n" + "\n".join(field_defs) if field_defs else ""
    return model_prompt


def create_pydantic_model_from_dict(data: Dict[str, Any]) -> BaseModel:
    fields = {key: (type(value), ...) for key, value in data.items()}
    JSONOutput = create_model('JSONOutput', **fields)
    model_instance = JSONOutput(**data)

    return model_instance


def model_to_string(model) -> str:
    fields = model.__fields__
    field_defs = []
    for field_name, field in fields.items():
        field_type = field.annotation.__name__
        description = getattr(field, 'description', None)
        description = f" | Description: {field.description}" if description else ""
        field_defs.append(
            f"    {field_name}: {field_type}" + description)
    model_prompt = "Model:\n" + "\n".join(field_defs) if field_defs else ""
    return model_prompt


def get_system_role(func,
                    output_model,
                    model) -> str:
    system_tag = extract_html(func.__doc__.strip(), tag='system')
    system_prompt = dedent(system_tag[0]) + '\n\n' + dedent("""
    OUTPUT FORMAT
    Your output must be in JSON

    {data_model}

    {enclosing_requirement}

    You must respect all the requirements above.
    """)

    enclosing_requirement = "Your output must be a JSON object enclosed by ```json\n{...}\n```" if model not in json_mode_models else ""

    pydantic_model = model_to_string(output_model) if output_model else None

    data_model_prompt = dedent(f"""
    DATA MODEL
    Your output must respect the following pydantic model:
    {pydantic_model}
    """) if pydantic_model else ""

    final_prompt = system_prompt.format(pydantic_model=pydantic_model,
                                        enclosing_requirement=enclosing_requirement,
                                        data_model=data_model_prompt)
    return final_prompt


default_model_params = {'model': 'gpt-3.5-turbo'}


def tiny_function(output_model: Type[BaseModel] = None,
                  example_manager=None,
                  model_params={'model': DEFAULT_LLM_MODEL}):
    def decorator(func):
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_random_exponential(min=1, max=5),
            retry=retry_if_exception_type((json.JSONDecodeError))
        )
        async def wrapper(*args, **kwargs):

            if model_params['model'] in json_mode_models:
                kwargs['response_format'] = {"type": "json_object"}
            else:
                if example_manager:
                    if len(example_manager.constant_examples)>0:
                        for message in [i.assistant_message for i in example_manager.constant_examples]:
                            for content in message.content:
                                if type(content) == Text:
                                    content.text = f"```json{content.text}```"

            system_role = get_system_role(func=func,
                                          output_model=output_model,
                                          model=model_params['model'])

            prompt = extract_html(func.__doc__.strip(), tag='prompt')
            if len(prompt) == 0:
                assert 'content' in kwargs, "tinyllm_function takes content kwargs by default"
                agent_input_content = kwargs['content']
            else:
                prompt = prompt[0]
                agent_input_content = prompt.format(**kwargs)

            agent = Agent(
                name=func.__name__,
                system_role=system_role,
                example_manager=example_manager
            )

            result = await agent(content=agent_input_content,
                                 **model_params)
            if result['status'] == 'success':
                msg_content = result['output']['response']['choices'][0]['message']['content']
                try:
                    if model_params['model'] in json_mode_models:
                        parsed_output = json.loads(msg_content)
                    else:
                        blocks = extract_block(msg_content, 'json')
                        if not blocks:
                            try:
                                parsed_output = json.loads(msg_content)
                            except json.JSONDecodeError:
                                raise MissingBlockException("Missing JSON block")
                        else:
                            parsed_output = blocks[0]

                    if output_model is None:
                        function_output_model = create_pydantic_model_from_dict(parsed_output)
                    else:
                        function_output_model = output_model(**parsed_output)
                    return {
                        'status': 'success',
                        'output': function_output_model
                    }
                except (ValueError, json.JSONDecodeError) as e:
                    return {"message": "Parsing error", "details": str(e),
                            'status': 'error'}
            else:
                return {
                    'status': 'error',
                    "message": "Agent failed", "details": result['response']['status']}

        return wrapper

    return decorator
