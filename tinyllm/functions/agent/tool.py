import datetime as dt
from typing import Dict, Callable

from langfuse.model import CreateSpan, UpdateSpan

from tinyllm.function import Function
from tinyllm.functions.helpers import get_openai_message
from tinyllm.validator import Validator


class ToolInitValidator(Validator):
    description: str
    parameters: dict
    python_lambda: Callable

class ToolInputValidator(Validator):
    arguments: Dict

class Tool(Function):
    def __init__(self,
                 description,
                 parameters,
                 python_lambda,
                 **kwargs):
        ToolInitValidator(
            description=description,
            parameters=parameters,
            python_lambda=python_lambda,
        )
        super().__init__(
            input_validator=ToolInputValidator,
            **kwargs)
        self.description = description
        self.parameters = parameters
        self.python_lambda = python_lambda

    def as_dict(self):
        return {
            "type": "function",
            "function":{
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    async def run(self, **kwargs):
        if self.trace:
            span = self.trace.span(
                CreateSpan(
                    name="Tool: " + self.name,
                    input=kwargs,
                    startTime=dt.datetime.utcnow()
                )
            )
        tool_response = self.python_lambda(**kwargs['arguments'])
        if self.trace:
            span.update(
                UpdateSpan(
                    output=tool_response,
                    endTime=dt.datetime.now())
            )

        return {'response': get_openai_message(role='tool', content=tool_response, name=self.name)}

