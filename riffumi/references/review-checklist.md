# Review checklist

Run `preflight.py spec.json` first and fix every FAIL. For bold and wild work the production score
must clear its floor (65 bold, 80 wild); report the score with the delivery. Then render a contact sheet
(`--sheet 12`) and full-size stills (`--stills`) at the busiest moments - the hook, each text
beat, the reveal, the end card - and actually look at them. Only then render the preview or
final. One full render per request is the goal.

## Promise
- [ ] Length matches what was promised (within ~10%); the plan was not quietly shortened.
- [ ] The concept is visible: someone watching could say the idea back.
- [ ] The signature device appears early and pays off.
- [ ] Platform aspect, length and safe zones are right for where it will be posted.

## First seconds
- [ ] Frame 0 is fully composed (no fading-in hook text) and works as a thumbnail.
- [ ] The subject or the question is on screen within 1 s.

## Text
- [ ] Every claim, number, rating, price, review and quote comes from the facts list.
- [ ] Each line stays on screen long enough (~0.35 s + 0.22 s per word).
- [ ] Readable on the busiest frame (stroke, shadow or panel); not over faces or the product.
- [ ] Inside the safe zone; nothing important under platform UI.
- [ ] Spelling, brand names and capitalisation checked.

## Picture
- [ ] Moving footage (the user's clips or b-roll) carries most non-product beats; no more than two
      stills in a row. If the cut has little or no b-roll, the plan states why.
- [ ] B-roll matches: one grade, similar camera energy, cut on the beat, no logos, nothing implying
      the product does what it does not.
- [ ] No unintended black bars, stretched footage, soft upscales, watermarks, or logos/trademarks
      from stock clips.
- [ ] Holds vary; the key moment holds longest; the end card lasts >= 1.5 s.
- [ ] Camera moves and transitions vary; no effect soup.
- [ ] Cutouts are clean (no white fringe or missing parts) - look at them full size.
- [ ] Generated shots keep the real product unchanged.

## Sound
- [ ] Music present (unless declined), licensed, matching the energy, ending cleanly (fade or
      phrase end).
- [ ] Cuts land on beats where intended; the reveal lands on the drop.
- [ ] Voice intelligible, music ducked under it; sound effects sparse and on the moments that matter.
- [ ] Final level around -14 LUFS (render.py does this).

## Delivery
- [ ] File plays start to finish with sound; duration and resolution as expected.
- [ ] Delivery note: what it is (concept + device), where it fits, sources and licences of
      stock and music (credits where required), and 1-2 ideas for a next version.
