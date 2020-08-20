import urllib
from datetime import datetime

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token

from cphapp.models import LoadOutlet, LoadTransaction, UserAgent
from cphapp.test_assets import defines


USER_MODEL = get_user_model()


class CphAppAPITestCase(APITestCase):
    buy_product_endpoint = 'buy-product'
    list_endpoint = 'transaction-list'
    detail_endpoint = 'transaction-detail'

    def _login_user(self, username):
        user = USER_MODEL.objects.get(username=username)
        token = Token.objects.get_or_create(user=user)[0]
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    def _logout_user(self):
        self.client.logout()

    @classmethod
    def setUpClass(cls) -> None:
        # Create UserAgent objects
        ua_a = UserAgent.objects.create(
            device='test', platform='test', device_hash=defines.DEV_HASH_USERA)
        ua_b = UserAgent.objects.create(
            device='test', platform='test', device_hash=defines.DEV_HASH_USERB)

        user_a = USER_MODEL.objects.create(**defines.USERA)
        user_b = USER_MODEL.objects.create(**defines.USERB)
        USER_MODEL.objects.create(**defines.USERC)

        user_a.profile.user_agent = ua_a
        user_a.profile.save()
        user_b.profile.user_agent = ua_b
        user_b.profile.save()

        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        UserAgent.objects.all().delete()
        USER_MODEL.objects.all().delete()


class LoadOutletAPITestCase(CphAppAPITestCase):

    def add_new_outlet(self, phone_number):
        query_params = {'phone_number': phone_number}
        endpoint = f'{reverse(self.buy_product_endpoint)}?' + \
            urllib.parse.urlencode(query_params)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_new_outlet(self):
        self._login_user(defines.USERA['username'])
        phone_numbers = [defines.PHONE_NUMBER_GLOBE,
                         defines.PHONE_NUMBER_SMART, defines.PHONE_NUMBER_SUN]
        for phone_number in phone_numbers:
            self.add_new_outlet(phone_number)
        self.assertEqual(LoadOutlet.objects.all().count(), 3)

    def test_add_new_outlet_invalid_phone_number(self):
        self._login_user(defines.USERA['username'])
        query_params = {'phone_number': defines.PHONE_NUMBER_INVALID}
        endpoint = f'{reverse(self.buy_product_endpoint)}?' + \
            urllib.parse.urlencode(query_params)
        resp = self.client.get(endpoint)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoadTransactionAPITestCase(CphAppAPITestCase):

    @classmethod
    def setUpClass(cls) -> None:
        """
        Since post_save handlers are async, actual process was mocked with
        synchrounous to perform test properly. i.e how can you call
        self.assertEqual if the instance is being update by another task?
        """
        # post_save.disconnect(post_eload_data, LoadTransaction)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()

    def setUp(self):
        latc = LoadOutletAPITestCase()
        self._login_user(defines.USERA['username'])
        latc.client = self.client
        latc.add_new_outlet(defines.PHONE_NUMBER_GLOBE)
        return super().setUp()

    def test_create_transaction_no_auth(self):
        self._logout_user()
        endpoint = reverse(self.list_endpoint)
        resp = self.client.post(endpoint, {})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_transaction_retailer_invalid(self):
        self._login_user(defines.USERA['username'])
        endpoint = reverse(self.list_endpoint)

        # 1. Invalid amount
        post_data = {
            'amount': 1,
            'phone_number': defines.PHONE_NUMBER_GLOBE,
            'outlet_id': 'load-globe'
        }
        response = self.client.post(endpoint, post_data)
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

        # 2. Invalid phone_number
        post_data = {
            'amount': 5,
            'phone_number': defines.PHONE_NUMBER_INVALID,
            'outlet_id': 'load-globe'
        }

        response = self.client.post(endpoint, post_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_transaction_user_initiated(self):
        """ Test sunny day scenario (transaction.status == 'settled') """

        endpoint = reverse(self.list_endpoint)
        # id is provided just to accomplish test mocking
        # posted_data mocks the post data from the user
        posted_data = {
            'id': defines.ORDER_TEST_ID,
            'amount': 5,
            'phone_number': defines.PHONE_NUMBER_GLOBE,
            'outlet_id': 'load-globe',
        }

        response = self.client.post(endpoint, posted_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        obj_id = response.json().get('id')
        obj = LoadTransaction.objects.get(id=obj_id)
        self.assertEqual(obj.retailer.username, defines.USERA['username'])
        self.assertEqual(obj.id.hex, posted_data.get('id'))
        self.assertEqual(obj.amount, posted_data.get('amount'))
        self.assertEqual(obj.phone_number, posted_data.get('phone_number'))
        self.assertEqual(obj.outlet_id, posted_data.get('outlet_id'))

        self.assertTrue(obj.confirmation_code is not None)
        self.assertTrue(obj.order_id is not None)
        self.assertEqual(obj.status, 'settled')
        self.assertEqual(obj.transaction_type, 'sellorder')
        self.assertTrue(isinstance(obj.transaction_date, datetime))
        self.assertTrue(obj.user_agent is not None)
        self.assertTrue(obj.running_balance is not None)
        self.assertTrue(obj.posted_amount == -obj.amount)

        # Test retrieve endpoint
        endpoint = reverse(self.detail_endpoint,
                           kwargs={'pk': defines.ORDER_TEST_ID})
        resp = self.client.get(endpoint)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp = self.client.delete(endpoint)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_transaction_sync_initiated(self):
        pass
