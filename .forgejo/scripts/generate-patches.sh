#!/bin/bash
# Patches are maintained as static .patch files in .forgejo/patches/
# They are committed directly to the repo and applied fresh each run.
# No generation step is needed — this script is a no-op.

echo "=== Patch Generation ==="
echo "Patches are managed as static files in .forgejo/patches/"
echo "To update a patch: edit the .patch file directly and commit it."
echo ""
echo "Current patches:"
ls -lh .forgejo/patches/*.patch 2>/dev/null || echo "  (none)"
