import asyncio
import os

import openai

from tinyllm.config import APP_CONFIG
from tinyllm.functions.chain import Chain
from tinyllm.functions.decision import Decision
from tinyllm.functions.llms.openai_chat import OpenAIChat
from tinyllm.functions.parallel import Parallel
from tinyllm.functions.function import Function
from tinyllm.functions.prompts.openai_chat.system import OpenAISystemMessage
from tinyllm.functions.prompts.template import OpenAIPromptTemplate
from tinyllm.functions.prompts.user_input import OpenAIUserMessage
from tinyllm.logger import get_logger

openai.api_key = os.getenv("OPENAI_API_KEY")

good_loan_application_example = """
The loan application showcases a commendable financial profile with an excellent credit history. The applicant's credit score
demonstrates a history of timely payments, responsible credit usage, and a low utilization rate, reflecting a consistent
track record of financial prudence. Moreover, the applicant's income documentation reveals a stable employment history
with a steady and substantial income stream. The debt-to-income ratio is well within the acceptable range, indicating a
manageable level of existing debt. Overall, the applicant's solid credit standing and stable financial situation make
this loan application an appealing opportunity for potential lenders.
"""

openai_chat = OpenAIChat(name='openai_chat',
                         model_name='gpt-3.5-turbo',
                         temperature=0,
                         n=1)

loan_officer_role = OpenAISystemMessage(name="Role",
                                        content="You will be provided with a loan application."
                                                "Your role is to classify if as as good or bad. Your output should be one one of these 2 words:[good, bad]")

loan_classifier_template = OpenAIPromptTemplate(name="Loan Classifier Template",
                                                sections=[
                                                    loan_officer_role,
                                                    OpenAIUserMessage(name="name"),
                                                ])


class CreditClassifier(Decision):
    def __init__(self, choices, **kwargs):
        super().__init__(choices=choices,
                         **kwargs)

    async def run(self, **kwargs):
        loan_application = kwargs.get('loan_application')
        messages = await loan_classifier_template(message=loan_application)
        chat_response = await openai_chat(**messages)
        print(f"Credit classification: {chat_response}")
        return {'decision': chat_response}


class EmailNotification(Function):

    async def run(self, **kwargs):
        print("Sending email notification...")
        return {'success': True}


class FurtherAnalysis(Function):

    async def run(self, **kwargs):
        print("Performing further analysis...")
        return {'further_analysis': 'Completed'}


async def main():
    credit_classifier = CreditClassifier(name="CreditClassification",
                                         choices=['good', 'bad'])
    email_notification = EmailNotification(name="EmailNotification")
    further_analysis = FurtherAnalysis(name="FurtherAnalysis")

    credit_analysis_chain = Chain(name="Credit analysis",
                                  children=[
                                      credit_classifier,
                                      Parallel(name="Bad credit analysis",
                                               children=[email_notification,
                                                         further_analysis])])

    result = await credit_analysis_chain(loan_application=good_loan_application_example)


if __name__ == '__main__':
    APP_CONFIG.set_logging('default', get_logger(name='default'))
    asyncio.run(main())