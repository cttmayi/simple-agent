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


def test_agent_loader_scan():
    from simple_agent.resources.agents import AgentLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test agent
        agent_dir = Path(tmpdir) / "test-agent"
        agent_dir.mkdir()
        md_file = agent_dir / "AGENT.md"
        md_file.write_text("---\nname: test-agent\ndescription: A test agent\ntools: [Read, Glob]\ntype: explore\n---\n# Test Agent")

        loader = AgentLoader(Path(tmpdir))
        agents = loader.list_agents()
        assert len(agents) == 1
        assert agents[0]["name"] == "test-agent"
        assert agents[0]["metadata"]["type"] == "explore"


def test_agent_get_tools():
    from simple_agent.resources.agents import AgentLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test agent
        agent_dir = Path(tmpdir) / "test-agent"
        agent_dir.mkdir()
        md_file = agent_dir / "AGENT.md"
        md_file.write_text("---\nname: test-agent\ntools: [Read, Glob, Grep]\n---\n# Test Agent")

        loader = AgentLoader(Path(tmpdir))
        tools = loader.get_agent_tools("test-agent")
        assert tools == ["Read", "Glob", "Grep"]


def test_hook_loader_loads_json_config():
    """HookLoader loads hooks from JSON configuration file."""
    from simple_agent.resources.hooks import HookLoader
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create hooks.json
        hooks_file = Path(tmpdir) / "hooks.json"
        hooks_file.write_text('''
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Session started'",
            "async": false
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "markdown",
            "content": "Processing..."
          }
        ]
      }
    ]
  }
}
''')

        loader = HookLoader(hooks_file)
        hooks = loader.list_hooks()

        assert len(hooks) == 2
        assert hooks[0]["event_name"] == "SessionStart"
        assert hooks[1]["event_name"] == "UserPromptSubmit"

        # Test getting hooks for specific event
        session_hooks = loader.get_hooks_for_event("SessionStart")
        assert len(session_hooks) == 1
        assert session_hooks[0]["matcher"] == ""
        assert len(session_hooks[0]["hooks"]) == 1


def test_command_loader_scan():
    from simple_agent.resources.commands import CommandLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command as flat .md file
        md_file = Path(tmpdir) / "test-cmd.md"
        md_file.write_text("---\nname: test-cmd\nusage: /test [args]\n---\n# Test Command")

        loader = CommandLoader(Path(tmpdir))
        commands = loader.list_commands()
        assert len(commands) == 1
        assert commands[0]["name"] == "test-cmd"
        assert commands[0]["metadata"]["usage"] == "/test [args]"


def test_command_get_usage():
    from simple_agent.resources.commands import CommandLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command as flat .md file
        md_file = Path(tmpdir) / "test-cmd.md"
        md_file.write_text("---\nname: test-cmd\nusage: /test <arg1> [arg2]\n---\n# Test Command")

        loader = CommandLoader(Path(tmpdir))
        usage = loader.get_command_usage("test-cmd")
        assert usage == "/test <arg1> [arg2]"


def test_command_get_usage_default():
    from simple_agent.resources.commands import CommandLoader
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command without usage in metadata as flat .md file
        md_file = Path(tmpdir) / "test-cmd.md"
        md_file.write_text("---\nname: test-cmd\ndescription: A test command\n---\n# Test Command")

        loader = CommandLoader(Path(tmpdir))
        usage = loader.get_command_usage("test-cmd")
        assert usage == "/test-cmd"


def test_skill_loader_multiple_dirs():
    """Test SkillLoader with multiple directories."""
    with tempfile.TemporaryDirectory() as tmpdir1:
        with tempfile.TemporaryDirectory() as tmpdir2:
            # Create skill in first directory
            skill1_dir = Path(tmpdir1) / "skill1"
            skill1_dir.mkdir()
            md_file1 = skill1_dir / "SKILL.md"
            md_file1.write_text("---\nname: skill1\ndescription: First skill\n---\n# Skill 1")

            # Create skill in second directory
            skill2_dir = Path(tmpdir2) / "skill2"
            skill2_dir.mkdir()
            md_file2 = skill2_dir / "SKILL.md"
            md_file2.write_text("---\nname: skill2\ndescription: Second skill\n---\n# Skill 2")

            # Create skill with same name in second directory (should be skipped)
            skill1_dup = Path(tmpdir2) / "skill1"
            skill1_dup.mkdir()
            md_file_dup = skill1_dup / "SKILL.md"
            md_file_dup.write_text("---\nname: skill1\ndescription: Duplicate skill\n---\n# Duplicate")

            # Load from both directories
            loader = SkillLoader([tmpdir1, tmpdir2])
            skills = loader.list_skills()

            # Should have 2 skills (skill1 from first dir, skill2 from second dir)
            # skill1 from second dir should be skipped due to duplicate name
            assert len(skills) == 2
            skill_names = [s["name"] for s in skills]
            assert "skill1" in skill_names
            assert "skill2" in skill_names

            # skill1 should have description from first directory (not duplicate)
            skill1_info = next(s for s in skills if s["name"] == "skill1")
            assert skill1_info["description"] == "First skill"


def test_skill_loader_string_paths():
    """Test SkillLoader with string paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()
        md_file = skill_dir / "SKILL.md"
        md_file.write_text("---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill")

        # Test with string path
        loader = SkillLoader(str(tmpdir))
        skills = loader.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"
