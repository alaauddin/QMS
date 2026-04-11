# 🏗️ Queue Management System – Project Skeleton

This document outlines the full Django project skeleton for the Queue Management System (QMS).

---

## 1. **Project Setup**

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows (Commented for Linux reference)

# Install Django + Channels + Redis
pip install django channels channels_redis

# Create project
django-admin startproject qms_project
cd qms_project

# Create app
python manage.py startapp qms_core
```

---

## 2. **settings.py**

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Our app
    'qms_core',

    # Channels
    'channels',
]

# Channels config
ASGI_APPLICATION = 'qms_project.asgi.application'

# Redis backend for Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

# Static & Templates
STATIC_URL = '/static/'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    }
]
```

---

## 3. **ASGI Setup for Channels**

`qms_project/asgi.py`:

```python
import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import qms_core.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qms_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            qms_core.routing.websocket_urlpatterns
        )
    ),
})
```

---

## 4. **Models (qms_core/models.py)**

```python
from django.db import models
from django.contrib.auth.models import User


class Service(models.Model):
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=5)

    def __str__(self):
        return self.name


class Counter(models.Model):
    number = models.IntegerField()
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    def __str__(self):
        return f"Counter {self.number}"


class CounterAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    counter = models.ForeignKey(Counter, on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'counter')

    def __str__(self):
        return f"{self.user} → Counter {self.counter.number}"


class Token(models.Model):
    number = models.IntegerField()
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('done', 'Done'),
        ('skipped', 'Skipped'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    counter = models.ForeignKey(Counter, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.service.prefix}{self.number}"


class Screen(models.Model):
    name = models.CharField(max_length=50)
    counter = models.ForeignKey(Counter, on_delete=models.CASCADE)
    device_token = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Screen for Counter {self.counter.number}"
```

---

## 5. **Routing (qms_core/routing.py)**

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/counter/(?P<counter_id>\d+)/$', consumers.CounterConsumer.as_asgi()),
]
```

---

## 6. **Consumer for Real-Time Updates (qms_core/consumers.py)**

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CounterConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.counter_id = self.scope['url_route']['kwargs']['counter_id']
        self.group_name = f"counter_{self.counter_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from group
    async def token_called(self, event):
        await self.send(text_data=json.dumps({
            'token': event['token'],
            'service': event['service']
        }))
```

---

## 7. **Views (qms_core/views.py)**

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Token, CounterAssignment, Counter
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

@login_required
def counter_dashboard(request):
    assignment = CounterAssignment.objects.filter(user=request.user, is_active=True).first()
    if not assignment:
        return render(request, "queue/select_counter.html")

    counter = assignment.counter
    return render(request, "queue/counter_dashboard.html", {'counter': counter})


@login_required
def call_next(request):
    assignment = CounterAssignment.objects.filter(user=request.user, is_active=True).first()
    counter = assignment.counter
    token = Token.objects.filter(service=counter.service, status='waiting').order_by('created_at').first()
    if token:
        token.status = 'called'
        token.counter = counter
        token.called_at = timezone.now()
        token.save()

        # Send to WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"counter_{counter.id}",
            {
                'type': 'token_called',
                'token': str(token),
                'service': token.service.prefix
            }
        )
        return JsonResponse({'token': str(token), 'service': token.service.prefix})

    return JsonResponse({'error': 'No tokens waiting'})
```

---

## 8. **URLs (qms_core/urls.py)**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('counter/', views.counter_dashboard, name='counter_dashboard'),
    path('counter/call_next/', views.call_next, name='call_next'),
]
```

---

## 9. **Templates (Bootstrap Example)**

### 9.1 Counter Dashboard (`templates/qms_core/counter_dashboard.html`)

```html
{% load static %}
<!DOCTYPE html>
<html>
<head>
    <title>Counter {{ counter.number }}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
</head>
<body class="p-5">
    <div class="container">
        <h1>Counter {{ counter.number }}</h1>
        <h2>Current Token: <span id="current">--</span></h2>
        <button class="btn btn-primary btn-lg" onclick="callNext()">Next</button>
    </div>

<script>
const counterId = "{{ counter.id }}";
const ws = new WebSocket('ws://' + window.location.host + '/ws/counter/' + counterId + '/');

ws.onmessage = function(e) {
    const data = JSON.parse(e.data);
    document.getElementById('current').innerText = data.service + data.token;
}

function callNext() {
    fetch('/counter/call_next/')
    .then(res => res.json())
    .then(data => {
        if(data.token){
            document.getElementById('current').innerText = data.service + data.token;
        }
    });
}
</script>
</body>
</html>
```

---

### 9.2 Public Screen (`templates/qms_core/screen.html`)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Screen Display</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
</head>
<body class="text-center p-5">
    <h1>Current Token</h1>
    <h1 id="token" class="display-1">--</h1>

<script>
const counterId = "{{ counter.id }}";
const ws = new WebSocket('ws://' + window.location.host + '/ws/counter/' + counterId + '/');

ws.onmessage = function(e) {
    const data = JSON.parse(e.data);
    document.getElementById('token').innerText = data.service + data.token;
    // Optional sound
    const utterance = new SpeechSynthesisUtterance(`Token ${data.service}${data.token}`);
    speechSynthesis.speak(utterance);
}
</script>
</body>
</html>
```

---

## 🔥 Next Steps

1. **Migrate Models**
2. **Create Superuser**
3. **Runserver**
4. **Install Redis** (for WebSocket backend)
5. **Open counter dashboard & screen URLs** to test real-time updates
