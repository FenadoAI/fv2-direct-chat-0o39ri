# Chat App Implementation Plan

## Backend API Endpoints

### Authentication
- POST /api/auth/signup - Create new user account
- POST /api/auth/login - Login and get JWT token

### Chat Rooms
- POST /api/chats/create - Create new chat room with invite token
- POST /api/chats/join/{invite_token} - Join chat room via invite link
- GET /api/chats/my-chats - Get all user's chat rooms

### Messages
- POST /api/messages/{chat_id} - Send message to chat room
- GET /api/messages/{chat_id} - Get messages for chat room (with pagination/polling)

## Database Schema

### users
- _id: ObjectId
- username: string (unique)
- email: string (unique)
- password: string (hashed)
- created_at: datetime

### chat_rooms
- _id: ObjectId
- invite_token: string (unique, UUID)
- participants: array[user_id] (max 2)
- created_by: user_id
- created_at: datetime
- is_active: boolean

### messages
- _id: ObjectId
- chat_id: chat_room_id
- sender_id: user_id
- content: string
- created_at: datetime

## Frontend Pages

### /login
- Login form with email/password
- Link to signup

### /signup
- Signup form with username, email, password
- Link to login

### /dashboard
- List of active chats
- Button to create new chat (generates invite link)
- Click chat to open conversation

### /chat/:chatId
- Message history (scrollable)
- Message input box
- Send button
- Display participant names

### /invite/:token
- Auto-join chat room if authenticated
- Redirect to login if not authenticated

## Implementation Order
1. Backend database models and auth
2. Backend API endpoints
3. Test all APIs
4. Frontend authentication pages
5. Frontend dashboard
6. Frontend chat interface
7. Integration testing