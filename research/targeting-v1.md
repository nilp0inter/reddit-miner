# v1 Targeting: ComfyUI / Stable Diffusion Communities for 3D and Video

Date: 2026-08-26. v1 scope locked by the operator: the Reddit threads where
the Stable Diffusion community compiles ComfyUI workflows and techniques for
generating 3D assets, video assets, and generative video in general.

## Target subreddits

Verification method: RSS probe (`https://www.reddit.com/r/<name>/.rss`,
2026-08-26). Reddit 429-throttled this IP after two requests, so only two
subreddits could be verified live. Re-verify the rest at collection time with
the authenticated API.

| Subreddit | Role | Status |
|---|---|---|
| r/comfyui | Primary. ComfyUI workflows, node graphs, techniques. | Verified live (HTTP 200) |
| r/StableDiffusionUI | Primary. ComfyUI-adjacent community (originally the AUTOMATIC1111 alternative UI community, now heavily ComfyUI). | Verified live (HTTP 200) |
| r/StableDiffusion | Primary. Largest SD community; workflows, model releases, techniques. | Unverified (probe 429); known active community |
| r/aivideo | Secondary. Generative video in general. | Unverified (probe 429) |
| r/wanvideo | Secondary. Wan video model community. | Unverified (probe 429) |
| r/GenAI | Secondary. Broad generative-AI, includes 3D and video tool posts. | Unverified (probe 429) |

Note on 3D assets: dedicated 3D-generation subreddits are small and unstable.
The bulk of the 3D-asset knowledge (TRELLIS, Hunyuan3D, TripoSR workflows)
lives inside r/comfyui and r/StableDiffusion as technique posts. v1 must use
keyword search inside the big communities, not a dedicated small subreddit.

## Keyword sets

### 3D asset generation

- Model/tool names: `TRELLIS`, `Hunyuan3D`, `Hunyuan3D-2`, `TripoSR`, `Tripo`,
  `Meshy`, `InstantMesh`, `Unique3D`, `CRM`, `Stable Zero123`, `Zero123++`
- Output terms: `3D asset`, `3D model`, `mesh`, `game asset`, `texture`,
  `PBR`, `UV unwrap`, `retopology`, `obj export`, `glb`, `USDZ`
- Pipeline terms: `image to 3D`, `text to 3D`, `mesh workflow`,
  `3D generation`

### Generative video

- Model/tool names: `Wan 2.1`, `Wan 2.2`, `WanVideo`, `HunyuanVideo`,
  `LTX-Video`, `LTXV`, `Mochi`, `AnimateDiff`, `CogVideoX`, `Stable Video
  Diffusion`, `SVD`
- Technique terms: `I2V`, `T2V`, `image to video`, `text to video`,
  `frame interpolation`, `RIFE`, `keyframe`, `first frame last frame`,
  `video upscale`, `temporal`, `flicker`
- Workflow terms: `video workflow`, `ComfyUI video`, `batch frames`,
  `latent video`

### ComfyUI-specific signal (both domains)

`workflow`, `node`, `custom node`, `workflow JSON`, `share your workflow`,
`ComfyUI`, `node graph`, `pack`, `coffee`
(r/comfyui's pinned community bundle)

## What to extract from a target thread

1. Post title, selftext, flair, score, upvote ratio, created date.
2. Comment tree, flattened, with scores and depths.
3. Links in selftext and comments: workflow JSON attachments, Civitai links,
  Hugging Face links, YouTube tutorials, Google Drive/Dropbox workflow files.
4. Media URLs (images/video) when the post shows the result.
5. Author and per-comment author, for later community-structure analysis.

## Collection plan (v1)

1. **Backfill history** from Arctic Shift dumps: full submission and comment
   history for r/comfyui and r/StableDiffusion. Filter with the keyword sets
   above. (No API cost.)
2. **Top up the recent window** (post-dump months) with PullPush search,
   then PRAW for anything PullPush misses.
3. **Keyword search sweeps** with PRAW against the primary subreddits,
   `search()` with each keyword, sort by relevance and by new.
4. **Optional live monitoring**: RSS feed poll for new post titles matching
   the keyword sets; fetch full data through PRAW on match.
5. Store raw JSON per submission and comment in dated files; dedupe by
   Reddit ID.

## Volume estimate

Backfill comes from dumps, so API budget only covers the recent window and
search sweeps. At 100 QPM with OAuth: roughly 6,000 listing calls per hour.
Each listing returns up to 100 items. A full keyword sweep of six subreddits
with ~40 keywords is a few hours of polite collection.

## Out of scope for v1

- Writing to Reddit (comments, votes, posts). Read-only.
- Non-English communities (defer).
- Discord, Civitai, and other non-Reddit sources (defer; workflow JSON
  sharing is heavy on Civitai and Discord, worth a v2).
