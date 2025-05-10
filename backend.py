from flask import Flask, request, jsonify
from flask_cors import CORS
import socket

SERVER_URL = "127.0.0.1"
SERVER_PORT = 6969

# ------- MESSAGE SENDING LOGIC -------#
def sender(nickname, message):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_URL, SERVER_PORT))
        client.send(f"{nickname} : {message}".encode("ascii"))
        client.close()
        return True
    except Exception as e:
        print("Error sending:", e)
        return False
# ------- MESSAGE SENDING LOGIC ENDS -------#

app = Flask(__name__)
CORS(app)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()

    username = data.get('username', '').strip()
    message = data.get('message', '').strip()

    if not username or not message:
        return jsonify({'error': 'username and message cannot be empty'}), 400

    if len(message) > 500:
        return jsonify({'error': 'message too long'}), 400

    if len(username) > 20:
        return jsonify({'error': 'username too long'}), 400

    # Attempt to send the message
    if sender(username, message):
        return jsonify({'status': 'message sent'}), 200
    else:
        return jsonify({'error': 'failed to send message'}), 500

if __name__ == '__main__':
    app.run(debug=True)
