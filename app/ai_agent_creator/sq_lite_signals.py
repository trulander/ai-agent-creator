from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver


class AIAgentCreatorConfig(AppConfig):
    name = 'ai_agent_creator'

    def ready(self):
        @receiver(connection_created)
        def setup_sqlite_pragmas(sender, connection, **kwargs):
            if connection.vendor == 'sqlite':
                cursor = connection.cursor()
                cursor.execute('PRAGMA journal_mode=wal;')
                cursor.execute('PRAGMA busy_timeout=10000;')
                cursor.close()
