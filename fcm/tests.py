from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

from cphapp.test_assets.defines import USERA, USERB

USER_MODEL = get_user_model()


class FCMAPITestCase(APITestCase):
    config_endpoint = 'fcm-config'

    def _login_user(self, username):
        user = USER_MODEL.objects.get(username=username)
        token = Token.objects.get_or_create(user=user)[0]
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def _logout_user(self):
        self.client.logout()

    @classmethod
    def setUpClass(cls) -> None:
        # Create test users
        USER_MODEL.objects.create(**USERA)
        USER_MODEL.objects.create(**USERB)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        USER_MODEL.objects.all().delete()


class FCMConfigAPITestCase(FCMAPITestCase):

    def test_retrieve_no_auth(self):
        endpoint = reverse(self.config_endpoint)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_config(self):
        endpoint = reverse(self.config_endpoint)
        self._login_user(USERA.get('username'))
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data == settings.FCM_CONFIG)
