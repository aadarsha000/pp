"""
Test WebSocket notifications in Docker environment.
Run via: docker-compose exec web python scripts/test_ws.py
"""
import os
import sys
import json
import asyncio
from urllib.parse import urlencode

# Add project to path
sys.path.insert(0, '/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from users.models import Role

User = get_user_model()

async def test_websocket():
    # Import websockets only when needed (avoid dependency issues)
    try:
        from websockets import connect
    except ImportError:
        print("❌ Installing websockets...")
        os.system('pip install websockets')
        from websockets import connect
    
    # 1. Get or create a test recruiter user
    user, created = User.objects.get_or_create(
        email='test.recruiter@example.com',
        defaults={
            'username': 'test_recruiter',
            'role': Role.RECRUITER,
            'is_active': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✅ Created test user: {user.email}")
    
    # 2. Generate JWT access token
    token = str(AccessToken.for_user(user))
    print(f"🔑 Access token: {token[:50]}...")
    
    # 3. Build WebSocket URL
    # Use service name 'web' for container-to-container, or 'localhost' for host-to-container
    host = os.getenv('WS_HOST', 'localhost')  # Override via env var if needed
    port = os.getenv('WS_PORT', '8000')
    ws_url = f"ws://{host}:{port}/ws/notifications/?token={token}"
    
    print(f"🔌 Connecting to: {ws_url[:80]}...")
    
    try:
        async with connect(ws_url, ping_interval=20, ping_timeout=10) as websocket:
            print("✅ Connected! Waiting for messages (Ctrl+C to exit)...\n")
            
            # Listen for messages
            async for message in websocket:
                data = json.loads(message)
                event = data.get('event', 'unknown')
                
                if event == 'connection_established':
                    print(f"📡 Connection confirmed | Unread: {data.get('unread_count', 0)}")
                elif event == 'acknowledgement':
                    print(f"✓ Ack: Notification {data.get('notification_id')} marked read")
                else:
                    # Real notification events
                    print(f"\n🔔 [{event.upper()}]")
                    for key, value in data.items():
                        if key != 'event':
                            print(f"   {key}: {value}")
                    print("-" * 50)
                    
    except ConnectionRefusedError:
        print(f"❌ Connection refused. Is the web service running on {host}:{port}?")
        print("💡 Try: docker-compose exec web python scripts/test_ws.py")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        if "4001" in str(e) or "code=4001" in str(e).lower():
            print("💡 4001 = Invalid/expired token or unauthorized role. Check user.role and token expiry.")

if __name__ == '__main__':
    asyncio.run(test_websocket())