"""
Generate the demo Takeout data committed under backend/fixtures/.

Run:  python scripts/generate_demo_data.py

The demo has to survive the same statistical thresholds as real data -- MIN_SUPPORT of
15, MIN_LIFT of 1.5, the seasonal three-month span rule. Sprinkling random watches
produces a Wrapped where every insight card reads "no patterns found", so the generator
plants specific, defensible signals:

  personality   a night-owl clock, weighted so the 0-5 slot beats every other slot
                once measured against its own share of the 24 hours
  co-occurrence themed sessions (music / science / tech), which is how real viewing
                clusters -- you do not watch one lofi channel, you watch three
  seasonal      one channel present all year but spiking in December
  day habit     a Sunday science ritual
  time habit    a morning tech ritual
  opener        one channel that reliably starts a session
  rewatch       a lofi radio stream played many times over

The output is a real Takeout ZIP, with history rendered as HTML -- the format Google
actually produces by default -- so the demo exercises the whole path: ZIP member
location, format detection, the HTML connector, timestamp resolution, year filtering,
preprocessing and card generation. Serving pre-parsed JSON would skip most of that and
let the demo keep working after the parts it is meant to showcase had broken.

Output is deterministic: same SEED, byte-identical fixtures.
"""

import csv
import io
import json
import os
import random
import zipfile
from datetime import datetime, timedelta
from html import escape

SEED = 20251
YEAR = 2025
TARGET_WATCHES = 2500

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "..", "fixtures")

# Session start slot -> weight. Tuned so that after sessions run their course, the
# measured 0-5 share beats every other slot's share-of-hours. Sessions starting at 23
# spill past midnight, which is what actually creates a night owl.
START_SLOT_WEIGHTS = [
    ((0, 4), 32),     # genuinely after midnight
    ((23, 24), 16),   # starts before midnight, spills past it
    ((18, 20), 14),
    ((7, 10), 20),    # the morning tech ritual
    ((13, 18), 18),
]

THEMES = {
    "music": [
        ("Lofi Girl", "UCSJ4gkVC6NrvII8umztf0Ow"),
        ("Chillhop Music", "UCfSUheoljDlGDjerRylO4Nw"),
        ("ODESZA", "UCwPCwqB2CqDdnBqmSJIcNRQ"),
    ],
    "science": [
        ("Kurzgesagt", "UCsXVk37bltHxD1rDPwtNM8Q"),
        ("Veritasium", "UCHnyfMqiRRG1u-2MsSQLbXA"),
        ("Mark Rober", "UCY1kMZp36IQSyNx_9h4mpCg"),
    ],
    "tech": [
        ("MKBHD", "UCBJycsmduvYEL83R_U4JriQ"),
        ("Linus Tech Tips", "UCXuqSBlHAE6Xw-yeJA0Tunw"),
        ("Fireship", "UCsBjURrPoezykLs9EqgamOA"),
    ],
    "craft": [
        ("Adam Savage's Tested", "UCiDJtJKMICpb9B1qf7qjEOA"),
        ("Steve Mould", "UCdC0An4ZPNr_YiFiYoVbwaw"),
        ("Practical Engineering", "UCMOqf8ab-42UUQIdVoKwjlQ"),
    ],
}

OPENER = ("Daily Dose Of Internet", "UCdC0An4ZPNr_YiFiYoVbwaXX")
# The opener appears in a third of all sessions, so it needs as many distinct titles as
# any other channel -- three of them would make it the "most rewatched" video by default.
OPENER_SUBJECTS = [
    "A Cat Discovers Gravity", "The World's Fastest Peeler", "A Very Confident Goose",
    "Sand Falling In Slow Motion", "A Robot Learns To Walk", "The Perfect Domino Run",
    "An Unusually Polite Crow", "A Wave Freezes Mid-Air", "The Loudest Quiet Room",
    "A Dog Meets A Mirror", "Lightning In Reverse", "A Bridge Made Of Paper",
]
SEASONAL = ("Advent of Code Solutions", "UCseasonalXXXXXXXXXXXXXX")

LONG_TAIL_TOPICS = [
    "how to", "explained", "review", "documentary", "tutorial", "highlights",
    "interview", "deep dive", "reaction", "top 10", "unboxing", "analysis",
]

