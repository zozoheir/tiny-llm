import random
import re
from typing import List, Dict, Any, Optional

from fuzzywuzzy import fuzz
from tinyllm.util import os_util

from typing import List, Type, get_args, get_origin
from pydantic import BaseModel, Field

import inspect

def extract_function_signature(function):
    sig = inspect.signature(function)
    return {k: str(v.annotation) for k, v in sig.parameters.items() if v.default != inspect.Parameter.empty}

def extract_models(model: Type[BaseModel], models_list: List[Type[BaseModel]]) -> None:
    if model not in models_list:
        models_list.append(model)
        fields = model.__fields__
        for field_name, field in fields.items():
            field_type = field.annotation
            origin = get_origin(field_type)
            args = get_args(field_type)

            if isinstance(field_type, type) and issubclass(field_type, BaseModel):
                extract_models(field_type, models_list)
            elif origin is not None:
                for arg in args:
                    if isinstance(arg, type) and issubclass(arg, BaseModel):
                        extract_models(arg, models_list)


def model_to_string(model: Type[BaseModel], indent=4) -> str:
    fields = model.__fields__
    field_defs = []
    for field_name, field in fields.items():
        field_type = field.annotation

        origin = get_origin(field_type)
        origin = str(origin).replace("<class '","").replace("'>","").capitalize()
        if origin:
            field_type_name = f"{str(origin)}[{str(field_type).split('.')[-1].replace(']', '')}]"
        else:
            field_type_name = field_type.__name__

        description = field.description
        description = f" | description: {description}" if description else ""
        field_defs.append(f"{' ' * indent}- {field_name}: {field_type_name}{description}")

    model_str = f"{model.__name__}:\n" + "\n".join(field_defs)
    return model_str


def pydantic_model_to_string(root_model: Type[BaseModel]) -> str:
    models_list = []
    extract_models(root_model, models_list)
    models_strings = []
    for model in models_list[1:]:
        model_str = model_to_string(model)
        models_strings.append(model_str)
    original_model_string = f"{model_to_string(models_list[0])}\n\n WHERE \n\n"
    recurive_models = " AND \n\n".join(models_strings)
    return  original_model_string + recurive_models



def stringify_string_list(paragraphs: List[str],
                          separator="\n") -> str:
    """
    Concatenates a list of strings with newline separator.

    :param paragraphs: A list of strings to concatenate.
    :return: A string concatenated with newline separator.
    """
    return separator.join(paragraphs)


def stringify_key_value(key: str, value: Any) -> str:
    """
    Formats a string based on a key-value pair.

    :param key: The key of the pair.
    :param value: The value of the pair.
    :return: A formatted string.
    """
    return f"- {key}: {value}"


def stringify_dict(header: str,
                   dict: Dict[str, Any],
                   include_keys: Optional[List[str]] = []) -> str:
    """
    Formats a dictionary into a string with a specific format.

    :param dict: A dictionary to format.
    :param include_keys: A list of keys to include. Default is None, which includes all keys.
    :return: A formatted string.
    """
    all_strings = []
    # if there are included ids, make sure the dict is filtered and follows the same order
    dict = {k: dict[k] for k in include_keys} if include_keys else dict
    for key, value in dict.items():
        # Include the key only if include_keys is None (include all keys) or the key is in include_keys
        if value is None:
            value = ""
        if key in ['created_at', 'updated_at', 'timestamp']:
            value = str(value).split('+')[0] if '+' in str(value) else str(value)
        generated_string = stringify_key_value(key, str(value).split('+')[0])
        all_strings.append(generated_string)

    dict_string_representation = stringify_string_list(all_strings, separator="\n")
    return header + "\n" + dict_string_representation


