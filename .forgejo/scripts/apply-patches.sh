#!/bin/bash
# Script to apply all patches in .forgejo/patches/ after merging upstream changes.
# No patch-definitions.txt needed — target file paths are embedded in each patch.
#
# Exit codes:
#   0 - All patches applied cleanly (or patched files are clean)
#   1 - One or more patches failed to apply
#   2 - Merge conflict markers detected in source files (build will fail)

# NOTE: No 'set -e' here — we track failures manually via FAILED_COUNT.

PATCHES_DIR=".forgejo/patches"

echo "=== Applying Custom Patches After Upstream Merge ==="

if [ ! -d "$PATCHES_DIR" ]; then
    echo "⚠️  No patches directory found at $PATCHES_DIR"
    exit 0
fi

PATCH_FILES=("$PATCHES_DIR"/*.patch)

if [ ! -e "${PATCH_FILES[0]}" ]; then
    echo "No .patch files found in $PATCHES_DIR"
    exit 0
fi

PATCH_COUNT=0
APPLIED_COUNT=0
FAILED_COUNT=0

for PATCH_FILE in "${PATCH_FILES[@]}"; do
    PATCH_NAME=$(basename "$PATCH_FILE")
    PATCH_COUNT=$((PATCH_COUNT + 1))

    echo ""
    echo "[$PATCH_COUNT] Applying: $PATCH_NAME"

    if git apply --check "$PATCH_FILE" 2>&1; then
        git apply "$PATCH_FILE"
        echo "  ✅ Applied successfully"
        APPLIED_COUNT=$((APPLIED_COUNT + 1))
    else
        echo "  ⚠️  Clean apply failed, capturing diagnostics..."
        # Record the check failure output
        CHECK_OUTPUT=$(git apply --check "$PATCH_FILE" 2>&1 || true)
        echo "$CHECK_OUTPUT" > "/tmp/patch_check_${PATCH_NAME}.log"

        # Extract target file paths from the patch for AI context
        TARGET_FILES=$(grep -E '^\+\+\+ b/' "$PATCH_FILE" | sed 's|^+++ b/||' | head -5)
        echo "$TARGET_FILES" > "/tmp/patch_targets_${PATCH_NAME}.txt"

        echo "  ⚠️  Clean apply failed, attempting 3-way merge..."
        if git apply --3way "$PATCH_FILE" 2>&1; then
            echo "  ⚠️  Applied with 3-way merge — checking for unresolved conflicts..."
        else
            MERGE_OUTPUT=$(git apply --3way "$PATCH_FILE" 2>&1 || true)
            echo "$MERGE_OUTPUT" > "/tmp/patch_3way_${PATCH_NAME}.log"
            echo "  ❌ Failed to apply (conflicts detected)"
            FAILED_COUNT=$((FAILED_COUNT + 1))
            echo "$PATCH_NAME|unknown|apply conflict" >> /tmp/failed_patches.txt
        fi
    fi
done

echo ""
echo "=== Checking for Unresolved Merge Markers ==="

# Scan all tracked .ts, .tsx, .js, .jsx, .scss, .css, .html files for unresolved merge markers.
# git apply --3way can leave <<<<<<< / ======= / >>>>>>> in files,
# which will cause build errors.
CONFLICT_FILES=$(grep -rlE '<<<<<<<|>>>>>>>|=======' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.scss' --include='*.css' --include='*.html' --include='*.json' . 2>/dev/null || true)

if [ -n "$CONFLICT_FILES" ]; then
    echo ""
    echo "❌ UNRESOLVED MERGE CONFLICT MARKERS DETECTED:"
    echo ""
    while IFS= read -r file; do
        echo "  $file"
    done <<< "$CONFLICT_FILES"
    echo ""
    echo "These markers will cause build errors."
    echo "Fix the conflicts manually or regenerate the patches."
    FAILED_COUNT=$((FAILED_COUNT + 1))
    # Record each conflicted file as a patch failure so the workflow can report it
    while IFS= read -r file; do
        echo "MERGE_MARKERS|$file|unresolved <<<<<<< markers" >> /tmp/failed_patches.txt
    done <<< "$CONFLICT_FILES"
fi

echo ""
echo "=== Patch Application Summary ==="
echo "Total: $PATCH_COUNT  Applied: $APPLIED_COUNT  Failed: $FAILED_COUNT"

if [ $FAILED_COUNT -gt 0 ]; then
    echo ""
    echo "⚠️  Some patches failed or left unresolved merge markers."
    if [ -f "/tmp/failed_patches.txt" ]; then
        while IFS='|' read -r patch_name file_path reason; do
            echo "  - $patch_name — $reason ($file_path)"
        done < /tmp/failed_patches.txt
    fi
    exit 1
fi

echo ""
echo "✅ All patches applied successfully!"
