import sys
import argparse
import threading
from pathlib import Path
from simple_agent.config.settings import load_config


def get_latest_log_file() -> Path:
    """Get the most recently modified log file."""
    log_dir = Path.cwd() / ".simple-agent" / "logs"
    if not log_dir.exists():
        return None

    log_files = list(log_dir.glob("*.jsonl"))
    if not log_files:
        return None

    return max(log_files, key=lambda f: f.stat().st_mtime)


def main():
    parser = argparse.ArgumentParser(
        description='Simple Agent - Claude Code-like CLI tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  simple-agent                        # 启动 Web 服务 (分析:5001, 聊天:5002)
  simple-agent --port 8080            # 指定聊天端口
  simple-agent --resume               # 从最近日志恢复
  simple-agent -p ./plugins/custom    # 指定插件目录""",
    )
    parser.add_argument('-p', '--plugin', type=str,
                        help='插件目录 (默认: ./plugins/default)')
    parser.add_argument('--resume', nargs='?', const='auto',
                        help='从最近日志恢复会话, 或指定日志文件路径')
    parser.add_argument('--port', type=int, default=5002,
                        help='Web 聊天端口 (默认: 5002)')
    args = parser.parse_args()

    run_web_servers(args)


def run_web_servers(args):
    """Run both web analyzer and chat servers concurrently."""
    import os

    resume_log = None
    if args.resume == "auto":
        latest = get_latest_log_file()
        if latest:
            resume_log = str(latest)
    elif args.resume:
        resume_log = args.resume

    config = load_config(plugin_dir=args.plugin)

    def _start_analyzer():
        try:
            from simple_agent.web.server import app, set_log_dir
            log_dir = Path.cwd() / ".simple-agent" / "logs"
            set_log_dir(log_dir)
            os.environ['FLASK_ENV'] = 'development'
            print("日志分析界面: http://localhost:5001")
            app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
        except ImportError:
            print("Error: Flask is not installed. Install with: pip install flask flask-cors")

    def _start_chat():
        if not config.api.api_key:
            print("Warning: No API key found, chat server may not work.")
            return
        try:
            from simple_agent.web.chat_server import init_runtime, app
            init_runtime(config, resume_log=resume_log)
            print(f"Web 聊天 UI:     http://localhost:{args.port}")
            if resume_log:
                print(f"已从日志恢复: {resume_log}")
            app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True, use_reloader=False)
        except ImportError:
            print("Error: Flask is not installed. Run: pip install -e .")

    threads = [
        threading.Thread(target=_start_chat, daemon=True),
        threading.Thread(target=_start_analyzer, daemon=True),
    ]
    for t in threads:
        t.start()

    print("=" * 50)
    print("Press Ctrl+C to stop all servers")
    print("=" * 50)

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
