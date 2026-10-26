# Contributing

Contributions are welcome, especially small reproducible cases from real
Roblox projects. Please avoid opening issues with unpublished game assets.

1. Open an issue describing an unsupported Roblox reference format or a
   false positive, and provide a minimal sample.
2. Make a branch for the change.
3. Add a test that fails before the fix and passes after it.
4. Run `python -m unittest discover -s tests -v` before opening a pull request.
5. Keep scanning read-only and offline. New dependencies should come with a
   clear maintenance and security rationale.

We prefer narrow features with predictable JSON output over heuristics that
silently invent or guess asset IDs.
