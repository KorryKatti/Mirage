
from flask import Blueprint, jsonify

misc_bp = Blueprint('misc', __name__)

@misc_bp.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'message': 'pong'}), 200