# Titles are built from templates x subjects rather than a short fixed list. With only
# a handful of titles per theme, 600 watches of that theme means the same video appears
# ~75 times and the "most rewatched" card reports nonsense. This yields a few hundred
# distinct titles per theme, so repeats happen at a believable rate.
TITLE_TEMPLATES = {
    "music": ["{} Mix", "{} Session", "{} Radio", "{} — Extended Set"],
    "science": ["Why {} Happens", "The Truth About {}", "{}, Explained", "What If {}?"],
    "tech": ["{} Review", "I Tried {} For A Week", "{} In 100 Seconds", "The Problem With {}"],
    "craft": ["One Day Build: {}", "How {} Actually Works", "Restoring {}", "Testing {}"],
}

TITLE_SUBJECTS = {
    "music": [
        "Rainy Day Jazz", "Sunset Drive", "Deep Focus", "Midnight City", "Ambient Study",
        "Late Night Piano", "Coffee Shop", "Winter Lights", "Slow Mornings", "Neon Streets",
        "Quiet Hours", "Rooftop Dusk", "Analog Dreams", "Paper Planes", "Blue Hour",
    ],
    "science": [
        "Black Holes", "The Fermi Paradox", "Cosmic Rays", "The Immune System",
        "Antimatter", "Deep Sea Vents", "Neutron Stars", "Gut Bacteria", "Ice Friction",
        "Solar Flares", "Memory Formation", "Plate Tectonics", "Dark Matter",
        "Bird Migration", "Quantum Tunnelling",
    ],
    "tech": [
        "The New Flagship", "A $500 Gaming PC", "Mechanical Keyboards", "TypeScript",
        "USB-C", "Rust", "This Studio Setup", "Server Components", "E-Ink Monitors",
        "Local LLMs", "Thunderbolt Docks", "Passkeys", "The Framework Laptop",
        "Neovim", "Docker Compose",
    ],
    "craft": [
        "A Workshop Cart", "Suspension Bridges", "A Spinning Top", "A 1950s Lathe",
        "Concrete", "Cheap Tools", "A Vacuum Former", "Ball Bearings", "Hydraulic Presses",
        "Wood Joinery", "A CNC Router", "Cast Iron",
    ],
}

# One deliberately replayed stream, so the "most rewatched" card has a real answer.
REPEAT_TITLE = "lofi hip hop radio - beats to relax/study to"
REPEAT_CHANNEL = "Lofi Girl"


def make_title(rng, theme):
    template = rng.choice(TITLE_TEMPLATES[theme])
    return template.format(rng.choice(TITLE_SUBJECTS[theme]))


def channel_url(channel_id):
    return f"https://www.youtube.com/channel/{channel_id}"


def video_url(rng):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    return "https://www.youtube.com/watch?v=" + "".join(rng.choice(alphabet) for _ in range(11))


