# Sound design

Silent video loses viewers. Music is part of the first cut, not a finishing touch.

## Music

**Source order**
1. The user's own track or a library they already pay for (Epidemic Sound, Artlist, Musicbed,
   Soundstripe, PremiumBeat...). Ask which they use before suggesting free ones; never steer a
   user away from a source they have.
2. Free for commercial use, no credit required: Mixkit music, Pixabay Music, YouTube Audio
   Library (tracks marked "no attribution"), Free Music Archive tracks under CC0.
3. CC-BY tracks (Free Music Archive, Incompetech, ccMixter): only when the credit can go
   somewhere (end card, caption, description) - ask where first.

Never use commercial songs, a trending sound you do not have rights to, or a track "found on
YouTube". Do not synthesise beeps as a stand-in for music; if no suitable track can be had,
say so and offer the cut without music or with the user's file. Record source and licence of
every track (`fetch_asset.py` writes `assets/manifest.json`).

**Choosing**: match tempo and energy to the cut (120-150 BPM for energetic social, 80-100 for
lifestyle, ambient/piano for memory and premium). Check the length covers the video, with a
real ending or a section you can fade.

**Beat sync** with `beats.py track.mp3`:
- Set `spec.beat.bpm` and trim the track with `music.start` = `offset` (or `downbeat_offset`
  to start on a bar). Then scene lengths in whole beats (`"beats": 2/4/8`) cut on the grid.
- Half and double tempo fit the same drums; choose the one that feels right for the cut density
  (fast edits use the faster count).
- Put the reveal on `drop` (the biggest energy rise) when the track has one: start the music
  earlier (`music.start` = drop - reveal time) so it lands.
- End: fade out 1-2 s, or end on a natural phrase end (multiples of 4 or 8 beats).

**Levels**: music alone -> it is the mix; under voiceover -> duck it (`music.duck`, default on)
and keep it around -18 to -12 dB below speech. Final mix is levelled to -14 LUFS (`loudness`),
the common streaming/social target; true peak -1.5 dB.

## Voiceover

- The user's recording, a voice tool they have (text-to-speech services, voice cloning they own
  rights to), or none. Never imitate a real person's voice without their permission.
- Write for the ear: short sentences, one idea each, ~2.5 words per second for ads, slower for
  stories. Time scenes to the voice, not the other way round.
- Add captions for every spoken line (`captions` layer from `transcribe.py`).

## Sound effects

Decide whether the edit wants them at all. Yes: product demos, social cuts, hard transitions,
animated text, counters. No: quiet testimonials, memory pieces, when the user said no.

Palettes - pick one per piece:
- **cinematic**: air, swells, shimmers, a riser into the close. Never pops.
- **interface**: soft pops, clicks, dings, a swish on slides. Demos, apps, social.
- **comic**: zips, boings, a bonk on a number, a zap on a flash. Playful pieces only.
- **foley / natural**: the product's own sound (pour, click, zip) - often the best choice.

Density: at most 2 per 10 s (sparse), 4 per 10 s (normal), more only on request; never two within
0.5 s; place them on beat frames and on the moments that matter (hook text, a number, the reveal,
the end card). Do not add whooshes and thuds to still photos pretending to be action.

Sources (free for commercial use): Mixkit sound effects, Pixabay sound effects, freesound.org
(check each file's licence - CC0 is simplest), the user's own recordings.

Add with `"sfx": [{"src": "sfx/pop.wav", "at": "8b", "gain_db": -8}]`.

## Natural sound

Clip audio (`"audio": true` on a clip scene) for speech, product sounds and atmosphere. It is
dropped automatically for reversed, frozen or ramped scenes and extreme speeds; put music under
those. Fade edges are added to avoid clicks.
