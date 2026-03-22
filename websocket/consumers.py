import json
import time
from channels.generic.websocket import AsyncWebsocketConsumer


class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print(f"Client connected: {self.channel_name}")

    async def disconnect(self, close_code):
        print(f"Client disconnected: {self.channel_name}, code: {close_code}")

    async def receive(self, text_data):
        start_time = time.time()

        try:
            data = json.loads(text_data)
            message = data.get('message', '')
        except json.JSONDecodeError:
            message = text_data

        if message.lower() == 'hello':
            response = "world"
        else:
            response = f"Echo: {message}"

        latency_ms = (time.time() - start_time) * 1000

        await self.send(text_data=json.dumps({
            'response': response,
            'latency_ms': round(latency_ms, 2),
            'original': message
        }))


class InterviewConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.interview_id = self.scope['url_route']['kwargs']['interview_id']
        self.group_name = f'interview_{self.interview_id}'

        # Add this connection to the interview group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        print(f"Interview {self.interview_id} — client connected: {self.channel_name}")

    async def disconnect(self, close_code):
        # Remove this connection from the interview group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        print(f"Interview {self.interview_id} — client disconnected: {self.channel_name}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            data = {'message': text_data}

        # Broadcast to all connections in this interview group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'transcript_message',
                'message': data.get('message', ''),
                'speaker': data.get('speaker', 'unknown'),
                'timestamp': data.get('timestamp', ''),
            }
        )

    async def transcript_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'speaker': event['speaker'],
            'timestamp': event['timestamp'],
        }))