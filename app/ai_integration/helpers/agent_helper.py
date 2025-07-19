import ast
import logging
import os

import re
import subprocess
from pathlib import Path
from typing import Optional

from git import Repo, GitCommandError
from github import Github, Repository
from langchain_core.tools import tool

from ai_integration.helpers.rate_limit import (
    rate_limited_tools_per_minute,
    rate_limiter,
)

logger = logging.getLogger(__name__)

class AIAutomation:
    github: Github = None
    repo_path: str = None
    repo_url: str = None
    todo_list_storage: dict = None

    def __init__(self, repo_url: str, github_token: str, todo_list_storage: dict, rate_limit: int):
        AIAutomation.todo_list_storage = todo_list_storage
        rate_limiter.update_rate_limit(new_limit=rate_limit)
        AIAutomation.github = Github(github_token)
        repo_name, user_name = self._extract_repo_name_from_url(repo_url)
        AIAutomation.repo_path = os.path.join("./repos/",user_name, repo_name)
        AIAutomation.repo_url = repo_url
        self._clone_repository(repo_url=repo_url, local_path=AIAutomation.repo_path)

    @staticmethod
    def _get_pull_request(repo: Repository.Repository, pr_number: int):
        return repo.get_pull(pr_number)

    @staticmethod
    def _get_repository() -> Optional[Repository.Repository]:
        try:
            repo_name, _ = AIAutomation._extract_repo_name_from_url(AIAutomation.repo_url)
            return AIAutomation.github.get_user().get_repo(repo_name)  # Assuming user's repo
        except Exception as e:
            logger.error(f"Error getting repository {AIAutomation.repo_url}: {e}")
            return None

    @staticmethod
    def _extract_repo_name_from_url(repo_url: str) -> (str, str):
        """
        # Expects URL like https://github.com/username/repo_name.git or https://github.com/username/repo_name
        :param repo_url:
        :return:
        repo_name, user_name
        """
        path = repo_url.split('/')
        if path[-1].endswith('.git'):
            path = path[:-4]
        return path[-1], path[-2]

    def _clone_repository(self, repo_url: str, local_path: str) -> Optional[Repo]:
        """
        Клонирует репозиторий или обновляет существующий, инициализируя ветку main, если она отсутствует.

        :param repo_url: URL репозитория
        :param local_path: локальный путь для клонирования
        :return: объект Repo или None при ошибке
        """
        try:
            if os.path.exists(local_path):
                logger.info(f"Repository already cloned at {local_path}. Pulling latest changes.")
                repo = Repo(local_path)
                # repo.remotes.origin.pull('main')
                # repo.git.checkout("main")  # Переключиться на ветку main
                repo.git.fetch("origin")  # Получить последние изменения с удалённого репозитория
                # repo.git.reset("--hard", "origin/main")  # Сбросить локальную ветку до состояния origin/main
                return repo
            else:
                repo_name, _ = self._extract_repo_name_from_url(repo_url)
                repo_url_with_token = repo_url.replace(
                    "https://", f"https://oauth2:{self.github.requester.auth.token}@"
                )
                repo = Repo.clone_from(repo_url_with_token, local_path)
                logger.info(f"Repository {repo_name} cloned to {local_path}")
                # Проверка, пустой ли репозиторий (нет веток)
                if not repo.branches:
                    logger.info("Remote repository is empty. Initializing main branch.")
                    # Создаём начальный коммит
                    open(f"{local_path}/README.md", "w").write("# Initial commit")
                    repo.index.add(["README.md"])
                    repo.index.commit("Initial commit")
                    # Создаём ветку main
                    repo.create_head("main")
                    # Пушим в удалённый репозиторий
                    repo.git.push("--set-upstream", "origin", "main")
                    logger.info("Main branch initialized and pushed to remote.")
                return repo
        except GitCommandError as e:
            logger.error(f"Git command error cloning/pulling {repo_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error cloning/pulling {repo_url}: {e}")
            return None

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def create_file(path: str, create_dir: bool = True) -> bool:
        """
        Создание файла в дирректории проекта, можно передавать вместе в путем до файла,
        если дирректории не существует, она будет создана, если передать параметр create_dir = True

        :param path: имя файла, можно передавать путь до файла
        :param create_dir: параметр отвечает за создание дирректорий по пути к файлу, если их не существует
        :return:
        """
        logger.info(f"create_file: path='{path}', create_dir={create_dir}")
        path = os.path.join(AIAutomation.repo_path, path)
        try:
            file_path = Path(path)
            if create_dir:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch(exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании файла '{path}': {e}")
            return False

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def create_folder(path: str) -> bool:
        """
        Создание дирректории, поддерживается передача пути до конечной дирректори,
        если какой-либо дирректории не существует в пути, она будет создана

        :param path:
        :return:
        """
        logger.info(f"create_folder: path='{path}'")
        path = os.path.join(AIAutomation.repo_path, path)
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании директории '{path}': {e}")
            return False

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def read_file(path: str) -> str:
        """
        Чтение файла

        :param path: путь до файла который нужно прочитать
        :return:
        """
        logger.info(f"read_file: path='{path}'")
        path = os.path.join(AIAutomation.repo_path, path)
        try:
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
                logger.info(f"read_file: data_length={len(content)}")
                return content
        except Exception as e:
            logger.error(f"Ошибка при чтении файла '{path}': {e}")
            return ""

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def update_file(path: str, data: str, append: bool = False) -> str:
        """
        Обновление существущего файла по пути path данными из data.
        Если указать append = True, то данные data будут просто добавлены в
        конец файла, без перезаписи существущих данных в файле

        :param path: путь до файла
        :param data: данные для сохранения в файл
        :param append: bool для определения нужно ли дописать в конец, или переписать весь файл целиком
        :return:
        """
        logger.info(f"update_file: path='{path}', append={append}, data_length={len(data)}")
        path = os.path.join(AIAutomation.repo_path, path)
        try:
            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as file:
                file.write(data)
            return "Данные успешно записаны"
        except Exception as e:
            logger.error(f"Ошибка при записи в файл '{path}': {e}")
            return f"Ошибка при записи файла: {e}"

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def delete_file(path: str) -> bool:
        """
        Удаление файла по указанному пути path

        :param path:
        :return:
        """
        logger.info(f"delete_file: path='{path}'")
        path = os.path.join(AIAutomation.repo_path, path)
        try:
            file_path = Path(path)
            if file_path.is_file():
                file_path.unlink()
                return True
            else:
                logger.warning(f"Файл не найден или не является обычным файлом: '{path}'")
                return False
        except Exception as e:
            logger.error(f"Ошибка при удалении файла '{path}': {e}")
            return False

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def get_project_structure(root_path: str = ".", max_depth: int = 3) -> str:
        """
        Возвращает иерархическую структуру файлов и папок начиная с root_path, исключая указанные файлы и директории.

        :param root_path: путь до корня проекта или поддиректории
        :param max_depth: максимальная глубина обхода (по умолчанию 3)
        :return: текстовое дерево структуры проекта
        """
        exclude = [".git",".venv"]
        logger.info(f"get_project_structure: root_path='{root_path}', max_depth={max_depth}")
        root_path = os.path.join(AIAutomation.repo_path, root_path)

        def walk(path, prefix="", depth=0):
            if depth > max_depth:
                return ""
            result = ""
            try:
                entries = sorted([e for e in os.listdir(path) if e not in exclude])
                for i, entry in enumerate(entries):
                    full_path = os.path.join(path, entry)
                    connector = "└── " if i == len(entries) - 1 else "├── "
                    result += f"{prefix}{connector}{entry}\n"
                    if os.path.isdir(full_path):
                        extension = "    " if i == len(entries) - 1 else "│   "
                        result += walk(full_path, prefix + extension, depth + 1)
            except Exception as e:
                logger.error(f"Ошибка при обходе директории '{path}': {e}")
                result += f"{prefix}└── [Ошибка доступа: {e}]\n"
            return result

        result = walk(root_path)
        # logger.info(f"get_project_structure: result='{result}'")
        return result

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def find_in_files(directory: str, pattern: str, extensions: list[str] = [".py"]) -> list[str]:
        """
        Поиск по тексту или регулярному выражению в указанных файлах директории

        :param directory: путь до директории, где искать
        :param pattern: текст или регулярное выражение
        :param extensions: список расширений файлов, например ['.py', '.txt']
        :return: список совпадений вида: путь:строка: содержимое
        """
        logger.info(f"find_in_files: directory='{directory}', pattern='{pattern}', extensions={extensions}")
        results = []
        regex = re.compile(pattern)
        directory = os.path.join(AIAutomation.repo_path, directory)
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            for i, line in enumerate(f, 1):
                                if regex.search(line):
                                    results.append(f"{path}:{i}: {line.strip()}")
                    except Exception as e:
                        logger.error(f"Ошибка при чтении файла '{path}': {e}")
        logger.info(f"find_in_files: result='{results}'")
        return results

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def get_function_defs(path: str) -> list[str]:
        """
        Возвращает список всех функций в файле с указанием строки

        :param path: путь до python-файла
        :return: список строк вида 'имя_функции (строка)'
        """
        logger.info(f"get_function_defs: path='{path}'")
        try:
            path = os.path.join(AIAutomation.repo_path, path)
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            result = [f"{node.name} (line {node.lineno})" for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            logger.info(f"find_in_files: result='{result}'")
            return result
        except Exception as e:
            logger.error(f"Ошибка при парсинге AST в '{path}': {e}")
            return []

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def get_class_structure(path: str) -> list[str]:
        """
        Возвращает описание всех классов и их методов в файле

        :param path: путь до python-файла
        :return: список строк вида 'Class MyClass: methods: [...]'
        """
        logger.info(f"get_class_structure: path='{path}'")
        try:
            path = os.path.join(AIAutomation.repo_path, path)
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            result = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    result.append(f"Class {node.name} (line {node.lineno}): methods: {methods}")
            logger.info(f"get_class_structure: result='{result}'")
            return result
        except Exception as e:
            logger.error(f"Ошибка при анализе классов в '{path}': {e}")
            return []

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def run_linter(path: str) -> str:
        """
        Запускает линтер ruff для указанного пути

        :param path: путь до файла или директории
        :return: результат выполнения линтера
        """
        logger.info(f"run_linter: path='{path}'")
        try:
            path = os.path.join(AIAutomation.repo_path, path)
            result = subprocess.run(
                ["ruff", path],
                capture_output=True,
                text=True,
                check=False
            )
            result = result.stdout or "Нет ошибок"
            logger.info(f"run_linter: result='{result}'")
            return result
        except FileNotFoundError:
            logger.error("Ruff не установлен")
            return "Ошибка: ruff не установлен"
        except Exception as e:
            logger.error(f"Ошибка при запуске линтера: {e}")
            return str(e)

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def list_git_branches() -> str:
        """
        Возвращает список локальных и удалённых веток, а также текущую ветку.

        :return: строка с информацией о ветках
        """
        try:
            logger.info("list_git_branches")
            repo = Repo(AIAutomation.repo_path)
            current_branch = repo.active_branch.name
            local_branches = [head.name for head in repo.heads]
            remote_branches = [ref.name for ref in repo.remotes.origin.refs]
            result = (
                f"Текущая ветка: {current_branch}\n\n"
                "Локальные ветки:\n" + "\n".join(local_branches) + "\n\n"
                "Удалённые ветки:\n" + "\n".join(remote_branches)
            )
            logger.info(f"list_git_branches result: {result}")
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении веток: {e}")
            return str(e)

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def create_and_checkout_branch(branch_name: str) -> str:
        """
        Создаёт новую ветку и переключается на неё

        :param branch_name: имя новой ветки
        """
        try:
            logger.info(f"create_and_checkout_branch branch_name: {branch_name}")
            repo = Repo(AIAutomation.repo_path)
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            result = f"Создана и активирована ветка: {branch_name}"
            logger.info(f"create_and_checkout_branch result: {result}")
            return result
        except GitCommandError as e:
            logger.error(f"Ошибка при создании ветки: {e}")
            return str(e)

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def checkout_branch(branch_name: str) -> str:
        """
        Переключается на указанную ветку

        :param branch_name: имя ветки
        """
        try:
            logger.info(f"checkout_branch branch_name: {branch_name}")
            repo = Repo(AIAutomation.repo_path)
            repo.git.checkout(branch_name)
            result = f"Переключено на ветку: {branch_name}"
            logger.info(f"checkout_branch result: {result}")
            return result
        except GitCommandError as e:
            logger.error(f"Ошибка при переключении ветки: {e}")
            return str(e)

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def delete_branch(branch_name: str) -> str:
        """
        Удаляет локальную ветку

        :param branch_name: имя ветки
        """
        try:
            logger.info(f"delete_branch branch_name: {branch_name}")
            repo = Repo(AIAutomation.repo_path)
            # Удаление локальной ветки
            repo.delete_head(branch_name, force=False)
            # Удаление удалённой ветки
            repo.remotes.origin.push(f":{branch_name}")

            result = f"Ветка '{branch_name}' удалена"
            logger.info(f"delete_branch result: {result}")
            return result
        except GitCommandError as e:
            logger.error(f"Ошибка при удалении ветки: {e}")
            return str(e)

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def commit_and_push_changes(branch_name: str, commit_message: str) -> (bool, str):
        """
        Закоммитить изменения и сразу запушить их в ветку {branch_name}

        :param branch_name: имя ветки
        :param commit_message: комментарий для коммита
        :return: статус выполнения: bool и текст ошибки или успешного выполнения: str
        """
        try:
            logger.info(f"commit_and_push_changes branch_name: {branch_name}, commit_message: {commit_message}")
            local_repo = Repo(AIAutomation.repo_path)
            local_repo.git.add(A=True)  # Add all changed files
            local_repo.index.commit(commit_message)
            origin = local_repo.remotes.origin
            origin.push(f"{branch_name}")
            logger.info(f"Changes committed and pushed to branch {branch_name}")
            return True, f"Changes committed and pushed to branch {branch_name}"
        except GitCommandError as e:
            logger.error(f"Git command error during commit/push to {branch_name}: {e}")
            return False, f"Git command error during commit/push to {branch_name}: {e}"
        except Exception as e:
            logger.error(f"Error committing/pushing to {branch_name}: {e}")
            return False, f"Error committing/pushing to {branch_name}: {e}"


    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def create_pull_request(head_branch: str, title: str, body: str = "", base_branch: str = 'main') -> int | str:
        """
        Создаёт pull request в GitHub

        :param head_branch: ветка-источник
        :param title: заголовок pull request
        :param body: описание
        :param base_branch: ветка-назначение (по умолчанию "main")
        :return: pr_number pull request или сообщение об ошибке
        """
        try:
            logger.info(f"create_pull_request head_branch: {head_branch}, title: {title}, body: {body}, base_branch: {base_branch}")
            repo = AIAutomation._get_repository()
            pull_request = repo.create_pull(title=title, body=body, head=head_branch, base=base_branch)
            logger.info(f"Pull request '{title}' created: {pull_request.html_url}, {pull_request.number}")
            return pull_request.number
        except Exception as e:
            logger.error(f"Ошибка при создании PR: {e}")
            return f"Ошибка: {e}"

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def create_code_review(pr_number: int, body: str) -> str:
        """
        Оставляет комментарий в pull request

        :param pr_number: номер pull request
        :param body: текст комментария
        :return: сообщение об успехе или ошибке
        """
        try:
            logger.info(f"create_code_review pr_number: {pr_number}, body: {body}")
            repo = AIAutomation._get_repository()
            pr = AIAutomation._get_pull_request(repo, pr_number)
            pr.create_review(body=body, event="COMMENT")
            logger.info(f"Комментарий к PR {pr.number} добавлен")
            return "Комментарий добавлен"
        except Exception as e:
            logger.error(f"Ошибка при создании ревью: {e}")
            return f"Ошибка: {e}"

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def approve_pull_request(pr_number: int) -> str:
        """
        Одобряет pull request

        :param pr_number: номер pull request
        :return: сообщение об успехе или ошибке
        """
        try:
            logger.info(f"approve_pull_request pr_number: {pr_number}")
            repo = AIAutomation._get_repository()
            pr = AIAutomation._get_pull_request(repo, pr_number)
            pr.create_review(event="APPROVE")
            logger.info(f"PR {pr.number} одобрен")
            return "Pull request одобрен"
        except Exception as e:
            logger.error(f"Ошибка при одобрении PR: {e}")
            return f"Ошибка: {e}"

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def merge_pull_request_and_checkout(pr_number: int, commit_message: str = "") -> str:
        """
        Мержит pull request в основную ветку main и переключается на нее

        :param pr_number: номер pull request
        :param commit_message: сообщение коммита при merge
        :return: сообщение об успехе или ошибке
        """
        try:
            logger.info(f"merge_pull_request_and_checkout pr_number: {pr_number}, commit_message: {commit_message}")
            repo = AIAutomation._get_repository()
            pr = AIAutomation._get_pull_request(repo, pr_number)
            result = pr.merge(commit_message=commit_message)
            if result.merged:
                # после успешного мержа, подтягиваем изменения локально
                local_repo = Repo(AIAutomation.repo_path)
                # local_repo.remotes.origin.pull('main')
                local_repo.git.checkout("main")
                local_repo.git.fetch("origin")  # Получить последние изменения
                # local_repo.git.pull("origin", "main", "--rebase")  # Использовать rebase для синхронизации
                local_repo.git.reset("--hard", "origin/main") #удалит все локальные изменения в ветке main и синхронизирует её с удалённой.
                logger.info(f"PR {pr.number} успешно смержен")
                return "Pull request успешно смержен и выполнен checkout в main"
            else:
                logger.warning(f"Merge pull request {pr.number} не удался")
                return "Не удалось смержить pull request"
        except Exception as e:
            logger.error(f"Ошибка при merge pull request: {e}")
            return f"Ошибка: {e}"


    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def update_todo_list(tasks: dict) -> dict:
        """
        Агент передаёт список задач целиком, они заменяют предыдущие.
        Пример структуры task:
        {
            "task_1":{
                "add_logger" : {"desc": "Добавить логгер....", "done": True},
                "add_exit": {"desc": "Добавить use case выхода... ", "done": False}
            },
            "task_2":{
                "update_readme" : {"desc": "обновить документацию для файла....", "done": False},
                "add_feature": {"desc": "Добавить фичу для чегото там...", "done": False}
            },
            "task_3":{
                "do_refactoring" : {"desc": "сделать рефакторинг 2 файлов какихто там...", "done": False},
                "update_docs": {"desc": "обновить документацию для тестов...", "done": False}
            },
        }
        :param tasks: dict - список новых задач, или обновленный список задач
        :return: тот же самый список который созранился в базе
        """
        logger.info(f"update_todo_list tasks: {tasks}")
        AIAutomation.todo_list_storage.clear()
        AIAutomation.todo_list_storage.update(tasks)
        logger.info(f"update_todo_list: {AIAutomation.todo_list_storage}")
        return AIAutomation.todo_list_storage

    @staticmethod
    @tool
    @rate_limited_tools_per_minute
    def get_todo_list() -> dict:
        """
        Получить список запланированных задач в виде dict:

        :return:
        Пример структуры ответа: {"add_logger" : {"desc": "Добавить логгер", "done": False},"add_exit": {"desc": "Добавить use case выхода", "done": True}}
        """
        logger.info(f"get_todo_list tasks: {AIAutomation.todo_list_storage}")
        return AIAutomation.todo_list_storage