def entry(title, url, channel, channel_id, when):
    return {
        "header": "YouTube",
        "title": f"Watched {title}",
        "titleUrl": url,
        "subtitles": [{"name": channel, "url": channel_url(channel_id)}],
        "time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def pick_start_hour(rng):
    total = sum(weight for _, weight in START_SLOT_WEIGHTS)
    roll = rng.uniform(0, total)
    running = 0
    for (start, end), weight in START_SLOT_WEIGHTS:
        running += weight
        if roll <= running:
            return rng.randrange(start, end) % 24
    return 21


def pick_theme(rng, day, hour):
    """Themes are what make co-occurrence real: a sitting has a mood."""
    if day.weekday() == 6 and rng.random() < 0.62:
        return "science"          # the Sunday ritual
    if 7 <= hour < 10 and rng.random() < 0.70:
        return "tech"             # the morning ritual
    return rng.choices(
        ["music", "science", "tech", "craft"], weights=[34, 22, 26, 18]
    )[0]


def build_watch_history():
    rng = random.Random(SEED)
    start = datetime(YEAR, 1, 1)
    entries = []
    long_tail = [
        (f"{topic.title()} Channel {i}", f"UClongtail{i:04d}XXXXXXXXXXX")
        for i, topic in enumerate(LONG_TAIL_TOPICS * 21)
    ]

    for day in range(365):
        date = start + timedelta(days=day)

        # ~82% active days, plus a deliberate unbroken streak in the summer
        in_streak = 165 <= date.timetuple().tm_yday <= 218
        if not in_streak and rng.random() > 0.82:
            continue

        for _ in range(rng.choices([1, 2], weights=[72, 28])[0]):
            hour = pick_start_hour(rng)
            when = date.replace(hour=hour, minute=rng.randrange(0, 60))
            theme = pick_theme(rng, date, hour)

            # A session opener is a habit: the same channel starts the run.
            if rng.random() < 0.34:
                entries.append(
                    entry(rng.choice(OPENER_SUBJECTS), video_url(rng),
                          OPENER[0], OPENER[1], when)
                )
                when += timedelta(minutes=rng.randrange(2, 6))

            marathon = date.weekday() >= 5 and rng.random() < 0.22
            length = (rng.randrange(26, 42) if marathon
                      else rng.choices([3, 5, 8, 14], weights=[40, 32, 20, 8])[0])
            for _ in range(length):
                # December spike on a channel that is present all year anyway --
                # concentration only counts as seasonal if it could have appeared
                # elsewhere.
                seasonal_chance = 0.42 if date.month == 12 else 0.02
                if rng.random() < seasonal_chance:
                    channel, channel_id = SEASONAL
                    title = f"Day {rng.randrange(1, 26)} Puzzle Walkthrough"
                elif rng.random() < 0.72:
                    channel, channel_id = rng.choice(THEMES[theme])
                    if channel == REPEAT_CHANNEL and rng.random() < 0.11:
                        title = REPEAT_TITLE
                    else:
                        title = make_title(rng, theme)
                else:
                    channel, channel_id = rng.choice(long_tail)
                    title = f"{rng.choice(LONG_TAIL_TOPICS).title()} {rng.randrange(1, 400)}"

                entries.append(entry(title, video_url(rng), channel, channel_id, when))
                when += timedelta(minutes=rng.randrange(3, 9))

    # Trim evenly across the year rather than keeping only the newest, so every month
    # survives -- truncating a sorted list would silently cut the demo to six months.
    if len(entries) > TARGET_WATCHES:
        keep = set(rng.sample(range(len(entries)), TARGET_WATCHES))
        entries = [e for i, e in enumerate(entries) if i in keep]

    entries.sort(key=lambda e: e["time"], reverse=True)  # Takeout is newest-first
    return entries


SEARCH_TERMS = [
    "kurzgesagt black hole", "how to learn rust", "lofi study mix", "mkbhd iphone review",
    "veritasium electricity", "typescript generics", "best mechanical keyboard",
    "advent of code day 7", "how do bridges work", "react server components",
    "chillhop radio", "python async explained", "mark rober squirrel maze",
    "docker compose tutorial", "why is the sky blue", "linux ricing guide",
    "odesza live set", "css grid vs flexbox", "quantum computing explained",
    "home lab setup",
]


def build_search_history():
    rng = random.Random(SEED + 1)
    start = datetime(YEAR, 1, 1)
    out = []
    for _ in range(180):
        term = rng.choice(SEARCH_TERMS)
        when = start + timedelta(
            days=rng.randrange(0, 365), hours=pick_start_hour(rng),
            minutes=rng.randrange(0, 60),
        )
        out.append({
            "header": "YouTube",
            "title": f"Searched for {term}",
            "titleUrl": "https://www.youtube.com/results?search_query="
                        + term.replace(" ", "+"),
            "time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    out.sort(key=lambda e: e["time"], reverse=True)
    return out


def build_subscriptions(watch_entries):
    """Subscribed channels, only some of which get watched -- that is the ghost stat."""
    rng = random.Random(SEED + 2)
    watched = []
    for item in watch_entries:
        for subtitle in item.get("subtitles", []):
            watched.append((subtitle["name"], subtitle["url"].rsplit("/", 1)[-1]))
    unique = sorted(set(watched))
    rng.shuffle(unique)

    rows = [(cid, f"https://www.youtube.com/channel/{cid}", name)
            for name, cid in unique[:58]]
    for i in range(92):  # subscribed and never watched
        cid = f"UCghost{i:04d}XXXXXXXXXXXXX"
        rows.append((cid, f"https://www.youtube.com/channel/{cid}", f"Ghost Channel {i}"))

    rng.shuffle(rows)
    return rows


TAKEOUT_ROOT = "Takeout/YouTube and YouTube Music"
CSV_NEWLINE = chr(10)
NBSP = " "      # Takeout puts this after the activity verb
NNBSP = " "   # ...and this before the meridiem

CAPTION = (
    "<b>Products:</b><br>&emsp;YouTube<br>"
    "<b>Why is this here?</b><br>&emsp;This activity was saved to your Google Account "
    "because the following settings were on:&nbsp;YouTube watch history."
)

HTML_HEAD = (
    "<html><head><title>My Activity History</title>"
    "<style type=\"text/css\">.outer-cell{margin-bottom:16px}</style></head>"
    "<body><div class=\"mdl-grid\">"
)
HTML_TAIL = "</div></body></html>"


def render_stamp(when):
    """e.g. 'Jan 5, 2025, 11:30:45 PM UTC' with the narrow no-break space Takeout uses.

    Rendered in UTC and tagged UTC so the demo's timezone round-trips exactly and the
    planted clock-hour signals land where the generator put them.
    """
    hour = when.hour % 12 or 12
    meridiem = "AM" if when.hour < 12 else "PM"
    return (
        f"{when.strftime('%b')} {when.day}, {when.year}, "
        f"{hour}:{when.strftime('%M:%S')}{NNBSP}{meridiem} UTC"
    )


def render_cell(verb, title, url, channel, channel_url_, stamp):
    """One outer-cell, matching the template takeout_html_scanner parses."""
    body = f"{verb}{NBSP}<a href=\"{escape(url, quote=True)}\">{escape(title)}</a><br>"
    if channel:
        body += f"<a href=\"{escape(channel_url_, quote=True)}\">{escape(channel)}</a><br>"
    body += f"{stamp}<br>"

    return (
        '<div class="outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp">'
        '<div class="mdl-grid">'
        '<div class="header-cell mdl-cell mdl-cell--12-col">'
        '<p class="mdl-typography--title">YouTube<br></p></div>'
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">'
        f"{body}</div>"
        '<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1 '
        'mdl-typography--text-right"></div>'
        '<div class="content-cell mdl-cell mdl-cell--12-col mdl-typography--caption">'
        f"{CAPTION}</div></div></div>"
    )


def render_watch_html(entries):
    cells = []
    for item in entries:
        when = datetime.strptime(item["time"], "%Y-%m-%dT%H:%M:%SZ")
        subtitle = (item.get("subtitles") or [{}])[0]
        cells.append(render_cell(
            "Watched", item["title"][len("Watched "):], item["titleUrl"],
            subtitle.get("name"), subtitle.get("url", ""), render_stamp(when),
        ))
    return HTML_HEAD + "".join(cells) + HTML_TAIL


def render_search_html(entries):
    cells = []
    for item in entries:
        when = datetime.strptime(item["time"], "%Y-%m-%dT%H:%M:%SZ")
        cells.append(render_cell(
            "Searched for", item["title"][len("Searched for "):], item["titleUrl"],
            None, "", render_stamp(when),
        ))
    return HTML_HEAD + "".join(cells) + HTML_TAIL


def write_takeout_zip(path, watch, search, subs_rows):
    """A real Takeout archive: HTML history plus the subscriptions CSV."""
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer, lineterminator=CSV_NEWLINE)
    writer.writerow(["Channel Id", "Channel Url", "Channel Title"])
    writer.writerows(subs_rows)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        # Fixed timestamps keep the archive byte-identical between runs.
        def add(name, text):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text)

        add(f"{TAKEOUT_ROOT}/history/watch-history.html", render_watch_html(watch))
        add(f"{TAKEOUT_ROOT}/history/search-history.html", render_search_html(search))
        add(f"{TAKEOUT_ROOT}/subscriptions/subscriptions.csv", csv_buffer.getvalue())


def main():
    os.makedirs(FIXTURES, exist_ok=True)

    watch = build_watch_history()
    search = build_search_history()
    subs = build_subscriptions(watch)

    zip_path = os.path.join(FIXTURES, "demo_takeout.zip")
    write_takeout_zip(zip_path, watch, search, subs)

    print(f"watch entries : {len(watch)}")
    print(f"search entries: {len(search)}")
    print(f"subscriptions : {len(subs)}")
    print(f"archive       : {os.path.getsize(zip_path) / 1024:.0f} KB  ({zip_path})")


if __name__ == "__main__":
    main()
