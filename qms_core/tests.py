from django.test import Client, TestCase, override_settings
from django.contrib.auth.models import User
from unittest.mock import patch
import hashlib
import json
import tempfile
from datetime import timedelta
from pathlib import Path
from django.urls import reverse
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .consumers import CounterConsumer
from .models import Counter, CounterAssignment, Screen, Service, SystemConfig, Token
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
        self.assertContains(response, 'id="audio-control"')
        self.assertNotContains(response, 'id="audio-overlay"')
        self.assertNotContains(response, 'id="publicAdCarousel"')

        data = self.client.get(
            reverse("qms_core:api_get_screen_data", args=[screen.device_token])
        ).json()
        self.assertEqual(data["queue"], [f"R{number}" for number in range(1, 17)])
        self.assertEqual(data["latest_issued"]["full_token"], "R19")

    def test_finishing_newer_counter_does_not_turn_older_call_into_new_announcement(self):
        service = Service.objects.create(name="Registration", prefix="R")
        first_counter = Counter.objects.create(number=1)
        second_counter = Counter.objects.create(number=2)
        screen = Screen.objects.create(name="Main lobby", device_token="main-lobby")
        screen.counters.add(first_counter, second_counter)
        first_call = Token.objects.create(
            number=1, service=service, status="called", counter=first_counter,
            called_at=timezone.now() - timedelta(minutes=5),
            announced_at=timezone.now() - timedelta(minutes=5),
            announcement_id="first-call",
        )
        second_call = Token.objects.create(
            number=2, service=service, status="called", counter=second_counter,
            called_at=timezone.now() - timedelta(minutes=1),
            announced_at=timezone.now() - timedelta(minutes=1),
            announcement_id="second-call",
        )
        user = User.objects.create_user(username="second-operator", password="test-password")
        CounterAssignment.objects.create(user=user, counter=second_counter, is_active=True)
        self.client.force_login(user)
        events = []

        def capture(group, event):
            events.append((group, event))

        with patch("qms_core.views.get_channel_layer") as layer, \
             patch("qms_core.views.async_to_sync", side_effect=lambda func: func):
            layer.return_value.group_send = capture
            self.assertEqual(self.client.get(reverse("qms_core:mark_token_done")).status_code, 200)

        second_call.refresh_from_db()
        self.assertEqual(second_call.status, "done")
        self.assertEqual(events[-1][1]["type"], "token_cleared")
        self.assertEqual(events[-1][1]["token_id"], second_call.id)

        data = self.client.get(
            reverse("qms_core:api_get_screen_data", args=[screen.device_token])
        ).json()
        self.assertEqual(data["current_call"]["id"], first_call.id)
        self.assertEqual(data["latest_announcement"]["id"], second_call.announcement_id)
        self.assertGreater(data["latest_announcement"]["sequence"], 0)

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


class RecallAnnouncementTests(TestCase):
    def test_each_recall_gets_a_new_announcement_id_for_screen_and_audio(self):
        user = User.objects.create_user(username="operator", password="test-password")
        service = Service.objects.create(name="Registration", prefix="R")
        counter = Counter.objects.create(number=3)
        CounterAssignment.objects.create(user=user, counter=counter, is_active=True)
        screen = Screen.objects.create(name="Main lobby", device_token="main-lobby")
        second_counter = Counter.objects.create(number=4)
        screen.counters.add(counter, second_counter)
        first_called_at = timezone.now() - timedelta(minutes=5)
        token = Token.objects.create(
            number=7, service=service, status="called",
            counter=counter, called_at=first_called_at,
        )
        Token.objects.create(
            number=8, service=service, status="called",
            counter=second_counter, called_at=timezone.now(),
        )
        events = []

        def capture(group, event):
            events.append((group, event))

        self.client.force_login(user)
        ids = []
        with patch("qms_core.views.threading.Thread") as worker, \
             patch("qms_core.views.get_channel_layer") as layer, \
             patch("qms_core.views.async_to_sync", side_effect=lambda func: func):
            layer.return_value.group_send = capture
            for _ in range(2):
                response = self.client.get(reverse("qms_core:recall_token"))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["success"])
                self.assertEqual(events[-2][0], "queue_updates")
                self.assertEqual(events[-2][1]["type"], "token_called")
                self.assertEqual(events[-2][1]["token_id"], token.id)
                self.assertEqual(events[-1][1]["type"], "queue_changed")
                ids.append(events[-2][1]["announcement_id"])
                self.assertEqual(
                    self.client.get(reverse("qms_core:api_get_screen_data", args=[screen.device_token]))
                    .json()["current_call"]["announcement_id"],
                    ids[-1],
                )

        self.assertNotEqual(ids[0], ids[1])
        self.assertEqual(worker.call_count, 2)
        self.assertEqual(worker.call_args.kwargs["args"][-1], ids[-1])
        token.refresh_from_db()
        self.assertEqual(token.announcement_id, ids[-1])
        self.assertEqual(token.called_at, first_called_at)
        self.assertIsNotNone(token.announced_at)
        self.assertEqual(
            self.client.get(reverse("qms_core:public_screen", args=[screen.device_token]))
            .context["current_token"].id,
            token.id,
        )
