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
import json
import uuid
from typing import Any, Callable, Optional, Type, Dict

from py2neo import Node, Relationship
from pydantic import field_validator

from tinyllm import APP
from tinyllm.exceptions import InvalidStateTransition
from tinyllm.state import States, ALLOWED_TRANSITIONS
from tinyllm.functions.validator import Validator
from inspect import iscoroutinefunction


class FunctionInitValidator(Validator):
    name: str
    input_validator: Optional[Type[Validator]]
    output_validator: Optional[Type[Validator]]
    run_function: Optional[Callable]
    parent_id: Optional[str]
    verbose: bool

    @field_validator('run_function')
    def validate_run_function(cls, v):
        if v is not None and not iscoroutinefunction(v):
            raise ValueError('run_function must be an async function')
        return v


class Function:

    def __init__(self,
                 name,
                 user=None,
                 input_validator=Validator,
                 output_validator=Validator,
                 run_function=None,
                 parent_id=None,
                 verbose=True):
        w = FunctionInitValidator(
            name=name,
            input_validator=input_validator,
            output_validator=output_validator,
            run_function=run_function,
            parent_id=parent_id,
            verbose=verbose)
        self.user = user
        self.function_id = str(uuid.uuid4())
        self.logger = APP.logging['default']
        self.name = name

        self.input_validator = input_validator
        self.output_validator = output_validator
        self.run_function = run_function if run_function is not None else self.run
        self.parent_id = parent_id
        self.verbose = verbose
        self.logs = ""
        self.state = None
        self.transition(States.INIT)
        self.error_message = None
        self.input = None
        self.output = None
        self.processed_output = None

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
            output = await self.validate_output(**output)
            self.transition(States.PROCESSING_OUTPUT)
            output = await self.process_output(**output)
            self.processed_output = output
            self.transition(States.COMPLETE)
            try:
                await self.push_to_db()
            except Exception as e:
                self.log(f"Error pushing to db: {e}", level='error')
            return output
        except Exception as e:
            self.error_message = str(e)
            self.transition(States.FAILED,
                            msg=str(e))
            try:
                await self.push_to_db()
            except Exception as e:
                self.log(f"Error pushing to db: {e}", level='error')

    def transition(self, new_state: States,
                   msg: Optional[str] = None):
        if new_state not in ALLOWED_TRANSITIONS[self.state]:
            raise InvalidStateTransition(self, f"Invalid state transition from {self.state} to {new_state}")
        self.state = new_state
        self.log(f"transition to: {new_state}" + (f" ({msg})" if msg is not None else ""))

    def log(self, message, level='info'):
        if self.logger is None or self.verbose is False:
            return
        log_message = f"[{self.name}] {message}"
        self.logs += '\n' + log_message
        if level == 'error':
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)

    async def validate_input(self, **kwargs):
        return self.input_validator(**kwargs).model_dump()

    async def validate_output(self, **kwargs):
        return self.output_validator(**kwargs).model_dump()

    def create_function_node(self):
        attributes_dict = vars(self)
        attributes_dict['class'] = self.__class__.__name__
        attributes_dict = {key: str(value) for key, value in attributes_dict.items()}
        to_ignore = ['input_validator', 'output_validator', 'run_function', 'logger']
        attributes_dict = {str(key): str(value) for key, value in attributes_dict.items() if value not in to_ignore}
        return Node(self.name, **attributes_dict)

    async def push_to_db(self):
        self.log("Pushing to db")
        included_specifically = APP.config['DB_FUNCTIONS_LOGGING']['DEFAULT'] is True and self.name in \
                                APP.config['DB_FUNCTIONS_LOGGING']['INCLUDE']
        included_by_default = APP.config['DB_FUNCTIONS_LOGGING']['DEFAULT'] is True and self.name not in \
                              APP.config['DB_FUNCTIONS_LOGGING']['EXCLUDE']
        if included_specifically or included_by_default:
            node = self.create_function_node()
            APP.graph_db.create(node)


    async def run(self, **kwargs) -> Any:
        pass

    async def process_output(self, **kwargs):
        return kwargs
