# Formats and platforms

Specs change. These were current in late 2026; check the platform's help page before a paid
campaign or a strict upload. `preflight.py` knows the ids in the first table.

## Canvases

| Aspect | Size | Use |
|---|---|---|
| 9:16 | 1080x1920 | Reels, TikTok, Shorts, Stories, Snapchat, vertical marketplace slots |
| 4:5 | 1080x1350 | Instagram/Facebook feed, LinkedIn feed (best feed real estate) |
| 1:1 | 1080x1080 | Feeds, product galleries, carousels |
| 16:9 | 1920x1080 | YouTube, websites, presentations, marketplace listing videos, TV |
| 4:3 | 1440x1080 | Some marketplace content modules, classic screens |
| 2:3 / 1:2 / 2:1 | 1080x1620 / 960x1920 / 1920x960 | Pinterest, Etsy-style galleries, banners |
| 21:9 | 2560x1080 | Website hero banners, cinematic |

30 fps is the safe default everywhere. 24 for a filmic feel, 60 only when the footage is 60.

## Social platforms

Safe zone = share of the frame covered by the app's UI (top, bottom, left, right). Keep text
and faces out of it.

| id | Aspect | Length | Safe zone T/B/L/R | Notes |
|---|---|---|---|---|
| `tiktok` | 9:16 (1:1, 16:9 ok) | 3 s - 10 min (ads up to 10 min, 9-30 s typical) | .07 / .25 / .06 / .13 | Bottom zone grows with long captions (use .34). Burn in captions; most watch with sound but many don't. |
| `instagram-reels` | 9:16 | up to 3 min shown to new audiences; ads/boost <= 90 s | .14 / .35 / .06 / .06 | Min 720 px, 30 fps. Cover frame matters. |
| `facebook-reels` | 9:16 | ads 3-90 s; organic longer | .14 / .35 / .06 / .06 | Mostly muted in feed - captions essential. |
| `youtube-shorts` | 9:16 or 1:1 | <= 3 min (ads: first 60 s) | .07 / .21 / .03 / .09 | Max upload 1080p. Original content is favoured. |
| `youtube` | 16:9 | any | bottom .12 for controls | Use closed captions (SRT) rather than burn-in; no baked letterbox. |
| `linkedin` | 4:5, 1:1, 9:16, 16:9 | 3 s - 30 min; 15-30 s ads | .06 / .10 / .04 / .04 | Under 30 fps advised; short videos loop. |
| `pinterest` | 9:16, 2:3, 4:5, 1:1 | 4 s - 5 min (ads 6-15 s ideal) | .14 / .41 / .06 / .18 | Large bottom/right UI. |
| `x` | 9:16, 1:1, 16:9 | <= 140 s standard | .08 / .20 / .04 / .12 | Feed autoplay muted. |
| `snapchat` | 9:16 | 3-180 s (5-6 s ideal for ads) | .08 / .17 / 0 / 0 | Keep top 150 px and bottom 330 px clear. |
| `instagram-feed` | 4:5 or 1:1 | up to 60 min | none | First frame is the cover. |

Verify: TikTok ads help (ads.tiktok.com/help), Instagram help (help.instagram.com), YouTube help
(support.google.com/youtube), LinkedIn ad specs (business.linkedin.com), Pinterest specs
(help.pinterest.com), X ad specs (help.x.com), Snapchat business help (businesshelp.snapchat.com).

## Marketplaces and stores

General rules across marketplaces: show the real product, no claims you cannot back up, no
competitor names or comparisons, no prices or time-limited offers in evergreen listing video
(prices change), no external URLs or contact details, no third-party trademarks or logos,
captions or on-screen text for muted playback, and the product recognisable in the first seconds.

**Amazon** (ids `amazon-listing`, `amazon-sponsored-brands`, `amazon-sponsored-display`,
`amazon-streaming-tv`):

