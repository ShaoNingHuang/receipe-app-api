"""
Test for models
"""
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from core import models

class ModelTest(TestCase):
    def test_create_user_with_email_successful(self):
        email = 'test@example.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )
        self.assertEqual(user.email, email)
    def test_new_user_email_normalize(self):
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['Test3@EXAMPLE.COM', 'Test3@example.com'],
            ['test4@example.COM', 'test4@example.com']
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'sample123')
            self.assertEqual(user.email, expected)


    def test_new_user_without_email_error(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')
    
    def test_create_superuser(self):
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test123'
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
    
    def test_create_recipe(self):
        user = get_user_model().objects.create_user(
            email='test123@example.com',
            password="test123",
        )
        recipe = models.Recipe.objects.create(
            user = user,
            title = 'Sample Recipe Name',
            time_minutes = 5,
            price = Decimal('5.50'),
            description = "Sample recipe description"
        )
        self.assertEqual(str(recipe), recipe.title)
    
    def test_create_tags(self):
        user = get_user_model().objects.create_user(
            email='test123@example,com', 
            password='pass123', name='test123'
        )
        tag = models.Tag.objects.create(user=user,name='Testing Tag')
        self.assertEqual(str(tag), tag.name)
        self.assertTrue(models.Tag.objects.filter(name='Testing Tag').exists())

    def test_create_ingredient(self):
        user = get_user_model().objects.create_user(
            email='test123@example,com', 
            password='pass123', name='test123'
        )
        ingredient = models.Ingredient.objects.create(user=user, name='New Ingredient')
        self.assertEqual(str(ingredient), ingredient.name)
        self.assertTrue(models.Ingredient.objects.filter(name='New Ingredient').exists())
    @patch('core.models.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f"uploads/recipe/{uuid}.jpg")

        