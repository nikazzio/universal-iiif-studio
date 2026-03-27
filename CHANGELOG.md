# Changelog

All notable changes to this project are documented in this file.

## Changelog Format Policy

- Release sections may use either the historical heading format `## [vX.Y.Z] - YYYY-MM-DD`
  or the `python-semantic-release` heading format `## vX.Y.Z (YYYY-MM-DD)`.
- Historical/manual entries may keep the `### Added` / `### Changed` / `### Fixed` layout.
- Auto-generated entries may use `python-semantic-release` categories such as
  `### Features`, `### Bug Fixes`, `### Documentation`, `### Chores`, and similar.
- Every non-empty bullet should reference an issue/PR identifier or a generated commit link.
- Sparse historical auto-generated releases with only `Detailed Changes` are also accepted.
- The file must include the semantic-release insertion marker line used by the release workflow.
- If a section has no items, use `- None.`

## [Unreleased]

### Added

- None.

### Changed

- None.

### Fixed

- None.

<!-- version list -->

## v0.23.0 (2026-03-27)

### Bug Fixes

- Add official vatican text search fallback
  ([`478cd04`](https://github.com/nikazzio/universal-iiif-studio/commit/478cd04f4a5a333e939917440211200acb0ab8b1))

- Avoid bogus archive.org direct manifests
  ([`b659b77`](https://github.com/nikazzio/universal-iiif-studio/commit/b659b77c9dcc718afd4f4aff08f5d0f496e3d3fa))

- Correct e-codices URL parsing and Harvard canonical ID handling
  ([`83b2d9e`](https://github.com/nikazzio/universal-iiif-studio/commit/83b2d9ec1d49a3066e481348e4a7750d56c3aaeb))

- Filter broken archive.org manifests
  ([`d0de3af`](https://github.com/nikazzio/universal-iiif-studio/commit/d0de3af6b3803ca5eba76ac446f5a6bb71b07d06))

- Harden provider resolver matching and archive search probing
  ([`2e802ef`](https://github.com/nikazzio/universal-iiif-studio/commit/2e802efe629a79b6666616f88764e821fa9c2235))

- Harden resolver correctness and archive.org probe performance
  ([`8f24032`](https://github.com/nikazzio/universal-iiif-studio/commit/8f240324d8e0f5fd61ac7903b98c64be34b88976))

- Preserve provider viewer links in discovery
  ([`27a29ba`](https://github.com/nikazzio/universal-iiif-studio/commit/27a29bac074bc067d702ae9ce5a8db25b7063a88))

### Documentation

- Normalize changelog policy references
  ([`c854a81`](https://github.com/nikazzio/universal-iiif-studio/commit/c854a81c2e18c47a61ddcf01e28348897cd0da6a))

### Features

- Add archive.org discovery search
  ([`f18c07a`](https://github.com/nikazzio/universal-iiif-studio/commit/f18c07a0d7a73654b75bdcf538be2b9d78357b9c))

- Add Bodleian and e-codices search adapters
  ([`693b14d`](https://github.com/nikazzio/universal-iiif-studio/commit/693b14d82cd51fce6e6e62b92958f83ddfda34e2))

- Enrich Archive.org search results and reduce probe latency
  ([`988dc24`](https://github.com/nikazzio/universal-iiif-studio/commit/988dc2439d4f21c33bc1dbd4bbb8a828d72882bb))

- Expand discovery search adapters and job-ready result UX
  ([`098c7d1`](https://github.com/nikazzio/universal-iiif-studio/commit/098c7d1c60e5ea56c38337cc724ecf014b6e0162))

### Refactoring

- Split discovery orchestration and UI modules
  ([`93ac20d`](https://github.com/nikazzio/universal-iiif-studio/commit/93ac20d854dde6c0cfcda58048d816a7dc4593ad))

- Tidy discovery provider flow
  ([`be818ba`](https://github.com/nikazzio/universal-iiif-studio/commit/be818ba19c7e65cdbc37d69591cd4370b554555b))


## v0.22.4 (2026-03-11)

### Bug Fixes

- Restore semantic release changelog sync ([`4d174d5`](https://github.com/nikazzio/universal-iiif-studio/commit/4d174d55fa3dd5945be0a052c61b1a0ba49fe566))

### Documentation

- Backfill historical changelog releases ([`b128ea9`](https://github.com/nikazzio/universal-iiif-studio/commit/b128ea9c70fd68064c57000d8885c078a8fda0c8))

- Fix changelog markdownlint regressions ([`0efb088`](https://github.com/nikazzio/universal-iiif-studio/commit/0efb088221b7f75744127afd0f1f4c63f2392dce))

## v0.22.3 (2026-03-11)

_This release is published under the MIT License._

### Bug Fixes

- Preserve gallica titles and add library delete modal ([`74b4875`](https://github.com/nikazzio/universal-iiif-studio/commit/74b487564b0ad24dd99d4e1fa71d45234de22324))

---
**Detailed Changes**: [v0.22.2...v0.22.3](https://github.com/nikazzio/universal-iiif-studio/compare/v0.22.2...v0.22.3)

## v0.22.2 (2026-03-11)

_This release is published under the MIT License._

### Bug Fixes

- Tighten studio image subtab action buttons ([`571855e`](https://github.com/nikazzio/universal-iiif-studio/commit/571855e6d3f5d215e913bb74a87b60a3160f2094))

---

**Detailed Changes**: [v0.22.1...v0.22.2](https://github.com/nikazzio/universal-iiif-studio/compare/v0.22.1...v0.22.2)

## v0.22.1 (2026-03-11)

_This release is published under the MIT License._

### Bug Fixes

- Address copilot studio review feedback ([`d126a41`](https://github.com/nikazzio/universal-iiif-studio/commit/d126a418c089965e158edc3d2d6d27ea903f00c4))

- Keep studio manifest fallback and page sync ([`26077ee`](https://github.com/nikazzio/universal-iiif-studio/commit/26077eee665e8337dcf5575ef381a96348bb5533))

- Preserve cli manifest resolution metadata ([`5456674`](https://github.com/nikazzio/universal-iiif-studio/commit/5456674a09e630f6340a57f9e80a82766be35e51))

- Resolve issue 68 UI and remote studio regressions ([`8284314`](https://github.com/nikazzio/universal-iiif-studio/commit/828431473193bfc2b64dcf92b9eb8df39f48fc02))

### Chores

- Refresh pr governance metadata ([`3398bae`](https://github.com/nikazzio/universal-iiif-studio/commit/3398bae880ae2360a8813c05b39b3fc2d08990af))

---

**Detailed Changes**: [v0.22.0...v0.22.1](https://github.com/nikazzio/universal-iiif-studio/compare/v0.22.0...v0.22.1)

## v0.22.0 (2026-03-11)

_This release is published under the MIT License._

### Bug Fixes

- Address latest copilot review feedback ([`9fbe7d2`](https://github.com/nikazzio/universal-iiif-studio/commit/9fbe7d246cfdfa5ba8cc82ab7b4efa3f7fac1c73))

- Address PR review feedback for centralized HTTP client ([`bfb11e9`](https://github.com/nikazzio/universal-iiif-studio/commit/bfb11e9657cb4ff7f1493b3a5d30edb6a0055346))

- Refine studio export page workflows ([`dc7f3b0`](https://github.com/nikazzio/universal-iiif-studio/commit/dc7f3b037d132606dcece39fc65b743dfe704ff7))

- Use get_config_manager() instead of cm singleton ([`5ec2ab4`](https://github.com/nikazzio/universal-iiif-studio/commit/5ec2ab49547e798054f02cfc6c357659fda6927b))

- **changelog**: Replace manual v0.7.0 with Unreleased section ([`68f3497`](https://github.com/nikazzio/universal-iiif-studio/commit/68f3497c76143ec3186961f3fbc67c2e68aea4ae))

- **ci**: Ignore C901 complexity warnings and fix doc link ([`aec81d1`](https://github.com/nikazzio/universal-iiif-studio/commit/aec81d11285c32479d02552d4bef952beffa1606))

- **ci**: Mark new HTTPClient tests as slow ([`afce917`](https://github.com/nikazzio/universal-iiif-studio/commit/afce917e78f66856fdd02b47e4bb9c834e5d985b))

- **ci**: Relax language check for technical docs ([`a41bfbc`](https://github.com/nikazzio/universal-iiif-studio/commit/a41bfbc85c273a0fb33d2b48ac8080293b0ee3de))

- **docs**: Fix markdown table formatting in HTTP_CLIENT.md ([`ecc764f`](https://github.com/nikazzio/universal-iiif-studio/commit/ecc764f308ea2efd80b209cb3181c443f8f30c05))

- **downloader**: Add missing method attachment for _count_all_downloaded_pages ([`479677d`](https://github.com/nikazzio/universal-iiif-studio/commit/479677dfde536fe42a4afb3e98f2f8836cedd8de))

- **downloader**: Fix resume progress showing wrong total (X/404 instead of X/425) ([`9ba7cc4`](https://github.com/nikazzio/universal-iiif-studio/commit/9ba7cc45b95da9fbe008caac341bc2c27b0e9bbd))

- **http-client**: Fix 3 critical bugs found in code review ([`8b03c31`](https://github.com/nikazzio/universal-iiif-studio/commit/8b03c31e7ff626f2676bd00ccdac331fa814ba3c))

- **http_client**: Fix 3 code review issues ([`dcdca1e`](https://github.com/nikazzio/universal-iiif-studio/commit/dcdca1e85373641e924e67f7d98ea3d17f118eb1))

- **http_client**: Fix 3 critical runtime regressions ([`bd7fe76`](https://github.com/nikazzio/universal-iiif-studio/commit/bd7fe7621d959edacdb95fb9eae19f2ce64f0f55))

- **http_client**: Fix critical method signature mismatch in _compute_backoff ([`1aa745c`](https://github.com/nikazzio/universal-iiif-studio/commit/1aa745c46878017c2cc5eecbfaa938dde2c2db35))

- **lint**: Complete docstrings and ignore D417 self param ([`4a0ffa4`](https://github.com/nikazzio/universal-iiif-studio/commit/4a0ffa4d22380e1fa927263acf1636d6a7987ccf))

- **lint**: Fix all linting errors for CI ([`e9671b0`](https://github.com/nikazzio/universal-iiif-studio/commit/e9671b0996bf99b405f0ce3eafee62e1385522d8))

- **lint**: Fix import order in test_rate_limiter ([`ec64464`](https://github.com/nikazzio/universal-iiif-studio/commit/ec6446406b9edcc02453dba510e9421b1e5208f9))

- **utils**: Restore get_request_session() for backward compatibility ([`86a040d`](https://github.com/nikazzio/universal-iiif-studio/commit/86a040dfd6921b1c8174d80137c504d4026e3df7))

### Chores

- **ci**: Mark more I/O-heavy tests as slow ([`9887777`](https://github.com/nikazzio/universal-iiif-studio/commit/988777772d88d19981c1821f66cbb21b5020ee5d))

- **ci**: Mark settings and security routing tests as slow ([`98ff449`](https://github.com/nikazzio/universal-iiif-studio/commit/98ff4492b7044f795fd0eeecdfe07ad7c6e8f10f))

- **ci**: Optimize test suite with slow markers ([`7876075`](https://github.com/nikazzio/universal-iiif-studio/commit/78760757b71fb81450d96172d999c33dd2cabc8d))

### Code Style

- Fix whitespace in test mock classes ([`6f70d9e`](https://github.com/nikazzio/universal-iiif-studio/commit/6f70d9ede4373f46e3b65ec73a05ae7bb71194be))

### Documentation

- Add HTTP_CLIENT.md comprehensive documentation ([`02014c4`](https://github.com/nikazzio/universal-iiif-studio/commit/02014c46ea4fa00d82ff0791628f926e7fd64592))

- Align documentation with studio export workflow ([`d22ffec`](https://github.com/nikazzio/universal-iiif-studio/commit/d22ffeca6dc0d4f97f2026630950bbe807582527))

- Complete documentation update for Issue #71 features ([`1bf82dd`](https://github.com/nikazzio/universal-iiif-studio/commit/1bf82ddc78cf34e4ba91af51aa54063476d12599))

### Features

- Add per_host_concurrency configuration ([`9376dd6`](https://github.com/nikazzio/universal-iiif-studio/commit/9376dd63700e2624e1b2f9e220e84be8aaedf236))

- Extract HostRateLimiter and create HTTPClient skeleton ([`e83756c`](https://github.com/nikazzio/universal-iiif-studio/commit/e83756c67fca9432e2ba33b5f8ebbd4008b36795))

- Implement get_json() with robust JSON parsing ([`c5263ea`](https://github.com/nikazzio/universal-iiif-studio/commit/c5263ea7419ae727966283f18a2769234db43ceb))

- Implement main get() method with full integration ([`19826cc`](https://github.com/nikazzio/universal-iiif-studio/commit/19826cc6fc3224578b830383bfe1c2eacc9cfaae))

- Implement retry logic with exponential backoff ([`09758fc`](https://github.com/nikazzio/universal-iiif-studio/commit/09758fc1850e249d9bee46c3d704bb933cce0ff1))

- **catalog**: Migrate library_catalog.py to HTTPClient ([`0b4b176`](https://github.com/nikazzio/universal-iiif-studio/commit/0b4b176d77e962ca4fdfb7e0bbb88386df7c6611))

- **downloader**: Add HTTPClient instance to IIIFDownloader ([`7923582`](https://github.com/nikazzio/universal-iiif-studio/commit/79235828abefda641179f2c72345313aa309c6d9))

- **downloader**: Use HTTPClient for canvas downloads ([`85564f4`](https://github.com/nikazzio/universal-iiif-studio/commit/85564f4776d37908d33bda65e5bf10bebf314a95))

- **http_client**: Add POST method and migrate OCR model_manager ([`c43064d`](https://github.com/nikazzio/universal-iiif-studio/commit/c43064d319eaae18ad20a1933ab95d0a14184df6))

- **ocr**: Migrate processor.py to HTTPClient for API calls ([`0f7b851`](https://github.com/nikazzio/universal-iiif-studio/commit/0f7b8518d3f35d7326fc33c744f5b7877ffc4f0f))

- **resolution**: Migrate iiif_resolution.py to HTTPClient ([`f94802d`](https://github.com/nikazzio/universal-iiif-studio/commit/f94802d90117c0b5654e439a65a7fbf963865e48))

- **resolvers**: Migrate discovery.py JSON calls to get_json() ([`10e7b33`](https://github.com/nikazzio/universal-iiif-studio/commit/10e7b3352bcfe1cf366db516dad1df57238ceaf3))

- **tiles**: Migrate iiif_tiles.py to HTTPClient ([`6105563`](https://github.com/nikazzio/universal-iiif-studio/commit/6105563b366d3de7042a86b26ad508ac87f73442))

- **ui**: Add professional status panel with color-coded badges ([`7546741`](https://github.com/nikazzio/universal-iiif-studio/commit/75467410a2c664d35d4faeabbe57d3860e1a5420))

- **utils**: Migrate utils.py get_json() to HTTPClient ([`b70d82c`](https://github.com/nikazzio/universal-iiif-studio/commit/b70d82cc057317a94921f0949ab8d1f928e52280))

### Refactoring

- **downloader**: Remove duplicate retry/backoff logic ([`adeb80a`](https://github.com/nikazzio/universal-iiif-studio/commit/adeb80ab6ca09c6c4326b34fad99aefb6f337263))

### Testing

- Update test mocks for HTTPClient migration ([`7e9f316`](https://github.com/nikazzio/universal-iiif-studio/commit/7e9f3166609406c4c4ea71988f06f8db049f4190))

---

**Detailed Changes**: [v0.21.0...v0.22.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.21.0...v0.22.0)

## v0.21.0 (2026-03-08)

_This release is published under the MIT License._

### Bug Fixes

- Add immediate inline loading feedback for thumbnail actions ([`693b6ea`](https://github.com/nikazzio/universal-iiif-studio/commit/693b6eab057eeb19eab4f578aea0b2af2e45e696))

- Preserve active highres state and sync profile booleans ([`24a326e`](https://github.com/nikazzio/universal-iiif-studio/commit/24a326ef907d26ca5cdc3dbd98977b507c0c38d0))

- Prevent export live polling from resetting form edits ([`1094473`](https://github.com/nikazzio/universal-iiif-studio/commit/1094473b1186248b4fcad889717394de26837f46))

- Prevent symlink-based path traversal in scan optimization ([`a27c567`](https://github.com/nikazzio/universal-iiif-studio/commit/a27c5670689644fef8aed00f433476e8ed2623e9))

- Refactor studio thumbnail cards with compact dual actions ([`1a09621`](https://github.com/nikazzio/universal-iiif-studio/commit/1a09621ea9bcdbe60083d721cf73e80b4d62f4c6))

- Replace studio tab scrollbar with arrow-based scroller ([`3926892`](https://github.com/nikazzio/universal-iiif-studio/commit/3926892e1cb67738af2933e82a7102ba9827199c))

- Simplify studio thumbnails layout and remove noisy chips ([`0a11855`](https://github.com/nikazzio/universal-iiif-studio/commit/0a11855601a2a816401419d7155d270e1616aa89))

- Stabilize studio export UX, polling, and output sub-tabs ([`d24633f`](https://github.com/nikazzio/universal-iiif-studio/commit/d24633f8fcac22faabdff297e027c29835c43df5))

- Stabilize studio thumb progress and image source state ([`fe8f737`](https://github.com/nikazzio/universal-iiif-studio/commit/fe8f73702438fd56f2ff3556c68d0a7ffbc931a0))

### Documentation

- Update wiki and user docs for Studio Output tab and scan optimization ([`4e91f5e`](https://github.com/nikazzio/universal-iiif-studio/commit/4e91f5e8aeca0790ee293e31b4613d6e0d9df1f9))

### Features

- Move scans optimization to Studio Export pages ([`da54991`](https://github.com/nikazzio/universal-iiif-studio/commit/da5499193d26ac292a10243fdfd7c206e14cb085))

- Redesign studio export as images-first workspace with stable action states ([`840bc4b`](https://github.com/nikazzio/universal-iiif-studio/commit/840bc4b5e1cd1267a44f68c11667a8d728e61fd2))

---

**Detailed Changes**: [v0.20.0...v0.21.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.20.0...v0.21.0)

## v0.20.0 (2026-03-07)

_This release is published under the MIT License._

### Bug Fixes

- Handle malformed app prefs and preserve tab on transcription refresh ([`5f01664`](https://github.com/nikazzio/universal-iiif-studio/commit/5f01664c0ca14352ecf9e03df49f99c17f0f0642))

### Features

- Add studio recent hub and server-side resume context ([`83f14a7`](https://github.com/nikazzio/universal-iiif-studio/commit/83f14a7f6f2d61702eff2ffcc270becb0ba6f0ac))

---

**Detailed Changes**: [v0.19.1...v0.20.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.19.1...v0.20.0)

## v0.19.1 (2026-03-06)

_This release is published under the MIT License._

### Bug Fixes

- Allow full download action only for remote/saved manuscripts ([`5495c0a`](https://github.com/nikazzio/universal-iiif-studio/commit/5495c0ab9a9e30d69d3aa48e1aa2bdc0d3d9338a))

---

**Detailed Changes**: [v0.19.0...v0.19.1](https://github.com/nikazzio/universal-iiif-studio/compare/v0.19.0...v0.19.1)

## v0.19.0 (2026-03-06)

_This release is published under the MIT License._

### Bug Fixes

- Address review findings on path safety and source consistency ([`c6d3818`](https://github.com/nikazzio/universal-iiif-studio/commit/c6d3818cab4e3bca53cdc8d2a351ff91c92dfbc5))

### Documentation

- Record studio PR3 route-scope decision ([`fd2c362`](https://github.com/nikazzio/universal-iiif-studio/commit/fd2c3622e0ef4505e62119d28691e7a85cd15396))

### Features

- Complete PR2 staging availability UX and safety hardening ([`7cc8d0c`](https://github.com/nikazzio/universal-iiif-studio/commit/7cc8d0c293f57f5d97197f6fbd5354cdc196ef51))

---

**Detailed Changes**: [v0.18.0...v0.19.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.18.0...v0.19.0)

## v0.18.0 (2026-03-05)

_This release is published under the MIT License._

### Features

- Unify discovery download polling with configurable intervals ([`a30abef`](https://github.com/nikazzio/universal-iiif-studio/commit/a30abefeb4f69b5a91e3039b6d78d6625fc359b6))

---

**Detailed Changes**: [v0.17.0...v0.18.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.17.0...v0.18.0)

## v0.17.0 (2026-03-04)

_This release is published under the MIT License._

### Bug Fixes

- Finalize only validated staged pages and keep late-stop finalize ([`7b9cde6`](https://github.com/nikazzio/universal-iiif-studio/commit/7b9cde65b63462af3a4c1cfa274bfb0bf6ae384c))

- Finalize staged pages across segmented download runs ([`f42f333`](https://github.com/nikazzio/universal-iiif-studio/commit/f42f333cd22dc946203ead2954ef2243b84f0147))

- Keep overwrite semantics on pause promotion ([`8369d92`](https://github.com/nikazzio/universal-iiif-studio/commit/8369d92b265ccc049df77a2895e2532f8573316e))

- Keep partial downloads staged in temp and preserve progress counters ([`ea0fef3`](https://github.com/nikazzio/universal-iiif-studio/commit/ea0fef3dc4dae337a58cb02c500435f734bae4b0))

- Scope finalized files to manifest pages ([`9100e7f`](https://github.com/nikazzio/universal-iiif-studio/commit/9100e7f01f94e98d94c0bc6e162c6f9ada06c999))

### Chores

- **main**: Add reload option for development mode ([`f3f9036`](https://github.com/nikazzio/universal-iiif-studio/commit/f3f9036a08dc8a499e7b0ec2c2b1aba88a20b385))

### Documentation

- Align staging, pause promotion and viewer gating documentation ([`32031ed`](https://github.com/nikazzio/universal-iiif-studio/commit/32031edcee3ef0a9ca3a74cc1a01966bc8986d7f))

### Features

- Add configurable partial promotion of staged pages on pause ([`23fd8c3`](https://github.com/nikazzio/universal-iiif-studio/commit/23fd8c30de71ae303e2ced8d6decaaa12eca9599))

- Gate mirador on local readiness and expose temp pages ([`5003a75`](https://github.com/nikazzio/universal-iiif-studio/commit/5003a75ab56f653c067d8666894dc6ed9280abed))

---

**Detailed Changes**: [v0.16.2...v0.17.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.16.2...v0.17.0)

## v0.16.2 (2026-03-03)

_This release is published under the MIT License._

### Bug Fixes

- Reset stale pausing/cancelling downloads on startup ([`ef82218`](https://github.com/nikazzio/universal-iiif-studio/commit/ef822184cecc7fbf6275adfd11f54d38f373c271))

- **download**: Address pause/cancel review regressions ([`e324257`](https://github.com/nikazzio/universal-iiif-studio/commit/e324257fd25f655d0e43cd44d78f24ebaf2d6a67))

- **download**: Avoid pause->cancelled race in runtime status updates ([`bf1270b`](https://github.com/nikazzio/universal-iiif-studio/commit/bf1270bfafbb5723e3d70641f8a9e06de93471f3))

- **download**: Complete pause/cancel with orphan fallback ([`42be062`](https://github.com/nikazzio/universal-iiif-studio/commit/42be062f021ddc12efc2b9608b634a674720c45f))

- **download**: Keep manager resume/retry on same job id ([`02572e6`](https://github.com/nikazzio/universal-iiif-studio/commit/02572e64d870e8ca96590bb12f0c392efdd3f8cd))

- **download**: Separate pause/cancel semantics and clear non-error states ([`cf262f6`](https://github.com/nikazzio/universal-iiif-studio/commit/cf262f666dc92609c0d41d32600e63a65d585fdf))

- **download**: Simplify pause/cancel state machine and add pausing state ([`2c40d91`](https://github.com/nikazzio/universal-iiif-studio/commit/2c40d913832513debb6abecdeb6a8f69afcc4779))

- **ui**: Stop polling for paused/cancelled legacy status card ([`fe8d74e`](https://github.com/nikazzio/universal-iiif-studio/commit/fe8d74e0e25742fb1897490ef4bc9de05c9ad88f))

---

**Detailed Changes**: [v0.16.1...v0.16.2](https://github.com/nikazzio/universal-iiif-studio/compare/v0.16.1...v0.16.2)

## v0.16.1 (2026-03-03)

_This release is published under the MIT License._

### Bug Fixes

- **settings**: Align network global defaults and library overrides ([`a47c534`](https://github.com/nikazzio/universal-iiif-studio/commit/a47c534e5c96ce76ef430e035f542c66d9b9660f))

### Documentation

- Fix config reference language consistency ([`c728007`](https://github.com/nikazzio/universal-iiif-studio/commit/c72800742cb68c2805975aced035455abc39ab10))

---

**Detailed Changes**: [v0.16.0...v0.16.1](https://github.com/nikazzio/universal-iiif-studio/compare/v0.16.0...v0.16.1)

## v0.16.0 (2026-03-02)

_This release is published under the MIT License._

### Chores

- Re-trigger CI ([`7b8a465`](https://github.com/nikazzio/universal-iiif-studio/commit/7b8a46547373250ffcc1d52354ddbf57085e812d))

- Split oversized modules for issue #61 without API regressions ([`98cee19`](https://github.com/nikazzio/universal-iiif-studio/commit/98cee198ab992301cd2075c3063a3cd1b98fdb20))

### Features

- Enhance library metadata schema, pipeline, and UI ([`dc82a10`](https://github.com/nikazzio/universal-iiif-studio/commit/dc82a1053a3cb0a1488be8479133ff68dbe00acf))

---

**Detailed Changes**: [v0.15.0...v0.16.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.15.0...v0.16.0)

## v0.15.0 (2026-03-02)

_This release is published under the MIT License._

### Bug Fixes

- **exceptions**: Rename TimeoutError to RequestTimeoutError ([`1d6fc5b`](https://github.com/nikazzio/universal-iiif-studio/commit/1d6fc5b1eb3a18aa21fd385caf23e09c331b4b03))

- **refactor**: Add exception binding in handlers ([`fb85e7b`](https://github.com/nikazzio/universal-iiif-studio/commit/fb85e7b60766c789242b8e1c50f5536a60142a31))

- **refactor**: Add exception binding in OCR processor ([`82b1b79`](https://github.com/nikazzio/universal-iiif-studio/commit/82b1b795980da3c3995b39f6e4bea25652bd5258))

- **refactor**: Add missing imports and exception bindings ([`c62c329`](https://github.com/nikazzio/universal-iiif-studio/commit/c62c3299bf6be509000f2325dff9343d31ce327a))

- **test**: Use requests.HTTPError in mock ([`c3e0a57`](https://github.com/nikazzio/universal-iiif-studio/commit/c3e0a572c365be16349878e04813d6d58e1c5ed0))

### Chores

- Add global config validation diagnostics ([`b7129bd`](https://github.com/nikazzio/universal-iiif-studio/commit/b7129bd42a2c5743b07ef81ef4a3925a5c8005a2))

### Documentation

- Complete CONFIG_REFERENCE with detailed descriptions for 4 keys ([`acf4420`](https://github.com/nikazzio/universal-iiif-studio/commit/acf442054b3e27fab9459082e95106c77a9ae1d4))

### Features

- **exceptions**: Create comprehensive exception hierarchy ([`318f544`](https://github.com/nikazzio/universal-iiif-studio/commit/318f544451aaabc59d3cc3cecc422125ca487391))

### Refactoring

- **core**: Narrow exceptions in utils and core files ([`5a965be`](https://github.com/nikazzio/universal-iiif-studio/commit/5a965be8a36144647b03c79b88b6272018862b8d))

- **downloader**: Narrow safe exception handlers ([`c72a28b`](https://github.com/nikazzio/universal-iiif-studio/commit/c72a28bc09e8e91678d8c67c2017b2e6aa96e77b))

- **jobs**: Replace generic exceptions with DatabaseError ([`7ba5c1a`](https://github.com/nikazzio/universal-iiif-studio/commit/7ba5c1ad04fa214fe2e9e3b3b8b8d5de536d3f7c))

- **ocr**: Narrow exceptions in OCR services ([`6d1e023`](https://github.com/nikazzio/universal-iiif-studio/commit/6d1e023a0e2f752fef4af8f7f9bbcc7a20a61453))

- **resolvers**: Narrow exceptions with proper ResolverError handling ([`8504f4f`](https://github.com/nikazzio/universal-iiif-studio/commit/8504f4f9aae12b238dff7d69643fa9ad98c2aa7e))

- **vault**: Narrow exceptions to DatabaseError and OSError ([`35e8166`](https://github.com/nikazzio/universal-iiif-studio/commit/35e8166be33bc566d34038abe928897a076ac2de))

---

**Detailed Changes**: [v0.14.2...v0.15.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.14.2...v0.15.0)

## v0.14.2 (2026-03-02)

_This release is published under the MIT License._

### Bug Fixes

- **core**: Eliminate PIL Image memory leaks for long-running desktop sessions ([`7d60bb3`](https://github.com/nikazzio/universal-iiif-studio/commit/7d60bb345a5f78eef1d7653478cc089011f1bc3f))

---

**Detailed Changes**: [v0.14.1...v0.14.2](https://github.com/nikazzio/universal-iiif-studio/compare/v0.14.1...v0.14.2)

## v0.14.1 (2026-03-02)

_This release is published under the MIT License._

### Bug Fixes

- **core**: Replace print() with logger in core modules ([`9d39cc1`](https://github.com/nikazzio/universal-iiif-studio/commit/9d39cc18ad960c48ae910e9c9f6491224fb70cae))

---

**Detailed Changes**: [v0.14.0...v0.14.1](https://github.com/nikazzio/universal-iiif-studio/compare/v0.14.0...v0.14.1)

## v0.14.0 (2026-03-02)

_This release is published under the MIT License._

---

**Detailed Changes**: [v0.13.4...v0.14.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.13.4...v0.14.0)

## v0.13.4 (2026-03-02)

_This release is published under the MIT License._

### Bug Fixes

- Unblock PR54 pipelines (FAQ links and sync script complexity) ([`bd2c8c3`](https://github.com/nikazzio/universal-iiif-studio/commit/bd2c8c313ee44460077fafab7c399021de553a99))

### Chores

- Add issue and PR governance templates with automated checks ([`63344e4`](https://github.com/nikazzio/universal-iiif-studio/commit/63344e414a6bc9429e39be94c1264d84ae5a8260))

### Documentation

- Add wiki source structure and automated sync workflow ([`28bf41e`](https://github.com/nikazzio/universal-iiif-studio/commit/28bf41eab3e491a354c31d63c85ef7192f799d11))

- Fix wiki home links and update repository badge URLs ([`ca03e48`](https://github.com/nikazzio/universal-iiif-studio/commit/ca03e48ce01affad29f7f1b7051ec1f44c94085a))

- Harden wiki sync flow and refine wiki sources ([`c82e0db`](https://github.com/nikazzio/universal-iiif-studio/commit/c82e0dbc4915ff243767b21522acb10e2a998571))

- Strengthen AGENTS playbook with pragmatic workflow and skills ([`e388eb2`](https://github.com/nikazzio/universal-iiif-studio/commit/e388eb2ed45acd8c9f6a917a243dca6d94046497))

---

**Detailed Changes**: [v0.13.3...v0.13.4](https://github.com/nikazzio/universal-iiif-studio/compare/v0.13.3...v0.13.4)

## v0.13.3 (2026-03-01)

_This release is published under the MIT License._

### Bug Fixes

- Prevent gallica discovery freeze on repeated searches ([`864b4ec`](https://github.com/nikazzio/universal-iiif-studio/commit/864b4ec71bbd187a3ab98dd07294a6f45cbbe520))

---

**Detailed Changes**: [v0.13.2...v0.13.3](https://github.com/nikazzio/universal-iiif-studio/compare/v0.13.2...v0.13.3)

## v0.13.2 (2026-03-01)

_This release is published under the MIT License._

### Bug Fixes

- Avoid library filter flash on navigation ([`dbfeb5a`](https://github.com/nikazzio/universal-iiif-studio/commit/dbfeb5a0adeec02c05001e02fa55958384a6fa4e))

- Persist collapsible state for library filters and archive sections ([`35c040a`](https://github.com/nikazzio/universal-iiif-studio/commit/35c040ab799bd29f057f5684450c9bc5422c58dc))

- Persist library filters across section changes ([`d6b96a1`](https://github.com/nikazzio/universal-iiif-studio/commit/d6b96a1859cd1a0fc73e95f9e6114f83e68acc34))

- Refine library cards and persist filters across navigation ([`10fb6d5`](https://github.com/nikazzio/universal-iiif-studio/commit/10fb6d599ab89213738421bbb07e6404905193ff))

---

**Detailed Changes**: [v0.13.1...v0.13.2](https://github.com/nikazzio/universal-iiif-studio/compare/v0.13.1...v0.13.2)

## v0.13.1 (2026-03-01)

_This release is published under the MIT License._

### Bug Fixes

- Improve gallica filters and discovery UX consistency ([`71db4a7`](https://github.com/nikazzio/universal-iiif-studio/commit/71db4a7be3d6e621c148e609fe732a32e44868ae))

### Documentation

- Align discovery behavior and config reference ([`df41a8e`](https://github.com/nikazzio/universal-iiif-studio/commit/df41a8e73de9162a76f6624187e87c93b9120436))

---

**Detailed Changes**: [v0.13.0...v0.13.1](https://github.com/nikazzio/universal-iiif-studio/compare/v0.13.0...v0.13.1)

## v0.13.0 (2026-03-01)

_This release is published under the MIT License._

### Bug Fixes

- Address copilot review feedback on export flow ([`5a5235e`](https://github.com/nikazzio/universal-iiif-studio/commit/5a5235ede26c5129baec4d0ee354ae293dd44b5b))

- Align export page layout with app section structure ([`a44d816`](https://github.com/nikazzio/universal-iiif-studio/commit/a44d8161d7a1665f7ef0949486388d9b1e815811))

- Harmonize studio, export and library UI with theme tokens ([`dfc9048`](https://github.com/nikazzio/universal-iiif-studio/commit/dfc9048072af892a4b328124b2277d42a2d9ea8a))

- Stabilize studio export thumbnail selection and clean export service ([`2a4b691`](https://github.com/nikazzio/universal-iiif-studio/commit/2a4b69142562d1dfad11ade8f131085b0ae4e45f))

### Features

- Add studio single-item export workflow and export monitor ([`b9eb67f`](https://github.com/nikazzio/universal-iiif-studio/commit/b9eb67ffb930bf7c731adf192b82c5f0295c9d26))

- Complete studio/settings/export integration and UI refinements ([`2118e98`](https://github.com/nikazzio/universal-iiif-studio/commit/2118e98a44ecbe41ce72f19744d4bd44537268ec))

---

**Detailed Changes**: [v0.12.0...v0.13.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.12.0...v0.13.0)

## v0.12.0 (2026-02-28)

_This release is published under the MIT License._

### Bug Fixes

- Address copilot review findings for pause progress and institut page count ([`de0a4ff`](https://github.com/nikazzio/universal-iiif-studio/commit/de0a4ff0ad418bf202f1bcb7b24fad79bc876886))

### Features

- Implement Institut de France resolver and search functionality ([`b45eacc`](https://github.com/nikazzio/universal-iiif-studio/commit/b45eacc3710fc5301fa3fcc3234b5dbdfef41099))

---

**Detailed Changes**: [v0.11.1...v0.12.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.11.1...v0.12.0)

## v0.11.1 (2026-02-28)

_This release is published under the MIT License._

### Bug Fixes

- Stabilize gallica download state and prevent duplicate jobs ([`3a4d5db`](https://github.com/nikazzio/universal-iiif-studio/commit/3a4d5db0862f106384a36fce9b80e76ab0bc5127))

---

**Detailed Changes**: [v0.11.0...v0.11.1](https://github.com/nikazzio/universal-iiif-studio/compare/v0.11.0...v0.11.1)

## v0.11.0 (2026-02-28)

_This release is published under the MIT License._

### Bug Fixes

- Clean stale download manager state and stabilize routing tests ([`5efdc2a`](https://github.com/nikazzio/universal-iiif-studio/commit/5efdc2afe1c2baf426357d1d93a3fbc2ecd223f6))

- Prefer shelfmark over generic catalog titles ([`31b9af9`](https://github.com/nikazzio/universal-iiif-studio/commit/31b9af99b0d5089afad5edd42a61a543253504b8))

### Features

- Complete library metadata and state workflow ([`bb98006`](https://github.com/nikazzio/universal-iiif-studio/commit/bb9800621b9c292f247aec1ca66afb8c62c03eac))

- Implement library section and discovery/download manager upgrades ([`2e90cf9`](https://github.com/nikazzio/universal-iiif-studio/commit/2e90cf9990f83d07d5faa61823a079dd9f7ed95a))

- **download-manager**: Add remove download functionality and related handlers ([`6471d75`](https://github.com/nikazzio/universal-iiif-studio/commit/6471d757cd884c5e935ffef0bf0b5fd38271c49c))

---

**Detailed Changes**: [v0.10.3...v0.11.0](https://github.com/nikazzio/universal-iiif-studio/compare/v0.10.3...v0.11.0)

## v0.10.3 (2026-02-23)

_This release is published under the MIT License._

### Bug Fixes

- Avoid race between failed status and DB error state ([`e63ce2f`](https://github.com/nikazzio/universal-iiif-downloader/commit/e63ce2fc53682ccb17ac5304c0c21cf76f20aad6))

- Make OOB toasts visible by default ([`7f3de7a`](https://github.com/nikazzio/universal-iiif-downloader/commit/7f3de7ad3dda87bb8f522277659344d4e587c8fb))

- Stabilize global toasts and unify studio feedback ([`dc97d6d`](https://github.com/nikazzio/universal-iiif-downloader/commit/dc97d6d9b0699f979dc1bb320d456146955effd6))

---

**Detailed Changes**: [v0.10.2...v0.10.3](https://github.com/nikazzio/universal-iiif-downloader/compare/v0.10.2...v0.10.3)

## v0.10.2 (2026-02-23)

_This release is published under the MIT License._

### Bug Fixes

- Make toasts self-dismissing with reliable close and gradient UI ([#19](https://github.com/nikazzio/universal-iiif-downloader/pull/19), [`8141187`](https://github.com/nikazzio/universal-iiif-downloader/commit/814118745099062a2f1124286f081eaa65f60c24))

- Repair toast dismiss behavior and theme gradient styling ([#19](https://github.com/nikazzio/universal-iiif-downloader/pull/19), [`2d4579a`](https://github.com/nikazzio/universal-iiif-downloader/commit/2d4579a52050b2381e27a504f7141e0e2cb8b0fe))

- Unify OOB toast system and discovery inline feedback ([#19](https://github.com/nikazzio/universal-iiif-downloader/pull/19), [`ded7583`](https://github.com/nikazzio/universal-iiif-downloader/commit/ded7583c9c3b2d343c6d54990c79d55c784569d4))

- Wrap OOB toast payload to preserve card styles and interactions ([#19](https://github.com/nikazzio/universal-iiif-downloader/pull/19), [`015383b`](https://github.com/nikazzio/universal-iiif-downloader/commit/015383befd7ecba36ef12f8711967f44dc8da537))

---

**Detailed Changes**: [v0.10.1...v0.10.2](https://github.com/nikazzio/universal-iiif-downloader/compare/v0.10.1...v0.10.2)

## v0.10.1 (2026-02-23)

_This release is published under the MIT License._

### Bug Fixes

- Stabilize progress output and avoid duplicate download updates ([`45e66fe`](https://github.com/nikazzio/universal-iiif-downloader/commit/45e66fed611b5db7ed5d2c48d9a9f38ef0690820))

### Continuous Integration

- Remove deprecated lychee exclude-mail flag ([`7874d7f`](https://github.com/nikazzio/universal-iiif-downloader/commit/7874d7f60abaae963c2db7e856f1e7934fe6d96d))

- Run full-repo checks in CI workflows ([`e03e8bb`](https://github.com/nikazzio/universal-iiif-downloader/commit/e03e8bb86e925d402e3bacffdcdb43a933455b5f))

### Documentation

- Add LICENSE file referenced by README ([`dfcc471`](https://github.com/nikazzio/universal-iiif-downloader/commit/dfcc471c9af392afddd04ea5e7404b5c44dc3839))

### Refactoring

- Fix downloader lint after main rebase ([`202f6e3`](https://github.com/nikazzio/universal-iiif-downloader/commit/202f6e3172ac297d8e34b2141d78ef38a285aa4e))

- Resolve Ruff baseline and simplify C901 hotspots ([`be9f5d2`](https://github.com/nikazzio/universal-iiif-downloader/commit/be9f5d2025a31338fac262883755054a726804ae))

---

**Detailed Changes**: [v0.10.0...v0.10.1](https://github.com/nikazzio/universal-iiif-downloader/compare/v0.10.0...v0.10.1)

## v0.10.0 (2026-02-23)

_This release is published under the MIT License._

### Bug Fixes

- **ci**: Harden checks and scope docs/code lint to changed files ([`7a1b2f7`](https://github.com/nikazzio/universal-iiif-downloader/commit/7a1b2f7885498a6dab73be183683b1b76f9928d7))

- **config**: Add default security allowed_origins for CI/runtime parity ([`410512d`](https://github.com/nikazzio/universal-iiif-downloader/commit/410512d5d025969ffacf6839195103e2c1a769f6))

### Chores

- Apply lint cleanup to routing and resolver modules ([`1b76419`](https://github.com/nikazzio/universal-iiif-downloader/commit/1b764196c4d53206fe66bd6a25d23eb75fa30e51))

### Features

- Implement native PDF priority flow and docs quality gates ([`2b6bb5b`](https://github.com/nikazzio/universal-iiif-downloader/commit/2b6bb5bf0dcc3f59762f471079ef98679fa7ff21))

---

**Detailed Changes**: [v0.9.0...v0.10.0](https://github.com/nikazzio/universal-iiif-downloader/compare/v0.9.0...v0.10.0)

## v0.9.0 (2026-02-07)

_This release is published under the MIT License._

### Bug Fixes

- Security hardening for routing layer ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

- **db**: Unify ms_id/folder_name and add display_title column ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

- **gallica**: Correct SRU query format and add ID-based search ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

- **studio**: Add explicit route for serving download files ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

- **studio**: Ensure downloads directory is always mounted ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

- **studio**: Remove FastHTML static route to serve downloads correctly ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

### Features

- Discovery resolvers + Security hardening ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

- Enhance utility functions and add robust error handling ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

- **search**: Enhance results UI and add Vatican search ([#28](https://github.com/nikazzio/universal-iiif-downloader/pull/28), [`9cf59d9`](https://github.com/nikazzio/universal-iiif-downloader/commit/9cf59d9a2d9aa3be770143cad8e301249b61acbe))

---

**Detailed Changes**: [v0.8.0...v0.9.0](https://github.com/nikazzio/universal-iiif-downloader/compare/v0.8.0...v0.9.0)

## v0.8.0 (2026-01-30)

_This release is published under the MIT License._

### Features

- Enhance settings management and downloader functionality with improved logging and directory handling ([#21](https://github.com/nikazzio/universal-iiif-downloader/pull/21), [`adbfc95`](https://github.com/nikazzio/universal-iiif-downloader/commit/adbfc95d9631a021fb1b0ab04472355b4214f182))

- Implement download job management, including cancellation feedback and cleanup of stale jobs ([#21](https://github.com/nikazzio/universal-iiif-downloader/pull/21), [`adbfc95`](https://github.com/nikazzio/universal-iiif-downloader/commit/adbfc95d9631a021fb1b0ab04472355b4214f182))

- Implement download management features with UI updates ([#21](https://github.com/nikazzio/universal-iiif-downloader/pull/21), [`adbfc95`](https://github.com/nikazzio/universal-iiif-downloader/commit/adbfc95d9631a021fb1b0ab04472355b4214f182))

- Implement settings management with UI controls and logging enhancements ([#21](https://github.com/nikazzio/universal-iiif-downloader/pull/21), [`adbfc95`](https://github.com/nikazzio/universal-iiif-downloader/commit/adbfc95d9631a021fb1b0ab04472355b4214f182))

### Refactoring

- Extract discovery helpers and simplify discovery routes (reduce complexity C901) ([#16](https://github.com/nikazzio/universal-iiif-downloader/pull/16), [`7600082`](https://github.com/nikazzio/universal-iiif-downloader/commit/76000822ac465c3e3590de45ae785f071987ef20))

- Simplify discovery routes ([#16](https://github.com/nikazzio/universal-iiif-downloader/pull/16), [`7600082`](https://github.com/nikazzio/universal-iiif-downloader/commit/76000822ac465c3e3590de45ae785f071987ef20))

- Simplify discovery routes and extract handlers into separate files ([#16](https://github.com/nikazzio/universal-iiif-downloader/pull/16), [`7600082`](https://github.com/nikazzio/universal-iiif-downloader/commit/76000822ac465c3e3590de45ae785f071987ef20))

- Web app entry point ([`60c1f2a`](https://github.com/nikazzio/universal-iiif-downloader/commit/60c1f2abdde7b6d4ec1e51f9a7ea4adfaa87e375))

---

**Detailed Changes**: [v0.7.1...v0.8.0](https://github.com/nikazzio/universal-iiif-downloader/compare/v0.7.1...v0.8.0)

## v0.7.1 (2026-01-28)

_This release is published under the MIT License._

### Bug Fixes

- Clean up print statement formatting and add missing newline in verify_image_processing.py ([#15](https://github.com/nikazzio/universal-iiif-downloader/pull/15), [`ad465c4`](https://github.com/nikazzio/universal-iiif-downloader/commit/ad465c4542eb8f249495cdabae105bcce7b95c05))

- **runtime**: Move runtime data to data/local ([#15](https://github.com/nikazzio/universal-iiif-downloader/pull/15), [`ad465c4`](https://github.com/nikazzio/universal-iiif-downloader/commit/ad465c4542eb8f249495cdabae105bcce7b95c05))

- **runtime**: Move runtime data to data/local and update docs ([#15](https://github.com/nikazzio/universal-iiif-downloader/pull/15), [`ad465c4`](https://github.com/nikazzio/universal-iiif-downloader/commit/ad465c4542eb8f249495cdabae105bcce7b95c05))

### Chores

- Mount data/local/snippets at /assets/snippets; remove unused static/snippets ([#15](https://github.com/nikazzio/universal-iiif-downloader/pull/15), [`ad465c4`](https://github.com/nikazzio/universal-iiif-downloader/commit/ad465c4542eb8f249495cdabae105bcce7b95c05))

- **release**: Update version to 0.7.0 and clean up egg-info files ([`039cfed`](https://github.com/nikazzio/universal-iiif-downloader/commit/039cfedf93b56e14a8a027bb16970a851df6348d))

### Documentation

- Clarify roles of data/local, assets, static; changelog runtime path update ([#15](https://github.com/nikazzio/universal-iiif-downloader/pull/15), [`ad465c4`](https://github.com/nikazzio/universal-iiif-downloader/commit/ad465c4542eb8f249495cdabae105bcce7b95c05))

---

**Detailed Changes**: [v0.7.0...v0.7.1](https://github.com/nikazzio/universal-iiif-downloader/compare/v0.7.0...v0.7.1)

## v0.7.0 (2026-01-28)

_This release is published under the MIT License._

### Chores

- **config**: Add ocr.kraken_enabled ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **release**: Align version metadata ([#11](https://github.com/nikazzio/universal-iiif-downloader/pull/11), [`884c027`](https://github.com/nikazzio/universal-iiif-downloader/commit/884c02792a1d80872036f6ca0999aee63585e6e1))

- **release**: Fix semantic-release v9 config ([#12](https://github.com/nikazzio/universal-iiif-downloader/pull/12), [`bd82784`](https://github.com/nikazzio/universal-iiif-downloader/commit/bd827847951daf3f45ccb60fe20f9ad0322b5447))

- **release**: Stabilize semantic-release ([#11](https://github.com/nikazzio/universal-iiif-downloader/pull/11), [`884c027`](https://github.com/nikazzio/universal-iiif-downloader/commit/884c02792a1d80872036f6ca0999aee63585e6e1))

- **release**: Stabilize semantic-release ([#10](https://github.com/nikazzio/universal-iiif-downloader/pull/10), [`164a27e`](https://github.com/nikazzio/universal-iiif-downloader/commit/164a27e5ad4c5871edee0db95a37391bbf6efb8e))

### Continuous Integration

- Implement semantic release with a new GitHub Actions workflow and update documentation. ([#9](https://github.com/nikazzio/universal-iiif-downloader/pull/9), [`7065fdc`](https://github.com/nikazzio/universal-iiif-downloader/commit/7065fdc779481e8220e522a70e52e896730a8b3e))

- Implement semantic release with a new GitHub Actions workflow and update documentation. ([#8](https://github.com/nikazzio/universal-iiif-downloader/pull/8), [`8f0d756`](https://github.com/nikazzio/universal-iiif-downloader/commit/8f0d756c2d55a3e36cb55ac1778d186e2ffdb67d))

### Documentation

- Refresh workflows and guidelines ([#9](https://github.com/nikazzio/universal-iiif-downloader/pull/9), [`7065fdc`](https://github.com/nikazzio/universal-iiif-downloader/commit/7065fdc779481e8220e522a70e52e896730a8b3e))

- Update AGENTS.md guidelines ([#9](https://github.com/nikazzio/universal-iiif-downloader/pull/9), [`7065fdc`](https://github.com/nikazzio/universal-iiif-downloader/commit/7065fdc779481e8220e522a70e52e896730a8b3e))

- Update CHANGELOG for v0.6.0 [skip-release] ([`f47c40a`](https://github.com/nikazzio/universal-iiif-downloader/commit/f47c40ac12d398a3076c09d4e8360a98a7169a0f))

- **agents**: Clarify branching rule ([#11](https://github.com/nikazzio/universal-iiif-downloader/pull/11), [`884c027`](https://github.com/nikazzio/universal-iiif-downloader/commit/884c02792a1d80872036f6ca0999aee63585e6e1))

- **agents**: Clarify branching rule ([#10](https://github.com/nikazzio/universal-iiif-downloader/pull/10), [`164a27e`](https://github.com/nikazzio/universal-iiif-downloader/commit/164a27e5ad4c5871edee0db95a37391bbf6efb8e))

### Features

- Implement transcription versioning with restore, verification, and detailed history diffs in the Studio UI. ([#14](https://github.com/nikazzio/universal-iiif-downloader/pull/14), [`f278261`](https://github.com/nikazzio/universal-iiif-downloader/commit/f2782619173137e439e7cd396dc26cd0cdd9cb08))

- Introduce new FastHTML-based Studio UI for manuscript viewing and transcription, including document selection and OCR integration. ([#14](https://github.com/nikazzio/universal-iiif-downloader/pull/14), [`f278261`](https://github.com/nikazzio/universal-iiif-downloader/commit/f2782619173137e439e7cd396dc26cd0cdd9cb08))

- Overhaul visual filter controls for the Mirador viewer, adding presets and configuration management. ([#14](https://github.com/nikazzio/universal-iiif-downloader/pull/14), [`f278261`](https://github.com/nikazzio/universal-iiif-downloader/commit/f2782619173137e439e7cd396dc26cd0cdd9cb08))

- **routes**: Add API and discovery routes for IIIF manifest serving and document download ([#14](https://github.com/nikazzio/universal-iiif-downloader/pull/14), [`f278261`](https://github.com/nikazzio/universal-iiif-downloader/commit/f2782619173137e439e7cd396dc26cd0cdd9cb08))

### Refactoring

- **cli**: Reduce CLI complexity ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **iiif**: Split tile stitching helpers ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **ocr**: Gate kraken and split hf flow ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **ocr**: Gate kraken via config ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **ocr**: Split model manager download flow ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **storage**: Simplify manuscript upsert ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **ui**: Reduce remaining ruff complexity ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **ui**: Split export studio page ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

- **ui**: Split settings panel helpers ([#13](https://github.com/nikazzio/universal-iiif-downloader/pull/13), [`40b12c1`](https://github.com/nikazzio/universal-iiif-downloader/commit/40b12c15f151ffaaed3f71ce513bd4e7b61c792b))

---

**Detailed Changes**: [v0.6.0...v0.7.0](https://github.com/nikazzio/universal-iiif-downloader/compare/v0.6.0...v0.7.0)

## [v0.6.1] - 2026-03-02

### Added

- Added global, non-mutating `config.json` validation with severity-based diagnostics (`WARNING`/`ERROR`) during `ConfigManager.load()` (#73).
- Added dedicated tests for config schema/deprecation validation and load-time logging behavior (#73).

### Changed

- Deprecated thumbnail keys are now explicitly reported as runtime warnings instead of being silently ignored (#73).
- Validation logs avoid leaking sensitive config values such as API keys and tokens (#73).

### Fixed

- Improved startup diagnostics for malformed configuration roots and invalid JSON payloads (`ERROR` severity where appropriate) (#73).

## [v0.6.0] - 2026-01-23

### Added

- Snippet SQLite feature set (#6).

### Changed

- None.

### Fixed

- Moved runtime data from `var/` to `data/local/` and served snippets from `/assets/snippets/` (chore/docs) (#15).

## [v0.5.1] - 2026-01-19

### Added

- None.

### Changed

- Refactored logging setup and improved code formatting across multiple modules (#5).

### Fixed

- None.

## [v0.5.0] - 2026-01-19

### Added

- **Rich Text Editor**: Replaced the legacy plain text editor with an advanced RTE based on a dedicated Quill wrapper (#4).
  - Text formatting support (bold, italic, underline).
  - Bullet and numbered lists.
  - Superscript and subscript.
  - Hybrid save mode (HTML for rendering, plain text for indexing).
- **History Restoration**: Improved history restore logic to correctly handle RTE content (#4).

### Changed

- **Logging**: Refactored logging to use centralized setup (`get_logger`) instead of scattered direct calls, improving debuggability and consistency (#4).
- **Config**: Improved dependency/import handling to reduce circular import conflicts (#4).

### Fixed

- Resolved critical merge conflicts during integration of branch `add-rich-text` (#4).
- Fixed minor issues in legacy UI session-state handling during save operations (#4).

## [v0.4.0] - 2026-01-19

### Added

- **Local PDF Import**: Added local PDF import into `downloads/Local` with automatic page image extraction (#3).
- **Studio UI Remaster**: Introduced a redesigned Studio page with collapsible sidebar and improved navigation (#3).
- **Global Search**: Added a page to search text across all saved transcriptions (#3).

### Changed

- Improved UI notification handling (#3).
- Improved performance for high-resolution image loading (#3).

### Fixed

- None.
