"""Tests for subagent execution system."""

from simple_agent.core.subagent import SubAgentRunner
from simple_agent.tools.builtin.run_subagent import RunSubAgent


def test_subagent_runner_init():
    """Test SubAgentRunner initialization."""
    runner = SubAgentRunner(
        agent_name="test-agent",
        agent_content="You are a test agent.",
        agent_tools=["read"]
    )

    assert runner._agent_name == "test-agent"
    assert runner._agent_content == "You are a test agent."
    assert runner._agent_tools == ["read"]


def test_subagent_runner_without_api_client():
    """Test SubAgentRunner run without API client returns error."""
    runner = SubAgentRunner(
        agent_name="test-agent",
        agent_content="You are a test agent."
    )

    result = runner.run("test task")
    assert result["success"] is False
    assert "API client not configured" in result["error"]


def test_run_subagent_tool():
    """Test RunSubAgent tool definition."""
    assert RunSubAgent.name == "run_subagent"
    assert "subagent" in RunSubAgent.description.lower()
    assert "execution context" in RunSubAgent.description.lower()


def test_run_subagent_set_runtime():
    """Test RunSubAgent set_runtime method."""
    from simple_agent.resources.agents import AgentLoader

    loader = AgentLoader('plugin/agents')
    loaded_agents = set()

    RunSubAgent.set_runtime(
        agent_loader=loader,
        loaded_agents=loaded_agents,
        api_config=None,
        logger=None,
        runtime=None,
        event_bus=None
    )

    assert RunSubAgent._agent_loader is loader
    assert RunSubAgent._loaded_agents is loaded_agents


def test_run_subagent_without_loader():
    """Test RunSubAgent execute without loader returns error."""
    RunSubAgent.set_runtime(
        agent_loader=None,
        loaded_agents=set(),
        api_config=None,
        logger=None,
        runtime=None,
        event_bus=None
    )

    result = RunSubAgent.execute("test-agent", "test task")
    assert result["success"] is False
    assert result["error"] == "Agent loader not initialized"


def test_run_subagent_nonexistent_agent():
    """Test RunSubAgent execute with nonexistent agent."""
    from simple_agent.resources.agents import AgentLoader

    loader = AgentLoader('plugin/agents')
    loaded_agents = set()

    RunSubAgent.set_runtime(
        agent_loader=loader,
        loaded_agents=loaded_agents,
        api_config=None,
        logger=None,
        runtime=None,
        event_bus=None
    )

    result = RunSubAgent.execute("nonexistent-agent", "test task")
    assert result["success"] is False
    assert "not found" in result["error"]


def test_run_subagent_finds_agent():
    """Test RunSubAgent can find existing agents."""
    from simple_agent.resources.agents import AgentLoader

    loader = AgentLoader('plugin/agents')
    loaded_agents = set()

    RunSubAgent.set_runtime(
        agent_loader=loader,
        loaded_agents=loaded_agents,
        api_config=None,
        logger=None,
        runtime=None,
        event_bus=None
    )

    # Check that agents can be found
    agents = loader.list_agents()
    if agents:
        agent_name = agents[0]['name']
        # Can't run without API config, but can verify it finds the agent
        result = RunSubAgent.execute(agent_name, "test task")
        # Should fail due to API client, not "not found"
        assert result["success"] is False
        assert "not found" not in result["error"]


def test_run_subagent_tool_def():
    """Test run_subagent_tool_def properties."""
    from simple_agent.tools.builtin.run_subagent import run_subagent_tool_def

    assert run_subagent_tool_def.name == "run_subagent"
    assert "agent_name" in run_subagent_tool_def.parameters["properties"]
    assert "task" in run_subagent_tool_def.parameters["properties"]
    assert "max_turns" in run_subagent_tool_def.parameters["properties"]
    assert "agent_name" in run_subagent_tool_def.parameters["required"]
    assert "task" in run_subagent_tool_def.parameters["required"]
    assert "max_turns" not in run_subagent_tool_def.parameters["required"]