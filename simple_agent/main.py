import sys
from simple_agent.config.settings import load_config
from simple_agent.core.runtime import Runtime
from simple_agent.cli.view_logs import main as view_logs_main


def main():
    # Check for --view-logs flag
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

    config = load_config()

    if not config.api.api_key:
        print("Error: No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    runtime = Runtime(config)
    runtime.run()


if __name__ == "__main__":
    main()
