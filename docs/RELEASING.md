# Releasing Forma v0.1.0-beta

The `v0.1.0-beta` tag is the only tag that can publish the signed beta. The workflow refuses to package a release if a required signing or notarization secret is missing. Do not create the tag until every item in this guide has been completed.

## Required GitHub Actions secrets

Configure these repository secrets before the tag is pushed. Never commit a certificate, key, password, Apple credential, or decoded certificate file.

| Secret | Platform | Value |
| --- | --- | --- |
| `WINDOWS_CERTIFICATE_PFX_BASE64` | Windows | Base64-encoded Authenticode `.pfx` certificate. |
| `WINDOWS_CERTIFICATE_PASSWORD` | Windows | Password that unlocks that certificate. |
| `MACOS_CERTIFICATE_P12_BASE64` | macOS | Base64-encoded Developer ID Application `.p12` certificate. |
| `MACOS_CERTIFICATE_PASSWORD` | macOS | Password that unlocks that certificate. |
| `APPLE_ID` | macOS | Apple ID authorized for notarization. |
| `APPLE_APP_SPECIFIC_PASSWORD` | macOS | Apple app-specific password, not the Apple ID password. |
| `APPLE_TEAM_ID` | macOS | Apple Developer team identifier. |

The workflow decodes certificates only into the ephemeral GitHub Actions runner. It imports the macOS certificate into a temporary keychain, uses it during packaging, and does not upload either certificate as a release artifact.

## Release procedure

1. Complete the upgrade checks below on copies of two supported prior versions before changing the tag.
2. Verify the checkout is clean and `desktop/package.json` has version `0.1.0-beta`.
3. Confirm every repository secret above is present and current. Test signing in a private release candidate repository if the certificate has changed.
4. Push the exact annotated tag `v0.1.0-beta`. The release workflow validates that the tag and package version match.
5. Review all three package jobs: Windows x64, macOS Intel, and macOS Apple Silicon. Windows validates the installer Authenticode signature; macOS validates the application signature and stapled notarization ticket.
6. Review the generated `SHA256SUMS` file and the release assets. Only then make the GitHub prerelease visible to testers.
7. Install from the published asset on clean Windows, Intel macOS, and Apple Silicon macOS devices. Confirm first-run provider setup, a Learn session, a Quiz, restart recovery, and local data persistence.

The release workflow creates a GitHub prerelease with the Windows installer, macOS DMG/ZIP assets, and `SHA256SUMS`. It does not create automatic-update metadata or publish a stable release channel.

## Upgrade validation plan

Use the two most recent supported builds. For this first beta, record the actual source commits/build artifacts in the release issue before testing.

For each source build:

1. Install the source build and create learner evidence, a review schedule, a paused Learn workflow, one Quiz attempt, and an imported material.
2. Close Forma completely. Make a copy of the platform's Forma application-data directory as a rollback backup.
3. Install `v0.1.0-beta` over the source build without deleting application data.
4. Open Forma and confirm migrations complete, the prior workflow can resume, learner evidence and review schedules remain present, imported material is available, and provider setup is unchanged.
5. Export local data, then compare the export with the pre-upgrade state. Keep the backup until beta validation is accepted.
6. Exercise the rollback procedure below on at least one test machine.

## Rollback

The beta has no automatic updater. Stop Forma, restore the copied application-data directory, then reinstall the previously tested installer. Do not delete learner data during an uninstall: local data is intentionally preserved. If a migration cannot be reversed safely, restore the backup instead of opening the older build against the newer database.
