#!/usr/bin/env python3
"""
AI-Powered Patch Fixer for Forgejo CI/CD.

Called after the 'Reset to Upstream and Merge PRs' workflow fails due
to patch application errors. Reads diagnostic files produced by
apply-patches.sh, sends them to DeepSeek API for correction, and writes
corrected .patch files back to .forgejo/patches/.

Usage:
    python3 ai-patch-fixer.py [--dry-run] [--max-retries N]

Environment variables:
    DEEPSEEK_API_KEY   – DeepSeek API key (required)
    PATCHES_DIR        – path to .forgejo/patches/ (default: .forgejo/patches)
    FORGEJO_REPO       – repo slug for log messages (e.g. jellyfin-server-unstable)
"""

import json
import os
import subprocess
import sys
import argparse
import hashlib
import time
from pathlib import Path
from urllib import request, error as urllib_error

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
MAX_RETRIES = 3
DIAGNOSTICS_FILE = "/tmp/failed_patches.txt"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[ai-patch-fixer] {msg}", flush=True)


def read_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def write_file(path: str, content: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")


def run_cmd(cmd: str, cwd: str = ".") -> tuple[int, str, str]:
    """Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# DeepSeek API call
# ---------------------------------------------------------------------------

def call_deepseek(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
) -> str:
    """Send a chat completion request to DeepSeek. Returns response text."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        DEEPSEEK_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
    except urllib_error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        log(f"DeepSeek API HTTP {e.code}: {error_body}")
        raise
    except Exception as e:
        log(f"DeepSeek API request failed: {e}")
        raise


# ---------------------------------------------------------------------------
# Patch extraction / sanitisation
# ---------------------------------------------------------------------------

def extract_unified_diff(text: str) -> str:
    """Extract only the unified diff block from the AI's response.
    Some models wrap the diff in markdown code fences — strip those."""
    lines = text.splitlines()
    start = None
    end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            if start is None:
                start = i + 1  # after the opening fence
            else:
                end = i
                break
    if start is not None and end is not None:
        return "\n".join(lines[start:end]).strip() + "\n"
    # If no fences, look for the first diff-like line
    for i, line in enumerate(lines):
        if line.startswith("diff --git "):
            return "\n".join(lines[i:]).strip() + "\n"
    return text.strip() + "\n"


def validate_patch(patch_content: str, patches_dir: str) -> bool:
    """Write patch to a temp file and run git apply --check."""
    tmp_patch = "/tmp/ai_generated.patch"
    write_file(tmp_patch, patch_content)
    rc, stdout, stderr = run_cmd(f"git apply --check {tmp_patch}")
    if rc == 0:
        return True
    log(f"  patch validation FAILED: {stderr.strip()}")
    return False


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert software engineer who fixes failing git patches.
You receive:
1. The ORIGINAL .patch file that failed to apply.
2. The current content of the file(s) the patch targets.
3. The error output from `git apply --check`.

Your task: return ONLY a corrected unified diff (.patch) that will apply
successfully to the current file state. Do not rewrite the diff format —
preserve the same intent, just adjust line offsets and context to match
the file as it exists now. If the change is already present in the target
file, return the comment "# PATCH ALREADY APPLIED — NO-OP"."""

SYSTEM_PROMPT_DIAGNOSE = """You are an expert Jellyfin developer diagnosing a CI/CD failure.
You receive:
1. The full error logs from a failed "Reset to Upstream & Merge PRs" workflow.
2. The list of files changed in the working tree (`git diff --name-only`).
3. The current state of relevant source files.

The workflow resets to upstream jellyfin/jellyfin, merges PRs, and applies
custom .patch files. It can fail due to:
- Merge conflicts between PRs and the base
- Code that no longer compiles after upstream changes
- Missing imports, renamed APIs, removed methods

Your task: analyze the error and return a unified diff (.patch file) that
fixes the issue. The patch should make the minimal necessary change to
resolve the specific error shown in the logs.

If the error is a merge conflict in a specific file, generate a patch that
resolves it by keeping our custom changes adapted to the new upstream code.
If the error is a build failure, generate a patch that fixes the broken code.

Return ONLY the corrected unified diff. Start with 'diff --git '.
If you cannot determine the fix from the available information, return
"# CANNOT_DIAGNOSE: <reason>"."""


def build_user_prompt(
    patch_name: str,
    patch_content: str,
    diagnostics_dir: str,
) -> str:
    parts = [f"## Failing Patch: {patch_name}\n"]

    # Add patch content
    parts.append("### Original Patch Content")
    parts.append("```diff")
    parts.append(patch_content)
    parts.append("```\n")

    # Add git apply --check output
    check_log_path = os.path.join(
        diagnostics_dir, f"patch_check_{patch_name}.log"
    )
    check_output = read_file(check_log_path)
    if check_output:
        parts.append("### Git Apply Check Error")
        parts.append("```")
        parts.append(check_output.strip())
        parts.append("```\n")

    # Add 3-way merge output if available
    threeway_path = os.path.join(
        diagnostics_dir, f"patch_3way_{patch_name}.log"
    )
    threeway_output = read_file(threeway_path)
    if threeway_output:
        parts.append("### 3-Way Merge Error")
        parts.append("```")
        parts.append(threeway_output.strip())
        parts.append("```\n")

    # Add current target file content
    targets_path = os.path.join(
        diagnostics_dir, f"patch_targets_{patch_name}.txt"
    )
    targets = read_file(targets_path).strip()
    if targets:
        parts.append("### Current Target File(s) Content")
        for target_file in targets.splitlines():
            target_file = target_file.strip()
            if not target_file:
                continue
            current_content = read_file(target_file)
            if current_content:
                parts.append(f"**{target_file}**:")
                # Limit to 300 lines to avoid blowing the token budget
                content_lines = current_content.splitlines()
                if len(content_lines) > 300:
                    current_content = (
                        "\n".join(content_lines[:300])
                        + f"\n... (truncated, {len(content_lines)} total lines)"
                    )
                parts.append("```")
                parts.append(current_content)
                parts.append("```\n")
            else:
                parts.append(f"**{target_file}**: (file not found in workspace)\n")

    parts.append("Return ONLY the corrected unified diff.patch content.")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main fixer logic
# ---------------------------------------------------------------------------

def fix_patch(
    patch_name: str,
    patches_dir: str,
    diagnostics_dir: str,
    api_key: str,
    max_retries: int = MAX_RETRIES,
) -> bool:
    """Attempt to fix a single failing patch. Returns True on success."""
    patch_path = os.path.join(patches_dir, patch_name)
    original_content = read_file(patch_path)

    if not original_content.strip():
        log(f"  SKIP: {patch_name} is empty")
        return False

    # Check if patch already applied (file already contains the change)
    # Quick heuristic: check if the added lines from the patch exist in target
    targets_path = os.path.join(
        diagnostics_dir, f"patch_targets_{patch_name}.txt"
    )
    target_files = read_file(targets_path).strip()
    all_already_applied = True
    if target_files:
        added_lines = [
            line[1:]  # strip the '+' prefix
            for line in original_content.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        for tf in target_files.splitlines():
            tf = tf.strip()
            if not tf:
                continue
            file_content = read_file(tf)
            if file_content:
                for added in added_lines:
                    if added.strip() and added.strip() not in file_content:
                        all_already_applied = False
                        break
                if not all_already_applied:
                    break

    if all_already_applied and target_files:
        # Verify: try applying the patch
        rc, _, _ = run_cmd(
            f"git apply --check {patch_path}"
        )
        if rc == 0:
            log(f"  ✅ {patch_name} — all hunks already applied (no-op, check passed)")
            return True
        else:
            # Failing despite lines present — check if git reports "already applied"
            # Use --reject (without --check) so reject files are generated and
            # stdout may contain "already applied" hints
            rc_reject, stdout, _ = run_cmd(
                f"git apply --reject {patch_path} 2>&1 || true"
            )
            if "already applied" in stdout.lower():
                log(f"  ✅ {patch_name} — all hunks already applied (no-op)")
                return True

    user_prompt = build_user_prompt(patch_name, original_content, diagnostics_dir)

    for attempt in range(1, max_retries + 1):
        log(f"  DeepSeek API call — attempt {attempt}/{max_retries}")

        try:
            response = call_deepseek(api_key, SYSTEM_PROMPT, user_prompt)
        except Exception as e:
            log(f"  ❌ API error on attempt {attempt}: {e}")
            if attempt == max_retries:
                return False
            continue

        corrected = extract_unified_diff(response)

        # Handle NO-OP signal from the model
        if "PATCH ALREADY APPLIED" in corrected:
            log(f"  ✅ {patch_name} — AI reports already applied (no-op)")
            return True

        if not corrected.strip() or not corrected.startswith("diff --git "):
            log(f"  ⚠️  AI response doesn't look like a diff, retrying...")
            # Append feedback to prompt for next attempt
            user_prompt += (
                f"\n\nYour previous response did not contain a valid unified diff. "
                f"It must start with 'diff --git '. Try again."
            )
            continue

        if validate_patch(corrected, patches_dir):
            write_file(patch_path, corrected)
            log(f"  ✅ {patch_name} — corrected patch written")
            return True
        else:
            log(f"  ⚠️  Corrected patch failed validation, retrying...")
            # Provide validation failure feedback
            rc, _, stderr = run_cmd(
                "git apply --check /tmp/ai_generated.patch"
            )
            user_prompt += (
                f"\n\nYour corrected patch still fails git apply --check with:\n{stderr}\n"
                f"Please fix the offsets and try again."
            )

    log(f"  ❌ {patch_name} — could not fix after {max_retries} attempts")
    return False


# ---------------------------------------------------------------------------
# Non-patch error diagnosis (create NEW patches for unknown failures)
# ---------------------------------------------------------------------------

def diagnose_non_patch_error(
    error_log_path: str,
    patches_dir: str,
    api_key: str,
    max_retries: int = MAX_RETRIES,
) -> bool:
    """
    Analyze workflow error logs (not a patch failure) and generate a brand-new
    .patch file to fix the issue. Returns True if a valid patch was created.
    """
    error_log = read_file(error_log_path)
    if not error_log.strip():
        log("  Error log is empty — cannot diagnose")
        return False

    # Limit log size to avoid token limits
    log_lines = error_log.splitlines()
    if len(log_lines) > 400:
        error_log = "\n".join(log_lines[:400]) + f"\n... (truncated, {len(log_lines)} total lines)"

    # Get list of modified files that might reveal the issue
    rc, changed_files, _ = run_cmd("git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only")
    changed = changed_files.strip()

    parts = [
        "## Workflow Failure Diagnosis\n",
        "### Error Logs",
        "```",
        error_log,
        "```\n",
    ]

    if changed:
        parts.append("### Files Changed in This Run")
        parts.append("```")
        parts.append(changed)
        parts.append("```\n")

        # Include content of relevant changed source files (up to 200 lines each)
        parts.append("### Changed Source Files (relevant excerpts)")
        for file_path in changed.splitlines()[:10]:
            file_path = file_path.strip()
            if not file_path:
                continue
            # Only include source files
            if not any(file_path.endswith(ext) for ext in (".cs", ".csproj", ".ts", ".tsx", ".js", ".jsx", ".json", ".scss", ".css", ".html")):
                continue
            content = read_file(file_path)
            if content:
                content_lines = content.splitlines()
                if len(content_lines) > 200:
                    content = "\n".join(content_lines[:200]) + f"\n... ({len(content_lines)} total lines)"
                parts.append(f"**{file_path}**:")
                parts.append("```")
                parts.append(content)
                parts.append("```\n")

    parts.append(
        "Generate a NEW unified diff patch that fixes the error shown above. "
        "The patch filename should follow the pattern: ai-fix-<descriptive-slug>.patch\n"
        "Return ONLY the diff content starting with 'diff --git '."
    )

    user_prompt = "\n".join(parts)

    for attempt in range(1, max_retries + 1):
        log(f"  DeepSeek diagnosis — attempt {attempt}/{max_retries}")

        try:
            response = call_deepseek(api_key, SYSTEM_PROMPT_DIAGNOSE, user_prompt)
        except Exception as e:
            log(f"  ❌ API error on attempt {attempt}: {e}")
            if attempt == max_retries:
                return False
            continue

        diff = extract_unified_diff(response)

        if "CANNOT_DIAGNOSE" in diff:
            log(f"  ❌ AI cannot diagnose: {diff.replace('# CANNOT_DIAGNOSE:', '').strip()}")
            return False

        if not diff.startswith("diff --git "):
            log(f"  ⚠️  Response doesn't contain a valid diff, retrying...")
            user_prompt += "\n\nYour previous response did not contain 'diff --git '. Try again."
            continue

        if validate_patch(diff, patches_dir):
            # Generate a unique patch filename
            slug = hashlib.md5(diff.encode()).hexdigest()[:8]
            timestamp = int(time.time())
            new_patch_name = f"ai-fix-{timestamp}-{slug}.patch"
            new_patch_path = os.path.join(patches_dir, new_patch_name)
            write_file(new_patch_path, diff)
            log(f"  ✅ New patch created: {new_patch_name}")
            return True
        else:
            log(f"  ⚠️  Generated patch failed validation, retrying...")
            rc, _, stderr = run_cmd("git apply --check /tmp/ai_generated.patch")
            user_prompt += (
                f"\n\nYour patch fails git apply --check with:\n{stderr}\n"
                f"Please fix it."
            )

    log(f"  ❌ Could not diagnose after {max_retries} attempts")
    return False


def main():
    parser = argparse.ArgumentParser(description="AI-powered patch fixer")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write corrected patches, only validate",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAX_RETRIES,
        help=f"Max AI retries per patch (default: {MAX_RETRIES})",
    )
    parser.add_argument(
        "--diagnose",
        type=str,
        default=None,
        metavar="ERROR_LOG_PATH",
        help="Diagnose a non-patch workflow failure and generate a new .patch",
    )
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        log("ERROR: DEEPSEEK_API_KEY environment variable not set")
        sys.exit(2)

    patches_dir = os.environ.get("PATCHES_DIR", ".forgejo/patches")
    diagnostics_dir = "/tmp"
    repo = os.environ.get("FORGEJO_REPO", "unknown")

    log(f"Repo: {repo}")
    log(f"Patches dir: {patches_dir}")
    log(f"Max retries per patch: {args.max_retries}")
    log("")

    # --- Diagnose mode: non-patch failure → create new patch ---
    if args.diagnose:
        log("Running in DIAGNOSE mode — workflow failure is NOT a patch error")
        log(f"Error log: {args.diagnose}")
        if not os.path.isfile(args.diagnose):
            log(f"ERROR: error log file not found: {args.diagnose}")
            sys.exit(1)
        ok = diagnose_non_patch_error(
            error_log_path=args.diagnose,
            patches_dir=patches_dir,
            api_key=api_key,
            max_retries=args.max_retries,
        )
        if ok:
            log("✅ New patch generated for non-patch workflow failure")
            sys.exit(0)
        else:
            log("❌ Could not diagnose non-patch failure")
            sys.exit(1)

    if not os.path.isfile(DIAGNOSTICS_FILE):
        log("No /tmp/failed_patches.txt found — nothing to fix")
        # Fall through to check if we should try diagnose mode
        error_log = os.environ.get("WORKFLOW_ERROR_LOG", "")
        if error_log and os.path.isfile(error_log):
            log("Attempting diagnose mode as fallback...")
            ok = diagnose_non_patch_error(
                error_log_path=error_log,
                patches_dir=patches_dir,
                api_key=api_key,
                max_retries=args.max_retries,
            )
            if ok:
                log("✅ New patch generated for non-patch workflow failure")
                sys.exit(0)
        sys.exit(0)

    failed_entries = []
    with open(DIAGNOSTICS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            patch_name = parts[0].strip()
            target_file = parts[1].strip() if len(parts) > 1 else "unknown"
            reason = parts[2].strip() if len(parts) > 2 else "unknown"
            # Skip merge-marker entries — those are handled separately
            if patch_name == "MERGE_MARKERS":
                log(f"  ⚠️  Unresolved merge markers in {target_file} — AI can't auto-fix these")
                continue
            failed_entries.append((patch_name, target_file, reason))

    if not failed_entries:
        log("All failures are merge markers — can't auto-fix")
        sys.exit(1)

    log(f"Found {len(failed_entries)} patch(es) to fix:")
    for name, target, reason in failed_entries:
        log(f"  ❌ {name} → {target} ({reason})")

    log("")
    log("Attempting AI-powered fixes...")

    success_count = 0
    fail_count = 0

    for patch_name, target_file, reason in failed_entries:
        log("")
        log(f"--- Fixing: {patch_name} ---")
        if args.dry_run:
            log("  (dry-run: would call DeepSeek API)")
            success_count += 1
            continue

        ok = fix_patch(
            patch_name=patch_name,
            patches_dir=patches_dir,
            diagnostics_dir=diagnostics_dir,
            api_key=api_key,
            max_retries=args.max_retries,
        )
        if ok:
            success_count += 1
        else:
            fail_count += 1

    log("")
    log(f"=== Fix Summary ===")
    log(f"  Fixed: {success_count}  Failed: {fail_count}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
