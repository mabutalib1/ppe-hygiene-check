# Manual checklist → CV checks

| Manual item (photo required) | Automated check | Camera region | Output |
|---|---|---|---|
| Nails | Fingertip crops → classifier (`ok`/`long`/`polish`/`dirty`) | Hands, close-up at check-in | PASS/FAIL + hand photo |
| Hair | Head crop → classifier (`covered`/`exposed`) | Head | PASS/FAIL + head photo |
| Facemask | Detector: `mask` / `no_mask` / `incorrect_mask` | Face | PASS/FAIL + face photo |
| Hairnet | Detector: `hairnet` / `no_hairnet` | Head | PASS/FAIL + head photo |
| Gloves | Detector: `glove` / `bare_hand`, need 2 gloved hands | Hands | PASS/FAIL + hand photo |
| Uniform | Torso crop embedding vs venue reference photos | Torso | PASS/FAIL + body photo |

Every item can also return `NEEDS_REVIEW` when confidence is low.

## Check-in flow

1. Employee selects their name/ID (or scans a badge).
2. Faces the camera → frame captured for mask / hairnet / hair / uniform.
3. Shows both hands, palms down → frame captured for gloves / nails.
4. Report generated in the same 6-field format as the manual form.
