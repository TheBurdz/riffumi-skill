# Assets: the user's material, stock, generated, fonts - and licences

## The user's own material comes first

- Product photos, logos, past ads, clips, screen recordings, voice notes, brand guides.
- For a product page (a marketplace listing, a store page), open it and collect the gallery
  images at the largest size, the title, key benefits, rating and review count. If the page
  blocks scripts, use a browser tool or ask the user for the images.
- Inspect everything with `inspect_media.py` before planning. Note: orientation, resolution
  (photos under ~900 px on the long side look soft when full screen - use them on cards or
  smaller, or upscale with a tool you have), usable moments, text already baked into images
  (avoid repeating it on screen).
- Product images often carry their own headline text. Crop around it, or use the image as a
  card while your headline says something different.

## B-roll: the default backbone

Moving footage is what makes a cut look produced. Product photos with animated text alone read as a
slideshow. So unless the user's own clips cover the beats (or b-roll would not fit the subject - see
SKILL.md step 4), every video gets b-roll.

**Plan it per beat.** For each beat that is not the product itself, write what the shot must show
and 2-3 search phrases:

| Beat job | What b-roll shows | Example searches |
|---|---|---|
| Hook / world | The setting the product lives in, at its most appealing | "neon bedroom night", "cozy kitchen morning light" |
| Problem | The frustration, close and honest | "tangled cables desk", "messy pantry shelves" |
| Feeling / payoff | People enjoying the outcome | "friends laughing living room party", "woman relaxing sofa evening" |
| Feature context | The kind of use the feature enables | "hands typing gaming keyboard rgb", "person cooking pan close up" |
| Energy / rhythm | Motion that cuts well on the beat | "dancer neon lights", "city traffic night timelapse" |
| Place | Where the story happens | "mountain lake sunrise drone", "small town main street" |

**Choose well.** Look at a contact sheet of every candidate (`inspect_media.py`), pick the clip whose
best 1-3 seconds match the beat, note the exact in-point. Prefer real-looking footage over glossy
corporate stock; prefer motion (camera or subject) over static shots; avoid clips where faces are the
main subject unless the beat is about people; reject anything with a visible logo or branded product.

**Make it feel shot together.** One grade for every clip (`vivid`, `warm`, `teal-orange`...), matching
camera energy (all handheld or all smooth), cuts on the beat, transitions from the same family, and the
product's own colour picked up in overlays or type so stock and product share a palette.

**Balance with the product.** B-roll sets the scene; the real product (cards, cutouts, the user's
photos and clips) owns the hook reveal, the feature proofs and the end card. Never more than two stills
in a row; never a b-roll shot that implies the product does something it does not.

**When stock has nothing that fits**, generate the clip (text- or image-to-video, 3-8 s, same style
block on every prompt) or ask the user for a quick phone clip. Do not drop the beat to stills by default.

## Stock footage and photos

Use stock for the b-roll beats - not to fake the product. Never present stock people as the brand's
customers, reviewers or staff; never use a clip with a visible logo, trademark or recognisable
branded product.

| Source | What | Licence (verify on the site) | Notes |
|---|---|---|---|
| Pexels | video + photos | Pexels License: free commercial use, no credit required | Largest free library. **No key needed**: `stock_search.py` builds the search pages, you read them, `--get` downloads through the public link. |
| Pixabay | video, photos, music, sfx | Pixabay Content License: free commercial use, no credit | Official API when the user gives a key: `stock_search.py --pixabay-key ...`. |
| Mixkit | video, music, sfx | Mixkit free licences (stock video, music, sfx) | Direct downloads from the site; rate-limits heavy use. |
| Coverr | video | free commercial use | Good lifestyle b-roll; download by hand. |
| Unsplash | photos | Unsplash License | Photos only. |
| Videvo, Vecteezy, Storyblocks | mixed | per-file licences, some paid | Check each file. |

### Getting stock clips: the pexels.com route (no key)

Pexels publishes a filtered search page and a public "Free download" link for every clip, so the
whole route works with the web tools you already have:

```bash
python3 scripts/stock_search.py --plan broll_plan.json --out broll.json
# open each "search" URL with your web tool; open the 2-3 clip pages that look right
# (creator, duration, dimensions, thumbnail); choose one per beat plus a backup; then:
python3 scripts/stock_search.py --get "hook=pexels:3209828@Pressmaster,payoff=pexels:857195@Creator" --to broll --sheet broll_sheet.jpg
```

The search page takes the site's own filters: `orientation`, `min_duration`/`max_duration` in
seconds, `people_count=0` for product and place shots with nobody in them, `resolution_name=1080p`,
`page=2` for more. Keep queries to plain nouns; two or three words beat a sentence. `--get` follows
the public download link (1080p rendition first, then the original), logs source, licence, page
and creator in `broll/manifest.json`, and draws the downloads on one sheet for the eye check.

**How many to look at.** Open enough clip pages to have a real choice: two or three per beat, one
pick and one backup. Judge the thumbnail and the description against the beat, never the title.
If a beat is weak, add two new phrases (`"alt"` in the plan): different nouns, a different angle
(close-up, top-down, silhouette), a different light (neon, golden hour, night).

**Keyed route (optional).** If the user hands you a Pexels or Pixabay API key, pass it as
`--pexels-key` / `--pixabay-key`: the script searches the APIs, ranks 15 results per phrase, draws
the candidates on a sheet, and `--pick` downloads your choices. The script takes keys only from
those flags, never from the environment or a file.

**pexels.com does not answer from this host.** Ask the user to open the search in their browser and
paste clip links; `--get` and `fetch_asset.py` take clip pages, download links or bare ids. Or use
the user's own footage, composites and generated shots. **Never scrape the sites' pages, use proxies
or work around bot protection.**

### Search well

Concrete nouns of what the shot shows + light + action ("hands pouring coffee close up",
"neon bedroom gaming setup night", "friends dancing at house party"), orientation matching the
canvas, and a minimum length around the beat length. Prefer clips with motion, real-looking light
and no readable brands. Titles and tags lie - choose from the pictures.

Every download is logged in `<folder>/manifest.json` (source, licence, creator, page). Name
creators in the delivery note when convenient and wherever a licence asks for it.

## Generated stills and clips

When an image or video model is available (see `routing-and-generation.md`):

- Good uses: backgrounds and sets, lifestyle scenes, abstract textures, title art, problem
  scenes, establishing shots, transitions, product-in-context **mockups clearly based on the real
  product photo**.
- Never change what the product is, what it includes, its size or its colours. Never generate
  fake results, fake before/after evidence, fake customers giving testimonials, or real people.
- Keep a consistent look across generated shots: same style words, palette, lens, light, and a
  reference image when the model accepts one.
- Disclose AI-generated people or scenes where the platform requires it (many ad platforms and
  social apps do).

## Fonts

All families on Google Fonts are open-licence (SIL OFL / Apache) and fine for commercial video.
`get_fonts.py "Family:weight"` downloads TrueType files into `fonts/`. A brand's own licensed font
can be used if the user supplies the file and has the rights.

## Music and sound

See `sound-design.md`. Same rule: the user's licensed library first, then no-credit free
libraries, then CC-BY with the credit placed where the user agrees.

## The manifest

`assets/manifest.json` (written by `fetch_asset.py`) holds file, url, page, source, licence,
creator, kind and date for every downloaded asset. Keep it with the project and summarise it in
the delivery note: which stock clips and music were used and under which licence.
