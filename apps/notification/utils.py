from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from users.models import Role
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_validated_user_from_token(token_string: str):
    if not token_string:
        return None
    
    try:
        access_token = AccessToken(token_string)
        user_id = access_token['user_id']
        user = User.objects.get(id=user_id, is_active=True)
        
        # Only HR Admins and Recruiters get real-time notifications
        if user.role in [Role.ADMIN, Role.RECRUITER]:
            return user
        return None
        
    except (TokenError, InvalidToken, User.DoesNotExist, KeyError):
        return None
