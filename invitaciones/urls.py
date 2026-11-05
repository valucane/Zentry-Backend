from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvitacionViewSet

router = DefaultRouter()
router.register(r'', InvitacionViewSet, basename='invitaciones')

urlpatterns = [
    path('', include(router.urls)),
]