def stringify_dict_list(header: str,
                        dict_list: List[Dict[str, Any]],
                        include_keys: Optional[List[str]] = None) -> str:
    """
    Formats a list of dictionaries into a string with a specific format.

    :param dict_list: A list of dictionaries to format.
    :param include_keys: A list of keys to include. Default is None, which includes all keys.
    :return: A formatted string.
    """
    all_strings = []
    for dict in dict_list:
        dict_string_representation = stringify_dict("", dict, include_keys)
        all_strings.append(dict_string_representation)

    dict_list_string_representation = stringify_string_list(all_strings, separator="\n\n")
    return header + "\n" + dict_list_string_representation


def remove_imports(code: str) -> str:
    lines = code.split('\n')
    lines = [line for line in lines if not line.lstrip().startswith(('import', 'from'))]
    return '\n'.join(lines)


def extract_markdown_python(text: str):
    if '```python' not in text:
        return text
    pattern = r"```python(.*?)```"
    python_codes = re.findall(pattern, text, re.DOTALL)
    return "\n".join(python_codes)


def get_files_content(file_list: list,
                      formats: list):
    code_context = []
    for file_name in file_list:
        if os_util.isDirPath(file_name):
            for file_path in os_util.listDir(file_name, recursive=True, formats=formats):
                try:
                    with open(file_path, 'r') as file:
                        content = file.read()
                        code_context.append(f'\n \nFILE: This is the content of the file {file_name}:\n \n {content}\n')
                        code_context.append(f'\n------------------------\n')
                except FileNotFoundError:
                    print(f'File {file_name} not found in the directory')

        else:
            try:
                with open(file_name, 'r') as file:
                    content = file.read()
                    code_context.append(f'\n \nFILE: This is the content of the file {file_name}:\n \n {content}\n')
                    code_context.append(f'\n------------------------\n')
            except FileNotFoundError:
                print(f'File {file_name} not found in the directory')

    final_prompt = '\n'.join(code_context)
    return final_prompt


def shuffle_with_freeze(input_list, freeze):
    not_frozen_dict = {i: input_list[i] for i in range(len(input_list)) if i not in freeze}
    not_frozen_indices = list(not_frozen_dict.keys())
    random.shuffle(not_frozen_indices)
    shuffled_dict = {i: not_frozen_dict[not_frozen_indices[i]] for i in range(len(not_frozen_indices))}
    output_list = [shuffled_dict.get(i) if i in shuffled_dict else input_list[i] for i in range(len(input_list))]
    return output_list


def remove_duplicate_lines(input_string: str) -> str:
    lines = input_string.split('\n')
    seen_lines = set()
    unique_lines = []
    for line in lines:
        trimmed_line = line.strip()  # Removing leading and trailing whitespaces
        if trimmed_line and trimmed_line not in seen_lines:
            seen_lines.add(trimmed_line)
            unique_lines.append(trimmed_line)
    return '\n'.join(unique_lines)


def find_closest_match_char_by_char(source, target):
    max_ratio = 0
    best_match = (0, 0)
    n = len(source)

    for start in range(n):
        for end in range(start, n):
            substring = source[start:end + 1]
            ratio = fuzz.token_set_ratio(substring, target)
            if ratio > max_ratio:
                max_ratio = ratio
                best_match = (start, end)

    return best_match


def get_smallest_chunk(source, matches):
    # Sort matches by start index
    matches.sort(key=lambda x: x[0])

    min_chunk = (0, len(source))
    for i in range(len(matches)):
        for j in range(i + 1, len(matches)):
            if matches[j][0] > matches[i][1]:  # Ensuring the second element starts after the first
                chunk_size = matches[j][1] - matches[i][0]
                if chunk_size < (min_chunk[1] - min_chunk[0]):
                    min_chunk = (matches[i][0], matches[j][1])
                    break  # No need to check further as we are looking for smallest chunk

    return min_chunk


def preprocess_text(text):
    # Convert to lower case and remove special characters
    return re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())

def blockify(text, title=None):
    title = title.upper() if title else None
    if title:
        return f"<{title}>\n{text}\n</{title}>\n\n"
    else:
        return text


INSTRUCTIONS_BOOSTS = [
    'You will be given $500 tip if you follow the instructions',
    'This is important for my career',
]
