---
description: Deploy with safety checks and automatic testing
argument-hint: [environment: staging | production]
allowed-tools: Bash(npm:*), Bash(git:*), Read
hooks:
  - event: PreToolUse
    matcher: Bash
    command: |
      if [[ "$TOOL_INPUT" == *"production"* ]] && [[ "$TOOL_INPUT" == *"deploy"* ]]; then
        echo "⚠️ Production deployment detected - extra verification required"
      fi
  - event: PostToolUse
    matcher: Bash
    command: echo "✓ Step completed at $(date +%H:%M:%S)"
    once: true
---

Deploy the application to: $ARGUMENTS

## Pre-deployment Checks

Before deploying, verify:
1. All tests pass (`npm test`)
2. No uncommitted changes (`git status`)
3. On correct branch (main/master for production)

## Deployment Steps

### For Staging ($ARGUMENTS = "staging")
1. Run tests
2. Build the application
3. Deploy to staging environment
4. Verify deployment health

### For Production ($ARGUMENTS = "production")
1. Run full test suite
2. Check that staging is healthy
3. Create a git tag for the release
4. Build and deploy
5. Verify production health
6. Notify team

## Safety Rules

- NEVER deploy to production from a non-main branch
- ALWAYS run tests before deploying
- If tests fail, STOP and report

## Output

```
## Deployment Report

Environment: [staging/production]
Status: [success/failed]
Time: [duration]

### Steps Completed
✓ Tests passed
✓ Build successful
✓ Deployed
✓ Health check passed

### Next Steps
[Any follow-up actions needed]
```
