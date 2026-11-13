## 1.3.6

- Fixed updates to TommiLin/Offline-Book-Converter; removed repository settings and build overrides.
- Included official GitHub release workflow and publication instructions.
- No published release is shown as information.

# Changelog

## 1.3.5 (simple branch)

- Dedicated successful-installation page with optional application launch.
- Launch is selected by default; the button reads Open app or Close setup.
- Optional View quick guide checkbox, off by default.
- Disable application launch if Python is unavailable.
- Conversion behavior is unchanged.

## 1.3.4 (simple branch)

- Replace Finish with Close setup after successful installation.
- Show a green Installation completed successfully message and full progress.
- Disable completed installation options to clarify that setup is finished.
- Application and conversion behavior are unchanged.

## 1.3.3 (simple branch)

- Check for locked application files before installation starts copying.
- Show a friendly close-and-Retry message for loaded DLLs.
- Reset progress to zero when installation is blocked before copying.
- Enlarge the installer status area so instructions remain readable.
- Conversion behavior is unchanged from 1.3.2.

## 1.3.2 (simple branch)

- Show chapterless conversion as an ordinary green success message.
- Keep technical navigation details in the diagnostic report, without a UI note.
- Shorten success messages to one filename instead of repeated folder paths.
- Conversion logic remains the same as 1.3.1.

## 1.3.1 (simple branch)

- Restore the 1.3.0 feature set; no library search, online covers or sending.
- Treat missing/empty chapter navigation as an ordinary continuous book.
- Verify readable content instead of requiring a Contents destination in that case.
- Preserve errors for malformed navigation and missing chapter destinations.
- Retain safe TkDND and main-thread GUI cleanup without changing the simple UI.

## 1.3.0

- Manual update checks using GitHub Releases.
- Repository settings, verified installer download and update-folder handoff.
- Complete source package, Windows build script and GitHub release workflow.

## 1.2.0

- Application icon and native Windows drag-and-drop.
- Separate folder for each output and a Diagnostics subfolder.

## 1.1.0

- Current-book and batch progress, elapsed time and activity indicator.

## 1.0.0

- Offline conversion and flattened, readable contents for Kindle 4.
