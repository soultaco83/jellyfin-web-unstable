#!/bin/bash
# AI Patch Fixer — Shell Wrapper
#
# Called by the "AI Patch Fix" workflow after the Reset workflow fails.
# Orchestrates: run AI fixer → commit any corrected patches → re-dispatch Reset workflow.
#
# Safety: tracks retry count via a counter file to prevent infinite loops.
#          Max 3 auto-fix retries total (across all workflow invocations).

set -euo pipefail

REPO="${FORGEJO_REPO:-jellyfin-web-unstable}"
PATCHES_DIR="${PATCHES_DIR:-.forgejo/patches}"
RETRY_COUNT_FILE=".forgejo/ai_fix_retry_count"
MAX_AUTO_RETRIES="${MAX_AUTO_RETRIES:-3}"
FORGEJO_URL="${FORGEJO_URL:-http://10.10.10.220:3000}"
OWNER="${OWNER:-soultaco83}"

echo "=== AI Patch Fixer — ${REPO} ==="
echo ""

# --- Read / increment retry counter ---
RETRY_COUNT=0
if [ -f "$RETRY_COUNT_FILE" ]; then
    RETRY_COUNT=$(cat "$RETRY_COUNT_FILE")
fi

echo "Current auto-fix retry count: ${RETRY_COUNT}/${MAX_AUTO_RETRIES}"

if [ "$RETRY_COUNT" -ge "$MAX_AUTO_RETRIES" ]; then
    echo ""
    echo "❌ MAX AUTO-RETRIES EXHAUSTED (${RETRY_COUNT}/${MAX_AUTO_RETRIES})"
    echo "   Manual intervention required. Review failing patches in .forgejo/patches/"
    exit 1
fi

# --- Check for diagnostics from the failed workflow ---
HAVE_PATCH_FAILURES=false
if [ -f "/tmp/failed_patches.txt" ]; then
    echo ""
    echo "Failed patches detected:"
    cat /tmp/failed_patches.txt
    HAVE_PATCH_FAILURES=true
else
    echo "No /tmp/failed_patches.txt found — checking for non-patch errors..."
fi

# --- Run the AI fixer ---
echo ""
echo "Running AI-powered patch fixer..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

WORKFLOW_ERROR_LOG="${WORKFLOW_ERROR_LOG:-/tmp/workflow_error.log}"

if [ "$HAVE_PATCH_FAILURES" = true ]; then
    if python3 "${SCRIPT_DIR}/ai-patch-fixer.py" --max-retries 3; then
        echo ""
        echo "✅ AI fixer completed successfully"
    else
        FIXER_EXIT=$?
        echo ""
        echo "⚠️  AI fixer exited with code ${FIXER_EXIT}"
        if [ "$FIXER_EXIT" -eq 2 ]; then
            echo "   DEEPSEEK_API_KEY not configured — skipping AI fix"
            exit 2
        fi
        # Continue anyway — maybe some patches were fixed
    fi
else
    echo ""
    echo "Skipping patch fixer (no patch failures to fix)"
fi

# --- If patch fixer found no .patch failures but workflow still failed, try diagnose ---
if [ ! -f "/tmp/failed_patches.txt" ] && [ -f "$WORKFLOW_ERROR_LOG" ]; then
    echo ""
    echo "No patch failures detected — trying non-patch error diagnosis..."
    if python3 "${SCRIPT_DIR}/ai-patch-fixer.py" --diagnose "$WORKFLOW_ERROR_LOG" --max-retries 3; then
        echo "✅ New patch generated for non-patch workflow failure"
    else
        DIAG_EXIT=$?
        echo "⚠️  Could not diagnose non-patch failure (exit code ${DIAG_EXIT})"
    fi
fi

# --- Check if any patch files changed ---
PATCH_CHANGES=$(git diff --name-only "$PATCHES_DIR" 2>/dev/null || true)
if [ -n "$PATCH_CHANGES" ]; then
    echo ""
    echo "Patches modified — committing and pushing fixes..."

    git config user.name "AI Patch Fixer (DeepSeek)"
    git config user.email "ai-fixer@forgejo.local"

    CHANGED_PATCHES=$(echo "$PATCH_CHANGES" | tr '\n' ' ')
    git add "$PATCHES_DIR"

    git commit -m "AI-fixed patches: ${CHANGED_PATCHES}" \
        -m "Auto-corrected by DeepSeek AI patch fixer (retry ${RETRY_COUNT}/${MAX_AUTO_RETRIES})" \
        -m "Patches were failing due to upstream changes — line offsets updated."

    # Push the fixes
    if ! git push origin master; then
        echo "❌ Failed to push corrected patches"
        exit 1
    fi

    echo "✅ Corrected patches pushed"
else
    echo ""
    echo "No patches were modified by the AI fixer"
fi

# --- Increment retry counter ---
NEW_COUNT=$((RETRY_COUNT + 1))
echo "$NEW_COUNT" > "$RETRY_COUNT_FILE"
git add "$RETRY_COUNT_FILE"
git commit -m "Bump AI fix retry counter: ${NEW_COUNT}/${MAX_AUTO_RETRIES}" || true
git push origin master || true

echo ""
echo "=== Triggering Reset workflow re-run ==="

# Use Forgejo API to re-dispatch the workflow
# POST /api/v1/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches
# The workflow file is: "Reset to Upstream and Merge PRs.yml"
WORKFLOW_FILE="Reset to Upstream and Merge PRs.yml"

HTTP_CODE=$(curl -s -o /tmp/forgejo_dispatch_response.txt -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: token ${FORGEJO_TOKEN}" \
    -d "{\"ref\": \"master\"}" \
    "${FORGEJO_URL}/api/v1/repos/${OWNER}/${REPO}/actions/workflows/$(echo -n "$WORKFLOW_FILE" | jq -sRr '@uri')/dispatches")

if [ "$HTTP_CODE" -eq 204 ] || [ "$HTTP_CODE" -eq 200 ]; then
    echo "✅ Reset workflow re-dispatched successfully (HTTP ${HTTP_CODE})"
else
    echo "❌ Failed to re-dispatch workflow (HTTP ${HTTP_CODE})"
    cat /tmp/forgejo_dispatch_response.txt
    exit 1
fi

echo ""
echo "=== AI Patch Fixer completed ==="
echo "Retry count: ${NEW_COUNT}/${MAX_AUTO_RETRIES}"
echo "Reset workflow has been re-triggered."
