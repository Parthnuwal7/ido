<p align="center">
  <img src="ido_icon.png" alt="Ido" width="120" />
</p>

<h1 align="center">Ido</h1>

<p align="center">
  <strong>Your YouTube Wrapped — see your year in videos</strong>
</p>

<p align="center">
  Upload your YouTube data and get a set of shareable cards about how you watched this year.
</p>

<p align="center">
  <a href="#what-it-does">What it does</a> •
  <a href="#try-it">Try it</a> •
  <a href="#how-to-use-it">How to use it</a> •
  <a href="#your-privacy">Privacy</a> •
  <a href="#run-it-yourself">Run it yourself</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## Why I built this

YouTube's own Recap felt thin to me — a few numbers and not much else. I wanted to see
what my viewing actually looked like over a year, so I built Ido. Drop in the data
Google already has on you and get 22 cards back in a few seconds.

If you like it, a star on GitHub is appreciated.

## What it does

**Your year, counted**
- How many videos you watched, how many channels, and how many days you showed up
- Roughly how many hours it added up to
- Your busiest month, and your first and last video of the year

**Your favourites**
- The channels you watched most
- The videos you came back to more than once
- Channels you subscribed to but never actually watched

**Your rhythm**
- What time of day you watch, as a 24-hour clock
- Your busiest day of the week
- Your longest run of days without missing one
- How much you watch after midnight, and how late you stayed up

**Your habits**
- Whether you scroll quickly or settle in and watch things properly
- Your longest unbroken viewing session
- Channels you return to like clockwork
- Patterns you probably haven't noticed — like a channel you only ever watch on Sundays

**Your taste**
- Your viewing sorted into a handful of "worlds" — Ido works these out from which
  channels you watch in the same sitting, so it finds them without being told
- How those worlds rose and fell across the months
- Whether you drifted towards new channels or settled into familiar ones
- How mainstream or obscure your channels are

## Try it

[**Open the demo**](https://ido-by-parth.vercel.app/wrapped-demo) — it runs on sample
data, so you can see all the cards without uploading anything.

## How to use it

1. Go to [Google Takeout](https://takeout.google.com/) and select **YouTube only**
2. Under YouTube, untick **videos** — those are your own uploads, they can be hundreds
   of megabytes, and Ido never looks at them
3. Download the ZIP when Google emails you
4. Open [Ido](https://ido-by-parth.vercel.app), pick your timezone and a year, and drop
   the ZIP in
5. Swipe through your cards

It takes a few seconds once the file is uploaded. Both formats Google offers work — you
don't need to change any export settings.

## Your privacy

- **Your Takeout file is never kept.** It's read, turned into cards, and thrown away.
- **Nothing is stored about you** unless you choose to save a Wrapped.
- **Naming your taste worlds is optional.** If you tick that box, a few channel names go
  to an AI service to turn "rajasthanroyals · cricinfo" into "IPL Cricket". Your watch
  history never leaves. Leave it unticked and Ido uses your channel names instead.
- **No tracking.** No analytics, no ads.
- **Open source**, so you can check all of this yourself.

## Run it yourself

You'll need Node.js 18+, Python 3.11+, and pnpm.

**Frontend**

```bash
cd ido_frontend
pnpm install
cp env.example .env.local
pnpm dev
```

**Backend**

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --reload --port 8000
```

Copy `backend/env.example` to `backend/.env` if you want the optional extras (naming
your taste worlds, and channel details). Everything else works without any keys.

## Built with

Next.js and Tailwind on the front, FastAPI on the back, deployed on Vercel and Hugging
Face Spaces.

## Contributing

Contributions are welcome — open an issue or send a pull request.

1. Fork the repository
2. Create your branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes
4. Push and open a pull request

## Contact

- **Email**: parthnuwal7@gmail.com
- **GitHub**: [@Parthnuwal7](https://github.com/Parthnuwal7)

## License

Dual use licence — free for personal use, commercial use needs permission. See
[LICENSE](LICENSE).

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Parthnuwal7">Parthnuwal7</a>
</p>
