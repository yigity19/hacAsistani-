from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import socketio
import uvicorn
from typing import Dict, Set

app = FastAPI()
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
socket_app = socketio.ASGIApp(sio, app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active rooms and their participants
rooms: Dict[str, Set[str]] = {}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    # Remove user from all rooms
    for room in rooms.values():
        room.discard(sid)

@sio.event
async def join_room(sid, data):
    room_id = data.get('room_id')
    if not room_id:
        return {'error': 'Room ID is required'}
    
    if room_id not in rooms:
        rooms[room_id] = set()
    
    rooms[room_id].add(sid)
    await sio.enter_room(sid, room_id)
    
    # Notify others in the room
    await sio.emit('user_joined', {'user': sid}, room=room_id, skip_sid=sid)
    return {'success': True, 'room_id': room_id}

@sio.event
async def leave_room(sid, data):
    room_id = data.get('room_id')
    if room_id and room_id in rooms:
        rooms[room_id].discard(sid)
        await sio.leave_room(sid, room_id)
        await sio.emit('user_left', {'user': sid}, room=room_id)

@sio.event
async def offer(sid, data):
    room_id = data.get('room_id')
    offer = data.get('offer')
    if room_id and room_id in rooms:
        await sio.emit('offer', {
            'offer': offer,
            'from': sid
        }, room=room_id, skip_sid=sid)

@sio.event
async def answer(sid, data):
    room_id = data.get('room_id')
    answer = data.get('answer')
    target_sid = data.get('target')
    if room_id and room_id in rooms:
        await sio.emit('answer', {
            'answer': answer,
            'from': sid
        }, room=target_sid)

@sio.event
async def ice_candidate(sid, data):
    room_id = data.get('room_id')
    candidate = data.get('candidate')
    target_sid = data.get('target')
    if room_id and room_id in rooms:
        await sio.emit('ice_candidate', {
            'candidate': candidate,
            'from': sid
        }, room=target_sid)

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
