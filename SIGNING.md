# Code signing (Windows, via SignPath)

The release workflow signs the Windows `.exe` automatically **once these are set
up**. Until then it still builds and releases, just unsigned (SmartScreen shows
"unknown publisher" -> More info -> Run anyway).

SignPath signs **Windows** binaries only. The macOS Gatekeeper warning is a
separate Apple notarization process and is not covered here.

## One-time setup

1. **Get the project approved** under the free SignPath Foundation OSS program
   (https://signpath.org) — this is a manual review, not instant.
2. In your SignPath dashboard, create/note:
   - the **Organization ID**
   - a **Project** (note its slug)
   - a **Signing Policy** for the project (note its slug, e.g. `release-signing`)
   - an **API token** (user or CI token)
3. In this GitHub repo -> **Settings -> Secrets and variables -> Actions**:
   - **Secret:** `SIGNPATH_API_TOKEN` = your API token
   - **Variables:**
     - `SIGNPATH_ORGANIZATION_ID`
     - `SIGNPATH_PROJECT_SLUG`
     - `SIGNPATH_POLICY_SLUG`
4. Push a new tag (e.g. `v0.1.2`). The Windows job uploads the unsigned exe,
   submits it to SignPath, waits for the signed result, and attaches the signed
   build to the release.

## Verify a signed download

Right-click `PlotterStudio.exe` -> **Properties -> Digital Signatures** should
list your publisher. Or compare the SHA-256 against the `.sha256` on the release.
