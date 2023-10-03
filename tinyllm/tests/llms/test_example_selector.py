import unittest

from sentence_transformers import SentenceTransformer
from sqlalchemy import delete

from tinyllm.functions.llms.util.example_selector import ExampleSelector
from tinyllm.tests.base import AsyncioTestCase

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
embedding_function = lambda x: model.encode(x)

class TestRedisExampleSelector(AsyncioTestCase):

    def setUp(self):
        super().setUp()
        self.example_texts = [{
            "USER": "Example question",
            "ASSISTANT": "Example answer",
        },
            {
                "USER": "Another example question",
                "ASSISTANT": "Another example answer"
            }
        ]

        self.local_example_selector = ExampleSelector(
            name="Test local example selector",
            examples=self.example_texts,
            embedding_function=embedding_function,
            is_traced=False
        )

    def test_selector(self):
        query = "Find a relevant example"
        results = self.loop.run_until_complete(self.local_example_selector(user_question=query,
                                                                           k=1))
        self.assertTrue(len(results['best_examples']) == 1)



if __name__ == '__main__':
    unittest.main()
