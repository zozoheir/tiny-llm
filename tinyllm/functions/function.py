"""
Function is the building block of tinyllm. A function has 4 main components:
    1. A name: required
    2. An input validator: optional, but recommended
    3. An output validator: optional, but recommended
    4. A run function: required

- Chains and Concurrent inherit from Functions.
- When creating Functions or child classes, the above requirements apply
- Functions, Chains, and Concurrents and
"""
import datetime
import datetime as dt
import uuid
from typing import Any, Callable, Optional, Type, Dict


import pytz
from py2neo import Node, Relationship
from pydantic import validator as field_validator

from tinyllm import APP
from tinyllm.exceptions import InvalidStateTransition
from tinyllm.llm_trace import LLMTrace
from tinyllm.state import States, ALLOWED_TRANSITIONS
from tinyllm.functions.validator import Validator
from inspect import iscoroutinefunction

def pretty_print(value):
    if isinstance(value, dict):
        return {key: pretty_print(val) for key, val in value.items()}
    elif isinstance(value, list):
        return [pretty_print(val) for val in value]
    else:
        return value


class FunctionInitValidator(Validator):
    name: str
    input_validator: Optional[Type[Validator]]
    output_validator: Optional[Type[Validator]]
    run_function: Optional[Callable]
    is_traced: bool

    @field_validator("run_function")
    def validate_run_function(cls, v):
        if v is not None and not iscoroutinefunction(v):
            raise ValueError("run_function must be an async function")
        return v




class Function:
    def __init__(
            self,
            name,
            user_id=None,
            input_validator=Validator,
            output_validator=Validator,
            run_function=None,
            is_traced=True,
            required=True,
            llm_trace: LLMTrace =None,
    ):
        w = FunctionInitValidator(
            name=name,
            input_validator=input_validator,
            output_validator=output_validator,
            run_function=run_function,
            is_traced=is_traced,
        )
        self.user = user_id
        self.init_timestamp = dt.datetime.now(pytz.UTC).isoformat()
        self.function_id = str(uuid.uuid4())
        self.logger = APP.logging["default"]
        self.name = name

        self.input_validator = input_validator
        self.output_validator = output_validator
        self.run_function = run_function if run_function is not None else self.run
        self.is_traced = is_traced
        self.required = required
        self.logs = ""
        self.state = None
        self.transition(States.INIT)
        self.error_message = None
        self.input = None
        self.output = None
        self.processed_output = None
        if llm_trace is None:
            self.llm_trace = LLMTrace(
                is_traced=is_traced,
                name=self.name,
                userId="test",
            )
        else:
            self.llm_trace = llm_trace


    @property
    def graph_state(self):
        """Returns the state of the current function."""
        return {self.name: self.state}

    async def __call__(self, **kwargs):
        try:
            self.input = kwargs
            self.transition(States.INPUT_VALIDATION)
            kwargs = await self.validate_input(**kwargs)
            self.transition(States.RUNNING)
            output = await self.run_function(**kwargs)
            self.output = output
            self.transition(States.OUTPUT_VALIDATION)
            self.output = await self.validate_output(**output)
            self.transition(States.PROCESSING_OUTPUT)
            self.output = await self.process_output(**output)
            self.processed_output = self.output
            self.transition(States.COMPLETE)
            return self.output
        except Exception as e:
            await self.handle_exception(e)

    async def handle_exception(self, e):
        self.error_message = str(e)
        self.transition(States.FAILED, msg=str(e))
        if self.required is True:
            raise e

    def transition(self, new_state: States, msg: Optional[str] = None):
        if new_state not in ALLOWED_TRANSITIONS[self.state]:
            raise InvalidStateTransition(
                self, f"Invalid state transition from {self.state} to {new_state}"
            )
        self.state = new_state
        log_level = "error" if new_state == States.FAILED else "info"
        self.log(
            f"transition to: {new_state}" + (f" ({msg})" if msg is not None else ""),
            level=log_level,
        )

    def log(self, message, level="info"):
        if self.logger is None :
            return
        log_message = f"[{self.name}][{self.function_id}] {message}"
        self.logs += "\n" + log_message
        if level == "error":
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)

    async def validate_input(self, **kwargs):
        return self.input_validator(**kwargs).dict()

    async def validate_output(self, **kwargs):
        return self.output_validator(**kwargs).dict()

    async def run(self, **kwargs) -> Any:
        pass

    async def process_output(self, **kwargs):
        return kwargs
