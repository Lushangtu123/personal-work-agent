Fix the settings import/export bug and add regression coverage in this small existing Python project. Users report that some valid settings do not survive an export/import cycle.

The public contract is:

- `encode_options(options)` accepts a dictionary with 0–8 unique ASCII keys matching `[a-z]{1,8}` and string values of 0–32 Unicode characters. Values are ordinary text, including punctuation, whitespace, and empty text; exclude surrogate code points.
- Encoding produces a URL query string with keys in ascending order. Preserve the existing standard form-encoding format so existing exports remain readable.
- `decode_options(encode_options(options))` must recover the original dictionary exactly. Dictionary insertion order is not meaningful.
- Re-encoding a decoded export must produce that same canonical export. This contract covers exports produced by this module, not arbitrary malformed external queries.

Use the standard library and repository-native tests. Keep the existing tests intact and add coverage in a new `test_*.py` file. Do not add dependencies, contact services, commit, or change this task description. Only modify this workspace. Report the actual checks you ran, what the new tests establish, and any limitations.
