# MacroPad Remote v0.5.0 RC2

Windows editor/controller + Android companion for a phone-based macro pad and PC remote.

This repository currently uses a bootstrap source bundle for CI. GitHub Actions expands `source-bundle.zip`, builds the Windows x64 self-contained app and Android release APK, and publishes rolling preview artifacts.

## Included

- three-column Windows editor UI with profiles, macro deck, action catalog, devices and profile properties;
- manual rows/columns and per-tile spans;
- profiles, pages/folders, macros, hotkeys, text, app/file/URL launch, media actions;
- trusted-device pairing and reconnect;
- LAN discovery;
- preset synchronization and phone proxy migration;
- managed `%APPDATA%\MacroPadRemote` storage so presets survive updates;
- in-place updater with SHA-256 package verification;
- GitHub Actions build for Windows x64 + Android APK.

## Preview build

Every push to `main` triggers `.github/workflows/release.yml`. When both platform builds succeed, the workflow updates a rolling prerelease named `preview` containing:

- `MacroPadRemote-win-x64.zip`
- `app-release.apk`
- `preview.json`

The preview channel is intended for device testing before the first stable release.
