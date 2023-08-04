from langfuse import Langfuse
from langfuse.api.model import CreateTrace, CreateGeneration, UpdateGeneration, CreateSpan, UpdateSpan

langfuse_client = Langfuse(
    public_key="pk-lf-3b6b0cb7-13c8-419b-adc6-b84dc9069021",
    secret_key="sk-lf-2f5aafe7-be17-4d54-af7f-46bb60e58c4c",
    host="https://cloud.langfuse.com/"
)


class LLMTrace:

    def __init__(self,
                 is_traced=True,
                 **kwargs):
        self.is_traced = is_traced
        if self.is_traced is True:
            self.trace = langfuse_client.trace(CreateTrace(**kwargs))

    def create_generation(self,
                          **kwargs):
        if self.is_traced is True:
            self.current_generation = self.trace.generation(CreateGeneration(
                **kwargs))

    def update_generation(self,
                          **kwargs):
        if self.is_traced is True:
            self.current_generation.update(UpdateGeneration(
                **kwargs
            ))

    def create_span(self,
                    **kwargs):
        if self.is_traced is True:
            self.current_span = self.trace.span(CreateSpan(
                    **kwargs
                )
            )

    def update_span(self,
                    **kwargs):
        if self.is_traced is True:
            self.current_span.update(UpdateSpan(**kwargs))