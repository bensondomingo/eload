from django.conf import settings

import firebase_admin
from firebase_admin import credentials

try:
    app = firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(settings.FCM_PRIVATE_KEY_FILE)
    app = firebase_admin.initialize_app(cred)
