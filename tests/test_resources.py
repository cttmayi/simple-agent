import tempfile
from pathlib import Path
from simple_agent.resources.base import BaseResource, ResourceLoader


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
