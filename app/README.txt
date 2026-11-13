OFFLINE BOOK CONVERTER — Windows

Version 1.3.6
Setup completion: Launch Offline Book Converter is selected by default.
Open app launches it and closes setup. Uncheck launch to use Close setup.
View quick guide is optional and off by default. If Python is not installed,
launch is disabled until the prerequisite is installed separately.
Installer fix: close the converter before installation. Setup now checks all
existing package files before replacing any of them. If a DLL is still in use,
it asks you to close the app and click Retry without changing application files.
Simple branch based on 1.3.0. No search, online covers or email sending.
Books without chapter navigation are converted normally. Contents repair is
skipped, and the result is reopened and checked for readable content.
Chaptered books retain the original contents-repair and link checks.
Safe TkDND replaces the original ctypes window hooks without adding UI features.
Install: run OfflineBookConverter-Setup.exe. No administrator access needed.
Then use the desktop or Start menu shortcut. Uninstall from Windows Apps.
Portable start: double-click OfflineBookConverter.exe (or Start.cmd).
The entire interface is in English.
On this computer Python and Calibre are already installed.
On another computer install Python 3 with Tkinter and Calibre for Windows first.
The included EXE is a launcher; Python and Calibre are not bundled. No pip packages,
account, API key, internet connection or cloud service are needed to run it.

Updates (optional; require internet):
- Click Check for updates to query the latest public stable GitHub Release.
- Updates use only TommiLin/Offline-Book-Converter on GitHub.
- The repository address is fixed. Old repository settings are ignored.
- A newer installer is downloaded and checked against SHA256SUMS.txt.
- You choose whether to close the app and open the installer; click Install
  in that installer to update the current installation folder.
- Personal settings and books are preserved. No background update check runs.
- GitHub repository setup and release instructions are in the source README.md.

1. Drag books from File Explorer into the window, or use Add books.
2. Choose Kindle 4 / MOBI, EPUB or AZW3.
3. Choose an output folder.
4. Click Convert & repair.

Each book gets its own result folder:
  Selected output folder/
    Book title_clean/
      Book title_clean.mobi
      Diagnostics/
        report.json
        conversion.log.txt

Only the ebook is needed for reading. report.json contains navigation checks,
warnings and the output checksum. conversion.log.txt helps diagnose failures.
Repeated conversions and books sharing a title receive unique numbered folders.
Failed conversions keep their error log in Diagnostics without a broken ebook.
Old results created by earlier versions are not moved automatically.

Drag and drop accepts multiple supported ebook files, including Unicode names
and spaces. Duplicates, unsupported files and directories are skipped. While
a batch is running, new drops are ignored until the batch has finished.

Progress:
- Current-book progress shows reading, repair, building and verification.
- Batch progress includes all processed books, including failed jobs.
- A moving activity indicator and elapsed timer remain visible during work.
- Last activity shows seconds since the conversion process last produced output.
- Percentages are based on processing stages, not an estimate of time remaining.

Inputs: MOBI, EPUB, FB2, AZW3, DOCX, HTML, HTM, TXT, RTF, LIT, PDB.
DRM-protected books are not supported.
PDF is intentionally omitted: reliable chapter structure cannot be recovered
from arbitrary page layouts. FB2 is supported as input, not as output.

Contents repair:
- Uses source chapter navigation, retaining order and destinations.
- Group headings (entries with children) are bold, separated vertically.
- Chapter entries can be marked with a dash.
- New HTML contents uses flat paragraphs, never nested blockquotes.
- Go To / Contents points to the new readable contents.
- Old inline contents is replaced when it contains only navigation. Its
  anchors are preserved for backlinks. If mixed with prose, the old contents
  is retained and its cascading blockquote wrappers are neutralized.
- Original books are never overwritten. Existing outputs receive new names.

Validation:
The resulting book is reopened and all new contents links and anchors are
checked. A JSON report and conversion log are saved in its Diagnostics folder.
An output is published only after validation succeeds.
MOBI output uses the old MOBI 6 format and the Kindle profile.
Actual Kindle hardware appearance is not tested automatically.

Limitations:
Source navigation may be absent; such books use normal conversion with content
verification. A flat source
navigation cannot reliably distinguish collections from stories; a warning
is included in the report. This version has no manual hierarchy editor.
Calibre conversion may normalize typography, images and metadata. This is
not a byte-preserving editor. Keep original books and inspect important files.
Books containing malformed navigation may be rejected instead of being saved.

Source files: app.pyw (English interface), engine.py (Calibre worker),
file_drop.py (native Windows drag-and-drop support).
License for these source files: MIT. Calibre and Python retain their own
licenses and are installed separately; they are not bundled here.
