# Brand assets

The mark is a ridgeline with the exit point marked in signal orange. It exists in three
forms, all drawn from the same geometry:

| File | Use |
|---|---|
| `../frontend/public/logo.svg` | The mark on the site. Stroke is `currentColor`, so it works on paper and on granite; the exit dot stays orange in both. |
| `../frontend/public/favicon.svg` | Browser tab. Heavier stroke and a larger dot than the wordmark version — at 16px a hairline disappears and the exit point is the only legible element. |
| `openexits-avatar-512.png`, `openexits-avatar-1024.png` | The GitHub organisation avatar and anywhere else a raster square is required. |

The wordmark (`OPENEXITS`, Archivo Black, letter-spaced) lives beside the mark in
`frontend/src/components/Layout.tsx`. Mark and wordmark are used together in the header and
the mark stands alone as an icon.

## Palette

| Token | Hex | Role |
|---|---|---|
| paper | `#f2f0ea` | background, and the mark's stroke on dark |
| ink | `#1a1c1e` | body text, and the mark's stroke on light |
| granite | `#14161a` | dark surfaces, and the avatar background |
| signal | `#e84e10` | the exit point, and only that — it is not a general accent |

Keeping `signal` exclusively for the exit point is the one rule worth holding to. The moment
it is also used for buttons and links, the mark stops meaning anything.

## Licence

These assets are part of this repository and covered by its MIT licence. Note that a name and
a mark are the assets a project most needs to control: the OpenExits name and this mark are
intended to pass to the non-profit association when it is constituted, and a trademark filing
is on the Phase 2 checklist. Reuse the mark to refer to OpenExits, not to badge something else
as OpenExits.
