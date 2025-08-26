#!/usr/bin/env python3
"""
量子精度ブースター API エンドポイント
"""

from flask import Blueprint, jsonify
from datetime import datetime
from quantum_accuracy_booster import quantum_booster

# Blueprint作成
quantum_bp = Blueprint('quantum', __name__)

@quantum_bp.route('/api/quantum/stats')
def api_quantum_stats():
    """量子精度ブースター統計API"""
    try:
        stats = quantum_booster.get_system_stats()
        return jsonify({
            'success': True,
            'quantum_stats': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })