from typing import Optional

from tinyllm.functions.function import Function
from tinyllm.functions.validator import Validator



class OutputValidator(Validator):
    evals: dict
    metadata: Optional[dict] = {}


class Evaluator(Function):

    def __init__(self,
                 **kwargs):
        super().__init__(output_validator=OutputValidator,
                         **kwargs)