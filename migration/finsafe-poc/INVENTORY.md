# FinSAFE POC staged-source inventory

Inventory date: 2026-10-28

Source root: `D:/git/geeksfino/finsafe/dist/poc`

Staging root: `migration/finsafe-poc/legacy`

Each staged file is a byte-identical copy. Matching SHA256 values establish
copy integrity only. They do not establish integration, correctness outside the
tested cases, or fitness for a future Agent Safety Arena contract.

## File provenance

| Source relative path | Staged relative path | Bytes | Source SHA256 | Staged SHA256 |
| --- | --- | ---: | --- | --- |
| `recording-tools/metadata_io.cjs` | `legacy/recording-tools/metadata_io.cjs` | 822 | `6d70bf35358f9b4080391b2a7004f6312a4a294905c0914f76a048eac8a79895` | `6d70bf35358f9b4080391b2a7004f6312a4a294905c0914f76a048eac8a79895` |
| `recording-tools/metadata_io.test.cjs` | `legacy/recording-tools/metadata_io.test.cjs` | 1885 | `adf676b7d98fba4564574ad6ad4cf78b8acabd9c13e871295faa6c50484c06f9` | `adf676b7d98fba4564574ad6ad4cf78b8acabd9c13e871295faa6c50484c06f9` |
| `recording-tools/native_completion.cjs` | `legacy/recording-tools/native_completion.cjs` | 560 | `8df1ed12432a4c3bab133c4f83c0044c6ed223706f5412f59125143d520b7949` | `8df1ed12432a4c3bab133c4f83c0044c6ed223706f5412f59125143d520b7949` |
| `recording-tools/native_completion.test.cjs` | `legacy/recording-tools/native_completion.test.cjs` | 1268 | `bfddb317800a6a1ba9be3ea82e9d9ddc5e30fa36a1155f5f5a292c45c7a232e8` | `bfddb317800a6a1ba9be3ea82e9d9ddc5e30fa36a1155f5f5a292c45c7a232e8` |
| `recording-tools/media_privacy.py` | `legacy/recording-tools/media_privacy.py` | 1665 | `c98c32be15b0760e74da89fc388bbcf6ceb16fe75412555b2d7f14110fcf2bfe` | `c98c32be15b0760e74da89fc388bbcf6ceb16fe75412555b2d7f14110fcf2bfe` |
| `recording-tools/media_privacy.test.py` | `legacy/recording-tools/media_privacy.test.py` | 2429 | `87d05dbc1b32154372814bde5ea6aa82a34bccca304b18a5a1b628a7a466265d` | `87d05dbc1b32154372814bde5ea6aa82a34bccca304b18a5a1b628a7a466265d` |

## Component audit

### Atomic metadata writer

Files:

- `recording-tools/metadata_io.cjs`
- `recording-tools/metadata_io.test.cjs`

Dependencies: The implementation uses only Node.js built-ins `node:fs` and
`node:crypto`, plus `SharedArrayBuffer` and `Atomics.wait`. The test uses
`node:test`, `node:assert/strict`, `node:fs`, `node:os`, and `node:path`. In the
source POC, `recording-tools/session.cjs` calls this module. That caller is not
staged because it is coupled to DSH sessions and the wider recording lifecycle.

Proposed final target: Candidate behavior for `src/arena/evidence/`, with its
replacement regression under `tests/`. This is not an approved module or API.

Reusable behavior: Write formatted JSON to a unique temporary file, keep the
previous document valid until replacement, retry `EBUSY`, `EPERM`, and
`EACCES` for a bounded period, and remove the temporary file after failure.

Required extraction: Define the metadata durability contract first. Decide
whether synchronous blocking and a fixed 20 ms retry interval are acceptable.
Test actual supported filesystems and concurrent writers. Preserve the rule
that a permanent failure keeps the previous valid document.

Tests: `node --test metadata_io.test.cjs` is included in the combined Node
command. Three tests passed in the source tree and three tests passed in the
staged tree. They cover a transient sharing conflict, a permanent bounded
failure, and an immediate non-sharing failure.

Platform limits: The retry set and source comment target Windows sharing
conflicts. The tests mock filesystem errors; they do not prove atomic rename or
locking behavior on each supported filesystem. Synchronous waiting blocks the
Node.js thread.

Evidence limits: The tests use temporary synthetic JSON. They do not validate
DSH session capture, multi-process contention, crash consistency, storage flush,
or recovery after machine failure.

Removal plan: Replace this pair after the accepted evidence-storage contract
has a maintained implementation and equivalent failure tests. Remove the pair
without retaining a runtime import from `legacy/`.

### Native completion selector

