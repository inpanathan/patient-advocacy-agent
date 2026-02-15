#!/usr/bin/env bash
# First-time git setup: create repo, configure auth, and push.
#
# Usage:
#   ./scripts/git_setup.sh                              # interactive prompts
#   ./scripts/git_setup.sh --token ghp_xxx              # provide token
#   ./scripts/git_setup.sh --token ghp_xxx --repo user/repo
#   ./scripts/git_setup.sh --token ghp_xxx --repo user/repo --private
#
# What it does:
#   1. Configures git user (from args or prompts)
#   2. Stores GitHub token in the remote URL
#   3. Creates the GitHub repo if --create flag is passed
#   4. Pushes local master to remote main

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# -- Defaults ---------------------------------------------------------------
TOKEN=""
REPO=""
VISIBILITY="--private"
CREATE_REPO=false
GIT_USER_NAME=""
GIT_USER_EMAIL=""
BRANCH="main"

# -- Parse args -------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --token)    TOKEN="$2"; shift 2 ;;
        --repo)     REPO="$2"; shift 2 ;;
        --private)  VISIBILITY="--private"; shift ;;
        --public)   VISIBILITY="--public"; shift ;;
        --create)   CREATE_REPO=true; shift ;;
        --name)     GIT_USER_NAME="$2"; shift 2 ;;
        --email)    GIT_USER_EMAIL="$2"; shift 2 ;;
        --branch)   BRANCH="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--token TOKEN] [--repo user/repo] [--create] [--private|--public]"
            echo "          [--name 'Git Name'] [--email email] [--branch main]"
            echo ""
            echo "Options:"
            echo "  --token   GitHub personal access token"
            echo "  --repo    GitHub repo (e.g., inpanathan/person-of-interest)"
            echo "  --create  Create the repo on GitHub (requires gh CLI)"
            echo "  --private Make repo private (default)"
            echo "  --public  Make repo public"
            echo "  --name    Git user name"
            echo "  --email   Git user email"
            echo "  --branch  Remote branch name (default: main)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# -- Interactive prompts for missing values ---------------------------------
if [[ -z "$GIT_USER_NAME" ]]; then
    existing=$(git config user.name 2>/dev/null || true)
    if [[ -n "$existing" ]]; then
        GIT_USER_NAME="$existing"
        echo "Git user.name: $GIT_USER_NAME"
    else
        read -rp "Git user name: " GIT_USER_NAME
    fi
fi

if [[ -z "$GIT_USER_EMAIL" ]]; then
    existing=$(git config user.email 2>/dev/null || true)
    if [[ -n "$existing" ]]; then
        GIT_USER_EMAIL="$existing"
        echo "Git user.email: $GIT_USER_EMAIL"
    else
        read -rp "Git user email: " GIT_USER_EMAIL
    fi
fi

if [[ -z "$TOKEN" ]]; then
    read -rsp "GitHub personal access token: " TOKEN
    echo
fi

if [[ -z "$REPO" ]]; then
    read -rp "GitHub repo (e.g., user/repo-name): " REPO
fi

# -- Configure git user -----------------------------------------------------
git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"
echo "Configured git user: $GIT_USER_NAME <$GIT_USER_EMAIL>"

# -- Create repo on GitHub if requested ------------------------------------
if [[ "$CREATE_REPO" == true ]]; then
    if command -v gh &>/dev/null; then
        echo "Creating GitHub repo: $REPO ($VISIBILITY)..."
        gh repo create "$REPO" "$VISIBILITY" --source=. --remote=origin 2>/dev/null || true
    else
        echo "Warning: gh CLI not found. Create the repo manually at https://github.com/new"
        echo "  Repo name: ${REPO#*/}"
        read -rp "Press Enter once the repo is created..."
    fi
fi

# -- Set remote with token auth --------------------------------------------
REMOTE_URL="https://${TOKEN}@github.com/${REPO}.git"

if git remote get-url origin &>/dev/null; then
    git remote set-url origin "$REMOTE_URL"
    echo "Updated remote origin"
else
    git remote add origin "$REMOTE_URL"
    echo "Added remote origin"
fi

# -- Ensure there's at least one commit ------------------------------------
if ! git rev-parse HEAD &>/dev/null; then
    echo "Error: No commits yet. Run 'git add . && git commit -m \"Initial commit\"' first."
    exit 1
fi

# -- Push -------------------------------------------------------------------
LOCAL_BRANCH=$(git branch --show-current)
echo "Pushing ${LOCAL_BRANCH} -> origin/${BRANCH}..."
git push -u origin "${LOCAL_BRANCH}:${BRANCH}"

echo ""
echo "Done! Repo is live at: https://github.com/${REPO}"
