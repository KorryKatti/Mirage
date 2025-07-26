# MIRAGE API Documentation

## Base URL
All API endpoints are prefixed with `/api/`

## Authentication
Most endpoints require authentication via an `Authorization` header containing a user token obtained from the login endpoint.

```
Authorization: <token>
```

---

## User Management

### Register User
**POST** `/api/register`

Create a new user account.

**Request Body:**
```json
{
  "username": "string (required)",
  "email": "string (required)", 
  "password": "string (required)",
  "avatar_url": "string (optional)",
  "description": "string (optional, max 500 words)"
}
```

**Response:**
- **201**: Registration successful
- **400**: Missing fields or user already exists

---

### Login
**POST** `/api/login`

Authenticate user and receive access token.

**Request Body:**
```json
{
  "username": "string (required)",
  "password": "string (required)"
}
```

**Response:**
```json
{
  "token": "uuid-token",
  "username": "string"
}
```

**Status Codes:**
- **200**: Login successful
- **400**: Missing fields
- **404**: User not found
- **401**: Wrong password

---

### Logout
**POST** `/api/logout`

Invalidate user token.

**Request Body:**
```json
{
  "token": "string (required)"
}
```

**Response:**
- **200**: Logout successful
- **400**: No token provided
- **401**: Invalid token

---

### Get User Count
**GET** `/api/usercount`

Get total number of registered users.

**Response:** Plain text number

---

## User Profiles & Social Features

### Get User Profile
**GET** `/api/user/<username>`

Get detailed user profile information.

**Response:**
```json
{
  "username": "string",
  "avatar_url": "string",
  "description": "string", 
  "created_at": "timestamp",
  "stats": {
    "followers": "number",
    "following": "number", 
    "posts": "number",
    "upvotes": "number",
    "downvotes": "number"
  }
}
```

**Status Codes:**
- **200**: Success
- **404**: User not found

---

### Follow User
**POST** `/api/follow`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "username": "string (target user to follow)"
}
```

**Response:**
- **200**: Successfully followed
- **400**: Missing fields or already following
- **401**: Unauthorized
- **404**: User not found

---

### Unfollow User
**POST** `/api/unfollow`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "username": "string (target user to unfollow)"
}
```

**Response:**
- **200**: Successfully unfollowed
- **400**: Missing fields or not following
- **401**: Unauthorized

---

### Check Follow Status
**GET** `/api/check_follow?username=<target_username>`

**Headers:** `Authorization: <token>`

**Response:**
```json
{
  "is_following": "boolean"
}
```

---

### Get Followers
**GET** `/api/get_followers/<username>`

Get list of users following the specified user.

**Response:**
```json
{
  "followers": [
    {
      "username": "string",
      "avatar_url": "string"
    }
  ]
}
```

---

### Get Following
**GET** `/api/get_following/<username>`

Get list of users that the specified user is following.

**Response:**
```json
{
  "following": [
    {
      "username": "string", 
      "avatar_url": "string"
    }
  ]
}
```

---

## Posts & Content

### Create Post
**POST** `/api/create_post`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "content": "string (required, max 512 characters)"
}
```

**Response:**
- **201**: Post created successfully
- **400**: Missing content or content too long
- **401**: Unauthorized

---

### Get User Posts
**GET** `/api/get_posts/<username>`

Get all posts by a specific user, ordered by creation date (newest first).

**Response:**
```json
{
  "posts": [
    {
      "id": "number",
      "username": "string",
      "content": "string", 
      "created_at": "timestamp",
      "upvotes": "number",
      "downvotes": "number"
    }
  ]
}
```

---

### Get Post by ID
**GET** `/api/get_post_by_id/<post_id>`

Get a specific post by its ID.

**Response:**
```json
{
  "id": "number",
  "username": "string",
  "content": "string",
  "created_at": "timestamp", 
  "upvotes": "number",
  "downvotes": "number"
}
```

**Status Codes:**
- **200**: Success
- **404**: Post not found

---

### Vote on Post
**POST** `/api/vote_post`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "post_id": "number (required)",
  "vote_type": "string (required: 'up' or 'down')"
}
```

**Response:**
- **200**: Vote counted
- **400**: Missing fields, invalid vote type, or already voted
- **401**: Unauthorized
- **403**: Cannot vote on own post
- **404**: Post not found

---

### Reply to Post
**POST** `/api/reply_to_post`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "post_id": "number (required)",
  "content": "string (required, max 512 characters)"
}
```

**Response:**
- **201**: Reply created
- **400**: Missing fields or content too long
- **401**: Unauthorized
- **404**: Post not found

---

### Get Post Replies
**GET** `/api/get_replies/<post_id>`

Get all replies to a specific post.

**Response:**
```json
{
  "replies": [
    {
      "id": "number",
      "username": "string",
      "content": "string",
      "created_at": "timestamp",
      "avatar_url": "string"
    }
  ]
}
```

---

### For You Page (FYP)
**GET** `/api/fyp`

**Headers:** `Authorization: <token>`

Get personalized feed with posts from followed users, global posts, and trending topics.

**Response:**
```json
{
  "posts": [
    {
      "id": "number",
      "username": "string", 
      "content": "string",
      "created_at": "timestamp",
      "upvotes": "number",
      "downvotes": "number"
    }
  ],
  "trending_topics": ["#hashtag1", "#hashtag2", "#hashtag3"]
}
```

**Notes:**
- Returns up to 30 posts
- Mix of followed users (~40%), recent global (~40%), and archive (~20%)
- Trending topics based on recent hashtag usage

---

## Room Management

### Create Room
**POST** `/api/create_room`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "room_name": "string (required)",
  "is_private": "number (0 or 1)",
  "password": "string (required if is_private=1)"
}
```

