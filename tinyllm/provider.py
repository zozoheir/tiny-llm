from typing import Dict, Any
from tinyllm.operator import Operator
from tinyllm.model_cache import ModelCache
from tinyllm.stores.openai import OpenAILLM


class Store(Operator):
    def __init__(self, name: str, llm_base: OpenAILLM, provider_kwargs: Dict[str, Any]):
        self.name = name
        self.llm_base = llm_base
        self.provider_kwargs = provider_kwargs
        self.model_cache = ModelCache()

    def get_model(self, llm_name: str, llm_params: Dict[str, Any]) -> Operator:
        if (llm_name, llm_params) in self.model_cache.index:
            return self.llm_base(llm_name=llm_name, llm_params=llm_params,
                                 provider_kwargs=self.provider_kwargs)
        else:
            model = self.llm_base(llm_name=llm_name, llm_params=llm_params, provider_kwargs=self.provider_kwargs)
            self.model_cache.add(model=model)
