from django.urls import path, include
from rest_framework import routers

from .views import (
    RepositoryView,
    TestView,
)

router = routers.DefaultRouter()
router.register(r'repository', RepositoryView, 'repository_view')
urlpatterns = [
    path('', include(router.urls)),
    path(route="test/", view=TestView.as_view(), name='test_view'),
] 