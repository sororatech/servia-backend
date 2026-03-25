import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class InterviewConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.interview_id = self.scope['url_route']['kwargs']['interview_id']
        self.group_name = f'interview_{self.interview_id}'

        query_string = self.scope['query_string'].decode()
        token_key = None
        if 'token=' in query_string:
            token_key = query_string.split('token=')[1].split('&')[0]

        self.user = await self.authenticate_token(token_key)

        if self.user is None:
            await self.accept()
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except:
            data = {'message': text_data}

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'transcript_message',
                'message': data.get('text') or data.get('message', ''),
                'speaker': data.get('speaker', 'unknown'),
                'timestamp': data.get('timestamp', ''),
                'event_type': data.get('type', 'transcript'),
            }
        )

    async def transcript_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'speaker': event['speaker'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def authenticate_token(self, token_key):
        if not token_key:
            return None
        try:
            from rest_framework.authtoken.models import Token
            token = Token.objects.get(key=token_key)
            return token.user
        except:
            return None