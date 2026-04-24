---
description: Deep analysis of code against project standards
argument-hint: [file or directory path]
allowed-tools: Read, Grep, Glob
---

Perform deep analysis on: $ARGUMENTS

## Analysis Context

Use our project's coding standards as reference:
@.claude/rules/coding-standards.md

## Analysis Dimensions

### 1. Code Quality
- Complexity (cyclomatic, cognitive)
- Duplication
- Dead code
- Naming conventions

### 2. Architecture
- Separation of concerns
- Dependency direction
- Module boundaries

### 3. Security
- Input validation
- Authentication/authorization
- Sensitive data handling

### 4. Performance
- Obvious inefficiencies
- Resource management
- Caching opportunities

### 5. Maintainability
- Documentation coverage
- Test coverage indicators
- Code readability

## Steps

1. Read the target file(s)
2. If a directory, identify key files
3. Analyze against each dimension
4. Compare with project standards (if available)
5. Generate report

## Output Format

```markdown
## Analysis Report: [target]

### Overview
[One paragraph summary]

### Scores
| Dimension | Score | Notes |
|-----------|-------|-------|
| Quality | ⭐⭐⭐⭐☆ | [brief] |
| Architecture | ⭐⭐⭐☆☆ | [brief] |
| Security | ⭐⭐⭐⭐⭐ | [brief] |
| Performance | ⭐⭐⭐☆☆ | [brief] |
| Maintainability | ⭐⭐⭐⭐☆ | [brief] |

### Key Findings

#### Strengths
- [positive points]

#### Areas for Improvement
- [issues with suggested fixes]

### Recommendations
1. [Prioritized action items]
```
