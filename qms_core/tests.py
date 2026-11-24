from django.test import Client, TestCase, override_settings
import hashlib
import json
import tempfile
from pathlib import Path
from django.urls import reverse
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .consumers import CounterConsumer
from .models import Counter, Screen, Service, SystemConfig, Token
from .views import call_voice_text


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
        csrf_token = client.cookies["qms_csrftoken"].value

        response = client.post(
            self.web_url + "?format=print",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 1)
        self.assertContains(response, '<div class="token-number">1</div>', html=True)

    def test_current_csrf_cookie_works_after_cookie_rotation(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("qms_core:kiosk"))
        client.cookies["qms_csrftoken"] = "a" * 32

        response = client.post(
            self.web_url + "?format=print",
            HTTP_X_CSRFTOKEN=client.cookies["qms_csrftoken"].value,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 1)

    def test_get_cannot_create_tokens(self):
        self.assertEqual(self.client.get(self.web_url).status_code, 405)
        self.assertEqual(self.client.get(self.api_url).status_code, 405)
        self.assertEqual(Token.objects.count(), 0)

    def test_mobile_post_still_creates_one_token(self):
        response = self.client.post(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 1)
        self.assertEqual(response.json()["token"]["number"], 1)

    def test_kiosk_shows_services_without_queue_or_ads(self):
        Token.objects.create(number=1, service=self.service, status="waiting")
        response = self.client.get(reverse("qms_core:kiosk"))

        self.assertContains(response, self.service.name)
        self.assertNotIn("queue_columns", response.context)
        self.assertNotContains(response, 'class="queue-panel"')
        self.assertNotContains(response, 'id="adCarousel"')

    def test_web_and_mobile_issue_events_include_the_new_token(self):
        layer = get_channel_layer()
        channel = async_to_sync(layer.new_channel)()
        async_to_sync(layer.group_add)("queue_updates", channel)

        self.client.post(self.web_url)
        web_event = async_to_sync(layer.receive)(channel)
        self.assertEqual(web_event["type"], "token_issued")
        self.assertEqual(web_event["full_token"], "T1")
        self.assertEqual(async_to_sync(layer.receive)(channel)["type"], "queue_changed")

        self.client.post(self.api_url)
        mobile_event = async_to_sync(layer.receive)(channel)
        self.assertEqual(mobile_event["type"], "token_issued")
        self.assertEqual(mobile_event["full_token"], "T2")
        self.assertEqual(async_to_sync(layer.receive)(channel)["type"], "queue_changed")


class PublicScreenTests(TestCase):
    def test_screen_shows_current_call_and_two_queue_columns_without_ads(self):
        service = Service.objects.create(name="Registration", prefix="R")
        counter = Counter.objects.create(number=3)
        screen = Screen.objects.create(name="Main lobby", device_token="main-lobby")
        screen.counters.add(counter)
        for number in range(1, 19):
            Token.objects.create(number=number, service=service, status="waiting")
        Token.objects.create(
            number=19, service=service, status="called",
            counter=counter, called_at=timezone.now(),
        )

        response = self.client.get(reverse("qms_core:public_screen", args=[screen.device_token]))
        columns = response.context["queue_columns"]
        self.assertEqual([len(column) for column in columns], [8, 8])
        self.assertEqual(response.context["current_token"].number, 19)
        self.assertContains(response, 'id="token-display"')
        self.assertNotContains(response, 'id="publicAdCarousel"')

        data = self.client.get(
            reverse("qms_core:api_get_screen_data", args=[screen.device_token])
        ).json()
        self.assertEqual(data["queue"], [f"R{number}" for number in range(1, 17)])
        self.assertEqual(data["latest_issued"]["full_token"], "R19")

    def test_screen_api_exposes_cached_mp3_url_for_current_call(self):
        service = Service.objects.create(name="Registration", prefix="R")
        counter = Counter.objects.create(number=3)
        screen = Screen.objects.create(name="Main lobby", device_token="main-lobby")
        screen.counters.add(counter)
        token = Token.objects.create(
            number=7, service=service, status="called",
            counter=counter, called_at=timezone.now(),
        )
        voice_name = SystemConfig.get_config().voice_name
        voice_text = call_voice_text(token.number, counter.number)
        file_hash = hashlib.md5(f"{voice_text}_{voice_name}".encode()).hexdigest()

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                audio_path = Path(media_root) / "audio_cache" / f"{file_hash}.mp3"
                audio_path.parent.mkdir()
                audio_path.write_bytes(b"ID3" + b"x" * 1100)
                response = self.client.get(
                    reverse("qms_core:api_get_screen_data", args=[screen.device_token])
                )

        self.assertEqual(
            response.json()["current_call"]["audio_url"],
            f"/media/audio_cache/{file_hash}.mp3",
        )


class ScreenAudioEventTests(TestCase):
    def test_audio_event_keeps_mp3_url_and_token_id(self):
        consumer = CounterConsumer()
        messages = []

        async def capture(text_data):
            messages.append(json.loads(text_data))

        consumer.send = capture
        async_to_sync(consumer.token_audio)({
            "audio": "base64-data",
            "audio_url": "/media/audio_cache/call.mp3",
            "token_id": 12,
            "counter_id": 3,
            "announcement_id": "one-call",
        })

        self.assertEqual(messages[0]["audio_url"], "/media/audio_cache/call.mp3")
        self.assertEqual(messages[0]["token_id"], 12)
        self.assertEqual(messages[0]["counter_id"], 3)

    def test_issued_event_keeps_new_token_details(self):
        consumer = CounterConsumer()
        messages = []

        async def capture(text_data):
            messages.append(json.loads(text_data))

        consumer.send = capture
        async_to_sync(consumer.token_issued)({
            "token_id": 21,
            "full_token": "R21",
            "service_name": "Registration",
        })

        self.assertEqual(messages[0]["type"], "token_issued")
        self.assertEqual(messages[0]["full_token"], "R21")
