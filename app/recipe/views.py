from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)

from core.models import Recipe, Tag, Ingredient
from . import serializer


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'tags',
                OpenApiTypes.STR,
                description='Comma separated list of IDs to filter'
            ),
            OpenApiParameter(
                'ingredients',
                OpenApiTypes.STR,
                description='Comma separated list of IDs to filter'
            ),
        ]
    )
)
class RecipeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing recipes in the system.

    - Provides CRUD operations for recipes.
    - Supports listing, creating, retrieving, updating, and deleting recipes.
    - Allows uploading an image for a specific recipe via a custom action.

    Serializer:
    - Default: RecipeDetailSerializer
    - List: RecipeSerializer
    - Upload Image: RecipeImageSerializer

    Authentication: TokenAuthentication
    Permissions: IsAuthenticated
    """
    serializer_class = serializer.RecipeDetailSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Recipe.objects.all()

    def _params_to_ints(self, qs):
        return [int(q) for q in qs.split(',')]

    def get_queryset(self):
        """
        Return recipes for the authenticated user, ordered by most recent.

        This ensures that users only see their own recipes.
        """
        tags = self.request.query_params.get('tags')
        ingredients = self.request.query_params.get('ingredients')
        queryset = self.queryset
        if tags:
            tag_id = self._params_to_ints(tags)
            queryset = queryset.filter(tags__id__in=tag_id)
        if ingredients:
            ingre_id = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredients__id__in=ingre_id)
        return queryset.filter(
            user=self.request.user).order_by('-id').distinct()

    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the current action.

        - List: RecipeSerializer
        - Upload Image: RecipeImageSerializer
        - Default: RecipeDetailSerializer
        """
        if self.action == 'list':
            return serializer.RecipeSerializer
        elif self.action == 'upload_image':
            return serializer.RecipeImageSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        """
        Save the new recipe with the authenticated user as the owner.
        """
        serializer.save(user=self.request.user)

    @action(methods=['POST'], detail=True, url_path='upload-image')
    def upload_image(self, request, pk=None):
        """
        Custom action to upload an image for a specific recipe.

        Endpoint: `POST /recipes/{id}/upload-image/`
        - Expects an image file as input.
        - Returns the updated recipe data or validation errors.
        """
        recipe = self.get_object()
        serializer = self.get_serializer(recipe, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'assigned_only',
                OpenApiTypes.INT, enum=[0, 1],
                description='Filter by items assigned to recipes'
            ),

        ]
    )
)
class BaseRecipeAttrViewSet(mixins.DestroyModelMixin,
                            mixins.UpdateModelMixin,
                            mixins.ListModelMixin,
                            viewsets.GenericViewSet):
    """
    Base ViewSet for managing recipe attributes like tags and ingredients.

    - Provides listing, updating, and deleting functionality.
    - Restricted to authenticated users.
    - Filters results to show only items created by the authenticated user.

    Authentication: TokenAuthentication
    Permissions: IsAuthenticated
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return attributes for the authenticated user, ordered by name.
        """
        is_assigned_only = bool(
            int(self.request.query_params.get('assigned_only', 0)))
        queryset = self.queryset
        if is_assigned_only:
            queryset = queryset.filter(recipe__isnull=False)

        return queryset.filter(
            user=self.request.user).order_by('-name').distinct()


class TagViewSet(BaseRecipeAttrViewSet):
    """
    ViewSet for managing tags in the system.

    - Extends BaseRecipeAttrViewSet for shared behavior.
    - Provides listing, updating, and deleting of tags.

    Serializer: TagSerializer
    Queryset: All Tag objects for the authenticated user.
    """
    serializer_class = serializer.TagSerializer
    queryset = Tag.objects.all()


class IngredientViewSet(BaseRecipeAttrViewSet):
    """
    ViewSet for managing ingredients in the system.

    - Extends BaseRecipeAttrViewSet for shared behavior.
    - Provides listing, updating, and deleting of ingredients.

    Serializer: IngredientSerializer
    Queryset: All Ingredient objects for the authenticated user.
    """
    serializer_class = serializer.IngredientSerializer
    queryset = Ingredient.objects.all()
