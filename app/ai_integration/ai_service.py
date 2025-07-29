import logging

from langchain_core.messages import SystemMessage

from ai_integration.helpers.agent_helper import AIAutomation
from ai_integration.helpers.ai_agent import LLMAgent, model_factory
from ai_integration.helpers.db_dict_factory import DjangoDBDict
from ai_integration.models import AIStateDefault
from ai_integration.helpers.ai_model_enum import AIModels

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self,
                 system_prompt: str | list[str | dict],
                 chat_id: str,
                 repo_url: str,
                 github_token: str,
                 github_username: str,
                 github_email: str,
                 model: AIModels = AIModels.GEMINI_2_0_FLASH):
        logger.info(f"model: {model}")
        model = model_factory(model=model)
        self.todo_list_storage = DjangoDBDict.db_dict_factory(record_id=chat_id, table_name=AIStateDefault)()
        automation = AIAutomation(
            repo_url=repo_url,
            github_token=github_token,
            github_username=github_username,
            github_email=github_email,
            todo_list_storage=self.todo_list_storage,
            rate_limit=10
        )
        system_message = SystemMessage(content=system_prompt)

        self._agent = LLMAgent(
            system_message=system_message,
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
                automation.merge_pull_request_and_checkout,
                automation.update_todo_list,
                automation.get_todo_list
            ],
            chat_id=chat_id
        )

    def invoke(self, human_message: str = "Продолжай"):
        try:
            response = self._agent.invoke(
                content=human_message,
                attachments=None,
                temperature=0.1
            )
            logger.info(f"Последнее сообщение: {response["messages"][-1]}")
            return response["messages"][-1]
        finally:
            self.todo_list_storage.sync_data()