# Labeling rules (paste into Roboflow job instructions)

**Classes (exact spelling):** mask, no_mask, gloves, no_gloves. `person` is optional: the backend tracks people with a stock model when our labels have none. Hairnet is not labeled (`docs/decisions.md` #8).

| Class | Box around |
|---|---|
| person | The whole visible body |
| mask / no_mask | Nose to chin |
| gloves / no_gloves | Each hand, one box per hand |

1. **Tight boxes.** The edge touches the object, not the background.
2. **Label every instance.** Two visible hands = two hand boxes. A missed box teaches the model that the object is background.
3. **Partly visible:** label it if you can clearly tell the class. If you have to guess, skip it.
4. **Can't see it at all → no box.** Hands behind the counter or a face turned away get nothing.
5. **Mask under the nose = no_mask.**
6. **When in doubt, ask in the group** and add the decision here. Two people labeling the same thing differently hurts more than a smaller dataset.

## Decisions log

| Date | Question | Decision |
|---|---|---|
| 2026-11-24 | Is uniform checked? | No. Scope is gloves, hairnet, mask only. Don't label torsos. |
| 2026-11-25 | Is hairnet checked? | No. Scope is gloves and mask only. Don't label heads. |
