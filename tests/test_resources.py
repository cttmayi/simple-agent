import tempfile
from pathlib import Path
from simple_agent.resources.base import BaseResource, ResourceLoader
from simple_agent.resources.skills import SkillLoader


class TestResource(BaseResource):
    pass


def test_base_resource_creation():
    resource = TestResource(
        name="test",
        description="A test resource",
        path=Path("/test/path"),
        metadata={"key": "value"}
    )
    assert resource.name == "test"
    assert resource.description == "A test resource"
    assert resource.path == Path("/test/path")
    assert resource.metadata == {"key": "value"}


def test_resource_loader_scan_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = ResourceLoader(Path(tmpdir))
        resources = loader.scan()
        assert resources == []


def test_resource_loader_with_frontmatter():
    class TestLoader(ResourceLoader):
        def _get_markdown_file(self, resource_dir: Path) -> Path:
            return resource_dir / "TEST.md"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test resource
        resource_dir = Path(tmpdir) / "test-resource"
        resource_dir.mkdir()
        md_file = resource_dir / "TEST.md"
        md_file.write_text("---\nname: test\ndescription: A test\n---\nContent")

        loader = TestLoader(tmpdir)
        resources = loader.scan()
        assert len(resources) == 1
        assert resources[0]["name"] == "test"


def test_skill_loader_scan():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test skill
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()
        md_file = skill_dir / "SKILL.md"
        md_file.write_text("---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill\n\nThis is a test.")

        loader = SkillLoader(Path(tmpdir))
        skills = loader.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"
        assert skills[0]["description"] == "A test skill"


def test_skill_loader_get_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test skill
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()
        md_file = skill_dir / "SKILL.md"
        md_file.write_text("---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill\n\nThis is content.")

        loader = SkillLoader(Path(tmpdir))
        content = loader.get_skill_content("test-skill")
        assert "# Test Skill" in content
        assert "This is content." in content


def test_subagent_loader_scan():
    from simple_agent.resources.subagents import SubagentLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test subagent
        agent_dir = Path(tmpdir) / "test-agent"
        agent_dir.mkdir()
        md_file = agent_dir / "AGENT.md"
        md_file.write_text("---\nname: test-agent\ndescription: A test agent\ntools: [Read, Glob]\ntype: explore\n---\n# Test Agent")

        loader = SubagentLoader(Path(tmpdir))
        agents = loader.list_subagents()
        assert len(agents) == 1
        assert agents[0]["name"] == "test-agent"
        assert agents[0]["metadata"]["type"] == "explore"


def test_subagent_get_tools():
    from simple_agent.resources.subagents import SubagentLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test subagent
        agent_dir = Path(tmpdir) / "test-agent"
        agent_dir.mkdir()
        md_file = agent_dir / "AGENT.md"
        md_file.write_text("---\nname: test-agent\ntools: [Read, Glob, Grep]\n---\n# Test Agent")

        loader = SubagentLoader(Path(tmpdir))
        tools = loader.get_subagent_tools("test-agent")
        assert tools == ["Read", "Glob", "Grep"]


def test_hook_loader_scan():
    from simple_agent.resources.hooks import HookLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test hook directory structure
        event_dir = Path(tmpdir) / "message_send_before"
        event_dir.mkdir()
        (event_dir / "hook.py").write_text("def on_message_send_before(): pass")

        loader = HookLoader(Path(tmpdir))
        hooks = loader.list_hooks()
        assert len(hooks) == 1
        assert hooks[0]["event_name"] == "message_send_before"
        assert "hook.py" in hooks[0]["files"]


def test_hook_get_events():
    from simple_agent.resources.hooks import HookLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create multiple event directories
        event1 = Path(tmpdir) / "message_send_before"
        event1.mkdir()
        (event1 / "hook.py").write_text("def on_message_send_before(): pass")

        event2 = Path(tmpdir) / "tool_call_after"
        event2.mkdir()
        (event2 / "hook.py").write_text("def on_tool_call_after(): pass")

        loader = HookLoader(Path(tmpdir))
        hooks = loader.list_hooks()
        assert len(hooks) == 2
        event_names = [h["event_name"] for h in hooks]
        assert "message_send_before" in event_names
        assert "tool_call_after" in event_names


def test_command_loader_scan():
    from simple_agent.resources.commands import CommandLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command
        cmd_dir = Path(tmpdir) / "test-cmd"
        cmd_dir.mkdir()
        md_file = cmd_dir / "COMMAND.md"
        md_file.write_text("---\nname: test-cmd\nusage: /test [args]\n---\n# Test Command")

        loader = CommandLoader(Path(tmpdir))
        commands = loader.list_commands()
        assert len(commands) == 1
        assert commands[0]["name"] == "test-cmd"
        assert commands[0]["metadata"]["usage"] == "/test [args]"


def test_command_get_usage():
    from simple_agent.resources.commands import CommandLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command
        cmd_dir = Path(tmpdir) / "test-cmd"
        cmd_dir.mkdir()
        md_file = cmd_dir / "COMMAND.md"
        md_file.write_text("---\nname: test-cmd\nusage: /test <arg1> [arg2]\n---\n# Test Command")

        loader = CommandLoader(Path(tmpdir))
        usage = loader.get_command_usage("test-cmd")
        assert usage == "/test <arg1> [arg2]"


def test_command_get_usage_default():
    from simple_agent.resources.commands import CommandLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command without usage in metadata
        cmd_dir = Path(tmpdir) / "test-cmd"
        cmd_dir.mkdir()
        md_file = cmd_dir / "COMMAND.md"
        md_file.write_text("---\nname: test-cmd\ndescription: A test command\n---\n# Test Command")

        loader = CommandLoader(Path(tmpdir))
        usage = loader.get_command_usage("test-cmd")
        assert usage == "/test-cmd"
