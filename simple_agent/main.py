import sys
import argparse
from pathlib import Path
from typing import Optional
from simple_agent.config.settings import load_config
from simple_agent.core.runtime import Runtime
from simple_agent.cli.view_logs import main as view_logs_main


def get_latest_log_file() -> Path:
    """Get the most recently modified log file.

    Returns:
        Path to the latest log file, or None if no logs exist
    """
    log_dir = Path.cwd() / ".simple-agent" / "logs"
    if not log_dir.exists():
        return None

    log_files = list(log_dir.glob("*.jsonl"))
    if not log_files:
        return None

    return max(log_files, key=lambda f: f.stat().st_mtime)


def show_plugin_info(plugin_dir: Optional[str] = None):
    """Show plugin information.

    Args:
        plugin_dir: Path to the plugin directory
    """
    config = load_config(plugin_dir=plugin_dir)
    base_dir = Path.cwd()

    print(f"\n{'='*50}")
    print(f"插件信息 (Plugin Info)")
    print(f"{'='*50}")

    if config.plugin_info:
        info = config.plugin_info
        print(f"名称 (Name):        {info.get('name', 'N/A')}")
        print(f"描述 (Description): {info.get('description', 'N/A')}")
        print(f"版本 (Version):     {info.get('version', 'N/A')}")
        if 'author' in info:
            author = info['author']
            print(f"作者 (Author):      {author.get('name', 'N/A')}")

        # 显示原始配置（来自 plugin.json）
        print(f"\n插件配置 (Plugin Config):")
        if 'agents' in info:
            print(f"  agents:           {info['agents']}")
        if 'skills' in info:
            print(f"  skills:           {info['skills']}")
        if 'commands' in info:
            print(f"  commands:         {info['commands']}")

    print(f"\n实际路径 (Resolved Paths):")
    print(f"  Plugin Dir:       {config.paths.plugin_dir}")
    # Get hooks config path
    from simple_agent.resources.hooks import HookLoader
    hook_loader = HookLoader()
    print(f"  Hooks Config:     {hook_loader._config_path}")
    print(f"  Hooks Dir:        ./plugins/default/hooks")
    for agents_dir in config.paths.agents_dirs:
        resolved = base_dir / agents_dir if not agents_dir.startswith("~") else Path(agents_dir).expanduser()
        print(f"  Agents:           {resolved}")
    for skill_dir in config.paths.skills_dirs:
        resolved = base_dir / skill_dir if not skill_dir.startswith("~") else Path(skill_dir).expanduser()
        print(f"  Skills:           {resolved}")
    for commands_dir in config.paths.commands_dirs:
        resolved = base_dir / commands_dir if not commands_dir.startswith("~") else Path(commands_dir).expanduser()
        print(f"  Commands:         {resolved}")
    print(f"{'='*50}\n")


def main():
    # Check for --view-logs or --logs flag
    if "--view-logs" in sys.argv or len(sys.argv) > 1 and sys.argv[1] in ["-l", "--logs"]:
        # Remove the flag and pass remaining args to view_logs
        if "--view-logs" in sys.argv:
            sys.argv.remove("--view-logs")
        else:
            sys.argv.pop(1)
        # Replace script name for argparse
        if len(sys.argv) > 0:
            sys.argv[0] = "simple-agent-logs"
        view_logs_main()
        return

    # Check for --web flag
    if "--web" in sys.argv:
        run_web_server()
        return

    # Check for --web-chat flag (interactive chat UI)
    if "--web-chat" in sys.argv:
        sys.argv.remove("--web-chat")
        run_chat_server()
        return

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Simple Agent - Claude Code-like CLI tool')
    parser.add_argument('-p', '--plugin', type=str,
                        help='Plugin directory (default: ./plugins/default)')
    parser.add_argument('--resume', nargs='?', const='auto',
                        help='Resume from latest log file or specified log file')
    parser.add_argument('--plugin-info', action='store_true',
                        help='Show plugin information')
    args = parser.parse_args()

    # Show plugin info if requested
    if args.plugin_info:
        show_plugin_info(plugin_dir=args.plugin)
        return

    # Check for --resume flag
    resume_log = None
    if args.resume == 'auto':
        latest = get_latest_log_file()
        if latest:
            resume_log = str(latest)
    elif args.resume:
        resume_log = args.resume

    # Load config with plugin directory
    config = load_config(plugin_dir=args.plugin)

    if not config.api.api_key:
        print("Error: No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    runtime = Runtime(config, log_file=resume_log)

    # Resume session if log file specified
    if resume_log:
        log_path = Path(resume_log)
        if log_path.exists():
            print(f"Resuming session from: {resume_log}")
            runtime._session.load_from_log(log_path)
        else:
            print(f"Warning: Log file not found: {resume_log}")

    runtime.run()


def run_web_server():
    """Run the web analyzer server."""
    try:
        from simple_agent.web.server import app, set_log_dir
        from pathlib import Path
        import os
        # Set log dir to where log files are actually stored
        log_dir = Path.cwd() / ".simple-agent" / "logs"
        set_log_dir(log_dir)
        os.environ['FLASK_ENV'] = 'development'
        print("Starting web server...")
        print("Web interface: http://localhost:5001")
        print(f"Log directory: {log_dir}")
        print("Press Ctrl+C to stop the server")
        app.run(host='0.0.0.0', port=5001, debug=False)
    except ImportError:
        print("Error: Flask is not installed. Install with: pip install flask flask-cors")
        sys.exit(1)


def run_chat_server():
    """Run the interactive web chat server."""
    parser = argparse.ArgumentParser(description="Simple Agent Web Chat")
    parser.add_argument("-p", "--plugin", type=str,
                        help="Plugin directory (default: ./plugins/default)")
    parser.add_argument("--resume", nargs="?", const="auto",
                        help="Resume from latest log file or specified log file")
    parser.add_argument("--port", type=int, default=5002,
                        help="Port to listen on (default: 5002)")
    args = parser.parse_args()

    resume_log = None
    if args.resume == "auto":
        latest = get_latest_log_file()
        if latest:
            resume_log = str(latest)
    elif args.resume:
        resume_log = args.resume

    config = load_config(plugin_dir=args.plugin)
    if not config.api.api_key:
        print("Error: No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")
        sys.exit(1)

    try:
        from simple_agent.web.chat_server import init_runtime, app
    except ImportError:
        print("Error: Flask is not installed. Run: pip install -e .")
        sys.exit(1)

    init_runtime(config, resume_log=resume_log)
    print(f"Simple Agent Web Chat: http://localhost:{args.port}")
    if resume_log:
        print(f"Resumed from: {resume_log}")
    print("Press Ctrl+C to stop the server")
    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
