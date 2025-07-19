import logging
import pickle
import sqlite3
from collections import defaultdict
from typing import Type


from ai_integration.models import (
    AIStateDefault,
    AIStateStorage,
    AIStateWrites,
    AIStateBlobs,
    AIState,
)

logger = logging.getLogger(__name__)


class DBDict(defaultdict):
    @classmethod
    def db_dict_factory(
        cls, db_path="mydatabase.db", record_id="default_id"
    ):
        def create_db_dict(default_factory=None):
            if default_factory is None:
                table_name = "blobs"
            elif default_factory is dict:
                table_name = "writes"
            elif callable(default_factory) and default_factory() == defaultdict(dict):
                table_name = "storage"
            else:
                table_name = "default"
            instance = cls(default_factory, db_path, table_name, record_id)
            return instance


        return create_db_dict

    def __init__(self, default_factory, db_path, table_name, record_id):
        super().__init__(default_factory)
        self.table_name = table_name
        self.record_id = record_id
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id TEXT PRIMARY KEY, data TEXT)")
        try:
            self.load_from_db()
        except Exception as e:
            logger.error(f"Error: {e}")

    def load_from_db(self):
        try:
            self.cursor.execute(f"SELECT data FROM {self.table_name} WHERE id = ?", (self.record_id,))
            result = self.cursor.fetchone()
            if result:
                data = pickle.loads(result[0])
                super().update(data)
        except Exception as e:
            logger.error(f"load_from_db error in {self.table_name}, {e}")
        logger.info(f"Loaded {self.table_name} from {self.record_id}")

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.sync_data()

    def sync_data(self):
        try:
            data = pickle.dumps(dict(self))
            self.cursor.execute(f"INSERT OR REPLACE INTO {self.table_name} (id, data) VALUES (?, ?)", (self.record_id, data))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Sync error in {self.table_name}: {e}")


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # print(f"Результат: {self.__class__.__name__}: {self}")
        self.sync_data()


    def __del__(self):
        try:
            # print(f"Результат: {self.__class__.__name__}: {self}")
            self.sync_data()
        except AttributeError as e:
            logger.error(f"Error: {e}")


class DjangoDBDict(defaultdict):
    @classmethod
    def db_dict_factory(cls, record_id="default_id", table_name=None):
        def create_db_dict(default_factory=None):
            if table_name:
                model_name=table_name
            elif default_factory is None:
                model_name = AIStateBlobs
            elif default_factory is dict:
                model_name = AIStateWrites
            elif callable(default_factory) and default_factory() == defaultdict(dict):
                model_name = AIStateStorage
            else:
                model_name = AIStateDefault
            instance = cls(default_factory=default_factory, model_name=model_name, record_id=record_id)
            return instance

        return create_db_dict

    def __init__(self, default_factory, model_name: Type[AIState], record_id):
        super().__init__(default_factory)
        self.model_name = model_name
        self.record_id = record_id

        try:
            self.load_from_db()
        except Exception as e:
            logger.error(f"Error: {e}")

    #Для случаев автоматической синхронизации при каждом обновлении словаря
    # def __setitem__(self, key, value):
    #     super().__setitem__(key, value)
    #     self.sync_data()
    #
    # def update(self, *args, **kwargs):
    #     super().update(*args, **kwargs)
    #     self.sync_data()

    def load_from_db(self):
        try:
            self.model_orm, _ = self.model_name.objects.get_or_create(id=self.record_id)
            if self.model_orm.data:
                data = pickle.loads(self.model_orm.data)
                super().update(data)
        except Exception as e:
            logger.error(f"load_from_db error in {self.model_name}, {e}")
        logger.info(f"Loaded {self.model_name} from {self.record_id}")

    def sync_data(self):
        try:
            logger.info(f"Syncing {self.model_name} from {self.record_id}")
            data = pickle.dumps(dict(self))
            if data != self.model_orm.data:
                self.model_orm.data = data
                self.model_orm.save()
        except Exception as e:
            logger.error(f"Sync error in {self.model_name}: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # print(f"Результат: {self.__class__.__name__}: {self}")
        self.sync_data()

    def __del__(self):
        try:
            # print(f"Результат: {self.__class__.__name__}: {self}")
            self.sync_data()
        except AttributeError as e:
            logger.error(f"Error: {e}")