import datetime as dt
import traceback
import uuid
from typing import Any, Optional, Type

import pytz

from smartpy.utility.log_util import getLogger
from smartpy.utility.py_util import get_exception_info
from tinyllm.exceptions import InvalidStateTransition
from tinyllm import langfuse_client, tinyllm_config
from tinyllm.state import States, ALLOWED_TRANSITIONS
from tinyllm.tracing.langfuse_context import observation
from tinyllm.validator import Validator
from tinyllm.util.fallback_strategy import fallback_decorator


def pretty_print(value):
    if isinstance(value, dict):
        return {key: pretty_print(val) for key, val in value.items()}
    elif isinstance(value, list):
        return [pretty_print(val) for val in value]
    else:
        return value


class FunctionInitValidator(Validator):
    user_id: Optional[str]
    input_validator: Optional[Type[Validator]]
    output_validator: Optional[Type[Validator]]
    processed_output_validator: Optional[Type[Validator]] = None
    run_evaluators: Optional[list]
    processed_output_evaluators: Optional[list]
    dataset_name: Optional[str]
    stream: Optional[bool]


class Function:

    def __init__(
            self,
            name=None,
            user_id=None,
            input_validator=Validator,
            output_validator=Validator,
            processed_output_validator=Validator,
            run_evaluators=[],
            processed_output_evaluators=[],
            required=True,
            stream=False,
            fallback_strategies={},

    ):
        FunctionInitValidator(
            user_id=user_id,
            input_validator=input_validator,
            output_validator=output_validator,
            processed_output_validator=processed_output_validator,
            run_evaluators=run_evaluators,
            processed_output_evaluators=processed_output_evaluators,
            stream=stream,
        )
        self.parent_observation = None

        self.user_id = str(user_id)
        self.init_timestamp = dt.datetime.now(pytz.UTC).isoformat()
        self.function_id = str(uuid.uuid4())
        self.logger = getLogger(__name__)
        if name is None:
            self.name = self.__class__.__name__
        else:
            self.name = name

        self.input_validator = input_validator
        self.output_validator = output_validator
        self.processed_output_validator = processed_output_validator
        self.required = required
        self.logs = ""
        self.state = None
        self.transition(States.INIT)
        self.input = None
        self.output = None
        self.processed_output = None
        self.current_observation = None
        self.run_evaluators = run_evaluators
        self.processed_output_evaluators = processed_output_evaluators
        for evaluator in self.processed_output_evaluators:
            evaluator.prefix = 'proc:'

        self.cache = {}
        self.generation = None
        self.fallback_strategies = fallback_strategies
        self.stream = stream
        self.observation = None

    @observation('span')
    @fallback_decorator
    async def __call__(self, **kwargs):
        try:
            # Validate input
            self.input = kwargs
            self.transition(States.INPUT_VALIDATION)
            validated_input = self.validate_input(**kwargs)

            # Run
            self.transition(States.RUNNING)
            self.output = await self.run(**validated_input)

            # Validate output
            self.transition(States.OUTPUT_VALIDATION)
            self.validate_output(**self.output)

            # Evaluate output
            for evaluator in self.run_evaluators:
                await evaluator(**{'status': 'success', 'output': self.output}, observation=self.observation)

            # Process output
            self.transition(States.PROCESSING_OUTPUT)
            self.processed_output = await self.process_output(**self.output)

            # Validate processed output
            self.transition(States.PROCESSED_OUTPUT_VALIDATION)

            if self.processed_output_validator:
                self.validate_processed_output(**self.processed_output)

            # Evaluate processed output
            for evaluator in self.processed_output_evaluators:
                await evaluator(**{'status': 'success', 'output': self.processed_output}, observation=self.observation)

            final_output = {"status": "success",
                            "output": self.processed_output}

            # Complete
            self.transition(States.COMPLETE)
            langfuse_client.flush()
            return final_output

        except Exception as e:
            output_message = await self.handle_exception(e)
            # Raise or return error
            if tinyllm_config['OPS']['DEBUG']:
                raise e
            if type(e) in self.fallback_strategies:
                raise e
            else:
                return output_message


    async def handle_exception(self,
                               e):
        detailed_error_msg = str(traceback.format_exception(e))
        self.transition(States.FAILED, msg=detailed_error_msg)
        self.log(detailed_error_msg, level="error")
        langfuse_client.flush()
        output_message = {"status": "error",
                          "message": detailed_error_msg}

        # Evaluate output if not already done
        if self.state < States.OUTPUT_EVALUATION:
            for evaluator in self.run_evaluators:
                await evaluator(**output_message, observation=self.observation)

        if self.state < States.PROCESSED_OUTPUT_EVALUATION:
            for evaluator in self.processed_output_evaluators:
                await evaluator(**output_message, observation=self.observation)

        return output_message

    def transition(self, new_state: States, msg: Optional[str] = None):
        if new_state not in ALLOWED_TRANSITIONS[self.state]:
            raise InvalidStateTransition(
                self, f"Invalid state transition from {self.state.name} to {new_state.name}"
            )
        log_level = "error" if new_state == States.FAILED else "info"
        if log_level == 'error':
            self.log(
                f"transition from {self.state.name} to: {new_state.name}" + (f" ({msg})" if msg is not None else ""),
                level=log_level,
            )
        else:
            self.log(
                f"transition to: {new_state.name}" + (f" ({msg})" if msg is not None else ""),
                level=log_level,
            )

        self.state = new_state

    def log(self, message, level="info"):
        if tinyllm_config['OPS']['LOGGING']:
            log_message = f"[{self.name}] {message}"
            if getattr(self, 'trace', None):
                # Add generation id to log message if trace is enabled
                if self.generation:
                    log_message = f"[{self.name}|{self.generation.id}] {message}"

            self.logs += "\n" + log_message
            if level == "error":
                self.logger.error(log_message)
            else:
                self.logger.info(log_message)

    def validate_input(self, **kwargs):
        return self.input_validator(**kwargs).dict()

    def validate_output(self, **kwargs):
        return self.output_validator(**kwargs).dict()

    def validate_processed_output(self, **kwargs):
        return self.processed_output_validator(**kwargs).dict()

    async def run(self, **kwargs) -> Any:
        return kwargs

    async def process_output(self, **kwargs):
        return kwargs
