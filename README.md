# Peonies CSS

A bouquet of pink peonies that grows, blossoms and sways in the wind — built entirely
with HTML and CSS. **No JavaScript, no SVG, no images, no canvas.** Every petal is a
`<div>`; every movement is a `@keyframes`.

Open `index.html` in a browser. That's it — there is nothing to install or serve.

![the bouquet in full bloom](docs/preview.png)

## What it does

A 28-second loop that restarts itself without a line of script:

| time | |
|---|---|
| 0.3s | the paper wakes and pigment washes bleed outwards |
| 0.2s | stalks grow up through the bunch, the ribbon cinches round them |
| 1.5s | buds ride out of the bundle on their stems, leaves unfurl |
| 2.7s | eight peonies open one after another — outer petals first, the centre bloom last |
| 11s | full bloom: a travelling breeze, falling petals, drifting light |
| 26s | everything dissolves back into the paper and the cycle begins again |

316 petals (632 hinged panels) in 8 blooms, all gradients and 3D transforms.

## How it works

**The petals.** A petal is two hinged panels — a lower cup and an upper lip that rolls
back as it opens. The panels are siblings, not nested: nesting two animating 3D
transforms makes the browser re-solve the whole stack every frame. They are emitted
already sorted back-to-front, so the browser never has to depth-sort ~600 intersecting
planes.

**The breeze.** One multi-harmonic gust drives four layers at once — the whole held
bunch leaning about the hand, each stem flexing about the ribbon, each flower head
nodding, each leaf wagging — phase-shifted by horizontal position so the wave visibly
travels left to right. A flower and its stem share the *same* keyframe and pivot on the
ribbon, so a bloom can never drift off its stem.

**The loop, without script.** `<body>` runs a clock that flips a registered custom
property (`@property --loop`) for a moment each cycle. A style query
(`@container style(--loop: 1)`) reacts by taking the scene out of the display tree, and
putting it back restarts every animation inside it from zero.

**Why it stays smooth.** Chrome restyles every element that has a running animation on
every frame, even when the animation is composited. So anything that moves is kept
trivial to restyle: literal numbers only, no `var()` or `calc()`, with all the expensive
colour and lighting maths parked on a static child. Everything animated is a transform
or an opacity — no filters, no blend modes.

On a 2019 Intel MacBook Pro (integrated GPU, Retina) it holds 60fps once settled and
dips to 30–40fps at the busiest moment of the bloom.

## Building

`index.html` and `peonies.css` are **generated**. Don't edit them by hand — edit the
source and regenerate:

```bash
cd src && python3 build.py
```

- `src/build.py` — flower positions, sizes, poses and timing (the `FLOWERS` table),
  petal geometry, the breeze, and the paper grain. Also `CREDIT_NAME`.
- `src/peonies.src.css` — everything that isn't computed per element.

The build is deterministic (fixed random seed): the same source always produces byte
-identical output.

## Browser support

Developed and measured in Chrome. Uses `@property`, style queries, `color-mix()`,
`linear()` easing and trigonometric CSS functions. Where style queries are missing the
sequence plays once and the ambient motion keeps running, rather than looping.

Respects `prefers-reduced-motion`: readers who ask for less motion get the finished
bouquet, perfectly still.

## Licence

[MIT](LICENSE) © 2026 Abhyudh

## Credits

Made by [Abhyudh](https://github.com/AbhyudhPSS). Modelled on a watercolour bouquet
reference.
