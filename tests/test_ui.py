from simple_agent.ui.renderer import UIRenderer
from io import StringIO

def test_renderer_output():
    output = StringIO()
    renderer = UIRenderer(output)
    renderer.render_message("user", "Hello")
    result = output.getvalue()
    assert "Hello" in result

def test_renderer_code_block():
    output = StringIO()
    renderer = UIRenderer(output)
    renderer.render_code("python", "print('hello')")
    result = output.getvalue()
    assert "print('hello')" in result

def test_renderer_error():
    output = StringIO()
    renderer = UIRenderer(output)
    renderer.render_error("Something went wrong")
    result = output.getvalue()
    assert "Something went wrong" in result
