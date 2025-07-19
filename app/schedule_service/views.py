from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, generics, mixins


from ai_integration.helpers.agent_helper import AIAutomation
from ai_integration.helpers.db_dict_factory import DjangoDBDict
from ai_integration.models import AIStateDefault

from github_integration.models import Repository
from schedule_service.serializers import RepositorySerializer


class RepositoryView(viewsets.ModelViewSet):
    serializer_class = RepositorySerializer
    queryset = Repository.objects.all()


class TestView(APIView):
    def post(self, request):
        tools = AIAutomation(
            repo_url="***",
            github_token="***",
            todo_list_storage=DjangoDBDict.db_dict_factory(
                record_id="chat_id", table_name=AIStateDefault
            )(),
            rate_limit=10
        )
        tools.update_todo_list({"test":123})
        return Response({})