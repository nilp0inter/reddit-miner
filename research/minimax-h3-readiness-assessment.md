# MiniMax H3 Readiness Assessment

Date: 2026-08-26.

Scope: use genflow-miner as a research system for MiniMax H3. This assessment
proposes no product changes.

## Decision

Use genflow-miner as an evidence inbox. Do not treat it as a MiniMax H3 control
plane.

The collector can gather community practice. It cannot by itself establish
model expertise or generate a video.

## Model boundary

MiniMax H3 is the correct model name. It has two relevant base modes:

- **FL2VA**: text, optional first frame, and optional last frame.
- **Ref2VA**: text with reference images, videos, and audio.

Use Ref2VA when subject identity or style must persist. Use FL2VA when a sketch
defines the exact first or last composition.

A sketch is not a separate H3 input type. Use it as a `reference_image` when it
guides style or subject features. Use it as a `first_frame` when it must define
the opening shot.

MiniMax H3 does not generate every possible video without limits. Official
limits include 4–15 second clips, 24 FPS, bounded reference counts, input
format requirements, moderation, and license constraints. The local open model
produces the base result. Context-IR and 2K regeneration remain important parts
of the official full workflow.

## How to proceed with genflow-miner

### 1. Create separate evidence streams

Add these five topics. Keep each query narrow.

| Name | Query | Subreddit | Reason |
|---|---|---|---|
| `h3-model` | `MiniMax H3` | `all` | Finds model announcements, results, and broad user reports. |
| `h3-comfyui` | `MiniMax H3` | `comfyui` | Finds node graphs, installation details, and workflow files. |
| `h3-reference` | `H3 Ref2VA` | `all` | Finds subject-reference and multimodal reference practice. |
| `h3-frame-control` | `H3 FL2VA` | `all` | Finds first-frame and last-frame control practice. |
| `h3-context` | `H3 Context IR` | `all` | Finds prompt-orchestration and 2K workflow discussion. |

A broad MiniMax search mixes H3, Hailuo, text models, and unrelated AI-video
content. Narrow topics keep the evidence useful.

### 2. Treat queue items as evidence

Call `get_unprocessed_results` in small batches. Read the submission, relevant
comments, links, and available `media://` resources.

Reddit reports often omit checkpoint versions, node versions, input order,
hardware details, and failed retries. A good-looking clip is a lead, not proof
that a workflow reproduces.

The queue is at-most-once. A call marks returned items delivered. Write the
distillation record before moving to another batch.

### 3. Create one H3 knowledge card per useful finding

Record these five fields outside genflow-miner:

1. **Exact model and runtime.** Record FL2VA, Ref2VA, H3 API, Context-IR,
   Regenerate-2K, or a local checkpoint.
2. **Input roles.** Record which asset is the subject reference, first frame,
   last frame, style reference, motion reference, or audio reference.
3. **Prompt plan.** Record subject, action, shot sequence, camera motion,
   environment, soundscape, and dialogue.
4. **Technical recipe.** Record the workflow, node versions, precision,
   GPU/VRAM, resolution, duration, seed, and scheduler settings.
5. **Outcome.** Record what remained consistent, what drifted, what failed,
   and the source permalink.

This converts raw discussion into comparable evidence. It also prevents a
single strong output from becoming a false rule.

### 4. Classify the subject image and sketch before generation

Use the subject image as a `reference_image` when identity, clothing, object
design, or style must persist.

Use the sketch as a `first_frame` when it defines the first view, pose,
composition, or lighting. Use it as another `reference_image` when it gives a
style or composition constraint without a fixed opening frame.

State priority in the text prompt. Preserve the subject identity. Use the
sketch for composition. Describe motion separately.

### 5. Validate learned recipes with controlled experiments

Use a fixed subject reference and sketch. Change one factor per run: input
role, prompt wording, duration, reference count, camera motion, or Context-IR
use.

Compare identity retention, sketch adherence, motion coherence, audio quality,
and failure rate. Expertise comes from reproduced evidence, not collection
volume.

## What genflow-miner already supplies

- Persistent, narrow Reddit searches through saved topics.
- Threads and non-deleted comments for technique discussion.
- Reddit-hosted images and videos as `media://` MCP resources.
- Source permalinks, topic names, creation time, and media MIME types.
- Deduplication by Reddit ID.
- NSFW-submission exclusion.

This is enough to build a research queue for H3 workflows.

## What is missing

### 1. Official MiniMax material in the research corpus

The collector reads Reddit. It does not ingest the official release, API
reference, prompting guides, checkpoint documentation, license, or changelog.

This is the largest expertise gap. Community practice explains implementation.
MiniMax defines supported input roles, limits, task states, and formats.

### 2. A durable semantic knowledge base

The MCP queue only delivers raw items. It has no tool to save an H3 knowledge
card, cite evidence, merge duplicates, assign confidence, or correct an earlier
conclusion.

The at-most-once queue also loses an item from later reads after delivery. A
failed distillation needs an external record.

### 3. Reproducible workflow artifacts

The collector keeps Reddit text and Reddit-hosted media. It does not fetch
ComfyUI workflow JSON, custom-node versions, Hugging Face revisions, Civitai
metadata, model revisions, or external reference assets.

These artifacts decide whether another person can reproduce a claimed result.

### 4. A MiniMax H3 execution layer

The current MCP cannot submit a MiniMax task, construct H3 `content[]` input
roles, call Context-IR, poll task status, download output, regenerate at 2K, or
run a local H3 checkpoint.

A `media://` resource lets an MCP client inspect source media. It is not a
MiniMax API input. A generation client must upload or otherwise convert the
resource bytes into accepted H3 inputs.

### 5. An evaluation and rights process

The collector has no test corpus, output comparison, cost tracking, or human
review. It also cannot establish consent, likeness rights, or permitted use of
a subject reference.

MiniMax moderation and license terms still apply. These constraints matter most
when a reference image depicts a real person.

## H3 constraints for the target workflow

- A subject reference plus sketch fits Ref2VA when both images act as
  references. Ref2VA supports up to nine reference images.
- A composition sketch fits FL2VA when it must become the first frame. FL2VA
  supports zero, one, or two frame images.
- Reference videos and audio can add motion or voice direction. H3 limits them
  to three clips each and 15 seconds total.
- Input files have format and size limits. H3 accepts specific video, image,
  and audio formats.
- Native stereo audio is part of H3 output. A serious prompt must specify
  soundscape, dialogue, and music intent as well as visuals.
- The official 2K workflow uses Context-IR and regeneration services. A local
  H3 Base deployment alone does not reproduce the complete official pipeline.

## Verdict

genflow-miner can make a user well-informed about community H3 practice. It
cannot by itself make that user an H3 expert or generate arbitrary
reference-driven video.

The missing boundary is not more Reddit data. It is authoritative model
knowledge, reproducible workflow artifacts, a generation runner, and a
disciplined experiment record.

## Sources

- [MiniMax H3 open-source announcement](https://www.minimax.io/news/minimax-h3-open-source)
- [MiniMax H3 video generation guide](https://platform.minimax.io/docs/guides/video-generation)
- [genflow-miner MCP behavior](../README.md)
