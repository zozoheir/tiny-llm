from typing import List, Dict, Any, Optional
import re

# A dictionary for OpenAI context token sizes.
open_ai_max_context_tokens = {
    "gpt-4": 8192,
    "gpt-4-0314": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-32k-0314": 32768,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-0301": 4096,
    "text-ada-001": 2049,
    "ada": 2049,
    "text-babbage-001": 2040,
    "babbage": 2049,
    "text-curie-001": 2049,
    "curie": 2049,
    "davinci": 2049,
    "text-davinci-003": 4097,
    "text-davinci-002": 4097,
    "code-davinci-002": 8001,
    "code-davinci-001": 8001,
    "code-cushman-002": 2048,
    "code-cushman-001": 2048,
}


def concatenate_strings(paragraphs: List[str]) -> str:
    """
    Concatenates a list of strings with newline separator.

    :param paragraphs: A list of strings to concatenate.
    :return: A string concatenated with newline separator.
    """
    return "\n".join(paragraphs)


def generate_string_from_key_value(key: str, value: Any) -> str:
    """
    Formats a string based on a key-value pair.

    :param key: The key of the pair.
    :param value: The value of the pair.
    :return: A formatted string.
    """
    return f"- {key}: {value}"


def string_format_dict(news_dict: Dict[str, Any],
                       ommit_keys: Optional[List[str]] = None) -> str:
    """
    Formats a dictionary into a string with a specific format.

    :param news_dict: A dictionary to format.
    :param ommit_keys: A list of keys to omit. Default is None.
    :return: A formatted string.
    """
    ommit_keys = ommit_keys or []
    all_strings = []
    for key, value in news_dict.items():

        if key in ommit_keys or value is None or key is None:
            continue

        if key in ['created_at', 'updated_at', 'timestamp']:
            value = str(value).split('+')[0]

        generated_string = generate_string_from_key_value(key, str(value).split('+')[0])
        all_strings.append(generated_string)
    return concatenate_strings(all_strings)


def dicts_to_string(text_header: str,
                    dicts: List[Dict[str, Any]],
                    ommit_keys: Optional[List[str]] = None) -> str:
    """
    Transforms a list of dictionaries to a single string.

    :param text_header: The header of the text.
    :param dicts: A list of dictionaries to transform.
    :param ommit_keys: A list of keys to omit. Default is None.
    :return: A formatted string.
    """
    ommit_keys = ommit_keys or []
    return text_header.upper() + '\n' + concatenate_strings(
        [string_format_dict(data_dict, ommit_keys) for data_dict in dicts])


def split_texts_for_prompt(input_texts: List[str],
                           llm: Any,
                           max_llm_tokens: int) -> List[str]:
    """
    Splits a list of texts for prompts based on the maximum number of tokens allowed.

    :param input_texts: A list of input texts.
    :param llm: A language model instance.
    :param max_llm_tokens: The maximum number of tokens allowed.
    :return: A list of distributed texts.
    """
    distributed_texts = []
    single_prompt_input_text = ""
    for news_text in input_texts:
        if llm.get_num_tokens(news_text) > max_llm_tokens:
            news_text = news_text[:max_llm_tokens * 3]

        if llm.get_num_tokens(single_prompt_input_text + news_text) > max_llm_tokens:
            distributed_texts.append(single_prompt_input_text)
            single_prompt_input_text = ""
        else:
            single_prompt_input_text += news_text

    if len(single_prompt_input_text) > 0:
        distributed_texts.append(single_prompt_input_text)

    return distributed_texts


def get_allowed_n_input_tokens(llm: Any,
                               completion_tokens: int,
                               prompt_template: int) -> int:
    """
    Gets the allowed number of input tokens.

    :param llm: A language model instance.
    :param completion_tokens: The number of completion tokens.
    :param prompt_template: A prompt template.
    :return: The number of allowed input tokens.
    """
    empty_prompt = prompt_template.format(**{input_variable: "" for input_variable in prompt_template.input_variables})

    prompt_template_n_tokens = llm.get_num_tokens(empty_prompt)
    max_token_size = open_ai_max_context_tokens[llm.model_name]
    return max_token_size - prompt_template_n_tokens - completion_tokens

def remove_imports(code: str) -> str:
    lines = code.split('\n')
    lines = [line for line in lines if not line.lstrip().startswith(('import', 'from'))]
    return '\n'.join(lines)



def extract_markdown_python(text: str):
    pattern = r"```python(.*?)```"
    python_codes = re.findall(pattern, text, re.DOTALL)
    return "\n".join(python_codes)