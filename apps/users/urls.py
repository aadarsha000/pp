from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
    TokenObtainPairView

)
from .views import LogoutView, ManageSelfView, PromoteUserView, RegisterView, UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('register/', RegisterView.as_view(), name='user_register'),
    path('me/', ManageSelfView.as_view(), name='auth-me'),
    path('users/<int:pk>/promote/', PromoteUserView.as_view(), name='promote-user'),

    path('logout/', LogoutView.as_view(), name='logout'),

]
