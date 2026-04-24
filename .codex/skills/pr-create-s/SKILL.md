---
name: pr-create-s
description: Create a pull request with auto-detected context. Use when user wants to create a pull request with /pr-create-s.
argument-hint: [title] [description]
allowed-tools: Bash(git:*), Bash(gh:*)
---

# PR Create Skill (/pr-create-s)

Create a pull request with auto-detected branch and change context.

## Input

- `$1`: PR title
- `$2`: PR description (optional)

## Process

### Step 1: Detect Current Branch

Run `git branch --show-current` to get current branch name.

### Step 2: Get Recent Commits

Run `git log origin/main..HEAD --oneline` to see commits ahead of main.

### Step 3: Get Changed Files

Run `git diff --stat origin/main` to see files that changed.

### Step 4: Push Branch (if needed)

Check if branch exists on remote. If not, push with:
```
git push -u origin <branch-name>
```

### Step 5: Create PR

Use `gh pr create` with:
- `--title`: PR title from `$1`
- `--body`: PR description (use template below if `$2` not provided)
- `--base`: main

## PR Body Template

If description not provided, generate:

```markdown
## Summary
[Auto-generated from commit messages]

## Changes
[List of changed files with brief descriptions]

## Testing
- [ ] Tests pass locally
- [ ] Manual testing completed

---
Created with `/pr-create-s`
```

## Output

```
✓ PR Created: [URL]

Title: [title]
Branch: [branch] → main
Changes: [n] files
```

## Guidelines

- Ensure branch is pushed before creating PR
- Use clear, descriptive PR titles
- Provide meaningful descriptions that explain context and motivation
- Link related issues or discussions in the PR body
