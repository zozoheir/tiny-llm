from typing import List, Union, Dict


# Base class for content types
class Content:
    def dict(self) -> Dict:
        return self.__dict__


class Text(Content):
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class Image(Content):
    def __init__(self, url: str):
        self.type = "image_url"
        self.image_url = {"url": url}


class Message:

    def __init__(self,
                 role: str,
                 content: Union[List[Content], str]):
        self.role = role
        if type(content) == str:
            content = [Text(content)]
        self.content = content

    def dict(self) -> Dict:
        return {"role": self.role, "content": [c.dict() for c in self.content]}


class UserMessage(Message):
    def __init__(self, content: List[Content]):
        super().__init__("user", content)


class SystemMessage(Message):
    def __init__(self, content: List[Content]):
        super().__init__("system", content)


class FunctionMessage(Message):
    def __init__(self, content: List[Content]):
        super().__init__("function", content)


class ToolMessage(Message):
    def __init__(self,
                 content: List[Content],
                 name: str = None,
                 tool_calls: List[Dict] = None,
                 tool_call_id: str = None):
        self.name = name
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        super().__init__("tool", content)

    def dict(self) -> Dict:
        message = super().dict()
        if self.tool_call_id:
            message['tool_call_id'] = self.tool_call_id
        return message


class AssistantMessage(Message):
    def __init__(self,
                 content,
                 tool_calls: List[Dict] = None):
        self.tool_calls = tool_calls
        super().__init__("assistant", content)

    def dict(self) -> Dict:
        message = super().dict()
        if self.tool_calls:
            message['tool_calls'] = self.tool_calls
        return message