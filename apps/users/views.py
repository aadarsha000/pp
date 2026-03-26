from django.shortcuts import render
from rest_framework import generics, status, views
from rest_framework.permissions import AllowAny

from apps.users.permissions import IsHRAdmin
from config.utils import success_response, error_response

from .serializers import LogoutSerializer, UserProfileSerializer, UserRegistrationSerializer, UserRoleUpdateSerializer
from .models import CustomUser

from rest_framework_simplejwt.tokens import RefreshToken

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]



class ManageSelfView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    http_method_names = ['get', 'patch']

    def get_object(self):
        return self.request.user



class PromoteUserView(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRoleUpdateSerializer
    permission_classes = [IsHRAdmin]
    
    http_method_names = ['patch'] 



class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({"message": "Successfully logged out."}, status=status.HTTP_204_NO_CONTENT)