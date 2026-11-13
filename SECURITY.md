# Update trust and reporting

Updates are opt-in and use the fixed public repository TommiLin/Offline-Book-Converter.
embedded by the build. Only stable, newer MAJOR.MINOR.PATCH releases are used.
The installer and checksum file must use HTTPS GitHub release URLs for that
repository. The downloaded installer must match SHA256SUMS.txt before launch.
Partial and mismatched downloads are discarded. No installer executes without
the user's explicit confirmation in the application.

SHA-256 detects a download differing from the release checksum; it does not
replace publisher code signing. Only official repository release assets are accepted.
Do not store access tokens in this source tree. Private releases are unsupported.

Report bugs through the repository's Issues without attaching copyrighted books,
personal paths, or full logs unless necessary and reviewed first.
