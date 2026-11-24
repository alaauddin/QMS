import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CounterConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.counter_id = self.scope['url_route']['kwargs'].get('counter_id')
        
        # Join counter-specific group if ID is provided
        if self.counter_id:
            self.counter_group = f"counter_{self.counter_id}"
            await self.channel_layer.group_add(self.counter_group, self.channel_name)
        
        # Join general queue update group
        self.queue_group = "queue_updates"
        await self.channel_layer.group_add(self.queue_group, self.channel_name)
        
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'counter_group'):
            await self.channel_layer.group_discard(self.counter_group, self.channel_name)
        await self.channel_layer.group_discard(self.queue_group, self.channel_name)

    async def token_called(self, event):
        await self.send(text_data=json.dumps({
            'type': 'token_called',
            'token': event['token'],
            'service': event['service'],
            'counter': event['counter'],
            'audio': event.get('audio')
        }))

    async def token_audio(self, event):
        await self.send(text_data=json.dumps({
            'type': 'token_audio',
            'audio': event['audio'],
            'announcement_id': event['announcement_id'],
            'counter_id': event.get('counter_id'),
        }))

    async def token_cleared(self, event):
        await self.send(text_data=json.dumps({
            'type': 'token_cleared'
        }))

    async def queue_changed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'queue_changed'
        }))