Files:

- `recording-tools/native_completion.cjs`
- `recording-tools/native_completion.test.cjs`

Dependencies: The implementation has no imported module. It depends on the
historical DSH event object shape and sequence semantics. The test uses
`node:test` and `node:assert/strict`. In the source POC,
`recording-tools/session.cjs` supplies events to this module. That caller is not
staged.

Proposed final target: Candidate behavior for an agent-specific normalization
adapter under `src/arena/adapters/agents/`, with contract tests under `tests/`.
The common evidence layer must not assume the DSH event schema.

Reusable behavior: Select the last public assistant text event after the
matched human event and before the turn end, require the same turn identifier,
exclude reasoning-only content, and mark a completed turn with no public text.

Required extraction: Define a normalized native-event contract. Validate
missing or malformed event fields instead of relying on nested values. Keep
public reply text separate from reasoning and private native logs. Decide how
non-completed end reasons and multiple public text events are represented.

Tests: `node --test native_completion.test.cjs` is included in the combined
Node command. Three tests passed in the source tree and three tests passed in
the staged tree. They cover reasoning-only completion, exact public text, and
wrong-turn or post-end text.

Platform limits: The pure selection logic is platform-neutral, but its input
schema is DSH-specific and is not a verified vendor-neutral agent format.

Evidence limits: Synthetic rows test selection rules only. They do not prove
that a native session log is complete, correctly matched to the submitted
prompt, or safe to publish. The returned assistant object can contain fields
that require separate privacy review.

Removal plan: Replace this pair after the agent adapter contract and sanitized
evidence model have equivalent tests. Do not move the historical event schema
into the common runner.

### Declared media privacy mapping

Files:

- `recording-tools/media_privacy.py`
- `recording-tools/media_privacy.test.py`

Dependencies: The implementation uses only Python's `copy.deepcopy` and emits
FFmpeg filter strings. The test uses `unittest`, `subprocess`, and `pathlib`.
Its real-filter test imports `imageio-ffmpeg` from
`~/.cache/codex-media-tools`; this machine used version 0.6.0 and its bundled
FFmpeg 7.1 executable. In the source POC, `finalize_review.py` calls
`review_overrides`, and `export_display.py` calls `mask_runs` and
`ffmpeg_filters`. Those wider pipeline files are not staged.

Proposed final target: Candidate behavior for `src/arena/evidence/` or
`src/arena/reporting/`, after the public-media and privacy contracts assign
ownership. Replacement tests belong under `tests/`.

Reusable behavior: Retain only declared privacy masks from review overrides,
validate rectangle and time bounds, map actual source timestamps to inclusive
display-frame runs, and generate filters for only those runs.

Required extraction: Separate timestamp mapping from an FFmpeg renderer. Make
font selection and mask text configurable or use a renderer-owned neutral
overlay. Define overlap, empty sample, timestamp ordering, and missing-font
behavior. Preserve the rule that masks are declared by a reviewer and are not
inferred from model text.

Tests: `python media_privacy.test.py -v` passed 5 of 5 tests in the source tree
and 5 of 5 tests in the staged tree. It covers omitted waiting intervals, empty
masks, retention of reviewed masks, invalid rectangles, and real FFmpeg pixels
inside and outside a declared mask. `python -m unittest
media_privacy.test.py -v` does not run this dotted filename as a module and
failed at discovery with `AttributeError: module 'media_privacy' has no
attribute 'test'`.

Platform limits: The generated `drawtext` filter hardcodes
`C:/Windows/Fonts/msyh.ttc` and Chinese overlay text. The real-filter test
depends on a user-cache package and its bundled Windows FFmpeg binary. The
implementation does not execute FFmpeg by itself.

Evidence limits: The test creates synthetic white video frames in memory. It
does not modify or inspect an original recording. It does not prove that every
private region was declared, that a public export contains no other private
data, or that a mask follows a resized or cropped pipeline outside the tested
dimensions.

Removal plan: Replace this pair after the public-media contract, renderer
choice, font strategy, and privacy review procedure are accepted and covered by
portable tests. Keep raw recordings outside Git and never use the staged filter
as the only privacy assurance.

## Verification record

The byte comparison reported identical source and staged hashes for all six
files. The following offline commands were run against both the source and the
staged copy:

```powershell
node --test metadata_io.test.cjs native_completion.test.cjs
python media_privacy.test.py -v
```

Results in each location: 6 of 6 Node tests passed and 5 of 5 Python tests
passed. The checks did not start an agent, DSH, FinSAFE, a fixture, a recorder,
or a background queue. They did not read cases, records, browser profiles,
credentials, or raw recordings.
