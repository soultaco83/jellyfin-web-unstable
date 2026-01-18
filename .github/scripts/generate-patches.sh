#!/bin/bash
# Script to generate patches from custom modifications before resetting to upstream
# This preserves your custom changes as patch files

set -e

PATCHES_DIR=".github/patches"
PATCH_DEFINITIONS_FILE=".github/patch-definitions.txt"

echo "=== Generating Patches from Custom Modifications ==="

# Create patches directory if it doesn't exist
mkdir -p "$PATCHES_DIR"

# Check if patch definitions file exists
if [ ! -f "$PATCH_DEFINITIONS_FILE" ]; then
    echo "⚠️  No patch definitions file found at $PATCH_DEFINITIONS_FILE"
    echo "Create this file with format: patch-name.patch|file/path/to/modify.js|Brief description"
    exit 0
fi

# Read patch definitions and generate patches
while IFS='|' read -r patch_name file_path description; do
    # Skip empty lines and comments
    [[ -z "$patch_name" || "$patch_name" == \#* ]] && continue

    echo ""
    echo "Processing: $patch_name"
    echo "  File: $file_path"
    echo "  Description: $description"

    # Check if file exists
    if [ ! -f "$file_path" ]; then
        echo "  ⚠️  File not found: $file_path"
        continue
    fi

    # Check if there are changes to this file
    if git diff HEAD -- "$file_path" | grep -q '^[\+\-]'; then
        # Generate patch from current changes
        git diff HEAD -- "$file_path" > "$PATCHES_DIR/$patch_name"
        echo "  ✅ Generated patch: $PATCHES_DIR/$patch_name"
    elif [ -f "$PATCHES_DIR/$patch_name" ]; then
        echo "  ℹ️  No changes detected, keeping existing patch"
    else
        echo "  ⚠️  No changes to generate patch from"
    fi

done < "$PATCH_DEFINITIONS_FILE"

echo ""
echo "=== Patch Generation Complete ==="
echo "Generated patches are stored in: $PATCHES_DIR"
ls -lh "$PATCHES_DIR" || true
