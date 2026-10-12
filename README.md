# Peonies CSS

A bouquet of pink peonies that grows, blossoms and sways in the wind, with waves
rolling by behind it — built entirely with HTML and CSS. **No JavaScript, no SVG, no
images, no canvas.** Every brush stroke is an element cut to shape with `clip-path`;
every movement is a `@keyframes`.

Open `index.html` in a browser. That's it — there is nothing to install or serve.

![the bouquet in full bloom](docs/preview.png)

## What it does

A 28-second loop that restarts itself without a line of script:

| time | |
|---|---|
| 0.3s | the paper wakes, pigment washes bleed outwards, and waves well up behind |
| 0.2s | the cut stems grow up from their ends and the ribbon wraps round them |
| 1.5s | buds ride out of the bundle on their stems, each with its small leaves |
| 2.7s | eight peonies open, the middle one first — outer petals first, the heart last |
| 11s | full bloom: every petal, leaf and stem moving on its own in the breeze; falling petals, drifting light |
| 26s | everything dissolves back into the paper and the cycle begins again |

8 blooms, 13 leaves, a ribbon and seven cut stems, painted with 991 flat washes.

## How it works

**The picture.** The bouquet is traced from a watercolour. A watercolour is built up in
washes, and so is this: every shape (a petal, a leaf, the ribbon) is its whole outline
in its body colour, then the darker passages laid over it, then the lighter ones. Each
wash is one element with a `clip-path: polygon(…)` and a flat pigment. The outlines,
places and pigments are data, in `src/shapes.py`.

**The bloom.** A bloom is its silhouette with its petals laid over it. Folded, a petal
stands up from the page about the point the bloom opens from, turned a little way round
it; a bud is the whole bloom, small, with every petal folded like that. Opening is the
bloom growing while its petals lie down one after another, outermost first. Each leaf
lives inside the bloom it grows beside, so it rides out with that bud and grows with it.

**The breeze.** One multi-harmonic gust drives four layers at once — the whole held
bunch leaning about the hand, each stem flexing about the ribbon, each flower head
nodding, each leaf wagging — phase-shifted by horizontal position so the wave visibly
travels left to right. A flower and its stem share the *same* keyframe and pivot on the
ribbon, so a bloom can never drift off its stem.

**Nothing is quite still.** It is a picture made of pieces, and it should look like one.
So each of the 54 petals breathes on its own beat about the heart of its bloom, each leaf
wags and turns a little edge-on, each cut stem sways from its own point under the ribbon,
and a soft light travels up and down the satin. Two things keep that from tearing the
picture apart. Every shape carries on underneath its neighbours, so when two of them
slide over each other no gap opens between them. And under the petals of each bloom lie
two more washes, in the tones of its lit faces and of its creases: wherever two petals
part for a moment, what shows between them is close to the tone of what lies round it.

**The waves.** Behind the bouquet, four washes with a rolling edge drift across the page,
alternately left and right, the nearer ones shorter and quicker. Each is a strip one
wavelength wider than the page, with the swell cut along its top; it slides sideways by
exactly one wavelength and starts again, which cannot be seen.

**The loop, without script.** A registered custom property (`@property --loop`) is
flipped for a moment at the end of each cycle, while a paper-coloured veil covers the
scene. A style query (`@container … style(--loop: 1)`) reacts by switching the one-shot
animations off, and when the flip ends they start again from zero. Nothing is removed
from the page, so nothing is laid out or painted a second time. For the first half hour
each flip is its own one-shot animation with a delay, which costs nothing while it
waits; after that an ordinary repeating clock takes over.

**Why it stays smooth.** Everything animated is a transform or an opacity — no filters,
no blend modes — so the compositor can run all of it. The rest is about leaving it alone:

- *Nothing that moves has a `clip-path`.* An outline on an animated element is an
  offscreen pass on every frame. The washes are still children of the few elements that
  do move (a petal, a leaf blade), so every outline is cut exactly once, when its parent
  is first painted. Some 200 elements move; the 991 washes are along for the ride.
- *The main thread sleeps.* Starting or ending an animation wakes it, and it then
  restyles every running animation and commits, which stalls the compositor. So every
  one-shot is padded to start and end on a half-second grid, and the petals carry
  literal numbers only: no `var()` or `calc()` to resolve.
- *A petal is painted once.* The petals rest folded and are opened by an animation that
  fills forwards, and nothing above a bloom changes in a way that makes the browser
  repaint its layers.

Measured in Chrome on a 2019 Intel MacBook Pro (integrated GPU, 1440×900 at 2x): the
full bouquet in the breeze runs at a steady 60fps with no dropped frames; the bloom and
the restart each drop a handful of frames over their busiest eight seconds. The one
rough moment is the first second after the page loads, while the layers are rasterised
for the first and only time.

## Building

`index.html` and `peonies.css` are **generated**. Don't edit them by hand — edit the
source and regenerate:

```bash
cd src && python3 build.py
```

- `src/shapes.py` — the picture: every outline, where it sits, and its pigments.
- `src/build.py` — the stacking order, the timing (the `FLOWERS` table), the folding
  of the petals, the breeze and how far each kind of piece moves in it, the waves
  (`WAVES`), and the paper grain. Also `CREDIT_NAME`.
- `src/peonies.src.css` — everything that isn't computed per element.

The build is deterministic (fixed random seed): the same source always produces byte
-identical output.

## Browser support

Developed and measured in Chrome. Uses `clip-path`, `@property`, style queries,
`color-mix()`, `linear()` easing and the individual transform properties. Where style
queries are missing the sequence plays once and the ambient motion keeps running, rather
than looping.

Respects `prefers-reduced-motion`: readers who ask for less motion get the finished
bouquet, perfectly still.

## Licence

[MIT](LICENSE) © 2026 Abhyudh

## Credits

Made by [Abhyudh](https://github.com/AbhyudhPSS). The bouquet is traced from a
watercolour painting of peonies, used as the reference.
