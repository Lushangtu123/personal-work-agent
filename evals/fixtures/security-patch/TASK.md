Validate and, if needed, correct the containment repair in this local path-resolution helper. The earlier report was that a root named `downloads` accepted the requested location `../private/report.txt`. `download_path_before.py` is the original source snapshot; preserve it unchanged. `download_path.py` contains the attempted repair used by the application now.

The public contract is:

- `resolve_download(root, requested)` resolves both the root and the resulting target using the local filesystem's current state.
- Return the canonical `Path` only when the target is the root itself or a descendant of it; otherwise raise `ValueError`.
- Both relative and absolute requested strings are supported. Benign normalization and existing symlinks resolving within the root must continue to work. Existing symlinks resolving outside the root must not be accepted.
- This is a path-resolution helper, not a file-opening operation: targets need not exist. Concurrent filesystem changes and the security of subsequent file opening are outside this task's implementation scope and must not be claimed solved.

Use only synthetic directories created inside temporary storage; do not probe real user files or any network resource. Use the standard library and repository-native tests. Keep the existing tests intact and add regression coverage in a new `test_*.py` file. Do not add dependencies, commit, or change this task description. Only modify this workspace. Report what was demonstrated against the original source and final code, the checks actually run, and any remaining limits of the evidence.
