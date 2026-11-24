# Labeling rules (paste into Roboflow job instructions)

**Classes (exact spelling):** person, hairnet, no_hairnet, mask, no_mask, gloves, no_gloves, uniform, no_uniform

| Class | Box around |
|---|---|
| person | The whole visible body |
| hairnet / no_hairnet | The whole head |
| mask / no_mask | Nose to chin |
| gloves / no_gloves | Each hand, one box per hand |
| uniform / no_uniform | Torso, shoulders to waist |

1. **Tight boxes.** The edge touches the object, not the background.
2. **Label every instance.** Two visible hands = two hand boxes. A missed box teaches the model that the object is background.
3. **Partly visible:** label it if you can clearly tell the class. If you have to guess, skip it.
4. **Can't see it at all → no box.** Hands behind the counter or a face turned away get nothing.
5. **Mask under the nose = no_mask.**
6. **Hairnet with a fringe of hair showing = hairnet.** Hair fully visible = no_hairnet.
7. **Uniform = white chef coat or white apron.** Anything else = no_uniform.
8. **When in doubt, ask in the group** and add the decision here. Two people labeling the same thing differently hurts more than a smaller dataset.

## Decisions log

| Date | Question | Decision |
|---|---|---|
| | | |