**Response:**
```json
{
  "message": "room created",
  "room_id": "number"
}
```

**Status Codes:**
- **201**: Room created successfully  
- **400**: Invalid fields, room exists, or public room limit reached (max 5)
- **401**: Unauthorized

---

### Join Room
**POST** `/api/join_room`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "name": "string (room name, required)",
  "password": "string (required for private rooms)"
}
```

**Response:**
```json
{
  "message": "joined room",
  "room_id": "number",
  "room_name": "string"
}
```

**Status Codes:**
- **200**: Successfully joined
- **400**: Missing room name or token
- **401**: Unauthorized
- **403**: Wrong password for private room
- **404**: Room not found

---

### List Public Rooms
**GET** `/api/rooms`

**Headers:** `Authorization: <token>`

Get list of all public rooms and user's membership status.

**Response:**
```json
{
  "rooms": [
    {
      "room_id": "number",
      "name": "string", 
      "joined": "boolean"
    }
  ]
}
```

---

### Get User's Rooms
**GET** `/api/user_rooms`

**Headers:** `Authorization: <token>`

Get all rooms (public and private) that the user is a member of.

**Response:**
```json
{
  "rooms": [
    {
      "room_id": "number",
      "name": "string",
      "is_private": "number"
    }
  ]
}
```

---

### Get Room Members
**GET** `/api/room_members/<room_id>`

**Headers:** `Authorization: <token>`

Get list of all members in a specific room.

**Response:**
```json
{
  "members": ["username1", "username2", "username3"]
}
```

**Status Codes:**
- **200**: Success
- **401**: Unauthorized
- **404**: No members found

---

## Room Messaging

### Send Room Message
**POST** `/api/send_room_message`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "room_id": "number (required)",
  "message": "string (required)"
}
```

**Response:**
- **200**: Message sent
- **400**: Missing fields
- **401**: Unauthorized
- **403**: Not a room member

---

### Get Room Messages
**GET** `/api/get_room_messages?room_id=<room_id>`

**Headers:** `Authorization: <token>`

Get all messages for a specific room.

**Response:**
```json
{
  "messages": [
    {
      "username": "string",
      "message": "string",
      "created_at": "timestamp",
      "room_id": "number"
    }
  ]
}
```

**Notes:**
- Messages are automatically cleaned up after 30 minutes
- Maximum of 100 messages stored at any time

---

### Upload File to Room
**POST** `/api/upload_file`

**Headers:** `Authorization: <token>`

Upload a file to share in a room chat.

**Form Data:**
- `file`: File to upload (max 24MB)
- `room_id`: Target room ID

**Response:**
```json
{
  "message": "File uploaded successfully",
  "file_url": "string (URL to access the file)"
}
```

**Status Codes:**
- **200**: Upload successful
- **400**: Missing file, filename, or room ID
- **401**: Unauthorized
- **403**: Not a room member
- **500**: Upload failed

---

## Direct Messaging

### Send Inbox Message
**POST** `/api/send_inbox_message`

**Headers:** `Authorization: <token>`

Send a private message to another user.

**Request Body:**
```json
{
  "recipient": "string (username, required)",
  "message": "string (required)"
}
```

**Response:**
- **200**: Message sent
- **400**: Missing fields
- **401**: Unauthorized
- **404**: Recipient not found

---

### Get Inbox Messages
**GET** `/api/inbox`

**Headers:** `Authorization: <token>`

Get all messages received by the current user.

**Response:**
```json
{
  "messages": [
    {
      "id": "number",
      "sender": "string",
      "recipient": "string", 
      "message": "string",
      "created_at": "timestamp",
      "avatar_url": "string"
    }
  ]
}
```

---

### Delete Inbox Message
**POST** `/api/delete_inbox_message`

**Headers:** `Authorization: <token>`

**Request Body:**
```json
{
  "message_id": "number (required)"
}
```

**Response:**
- **200**: Message deleted
- **400**: Missing message ID
- **401**: Unauthorized
- **404**: Message not found or unauthorized access

---

### Get Inbox Count
**GET** `/api/inbox_count`

**Headers:** `Authorization: <token>`

Get the number of messages in user's inbox.

**Response:**
```json
{
  "inbox_count": "number"
}
```

---

## Utility Endpoints

### Ping Server
**GET** `/api/ping`

Health check endpoint.

**Response:**
```json
{
  "message": "pong"
}
```

---

## Error Responses

All endpoints may return these common error responses:

- **400 Bad Request**: Invalid request data or parameters
- **401 Unauthorized**: Invalid or missing authentication token
- **403 Forbidden**: User lacks permission for the requested action
- **404 Not Found**: Requested resource doesn't exist
- **500 Internal Server Error**: Server-side error occurred

Error responses include a JSON object with an `error` field describing the issue:

```json
{
  "error": "Description of what went wrong"
}
```

---

## Notes

- All timestamps are in ISO format
- File uploads are limited to 24MB
- Post and reply content is limited to 512 characters
- User descriptions are limited to 500 words
- Messages in rooms expire after 30 minutes
- Maximum of 5 public rooms can exist at once
- Users cannot vote on their own posts
- Hashtags in posts contribute to trending topics calculation
