[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/1462919984-byte/news-image-20261122/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/1462919984-byte/news-image-20261122/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

# The World in One Day

A make.fun news-image entry: one newspaper front page summing up the world
news of Sunday 22 November 2026, drawn entirely in code.

`main.py` renders a single 1024 by 1024 PNG with the Python PIL library. The
page uses a pale paper background, dark ink and one deep red accent, and is
built strictly from PIL shapes — rectangles, ellipses, lines, arcs and
polygons — plus PIL's built-in default font at several sizes. No font files,
network access, clock reads or randomness are used anywhere, so running the
program twice produces byte-identical output.

## Layout, top to bottom

- A top bar with the page name and the story/region count.
- A large centred masthead: **Sunday 22 November 2026**.
- An italic sub-headline naming the four lead stories.
- A double horizontal rule.
- A strip of six big key-figure numbers with short labels.
- Seven coloured region tabs (counts summing to 36).
- Four large feature panels, then two rows of five smaller panels: 14 feature
  stories in all.
- A simple shape-built world map with numbered pins for the 14 features,
  beside two columns of one-line briefs numbered 15 to 36.
- A boxed DATE CHECK strip listing big news from earlier days so it is never
  mistaken for 22 November news.
- A footer line naming the sources.

Each of the 14 feature panels contains a small original drawing, a bold red
banner across the top of the drawing, a kicker (number, place, topic), a
headline and a two-or-three-line summary that names its source in brackets.
All text is measured and wrapped before it is placed so nothing spills over a
panel edge.

## Running

```bash
MAKEFUN_OUTPUT_DIR=/some/folder python3 main.py
```

The finished image is written as `entry.png` in the directory named by the
`MAKEFUN_OUTPUT_DIR` environment variable, or in `/output` when that variable
is not set.
