# Kogi roots explorer

The About page includes a decorative sketch of Kogi and an interactive SVG explorer with place panels. The landing-page hero renders the same geometry as an oversized inline map: West and Central extend underneath the copy on wide screens, while Kogi East remains selectable. A hero selection only changes the area's fill, outline, and label weight. Clicking again or pressing Escape clears it. It never opens a preview, changes the URL, fetches content, or writes to the database. A separate “Explore our roots” link opens the full About explorer.

The hero keeps a single tab stop in the map; arrows move focus, Enter/Space select, and Home/End jump to the first/last area. Without JavaScript it remains a labeled static map, with no dead button controls. On smaller layouts the map stacks below the copy; mobile focuses Kogi East to keep names legible. The hero search form remains removed. No new map dependencies or migrations are required.

## Geometry and licence

- Original source: **GRID3**, 2022 local government and state boundaries, distributed by **geoBoundaries gbOpen**.
- Licence: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
- Metadata: [NGA ADM2](https://www.geoboundaries.org/api/current/gbOpen/NGA/ADM2/), [NGA ADM1](https://www.geoboundaries.org/api/current/gbOpen/NGA/ADM1/).
- Pinned upstream revision: `wmgeolab/geoBoundaries`, `9469f09`.
- Source files:
  - `https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/NGA/ADM1/geoBoundaries-NGA-ADM1_simplified.geojson`
  - `https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/NGA/ADM2/geoBoundaries-NGA-ADM2_simplified.geojson`
- Adaptations: subset to Kogi's 21 named LGAs using a geographic guard to disambiguate names, equirectangular projection with longitude scaled by central latitude, rounded SVG coordinates, visual restyling, and geographic-centroid labels. Boundaries are illustrative, not suitable for navigation, surveying, or legal decisions.
- Rebuild offline: `python scripts/build_kogi_map.py PATH_TO_ADM1_GEOJSON PATH_TO_ADM2_GEOJSON`.
- Outputs: `main/data/kogi_boundaries.json`, `static/images/kogi-sketch.svg`, `static/images/kogi-labeled.svg`, and `static/images/kogi-labeled-east.svg`. The labeled SVGs share the About map's paths, regional fills, and label locations, and contain no links or event handlers. The build uses only the Python standard library; downloads and geometry packages are not runtime dependencies.

Attribution is visible beside the interactive map and in its expandable notes. The decorative SVG also includes attribution metadata. The uploaded screenshots provided design context; they were not used as a source of precise boundaries.

## Editorial scope and sources

Highlighting follows the **nine administrative LGAs of Kogi East**, not a claim that all residents speak Igala, that a single language defines any LGA, or that no Igala communities exist outside the district. Bassa receives explicit multilingual context. Other 12 LGAs remain visible as geographic context.

- District membership: [Kogi State Gazette, 2015, page 4](https://kogistate.gov.ng/wp-content/uploads/LOCAL-GOVT.pdf).
- Headquarters: [INEC Kogi directory](https://www.inecnigeria.org/wp-content/uploads/2022/09/KOGI-STATE.pdf), cross-checked against the [Kogi State Development Plan 2024–2056](https://kogistate.gov.ng/wp-content/uploads/Kogi-State-Development-Plan-2024-2056.pdf).
- Kogi's ethnic and language diversity: state development plan above. The highlight deliberately avoids asserting exact language boundaries.
- Idah's historical role and River Niger location: [The Igala Kingdom, J. S. Boston, 1968, National Library of Nigeria repository](https://nigeriareposit.nln.gov.ng/items/f21921ac-6201-4dde-9deb-ac35781ddc5a), with the seat of the Attah cross-checked against Kogi government reporting.
- Dekina towns: [Kogi government ward directory](https://kogistate.gov.ng/official-list-of-elected-local-government-chairmen-and-ward-councillors-in-kogi-state-following-the-october-17-2026-elections/).
- Relative compass locations in other short overviews are descriptions of the supplied geometry, not independently asserted cultural histories.

Published HistoryArticle titles are matched on whole place names (including common separators for Igalamela-Odolu), with up to two links per place. Labels say **Stories mentioning [place]**, not that the article has verified geographical provenance. Pending submissions are never queried. Empty results invite a contribution; no records or counters are invented. The single bounded query returns at most 100 candidates for all nine profiles; no new database writes occur when browsing.

## Interaction and accessibility

- Click/tap an area, use the native area selector, or step with Previous/Next.
- The enhanced SVG uses one tab stop. Arrow keys move focus between areas; Home/End go to first/last; Enter/Space select. A visible dashed focus outline and pressed states supplement colour.
- Selection updates the panel, map, selector, live-region announcement, and URL. Back/Forward restores selections.
- On small screens the map initially focuses Kogi East for legible labels; Full state restores context. Desktop starts with the full state. Users can switch either view themselves.
- Native GET forms and SVG destination links work without JavaScript. Stepping/zoom controls are hidden until enhancement succeeds.
- Decorative sketch is excluded from the accessibility tree. Motion respects reduced-motion preferences. All runtime assets are local.

Run `python manage.py test main.test_kogi_map --settings=igalapedia.test_settings --noinput` for geometry, server rendering, graceful fallback, selection validation, real content matching, and query-count checks. Browser checks additionally cover map clicks, dropdown selection, keyboard control, stepping, history restoration, zoom, and mobile layout.
