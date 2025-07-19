import logging
import uuid
from typing import Sequence, Any, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import LanguageModelLike, BaseChatModel
from langchain_core.messages import SystemMessage, trim_messages, RemoveMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.outputs import LLMResult
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import create_react_agent

from ai_agent_creator.settings import GEMINI_API_KEY
from ai_integration.helpers.db_dict_factory import DjangoDBDict
from ai_integration.helpers.ai_model_enum import AIModels

logger = logging.getLogger(__name__)


def model_factory(model: AIModels) -> BaseChatModel:
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    # model = ChatGoogleGenerativeAI(model='gemini-2.0-flash-lite')
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-04-17")
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite-preview-06-17")
    return ChatGoogleGenerativeAI(model=model.value, api_key=GEMINI_API_KEY)

class LLMAgent:
    def __init__(self,
                 model: LanguageModelLike,
                 tools: Sequence[BaseTool],
                 system_message: SystemMessage,
                 chat_id: str
                 ):
        self._model = model

        # This function will be called every time before the node that calls LLM
        def pre_model_hook(state):
            trimmed_messages = trim_messages(
                state["messages"],
                strategy="last",
                token_counter=count_tokens_approximately,
                max_tokens=100000,
                start_on="human",
                end_on=("human", "tool"),
                include_system=True
            )
            # pprint.pp(trimmed_messages)

            # return {"llm_input_messages": trimmed_messages} #обрезать только для модели, но историю хранить всю
            return {"messages": [RemoveMessage(REMOVE_ALL_MESSAGES)] + trimmed_messages}# обрезать историю в том числе

        # Единый record_id для всех таблиц
        factory = DjangoDBDict.db_dict_factory(record_id=chat_id)
        self.checkpointer = InMemorySaver(factory=factory)
        logger.info(f"init agent system_message: {system_message}")
        self._agent = create_react_agent(
            prompt=system_message,
            pre_model_hook=pre_model_hook,
            model=model,
            tools=tools,
            checkpointer=self.checkpointer
        )

        self._tracer = ReasoningTracer()

        self._config: RunnableConfig = {
            "configurable": {"thread_id": chat_id},
            "recursion_limit": 100,
            "callbacks": [self._tracer],
        }

    def upload_file(self, file):
        print(f"upload file {file} to LLM")
        file_uploaded_id = self._model.upload_file(file).id_  # type: ignore
        return file_uploaded_id

    def invoke(
        self,
        content: str,
        attachments: list[str]|None=None,
        temperature: float=0.1
    ) -> str:
        """Отправляет сообщение в чат"""
        message: dict = {
            "role": "user",
            "content": content,
            **({"attachments": attachments} if attachments else {})
        }
        try:
            logger.info(f"invoke {message}")
            self._agent.invoke(
                input = {
                    "messages": [message],
                    "temperature": temperature
                },
                config=self._config
            )
            # Логика для просмотра reasoning
            # print("REASONING TRACE:")
            # for step in self._tracer.steps:
            #     print(step)
        except GraphRecursionError:

            logger.warning("⚠️ Достигнут лимит reasoning.")
        except Exception as e:
            logger.error(f"InvokeError: {e}")
            raise e

        result = self.checkpointer.get(config=self._config).get("channel_values")
        return result


class ReasoningTracer(BaseCallbackHandler):
    def __init__(self):
        self.steps = []

    def on_tool_start(self,
                    serialized: dict[str, Any],
                    input_str: str,
                    *,
                    run_id: uuid.UUID,
                    parent_run_id: Optional[uuid.UUID] = None,
                    tags: Optional[list[str]] = None,
                    metadata: Optional[dict[str, Any]] = None,
                    inputs: Optional[dict[str, Any]] = None,
                    **kwargs: Any):
        self.steps.append({
            "type": "tool_start",
            "tool": kwargs.get('name', None),
            "input": input
        })

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: uuid.UUID,
        parent_run_id: Optional[uuid.UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ):
        self.steps.append({
            "type": "tool_end",
            "output": output
        })

    def on_llm_start(self,
                     serialized: dict[str, Any],
                     prompts: list[str],
                     *,
                     run_id: uuid.UUID,
                     parent_run_id: Optional[uuid.UUID] = None,
                     tags: Optional[list[str]] = None,
                     metadata: Optional[dict[str, Any]] = None,
                     **kwargs: Any, ):
        self.steps.append({
            "type": "llm_start",
            "prompt": prompts
        })

    def on_llm_end(self,
                   response: LLMResult,
                   *,
                   run_id: uuid.UUID,
                   parent_run_id: Optional[uuid.UUID] = None,
                   **kwargs: Any,
                   ):
        self.steps.append({
            "type": "llm_end",
            "response": response.generations
        })
