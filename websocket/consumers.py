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