| Placement | Aspect | Length | Shape that works |
|---|---|---|---|
| Listing (detail page) video - demo | 16:9 (9:16 vertical recut also used) | 30-90 s | Result first, problem context, 2 real demonstrations, scale/detail, top objection answered, close |
| Listing - explainer | 16:9 | 45-75 s | What it is, who it is for, how it works in 3 steps, spec card, use cases |
| Listing - showcase / lifestyle | 16:9 | 30-45 s | Mood open, full reveal, three real settings, details and variants |
| Listing - features and benefits | 16:9 | 45-60 s | Strongest benefit, 4-5 feature blocks (title, proof, benefit), recap grid |
| Listing - comparison | 16:9 | 45-60 s | Same-brand lineup or before/after only; "pick this if..." |
| Listing - unboxing | 16:9 | 45-60 s | What arrives, contents inventory, size, first use |
| Listing - how-to/setup | 16:9 | 60-120 s | Numbered real-time steps, result check, tips |
| Sponsored Brands video (search) | 16:9 (vertical for Store-linked) | 6-45 s, ~15 s | Confirm the search intent in 3 s, product in frame 1, two benefits, brand in the last 20%. Captions; plays muted |
| Sponsored Display video | 16:9 | 6-15 s | Recognisable product in frame 1, one benefit, brand close; the unit adds its own CTA |
| Sponsored Products feature clips | 16:9 | 7-15 s, silent | One feature in use, product fills half the frame, 3-word title |
| Streaming TV | 16:9 | 15-60 s, ~30 s | Product or logo in first 3 s, brand on screen >= 3 s total, movement throughout, ~4 s end card |
| Premium A+ video modules | 16:9 or 4:3 | 6-30 s | Proof in the first 10 s; the module text carries the words |
| Brand Store video / background loop | 16:9 | 6-30 s / 6-12 s loop | Hero film, or a seamless muted text-free loop that survives cropping |

Marketplace creative policies forbid some devices on some ad units (for example strobing or
flash effects); keep wild levels to type and motion there. Check the current Seller/Advertising
help pages before uploading.

**Shopify product media**: 1:1, 16:9, 9:16 or 4:5 to match the theme's gallery; up to ~10 min;
loops well when short. **Etsy listing video**: 5-15 s, sound is removed, match the main photo's
ratio. **eBay**: 16:9, 9:16 or 1:1.

## Other formats

| Format | Shape |
|---|---|
| Website hero loop | 16:9 or 21:9, 6-20 s, muted, seamless loop, no text baked in (the site adds it), small file |
| Landing page explainer | 16:9, 45-120 s, voiceover + captions, question -> answer -> 3 steps -> proof -> CTA |
| Presentation / keynote insert | 16:9, any length, bold type, high contrast, no tiny captions |
| Email | 3-6 s GIF or a thumbnail linking to video; first frame must carry the message |
| Event recap / wedding / party | 9:16 for sharing or 16:9 for screens; 30-75 s; music-led; arrivals -> setting -> people -> the moment -> celebration -> send-off |
| Memory film / tribute | 9:16 or 16:9; 30-90 s; titles that serve the moment; climax held longest; cinematic sound, no UI pops |
| Real estate / place portrait | 9:16 or 16:9; 20-45 s; approach -> arrival -> rooms -> the detail -> invitation |
| Tutorial / how-to | 9:16 30-90 s or 16:9 2-10 min; result first; numbered steps |
| Testimonial / talking head | 9:16 or 1:1; 15-60 s; captions on every line; strongest line first |
| Recruiting / culture | 9:16 or 16:9; 30-60 s; people first, honest moments |
| App / SaaS demo | 16:9 or 9:16; 20-60 s; screen recording zoomed on the part that matters, speed through waits |

## Length guidance

Short-form social: hook in 1 s, total 9-30 s for ads, up to 60 s for value content.
Product pages: 30-90 s. Bumpers: 6 s. TV: 15/30 s. Stories: <= 15 s per segment.
Always deliver the length you promised; do not cut a 30 s plan to 15 s to save time.
