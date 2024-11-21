from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe, Tag, Ingredient
from recipe.serializer import RecipeSerializer, RecipeDetailSerializer, TagSerializer
import tempfile
import os

from PIL import Image

RECIPES_URL = reverse('recipe:recipe-list')

def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])

def detail_url(_id):
    return reverse('recipe:recipe-detail', args=[_id])


def create_recipe(user, **params):
    arg = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description' : 'Sameple recipe description',
        'link': 'http://example.com.recipe.pdf'
    }

    arg.update(params)
    recipe = Recipe.objects.create(user=user,**arg)
    return recipe

class PublicRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
    
    def test_auth_required(self):
        res = self.client.get(RECIPES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test123@example.com',
            password='test123',
            name='test name'
        )

        self.client.force_authenticate(self.user)
    
    def test_retrieve_recipes(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        another_user = get_user_model().objects.create_user(
            email='anothertest@example.com',
            name='test 321',
            password='testpassword'
        )
        create_recipe(user=another_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.get(url)
        
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_create_recipe(self):
        payload = {
            'title': 'Sample recipe title',
            'time_minutes': 22,
            'price': Decimal('5.25'),
            'description' : 'Sameple recipe description',
            'link': 'http://example.com.recipe.pdf',
        }
        res = self.client.post(RECIPES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)
    
    def test_partial_update(self):

        original_link = 'http://example.com/recipe.pdf'
        recipe = create_recipe(self.user)
        new_link = 'http://new_example.com/recipe.pdf'
        url = detail_url(recipe.id)
        res = self.client.patch(url,{'link': new_link})
        self.assertEqual(res.status_code,status.HTTP_200_OK)
        serializer = RecipeDetailSerializer(res.data)
        self.assertEqual(res.data['link'], new_link)
    
    def test_delete_recipe(self):
        recipe = create_recipe(self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        exist = Recipe.objects.filter(id=recipe.id).exists()
        self.assertFalse(exist)

        
    def test_full_upadte(self):
        recipe = create_recipe(
            user = self.user,
            title = 'test title',
            link = 'https://example.com/recipe.pdf',
            description = 'sample recipe description',
        )
        
        payload = {
            'title': 'new title',
            'link' : 'http://newlink.com/recipe.pdf',
            'description': 'the new description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
        }

        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(self.user, recipe.user)

    def test_access_other_user_recipe(self):
        other_user = get_user_model().objects.create_user(
            email='test123@other.com',
            password='test123',
            name='other name'
        )
        recipe = create_recipe(other_user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())
    
    def test_create_recipe_with_new_tags(self):
        payload = {
            'title': 'new title',
            'link' : 'http://newlink.com/recipe.pdf',
            'description': 'the new description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
            'tags':[{'name': 'Thai'}, {'name':'Dinner'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            self.assertTrue(recipe.tags.filter(name=tag['name']).exists())

        
    def test_create_recipe_with_existing_tag(self):
        tag_indian = Tag.objects.create(user=self.user, name= "Indian")
        payload = {
            'title': 'new title',
            'link' : 'http://newlink.com/recipe.pdf',
            'description': 'the new description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
            'tags':[{'name': 'Indian'}, {'name': 'Breakfast'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            self.assertTrue(recipe.tags.filter(name=tag['name']).exists())

    def test_create_tag_on_update_recipe(self):
        recipe = create_recipe(user=self.user)

        payload = {'tags':[{'name': 'Launch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(Tag.objects.filter(name='Launch').exists())
    
    def test_update_recipe_assign_tag(self):
        tag = Tag.objects.create(user=self.user, name = 'Tag')

        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)
        url = detail_url(recipe.id)
        new_tag = Tag.objects.create(user=self.user, name = 'New Tag')
        payload = {
            'tags':[{
                'name': 'New Tag'
            }]
        }
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(tag, recipe.tags.all())
        self.assertIn(new_tag, recipe.tags.all())
    
    def clear_recipe_tags(self):
        recipe = create_recipe(user=self.user)
        recipe.tags.add(Tag.objects.create(user=self.user, name = 'Tag'))

        payload = {
            'tags': []
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
    
    def test_create_recipe_with_new_ingredients(self):
        payload = {
            'title': 'new title',
            'link' : 'http://newlink.com/recipe.pdf',
            'description': 'the new description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
            'ingredients': [{'name': 'Ingredient1'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes[0].ingredients.count(), 1)
        ingredients = Ingredient.objects.all()
        self.assertEqual(ingredients.count(), 1)
        for ingredient in payload['ingredients']:
            self.assertTrue(Ingredient.objects.filter(name=ingredient['name']).exists())

    def test_create_recipe_with_existing_ingredients(self):
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Ingredient1'
        )

        payload = {
            'title': 'new title',
            'link' : 'http://newlink.com/recipe.pdf',
            'description': 'the new description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
            'ingredients': [{'name': 'Ingredient1'}]
        }

        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipe.count(), 1)
        self.assertEqual(recipe[0].ingredients.all().count(), 1)
        self.assertEqual(Ingredient.objects.filter(user=self.user).count(), 1)
        for ingredient in payload['ingredients']:
            self.assertTrue(Ingredient.objects.filter(name=ingredient['name']).exists())
        

    def test_update_with_new_ingredient(self):
        payload = {
            'ingredients':[{'name':'Ingredient1'}, {'name': 'Ingredient2'}]
        }

        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.all().count(), 2)
        for ingredient in payload['ingredients']:
            self.assertTrue(Ingredient.objects.filter(name=ingredient['name']).exists())


    def test_update_with_existing_ingredient(self):
        payload = {
            'ingredients':[{'name':'Ingredient1'}]
        }
        ingredient = Ingredient.objects.create(
            user=self.user,
            name= 'Ingredient1'
        )
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.ingredients.all().count(), 1)
        self.assertEqual(Ingredient.objects.all().count(), 1)
        self.assertTrue(Ingredient.objects.filter(name=ingredient.name).exists())

    def test_filter_by_tags(self):
        r1 = create_recipe(user=self.user, title='Thai Curry')
        r2 = create_recipe(user=self.user, title='Pork')
        tag1 = Tag.objects.create(user=self.user, name='Tag1')
        tag2 = Tag.objects.create(user=self.user, name='Tag2')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user)
        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPES_URL, params)
        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        r1 = create_recipe(user=self.user, title='Thai Curry')
        r2 = create_recipe(user=self.user, title='Pork')
        ing1 = Ingredient.objects.create(user=self.user, name='ing1')
        ing2 = Ingredient.objects.create(user=self.user, name='ing2')
        r1.ingredients.add(ing1)
        r2.ingredients.add(ing2)
        r3 = create_recipe(user=self.user)
        params = {'ingredients': f'{ing1.id},{ing2.id}'}
        res = self.client.get(RECIPES_URL, params)
        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test123@example.com',
            password='test123',
            name='test name'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)
    
    def tearDown(self):
        self.recipe.image.delete()
    
    def test_upload_image(self):
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')
        
        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
