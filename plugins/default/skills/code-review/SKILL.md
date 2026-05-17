---
name: code-review
description: Provide code review feedback and suggestions
---

# Code Review Skill

This skill helps review code for quality, bugs, and improvements.

## Guidelines

When reviewing code:
1. **Check for bugs**: Look for common issues like off-by-one errors, null pointer exceptions, etc.
2. **Check for security issues**: Look for SQL injection, XSS, improper authentication, etc.
3. **Check for performance issues**: Look for inefficient algorithms, unnecessary computations, etc.
4. **Check for code style**: Check for consistent formatting, naming conventions, etc.
5. **Provide actionable feedback**: Give specific suggestions with code examples

## Code Review Checklist

- [ ] Code works correctly
- [ ] No obvious bugs
- [ ] No security vulnerabilities
- [ ] Reasonable performance
- [ ] Follows project conventions
- [ ] Sufficient error handling
- [ ] Clear variable/function names
- [ ] Appropriate comments/documentation

## Response Format

When providing code review, structure your response like:

```
### Code Review: [filename]

#### Strengths
- [positive feedback]

#### Issues Found
1. **[severity] [issue]**
   - Location: [line number or function]
   - Problem: [description]
   - Suggestion: [fix with example]

#### Summary
[overall assessment]
```

Severity levels: Critical, High, Medium, Low, Nitpick