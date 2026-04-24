---
description: Create a pull request with auto-detected context
argument-hint: [title] [description]
allowed-tools: Bash(git:*), Bash(gh:*)
---

Create a pull request.

Title: $1
Description: $2

## Current Context (Auto-detected)

Current branch:
!`git branch --show-current`

Recent commits on this branch:
!`git log origin/main..HEAD --oneline 2>/dev/null || echo "No commits ahead of main"`

Files changed:
!`git diff --stat origin/main 2>/dev/null || git diff --stat HEAD~3`

## Steps

1. Ensure we're not on main/master branch
2. Push current branch to remote (if not already)
3. Create PR using `gh pr create`:
   - Title: $1 (or auto-generate from branch name)
   - Body: $2 (or auto-generate from commits)
4. Return the PR URL

## PR Body Template

If $2 is not provided, generate:

```markdown
## Summary
[Auto-generated from commit messages]

## Changes
[List of changed files with brief descriptions]

## Testing
- [ ] Tests pass locally
- [ ] Manual testing completed

---
Created with `/pr-create`
```

## Output

```
✓ PR Created: [URL]

Title: [title]
Branch: [branch] → main
Changes: [n] files
```
