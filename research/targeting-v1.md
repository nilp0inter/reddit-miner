# v1 Targeting: ComfyUI / Stable Diffusion Communities for 3D and Video

Date: 2026-08-26. v1 scope locked by the operator: the Reddit threads where
the Stable Diffusion community compiles ComfyUI workflows and techniques for
generating 3D assets, video assets, and generative video in general.

## Target subreddits

Verification method: RSS probe (`https://www.reddit.com/r/<name>/.rss`,
2026-08-26). Reddit 429-throttled this IP after roughly two requests, so live
verification (HTTP 200) succeeded for three subreddits. Search results back
the rest. Re-verify at collection time with the authenticated API.

Subscriber counts: no reliable source was reachable this session. The
subredditstats.com API is dead ("not found"), and Reddit blocks
unauthenticated API metadata. Get exact counts from PRAW
(`subreddit.subscribers`) at collection time; do not cite stale numbers.

| Subreddit | Role | Status | Evidence |
|---|---|---|---|
| r/comfyui | Primary. ComfyUI workflows, node graphs, techniques. | Verified live (RSS HTTP 200) | Probe |
| r/StableDiffusion | Primary. Largest SD community; workflows, model releases, techniques. | Live-ness unverified (probe 429); active confirmed | Search: Hunyuan3D 2.0 release thread (r/StableDiffusion, 19mo ago); "GenAI 3D Asset platforms compared, Tripo vs Meshy vs Trellis vs Hunyuan" (19mo ago) |
| r/StableDiffusionUI | Primary. ComfyUI-adjacent community. | Verified live (RSS HTTP 200) | Probe |
| r/unstable_diffusion | Secondary. NSFW image generation; heavy ComfyUI use. | Verified live (RSS HTTP 200) | Probe + search: community is NSFW AI image generation, shares ComfyUI workflows |
| r/aivideo | Secondary. Generative video in general. | Unverified (probe 429) | — |
| r/wanvideo | Secondary. Wan video model community. | Unverified (probe 429) | — |
| r/GenAI | Secondary. Broad generative-AI, includes 3D and video tool posts. | Unverified (probe 429) | — |

r/unstable_diffusion scope note: the community generates NSFW images. The
collector retains its submissions and comments, including their media, and
records the Reddit `over_18` state as `is_nsfw`. No hidden collection-time
filter decides which workflow evidence a downstream researcher can read.

Note on 3D assets: dedicated 3D-generation subreddits are small and unstable.
Search confirms the 3D-asset knowledge (TRELLIS, Hunyuan3D, TripoSR
comparisons) lives inside r/comfyui and r/StableDiffusion as technique posts:
"TripoSG vs Hunyuan3D (small comparison)" (r/comfyui, 16mo ago) and the two
r/StableDiffusion threads above. v1 must use keyword search inside the big
communities, not a dedicated small subreddit.

Evidence links (search, 2026-08-26):

- https://www.reddit.com/r/StableDiffusion/comments/1mg1kx9/ (3D asset
  platforms compared: Tripo vs Meshy vs Trellis vs Hunyuan)
- https://www.reddit.com/r/StableDiffusion/comments/1i6d0mr/ (Hunyuan3D 2.0
  release discussion)
- https://www.reddit.com/r/comfyui/comments/1jrrm15/ (TripoSG vs Hunyuan3D
  comparison in r/comfyui)


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
