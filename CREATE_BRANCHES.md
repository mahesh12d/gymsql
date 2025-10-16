# Creating Development Branches

## Current Situation
You currently only have:
- `main` branch (triggers **production** deployment)
- `replit-agent` branch

## What You Need
- `develop` branch (for development work → triggers **dev** deployment)
- `staging` branch (for UAT testing → triggers **UAT** deployment)
- `main` branch (for production → triggers **production** deployment)

## How to Create and Use Branches

### Step 1: Create the Branches

Run these commands in the Replit shell:

```bash
# Create develop branch from main
git checkout -b develop main

# Push to GitHub
git push -u origin develop

# Create staging branch from main
git checkout -b staging main

# Push to GitHub
git push -u origin staging

# List all branches to confirm
git branch -a
```

### Step 2: Verify Branches Exist

You should now see:
```
  develop
* staging
  main
  replit-agent
  remotes/origin/develop
  remotes/origin/staging
  remotes/origin/main
```

### Step 3: Set Your Default Working Branch

For daily development work, switch to `develop`:

```bash
git checkout develop
```

## ✅ Correct Workflow After Setup

### Daily Development (99% of the time)
```bash
# Make sure you're on develop branch
git checkout develop

# Make your changes
# ... edit files ...

# Commit and push
git add .
git commit -m "Add new feature"
git push origin develop

# ✅ This triggers DEVELOPMENT deployment (not production!)
```

### Deploy to UAT for Testing
```bash
# Switch to staging
git checkout staging

# Merge develop into staging
git merge develop

# Push to trigger UAT deployment
git push origin staging

# ✅ This triggers UAT deployment
```

### Deploy to Production
```bash
# Switch to main
git checkout main

# Merge staging into main
git merge staging

# Push to trigger production deployment
git push origin main

# ✅ This triggers PRODUCTION deployment
```

## 🚨 Important Rules

1. **Never work directly on `main`** - main is for production only
2. **Always start from `develop`** - this is your daily working branch
3. **Follow the flow:** develop → staging → main
4. **Test in UAT first** - always test in staging before deploying to production

## Branch Protection (Recommended)

After creating branches, go to GitHub and set up branch protection:

1. Go to: https://github.com/mahesh12d/gymsql/settings/branches
2. Add protection rules for `main` and `staging`:
   - Require pull request reviews before merging
   - Prevent direct pushes to these branches
   - This ensures you always go through the proper flow

## What Each Branch Does

| Branch | Purpose | Deploys To | When to Use |
|--------|---------|------------|-------------|
| `develop` | Daily development work | Dev environment (Cloud Run dev) | All the time! |
| `staging` | UAT/Testing before production | UAT environment (Cloud Run UAT) | Before production release |
| `main` | Production code only | Production (Cloud Run prod) | After UAT approval |

## Quick Reference

```bash
# See which branch you're on
git branch

# Switch to develop for daily work
git checkout develop

# Check what will be deployed
git status

# Always verify before pushing!
git log --oneline -5
```

Remember: **Work on `develop`, test on `staging`, deploy to `main`** 🚀
