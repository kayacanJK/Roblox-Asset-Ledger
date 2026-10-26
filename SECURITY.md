# Security

This tool works offline and does not upload scanned code or asset IDs.

**An approved ID is not a security certification.** It only means that someone on
your team explicitly accepted the identifier in a local allowlist. An asset may
still be private, revoked, malicious, infringing, or inaccessible.

Scanned files are treated as text. No content is executed. Paths that are
symbolic links are skipped, and only an explicit set of file extensions is read.
Reports contain relative source paths and asset identifiers; review them before
publishing to public CI logs.

If you discover a security issue, do not post exploit details in a public
issue. Contact the maintainers privately through the GitHub repository owner.
