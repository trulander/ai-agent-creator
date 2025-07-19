from langchain_core.messages import (
    SystemMessage,
)
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI

from langgraph.checkpoint.memory import InMemorySaver

import logging
import time
from collections import defaultdict

from ai_integration.helpers.ai_agent import LLMAgent
from ai_integration.helpers.agent_helper import AIAutomation
from ai_integration.helpers.db_dict_factory import DBDict

# GOOGLE_API_KEY="***"
# GITHUB_TOKEN="***"
#


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


# if not os.environ.get("GOOGLE_API_KEY"):
#     os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
# if not os.environ.get("GITHUB_TOKEN"):
#     os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN


def test():
    factory = DBDict.db_dict_factory(db_path="test.db", record_id="test_id_1232")
    instance = InMemorySaver(factory=factory)
    print("Loaded storage:", dict(instance.storage))
    print("Loaded writes:", dict(instance.writes))
    print("Loaded blobs:", dict(instance.blobs))

    # Тест 1: Простые типы (str, int, float, bool, None)
    instance.storage["string"] = "value"
    instance.storage[42] = 100
    instance.storage[3.14] = False
    instance.storage[None] = None
    instance.writes["key"] = True
    instance.blobs[True] = 42.0

    # Тест 2: Кортеж как ключ
    instance.storage[("a", "b")] = {"nested": 1}
    instance.writes[("x", "y")] = b"tuple_key"

    # Тест 3: Bytes как значение
    instance.writes["bytes"] = b"binary_data"
    instance.blobs["bytes2"] = b"\x00\x01\x02"

    # Тест 4: Вложенный defaultdict
    instance.storage["nested"] = defaultdict(dict)
    instance.storage["nested"]["subkey"] = {"deep": 2}

    # Тест 5: Update с разными типами
    instance.writes.update({42: "int_key", ("c", "d"): b"updated", "str": 3.14})

    # Тест 6: Pop и удаление
    # instance.storage.pop(("a", "b"))
    # instance.writes.pop("bytes")
    instance.storage["nested"][("x", "y")] = {"tuple_key": 3}


    # Тест 8: Доступ к несуществующему ключу (default_factory)
    print(instance.storage["new_key"])  # defaultdict(dict)
    print(instance.writes[123])  # dict
    # print(instance.blobs["new"])  # None

    # Ждем синхронизации
    time.sleep(2)
    del instance
    # Тест 9: Проверка загрузки из базы
    instance2 = InMemorySaver(factory=factory)
    print("Loaded storage:", dict(instance2.storage))
    print("Loaded writes:", dict(instance2.writes))
    print("Loaded blobs:", dict(instance2.blobs))

def main():
    model = ChatGoogleGenerativeAI(model='gemini-2.5-flash')
    # model = ChatGoogleGenerativeAI(model='gemini-2.0-flash-lite')
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-04-17")
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite-preview-06-17")
    automation = AIAutomation(repo_path="./repos/***", repo_url="***")
    system_prompt = SystemMessage(
        content = (
            "***"
        )
    )

    agent = LLMAgent(
        system_message=system_prompt,
        model=model,
        tools=[
            automation.create_folder,
            automation.create_file,
            automation.read_file,
            automation.update_file,
            automation.find_in_files,
            automation.get_function_defs,
            automation.get_class_structure,
            automation.run_linter,
            automation.delete_file,
            automation.get_project_structure,
            automation.list_git_branches,
            automation.create_and_checkout_branch,
            automation.checkout_branch,
            automation.delete_branch,
            automation.commit_and_push_changes,
            automation.create_pull_request,
            automation.create_code_review,
            automation.approve_pull_request,
            automation.merge_pull_request_and_checkout
        ],
        chat_id="123"
    )

    agent_response = agent.invoke(
        # content=HumanMessage(content="Продолжай")
        content="Продолжай"
    )
    logger.info(f"Последнее сообщение: {agent_response["messages"][-1]}")


if __name__ == "__main__":
    try:
        main()
        # automation = AIAutomation(repo_path="./repos/***", repo_url="***")
        # print(automation.get_project_structure())
    except KeyboardInterrupt:
        logger.info("\nдосвидули!")