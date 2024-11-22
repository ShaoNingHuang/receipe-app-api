from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal
from core.models import Ingredient, Recipe
from recipe.serializer import IngredientSerializer


INGREDIENT_URL = reverse('recipe:ingredient-list')


def detail_url(id):
    return reverse('recipe:ingredient-detail', args=[id])


class PublicIngredientAPITest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test1234@example.com',
            password='test123',
            name='test'
        )
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test123@example',
            password='pass123',
            name='test123',
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        ingredient = Ingredient.objects.create(
            user=self.user,
            name="New Ingredient"
        )
        res = self.client.get(INGREDIENT_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_limited_to_user(self):
        other_user = get_user_model().objects.create_user(
            email='test1234@example.com',
            name='pass123',
            password='password123'
        )
        Ingredient.objects.create(user=other_user, name='Ingredient1')
        ingredient = Ingredient.objects.create(
            user=self.user, name='Ingredient2')

        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        ingredient = Ingredient.objects.create(
            user=self.user, name='Ingredient1')
        url = detail_url(ingredient.id)
        payload = {
            'name': 'Ingredient2'
        }

        res = self.client.patch(url, payload)
        ingredient.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(str(ingredient), res.data['name'])

    def test_delete_ingredient(self):
        ingredient = Ingredient.objects.create(
            user=self.user, name='Ingredient1')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())

    def test_ingredients_assigned(self):
        in1 = Ingredient.objects.create(user=self.user, name='Ing1')
        in2 = Ingredient.objects.create(user=self.user, name='Ing2')

        recipe = Recipe.objects.create(
            user=self.user,
            title='New Recipe',
            time_minutes=22,
            price=Decimal('5.25'),
            description='Sameple recipe description',
            link='http://example.com.recipe.pdf'
        )
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})
        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        in1 = Ingredient.objects.create(user=self.user, name='Ing1')

        r1 = Recipe.objects.create(
            user=self.user,
            title='New Recipe',
            time_minutes=22,
            price=Decimal('5.25'),
            description='Sameple recipe description',
            link='http://example.com.recipe.pdf'
        )

        r2 = Recipe.objects.create(
            user=self.user,
            title='Other Recipe',
            time_minutes=22,
            price=Decimal('5.25'),
            description='Sameple recipe description',
            link='http://example.com.recipe.pdf'
        )
        r1.ingredients.add(in1)
        r2.ingredients.add(in1)
        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)
        s1 = IngredientSerializer(in1)
        self.assertIn(s1.data, res.data)
