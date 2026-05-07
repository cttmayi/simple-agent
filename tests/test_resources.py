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
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test resource
        resource_dir = Path(tmpdir) / "test-resource"
        resource_dir.mkdir()
        md_file = resource_dir / "TEST.md"
        md_file.write_text("---\nname: test\ndescription: A test\n---\nContent")

        loader = ResourceLoader(tmpdir)
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
        assert agents[0]["type"] == "explore"


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
        # Create test hook
        hook_dir = Path(tmpdir) / "test-hook"
        hook_dir.mkdir()
        md_file = hook_dir / "HOOK.md"
        md_file.write_text("---\nname: test-hook\nevents: [message_send_before]\n---\n# Test Hook")

        loader = HookLoader(Path(tmpdir))
        hooks = loader.list_hooks()
        assert len(hooks) == 1
        assert hooks[0]["name"] == "test-hook"
        assert "message_send_before" in hooks[0]["events"]


def test_hook_get_events():
    from simple_agent.resources.hooks import HookLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test hook
        hook_dir = Path(tmpdir) / "test-hook"
        hook_dir.mkdir()
        md_file = hook_dir / "HOOK.md"
        md_file.write_text("---\nname: test-hook\nevents: [message_send_before, tool_call_after]\n---\n# Test Hook")

        loader = HookLoader(Path(tmpdir))
        events = loader.get_hook_events("test-hook")
        assert events == ["message_send_before", "tool_call_after"]
