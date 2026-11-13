# Offline Book Converter

Offline Book Converter is a Windows app for converting ebooks and repairing their tables of contents. It can export MOBI 6 for the Kindle 4, as well as EPUB and AZW3.

## Features

- Opens MOBI, EPUB, FB2, AZW3, DOCX, HTML, TXT, RTF, LIT, and PDB files.
- Removes cascading indentation from the table of contents, highlights group headings, and checks navigation links.
- Supports drag and drop, batch conversion, a progress bar, and an elapsed-time display.
- Saves each converted book in its own folder, with a report and log in the Diagnostics subfolder.

Books without chapters are converted as continuous books. The app verifies that the output can be reopened and contains readable content. For books with a table of contents, it also verifies the navigation links.

## Table of contents before and after

| Before repair | After repair |
| --- | --- |
| ![Original table of contents with cascading indentation](docs/images/toc-before.png) | ![Repaired table of contents with readable entries and distinct group headings](docs/images/toc-after.png) |

## Installation

Install **Python 3.10 or later with Tkinter** and **Calibre for Windows**, then download and run the setup EXE from [Releases](https://github.com/TommiLin/Offline-Book-Converter/releases).

If setup asks you to close the converter, let any active conversion finish, close the app, and click **Retry**. After installation, you can open the app or view the quick guide from the setup window.

## Updates

Conversion works offline. Click **Check for updates** to look for a newer stable release in the official TommiLin/Offline-Book-Converter repository. The app asks before downloading the installer, verifies its SHA-256 checksum, and asks before opening setup.

## Build from source

Run these commands on Windows with Python and the .NET Framework 4.x compiler installed.

    python app/app.pyw
    python -m unittest discover -s tests -v
    python scripts/build.py

The build writes the setup EXE, portable ZIP, source ZIP, and SHA256SUMS.txt to dist. See [BUILD.md](BUILD.md) for build and release details.

## Publish a release

1. Extract the source ZIP and upload its contents to the root of the official repository, including .github/workflows/release.yml.
2. To build from the browser, open **Actions**, select **Build and release Windows app**, and click **Run workflow**. Download and extract the **Windows-build** artifact after the run succeeds.
3. In **Releases**, create a stable release and attach the four build files. For version 1.3.6, use the tag v1.3.6. If the workflow is enabled, temporarily disable it during manual publication to avoid a second attempt to publish the same tag, then re-enable it.
4. For later releases, update the version in app/update_config.json and record the changes in CHANGELOG.md. Keep the release tag and the app version in sync. Pushing a matching tag with Git triggers the automatic build and release workflow.

The updater needs the versioned setup EXE and its matching SHA256SUMS.txt from the same build.

## License

The source code is available under the [MIT License](LICENSE).
