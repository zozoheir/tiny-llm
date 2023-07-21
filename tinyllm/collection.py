import asyncio
from typing import List

from tinyllm.exceptions import InvalidOutput, InvalidInput
from tinyllm.types import Chains, States
from tinyllm.operator import Operator

class ParallelChain(Operator):
    def __init__(self, name: str, children: List['Operator'] = None, parent_id=None):
        super().__init__(name, Chains.PARALLEL, parent_id)
        self.children = children if children else []

    async def __call__(self, **kwargs):
        self.transition(States.INPUT_VALIDATION)
        if not await self.validate_input(**kwargs):
            raise InvalidInput(self, "Invalid parallel chain input")
        self.transition(States.RUNNING)
        inputs = kwargs['inputs']
        tasks = [child.__call__(**inputs[i]) for i, child in enumerate(self.children)]
        output = await asyncio.gather(*tasks)
        if not await self.validate_output(*output):
            raise InvalidOutput(self, "Invalid parallel chain output")
        self.transition(States.COMPLETE)
        return output

    async def validate_input(self, **kwargs):
        return True

class SequentialChain(Operator):
    def __init__(self, children: List['Operator'] = None, **kwargs):
        super().__init__(**kwargs)
        self.children = children if children else []

    async def __call__(self, **kwargs):
        self.transition(States.INPUT_VALIDATION)
        if not await self.validate_input(**kwargs):
            raise InvalidInput(self, "Invalid sequential chain input")
        self.transition(States.RUNNING)
        output = None
        for child in self.children:
            output = await child(**kwargs)
            kwargs = output
        if not await self.validate_output(**output):
            raise InvalidOutput(self, "Invalid sequential chain output")
        self.transition(States.COMPLETE)
        return output

    async def validate_input(self, **kwargs):
        if not isinstance(kwargs, dict):
            raise InvalidInput(self, "Invalid input type. Expected a dictionary.")
        return True
