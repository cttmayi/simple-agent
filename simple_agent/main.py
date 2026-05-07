import sys
from simple_agent.config.settings import load_config
from simple_agent.core.runtime import Runtime


def main():
    config = load_config()

    if not config.api.api_key:
        print("Error: No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    runtime = Runtime(config)
    runtime.run()


if __name__ == "__main__":
    main()
