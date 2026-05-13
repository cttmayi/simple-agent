"""View LLM logs in a human-readable format."""

import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_log_file(log_file: Path) -> List[Dict[str, Any]]:
    """Parse a log file into a list of entries."""
    entries = []
    if not log_file.exists():
        return entries

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to human-readable format."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.astimezone().strftime("%H:%M:%S")


def format_message(role: str, content: Optional[str]) -> str:
    """Format a message for display."""
    role_map = {
        "user": "用户",
        "assistant": "助手",
        "tool": "工具",
        "system": "系统"
    }
    role_name = role_map.get(role, role)

    if not content:
        return f"[{role_name}]\n  <无内容>\n"

    return f"[{role_name}]\n  {content}\n"


def format_tool_call(tool_call: Dict[str, Any]) -> str:
    """Format a tool call for display."""
    fn = tool_call.get("function", {})
    name = fn.get("name", "未知工具")
    args_str = fn.get("arguments", "{}")

    try:
        args = json.loads(args_str)
        args_display = ", ".join(f"{k}={v}" for k, v in args.items())
    except:
        args_display = args_str[:100]

    return f"  • {name}({args_display})"


def format_tool_execution(entry: Dict[str, Any]) -> str:
    """Format a tool execution for display."""
    tool_name = entry.get("tool_name", "未知工具")
    arguments = entry.get("arguments", {})
    result = entry.get("result", {})

    args_display = ", ".join(f"{k}={v}" for k, v in arguments.items())
    success = result.get("success", False)
    status = "✓ 成功" if success else "✗ 失败"

    output = f"\n  📦 工具执行: {tool_name}({args_display}) - {status}\n"

    if "error" in result:
        output += f"    错误: {result['error']}\n"
    elif "stdout" in result:
        stdout = result["stdout"].strip()
        if stdout:
            output += f"    输出: {stdout[:200]}\n"
    elif "content" in result:
        content = result["content"]
        if len(content) > 200:
            content = content[:200] + "..."
        output += f"    内容: {content}\n"
    elif "matches" in result:
        matches = result["matches"]
        output += f"    匹配: {len(matches)} 条\n"
        for m in matches[:3]:
            output += f"      行{m['line']}: {m['content'][:80]}\n"

    return output


def format_conversation(entries: List[Dict[str, Any]], request_id: str) -> str:
    """Format a single conversation."""
    output = f"\n{'='*60}\n"
    output += f"对话 ID: {request_id}\n"

    request_entry = None
    response_entry = None
    tool_execs = []
    skills_loaded = set()
    subagents_loaded = set()

    for entry in entries:
        if entry.get("request_id") != request_id:
            continue

        if entry["type"] == "request":
            request_entry = entry
        elif entry["type"] == "response":
            response_entry = entry
        elif entry["type"] == "tool_execution":
            tool_execs.append(entry)
        elif entry["type"] == "skill_loaded":
            skills_loaded.add(entry.get("skill_name"))
        elif entry["type"] == "subagent_loaded":
            subagents_loaded.add(entry.get("subagent_name"))

    if request_entry:
        ts = format_timestamp(request_entry["timestamp"])
        output += f"时间: {ts}\n"
        output += f"模型: {request_entry.get('model', '未知')}\n"

        # Show loaded skills and subagents
        if skills_loaded:
            output += f"🎯 技能: {', '.join(sorted(skills_loaded))}\n"
        if subagents_loaded:
            output += f"🤖 Subagent: {', '.join(sorted(subagents_loaded))}\n"

        # Format messages
        messages = request_entry.get("messages", [])
        for msg in messages:
            output += format_message(msg.get("role"), msg.get("content"))

    if response_entry:
        content = response_entry.get("content")
        if content:
            output += format_message("assistant", content)

        tool_calls = response_entry.get("tool_calls", [])
        if tool_calls:
            output += "\n  🔧 工具调用:\n"
            for tc in tool_calls:
                output += format_tool_call(tc) + "\n"

        usage = response_entry.get("usage")
        if usage:
            output += f"\n  📊 Token使用: {usage.get('prompt_tokens', 0)} + {usage.get('completion_tokens', 0)} = {usage.get('total_tokens', 0)}\n"

    # Format tool executions
    if tool_execs:
        for te in tool_execs:
            output += format_tool_execution(te)

    output += f"{'='*60}\n"
    return output


def print_all_conversations(log_file: Path, show_request_ids: bool = False):
    """Print all conversations from a log file."""
    entries = parse_log_file(log_file)

    if not entries:
        print(f"日志文件为空或不存在: {log_file}")
        return

    # Group by request_id
    request_ids = set()
    for entry in entries:
        if entry["type"] == "request":
            request_ids.add(entry["request_id"])

    if show_request_ids:
        print(f"找到 {len(request_ids)} 个对话:")
        for rid in sorted(request_ids):
            print(f"  - {rid}")
    else:
        for rid in sorted(request_ids):
            print(format_conversation(entries, rid))


def print_recent(log_file: Path, count: int = 5):
    """Print recent conversations."""
    entries = parse_log_file(log_file)

    if not entries:
        print(f"日志文件为空或不存在: {log_file}")
        return

    # Get latest request IDs (by timestamp)
    requests = [e for e in entries if e["type"] == "request"]
    requests.sort(key=lambda x: x["timestamp"], reverse=True)

    recent_ids = [r["request_id"] for r in requests[:count]]

    for rid in recent_ids:
        print(format_conversation(entries, rid))


def search_logs(log_file: Path, query: str):
    """Search logs for a query string."""
    entries = parse_log_file(log_file)

    if not entries:
        print(f"日志文件为空或不存在: {log_file}")
        return

    query = query.lower()
    matches = []

    for entry in entries:
        content = json.dumps(entry, ensure_ascii=False).lower()
        if query in content:
            matches.append(entry)

    if not matches:
        print(f"未找到匹配 '{query}' 的内容")
        return

    print(f"找到 {len(matches)} 条匹配 '{query}' 的记录:\n")

    # Get unique request IDs
    matched_requests = set()
    for entry in matches:
        if entry["type"] == "request":
            matched_requests.add(entry["request_id"])

    for rid in matched_requests:
        print(format_conversation(entries, rid))


def main():
    parser = argparse.ArgumentParser(description="查看 LLM 日志")
    parser.add_argument("log_file", nargs="?", type=Path,
                       help="日志文件路径 (默认: logs/llm/llm-TODAY.jsonl)")
    parser.add_argument("-r", "--recent", type=int, metavar="N",
                       help="显示最近 N 条对话")
    parser.add_argument("-s", "--search", type=str, metavar="QUERY",
                       help="搜索包含指定字符串的对话")
    parser.add_argument("-i", "--ids", action="store_true",
                       help="只显示对话 ID 列表")

    args = parser.parse_args()

    # Default to today's log file
    if args.log_file is None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        args.log_file = Path("logs/llm") / f"llm-{today}.jsonl"

    if args.search:
        search_logs(args.log_file, args.search)
    elif args.recent:
        print_recent(args.log_file, args.recent)
    else:
        print_all_conversations(args.log_file, show_request_ids=args.ids)


if __name__ == "__main__":
    main()
