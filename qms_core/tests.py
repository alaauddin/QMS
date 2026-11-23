from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Service, Token


@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
})
class TokenCreationTests(TestCase):
    def setUp(self):
        self.service = Service.objects.create(name="Test service", prefix="T")
        self.web_url = reverse("qms_core:take_token", args=[self.service.id])
        self.api_url = reverse("qms_core:api_take_token", args=[self.service.id])

    def test_web_kiosk_creates_one_token_and_returns_its_ticket(self):
        client = Client(enforce_csrf_checks=True)
        kiosk = client.get(reverse("qms_core:kiosk"))
        self.assertEqual(kiosk.status_code, 200)
        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            self.web_url + "?format=print",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 1)
        self.assertContains(response, '<div class="token-number">1</div>', html=True)

    def test_get_cannot_create_tokens(self):
        self.assertEqual(self.client.get(self.web_url).status_code, 405)
        self.assertEqual(self.client.get(self.api_url).status_code, 405)
        self.assertEqual(Token.objects.count(), 0)

    def test_mobile_post_still_creates_one_token(self):
        response = self.client.post(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 1)
        self.assertEqual(response.json()["token"]["number"], 1)
