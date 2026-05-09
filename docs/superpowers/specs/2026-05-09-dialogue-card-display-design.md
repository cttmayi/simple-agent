# Dialogue Card Display Design

**Date:** 2026-05-09
**Author:** Claude
**Status:** Approved

## Overview

Redesign the web log analyzer to display conversations as cards organized by log file. Each API call is shown as a card with a summary view and expandable details.

## Requirements

1. **Organize by log file** - Conversations from the same log file are grouped together
2. **Card-based display** - Each API call (request/response/tool_execution) is displayed as a card
3. **Summary view** - Cards show key information at a glance
4. **Expandable details** - Clicking a card reveals complete information in structured sections
5. **Usage display** - Response cards show token usage in summary

## Design

### Two-Level Structure

**Level 1: Log File Group**
- Shows log file name and total API calls
- Click to expand/collapse all cards in the group

**Level 2: API Call Card**
- Shows summary of request, response, and tool executions
- Click to expand/collapse detailed view

### Card Summary

Each card displays:
- **Header**: Model name + timestamp
- **Request summary**: `[REQUEST]` badge + last user message preview
- **Response summary**: `[RESPONSE]` badge + timestamp + **usage info** + tool count
- **Tool summary**: `[TOOL]` badges for each tool (if any)

**Usage display format:**
```
📤 [RESPONSE] 18:16:05 | 1500 tokens (500 + 1000) | 2 tools
                        总计    prompt  completion
```

### Expanded View

When expanded, each card shows structured sections:

**Request Section**
- Complete messages array
- Each message shows role and content
- Collapsible

**Response Section**
- Complete content
- Usage breakdown (prompt + completion + total)
- Tool calls list with names and parameters
- Each tool call collapsible for detailed parameters

**Tool Execution Section**
- Tool name and call ID
- Complete result object
- JSON formatted
- Red highlight for errors

### Interaction

- Click card header: toggle entire card
- Click section header: toggle individual section
- Double-click: quick expand/collapse

## Data Flow

1. `get_all_conversations()` returns conversations grouped by log file
2. Frontend groups conversations by `log_file` field
3. For each group, render a session header with the cards
4. Each card renders its summary by default
5. On click, card expands to show structured sections

## Implementation Notes

- Reuse existing `groupConversationsByLog()` function
- Modify `renderConversations()` to use card layout
- Add new `renderCardSummary()` and `renderCardDetails()` functions
- Add CSS for card styling and animations
- Maintain existing deduplication logic for messages