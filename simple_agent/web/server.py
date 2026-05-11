"""Simple Web Server for Log Analyzer."""

import json
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from simple_agent.core.llm_logger import get_all_conversations

app = Flask(__name__)
CORS(app)

# Store log dir at startup to avoid issues with directory changes
_log_dir = None


def set_log_dir(log_dir: Path):
    """Set the log directory for the web server."""
    global _log_dir
    _log_dir = log_dir


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get all parsed logs."""
    from flask import request
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', 0, type=int)

    try:
        # Debug: log the log_dir
        import sys
        from pathlib import Path
        print(f"[DEBUG] _log_dir: {_log_dir}", file=sys.stderr)
        print(f"[DEBUG] _log_dir exists: {_log_dir.exists() if _log_dir else 'None'}", file=sys.stderr)

        if _log_dir and _log_dir.exists():
            # List jsonl files
            jsonl_files = list(_log_dir.glob("*.jsonl"))
            print(f"[DEBUG] Found {len(jsonl_files)} jsonl files", file=sys.stderr)

            conversations = get_all_conversations(_log_dir)
            print(f"[DEBUG] Loaded {len(conversations)} conversations", file=sys.stderr)
        elif _log_dir:
            # Directory doesn't exist
            print(f"[DEBUG] Log directory does not exist: {_log_dir}", file=sys.stderr)
            conversations = []
        else:
            # _log_dir is None
            print(f"[DEBUG] _log_dir is None", file=sys.stderr)
            conversations = []

        if limit:
            conversations = conversations[offset:offset + limit]

        return jsonify(conversations)
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception in /api/logs: {e}", file=sys.stderr)
        print(f"[ERROR] Traceback: {traceback.format_exc()}", file=sys.stderr)
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc(),
            'log_dir': str(_log_dir) if _log_dir else None
        }), 500


@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id: str):
    """Get a specific conversation by ID."""
    if not _log_dir:
        return jsonify({'error': 'Log directory not configured'}), 500

    conversations = get_all_conversations(_log_dir)

    for conv in conversations:
        if conv.get('id') == conversation_id:
            return jsonify(conv)

    # Check in system messages
    for conv in conversations:
        if '_system_messages' in conv:
            for msg in conv['_system_messages']:
                if msg.get('content', '').find(f"Request ID: {conversation_id}") >= 0:
                    return jsonify(msg)

    return jsonify({'error': 'Conversation not found'}), 404


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about logs."""
    if not _log_dir:
        return jsonify({
            'total_conversations': 0,
            'total_tool_calls': 0,
            'total_tokens': 0,
            'success_rate': 0
        })

    conversations = get_all_conversations(_log_dir)

    # Filter out system messages for stats
    regular_convs = [c for c in conversations if not c.get('id', '').startswith('_')]

    total_conv = len(regular_convs)
    total_tools = sum(len(c.get('tool_executions', [])) for c in regular_convs)
    total_tokens = sum(
        len(r.get('responses', [])) *
        sum(r.get('usage', {}).get('total_tokens', 0) for r in c['responses'])
        for c in regular_convs
    )

    # Calculate success rate
    successful_tools = 0
    for conv in regular_convs:
        for tool_exec in conv.get('tool_executions', []):
            if tool_exec.get('result', {}).get('success', False):
                successful_tools += 1

    success_rate = (successful_tools / total_tools * 100) if total_tools > 0 else 0

    return jsonify({
        'total_conversations': total_conv,
        'total_tool_calls': total_tools,
        'total_tokens': total_tokens,
        'success_rate': round(success_rate, 2)
    })


@app.route('/web')
def serve_web():
    """Serve the web analyzer page."""
    # Get the directory where this script is located
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(script_dir, 'analyzer.html')


@app.route('/')
def index():
    """Redirect to web interface."""
    return serve_web()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Simple Agent Web Server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run server on')
    args = parser.parse_args()

    # Set log dir at startup (match actual log file location)
    set_log_dir(Path.cwd() / ".simple-agent" / "logs")

    print(f"Starting web server...")
    print(f"Web interface: http://localhost:{args.port}")
    print(f"Log directory: {_log_dir}")
    if not _log_dir.exists():
        print(f"Warning: Log directory does not exist: {_log_dir}")
    app.run(host='0.0.0.0', port=args.port, debug=False)
