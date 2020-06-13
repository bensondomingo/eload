from pprint import pprint

from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from budgetplanner.models import CategoryType
from profiles.api.serializers import ProfileSerializer, UserSerializer
from profiles.models import Profile


USER_MODEL = get_user_model()
ADMIN_USERNAME = settings.ADMIN_USERNAME


class EndpointTestCase(APITestCase):

    admin_creds = {'username': ADMIN_USERNAME,
                   'email': f'{ADMIN_USERNAME}@budgetbuddy.com',
                   'password': 'test1234'}
    usera_creds = {'username': 'usera',
                   'email': 'usera@gmail.com', 'password': 'test1234'}
    userb_creds = {'username': 'userb',
                   'email': 'userb@gmail.com', 'password': 'test1234'}

    @classmethod
    def setUpClass(cls):
        # admin
        user = USER_MODEL.objects.create_superuser(**cls.admin_creds)
        # Create a token for this user
        Token.objects.create(user=user)

    @classmethod
    def tearDownClass(cls):
        for user in USER_MODEL.objects.all():
            user.delete()

    def setUp(self):
        # Create users
        self._create_user(**self.usera_creds)
        self._create_user(**self.userb_creds)

    def tearDown(self):
        return super().tearDown()

    def _create_user(self, username, email, password, superuser=False):
        if not superuser:
            user = USER_MODEL.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            # Create a token for this user
            Token.objects.create(user=user)
        else:
            user = USER_MODEL.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            # Create a token for this user
            Token.objects.create(user=user)

        return user

    def _login_user(self, username):
        user = USER_MODEL.objects.get(username=username)
        token = Token.objects.get(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def _logout_user(self):
        self.client.logout()


class UserEndpointTestCase(EndpointTestCase):

    list_endpoint = 'users-list'
    detail_endpoint = 'users-detail'

    def test_user_list(self):
        # Test admin access
        # List created users, make sure superuser is excluded
        self._login_user(self.admin_creds['username'])
        response = self.client.get(reverse(self.list_endpoint))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        users = USER_MODEL.objects.exclude(is_superuser=True)
        serializer = UserSerializer(users, many=True)
        self.assertEqual(serializer.data, response.data)
        self._logout_user()

        # Test user access
        self._login_user(self.usera_creds['username'])
        response = self.client.get(reverse(self.list_endpoint))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self._logout_user()

        # Test anonymous access
        response = self.client.get(reverse(self.list_endpoint))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_retrieve_update(self):
        usera_endpoint = reverse(self.detail_endpoint, kwargs={
                                 'username': self.usera_creds['username']})

        # admin access
        # Test update usera is_active to False
        usera = USER_MODEL.objects.get(username=self.usera_creds['username'])
        # Make sure its True by default
        self.assertEqual(usera.is_active, True)

        self._login_user(self.admin_creds['username'])
        response = self.client.get(usera_endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        data['is_active'] = False
        response = self.client.put(usera_endpoint, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_active'], False)
        self._logout_user()

        self._login_user(self.usera_creds['username'])
        data['is_active'] = True
        response = self.client.put(usera_endpoint, data=data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self._logout_user()

        # test anonymous access
        response = self.client.get(usera_endpoint)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_destroy(self):
        usera_endpoint = reverse(self.detail_endpoint, kwargs={
                                 'username': self.usera_creds['username']})

        self._login_user(self.admin_creds['username'])
        response = self.client.delete(usera_endpoint)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ProfileEndpointTestCase(EndpointTestCase):

    list_endpoint = 'profiles-list'
    detail_endpoint = 'profiles-detail'

    def test_profile_list(self):

        # usera
        self._login_user(self.usera_creds['username'])
        response = self.client.get(reverse(self.list_endpoint))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profiles = Profile.objects.all()
        serializer = ProfileSerializer(profiles, many=True)
        self.assertListEqual(serializer.data, response.data)
        self._logout_user()

        # test anonymous user access
        response = self.client.get(reverse(self.list_endpoint))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_update(self):
        usera_endpoint = reverse(self.detail_endpoint, kwargs={
                                 'user__username': self.usera_creds['username']})

        # usera
        self._login_user(self.usera_creds['username'])
        response = self.client.get(usera_endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        usera_profile = Profile.objects.get(
            user__username=self.usera_creds['username'])
        serializer = ProfileSerializer(usera_profile)
        self.assertDictEqual(dict(response.data), dict(serializer.data))

        data = response.json()
        data['bio'] = 'test_update_bio'
        del(data['avatar'])  # read_only
        response = self.client.put(usera_endpoint, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        usera_profile = Profile.objects.get(
            user__username=self.usera_creds['username'])
        self.assertEqual(usera_profile.bio, response.data['bio'])

        # Test update userb profile with usera credentials
        userb_endpoint = reverse(self.detail_endpoint, kwargs={
                                 'user__username': self.userb_creds['username']})
        # GET request is permitted
        response = self.client.get(userb_endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # PUT request is not permitted
        data = response.data
        data['bio'] = 'test_update_bio'
        del(data['avatar'])
        response = self.client.put(userb_endpoint, data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self._logout_user()

        # test anonymous user access
        response = self.client.get(usera_endpoint)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
