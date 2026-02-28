#!/bin/bash
# Script to apply all patches in .forgejo/patches/ after merging upstream changes.
# No patch-definitions.txt needed — target file paths are embedded in each patch.

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
        echo "  ⚠️  Clean apply failed, attempting 3-way merge..."
        if git apply --3way "$PATCH_FILE" 2>&1; then
            echo "  ✅ Applied with 3-way merge"
            APPLIED_COUNT=$((APPLIED_COUNT + 1))
        else
            echo "  ❌ Failed to apply (conflicts detected)"
            FAILED_COUNT=$((FAILED_COUNT + 1))
            echo "$PATCH_NAME|unknown|apply conflict" >> /tmp/failed_patches.txt
        fi
    fi
done

echo ""
echo "=== Patch Application Summary ==="
echo "Total: $PATCH_COUNT  Applied: $APPLIED_COUNT  Failed: $FAILED_COUNT"

if [ $FAILED_COUNT -gt 0 ]; then
    echo ""
    echo "⚠️  Some patches failed. Check git status for conflicted files."
    if [ -f "/tmp/failed_patches.txt" ]; then
        while IFS='|' read -r patch_name file_path reason; do
            echo "  - $patch_name — $reason"
        done < /tmp/failed_patches.txt
    fi
    exit 1
fi

echo ""
echo "✅ All patches applied successfully!"
