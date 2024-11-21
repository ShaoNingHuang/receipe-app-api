from rest_framework import generics, authentication, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from user.serializers import UserSerializer, AuthTokenSerializer


class CreateUserView(generics.CreateAPIView):
    """
    View to create a new user in the system.

    This endpoint allows anonymous users to register by providing
    necessary user information (e.g., email, password).
    
    Serializer: UserSerializer
    """
    serializer_class = UserSerializer


class CreateTokenView(ObtainAuthToken):
    """
    View to create an authentication token for a user.

    This endpoint allows users to obtain an authentication token
    by providing valid credentials (email and password).
    
    Serializer: AuthTokenSerializer
    Renderer Classes: Configured from the default renderer classes.
    """
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class ManageUserView(generics.RetrieveUpdateAPIView):
    """
    View to retrieve or update the authenticated user's information.

    This endpoint is restricted to authenticated users, allowing them
    to view or update their own user profile.

    Serializer: UserSerializer
    Authentication: TokenAuthentication
    Permissions: IsAuthenticated
    """
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Retrieve and return the authenticated user.

        This method ensures that only the currently logged-in user
        can access or update their information.
        """
        return self.request.user