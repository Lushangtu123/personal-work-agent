# Label helper

This project uses Python's standard library unittest, with no third-party dependencies.
Run `python3 -B -m unittest discover -s . -p 'test_*.py'` from this directory.
`label(name)` strips outer whitespace, preserves internal whitespace, and rejects empty names with ValueError.
