"""Test chat API endpoints."""
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv("/workspace/repo/backend/.env")

API_BASE = os.getenv("API_BASE", "http://localhost:8001")
API_URL = f"{API_BASE}/api"


def test_chat_flow():
    """Test complete chat flow: signup, create chat, join, send/receive messages."""
    print("\n=== Testing Chat API Flow ===\n")

    # Test 1: Signup User 1
    print("1. Testing user signup (User 1)...")
    user1_data = {
        "username": "testuser1",
        "email": "test1@example.com",
        "password": "password123"
    }
    response = requests.post(f"{API_URL}/auth/signup", json=user1_data)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Signup failed: {response.text}"
    user1_token = response.json()["access_token"]
    user1_id = response.json()["user"]["id"]
    print(f"   ✓ User 1 signed up: {user1_data['username']}")
    print(f"   User ID: {user1_id}")

    # Test 2: Signup User 2
    print("\n2. Testing user signup (User 2)...")
    user2_data = {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "password456"
    }
    response = requests.post(f"{API_URL}/auth/signup", json=user2_data)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Signup failed: {response.text}"
    user2_token = response.json()["access_token"]
    user2_id = response.json()["user"]["id"]
    print(f"   ✓ User 2 signed up: {user2_data['username']}")
    print(f"   User ID: {user2_id}")

    # Test 3: Create chat room (User 1)
    print("\n3. Testing chat room creation...")
    headers1 = {"Authorization": f"Bearer {user1_token}"}
    response = requests.post(f"{API_URL}/chats/create", json={}, headers=headers1)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Create chat failed: {response.text}"
    chat_data = response.json()
    chat_id = chat_data["id"]
    invite_token = chat_data["invite_token"]
    print(f"   ✓ Chat room created")
    print(f"   Chat ID: {chat_id}")
    print(f"   Invite token: {invite_token}")

    # Test 4: Join chat room (User 2)
    print("\n4. Testing chat room join...")
    headers2 = {"Authorization": f"Bearer {user2_token}"}
    response = requests.post(f"{API_URL}/chats/join/{invite_token}", headers=headers2)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Join chat failed: {response.text}"
    joined_chat = response.json()
    assert len(joined_chat["participants"]) == 2, "Chat should have 2 participants"
    print(f"   ✓ User 2 joined chat")
    print(f"   Participants: {len(joined_chat['participants'])}")

    # Test 5: Get my chats (User 1)
    print("\n5. Testing get my chats (User 1)...")
    response = requests.get(f"{API_URL}/chats/my-chats", headers=headers1)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Get chats failed: {response.text}"
    chats = response.json()
    assert len(chats) >= 1, "User 1 should have at least 1 chat"
    print(f"   ✓ Found {len(chats)} chat(s)")
    if chats[0].get("other_user"):
        print(f"   Other user: {chats[0]['other_user']['username']}")

    # Test 6: Send message (User 1)
    print("\n6. Testing send message (User 1)...")
    message1 = {"content": "Hello from User 1!"}
    response = requests.post(f"{API_URL}/messages/{chat_id}", json=message1, headers=headers1)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Send message failed: {response.text}"
    sent_msg = response.json()
    print(f"   ✓ Message sent: {sent_msg['content']}")

    # Test 7: Send message (User 2)
    print("\n7. Testing send message (User 2)...")
    message2 = {"content": "Hello from User 2!"}
    response = requests.post(f"{API_URL}/messages/{chat_id}", json=message2, headers=headers2)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Send message failed: {response.text}"
    sent_msg = response.json()
    print(f"   ✓ Message sent: {sent_msg['content']}")

    # Test 8: Get messages (User 1)
    print("\n8. Testing get messages (User 1)...")
    response = requests.get(f"{API_URL}/messages/{chat_id}", headers=headers1)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Get messages failed: {response.text}"
    messages = response.json()
    assert len(messages) == 2, f"Should have 2 messages, got {len(messages)}"
    print(f"   ✓ Retrieved {len(messages)} messages")
    for msg in messages:
        print(f"   - {msg['sender_username']}: {msg['content']}")

    # Test 9: Login (User 1)
    print("\n9. Testing login...")
    login_data = {
        "email": user1_data["email"],
        "password": user1_data["password"]
    }
    response = requests.post(f"{API_URL}/auth/login", json=login_data)
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200, f"Login failed: {response.text}"
    login_response = response.json()
    assert "access_token" in login_response, "Should return access token"
    print(f"   ✓ Login successful: {login_response['user']['username']}")

    # Test 10: Unauthorized access
    print("\n10. Testing unauthorized access...")
    response = requests.get(f"{API_URL}/chats/my-chats")
    print(f"   Status: {response.status_code}")
    assert response.status_code == 403, "Should return 403 for unauthorized access"
    print(f"   ✓ Unauthorized access blocked")

    print("\n=== All Chat API Tests Passed ✓ ===\n")


if __name__ == "__main__":
    test_chat_flow()