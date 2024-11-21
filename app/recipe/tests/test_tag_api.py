from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from decimal import Decimal
from core.models import Tag, Recipe
from recipe.serializer import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def detail_url(id):
    return reverse('recipe:tag-detail', args=[id])

class PublicTagAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
    
    def test_auth_required(self):
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    
class PrivateTagAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user=get_user_model().objects.create_user(
            email='test123@example.com',
            password='password123',
            name='test123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        Tag.objects.create(user=self.user, name='Tag1')
        Tag.objects.create(user=self.user, name='Tag2')
        res = self.client.get(TAGS_URL)
        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_retrieve_limited_to_user(self):
        other_user = get_user_model().objects.create_user(
            email='test1234@example.com',
            name='pass123',
            password='password123'
        )
        Tag.objects.create(user=other_user, name='Tag1')
        tag = Tag.objects.create(user=self.user, name='Tag2')
        
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)
    
    def test_update_tag(self):
        tag = Tag.objects.create(user=self.user, name='Tag1')
        payload = {'name': 'Tag 2'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])
    def test_delete_tag(self):
        tag = Tag.objects.create(user=self.user, name='Tag1')
        
        url = detail_url(tag.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_tags_assigned(self):
        tag1 = Tag.objects.create(user=self.user, name='Tagg1')
        tag2 = Tag.objects.create(user=self.user, name='Tag2')

        recipe = Recipe.objects.create(
            user = self.user,
            title='New Recipe',
            time_minutes=22,
            price=Decimal('5.25'),
            description='Sameple recipe description',
            link='http://example.com.recipe.pdf'
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})
        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)
    
    def test_filtered_tags_unique(self):
        tag1 = Tag.objects.create(user=self.user, name='Tag1')

        r1 = Recipe.objects.create(
            user =self.user,
            title='New Recipe',
            time_minutes=22,
            price=Decimal('5.25'),
            description='Sameple recipe description',
            link='http://example.com.recipe.pdf'
        )

        r2 = Recipe.objects.create(
            user =self.user,
            title='Other Recipe',
            time_minutes=22,
            price=Decimal('5.25'),
            description='Sameple recipe description',
            link='http://example.com.recipe.pdf'
        )
        r1.tags.add(tag1)
        r2.tags.add(tag1)
        res = self.client.get(TAGS_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)
        s1 = TagSerializer(tag1)
        self.assertIn(s1.data,res.data)