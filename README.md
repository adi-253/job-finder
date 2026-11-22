# Job Finder

Get a Telegram alert within about 15–30 minutes of a **0–1 year software engineer job in India** appearing on the careers site of ~100 good companies (Google, Amazon, Microsoft, Apple, Oracle, Atlassian, Intuit, Rippling, Salesforce, Adobe, Nvidia, Stripe, Databricks, OpenAI, Goldman Sachs, JPMorgan, Postman, PhonePe, top Indian product companies like Swiggy, CRED, Razorpay and Meesho, trading firms…).

It reads each company's own job board directly (Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Oracle HCM, or the company's own API). Job boards like LinkedIn show the same postings hours or days later.

## How it works

```
every 15 min (GitHub Actions)
  1. collect   all postings from each company → keep only IDs never seen before
  2. filter    India location → junior software title → description doesn't ask for > 2 yrs
  3. alert     Telegram message per match
```

- Every posting ID seen (matched or not) is remembered, so each job is alerted only once.
- The first time a company is checked, its existing jobs are recorded **silently**, so adding a company doesn't flood you.
- If a company's site fails 8 runs in a row (~2 hours), you get one combined Telegram warning. A failed check loses nothing: the next successful run picks up anything new.
- Privacy: the repo is public so GitHub Actions is free, but it never stores or logs which jobs matched. Those only go to your Telegram, and on GitHub the run logs show counts only. Secrets are encrypted and shown as `***`.

## Setup (about 10 minutes)

1. **Create the Telegram bot**
   - In Telegram, open **@BotFather**, send `/newbot` and follow the prompts. Copy the **token**.
   - Open your new bot and send it any message (e.g. "hi").
   - Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `"chat":{"id": …}`: that number is your **chat ID**.

2. **Put the code on GitHub**: a **public** repo, so Actions minutes are free and unlimited. Nothing private is stored in it.
   ```bash
   git init && git add . && git commit -m "Job finder"
   gh repo create job-finder --public --source=. --push
   ```

3. **Add secrets**: in the repo, go to Settings → Secrets and variables → Actions → New repository secret:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

4. **Start it**: Actions tab → "Check for new jobs" → Run workflow. The first run records current jobs silently. After that it runs every 15 minutes on its own.

## See what's open right now

The bot only alerts on *new* postings. To list every **currently open** matching job (to apply today):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python main.py --all          # prints all current matches; sends nothing
```

Other useful commands:

```bash
.venv/bin/python main.py --dry-run                 # one normal check, print only
.venv/bin/python main.py --all --only Stripe,Google -v   # test companies, show every verdict
.venv/bin/python -m pytest tests                   # filter tests
```

## Customise (`config.yaml`)

- **Add a company**: one line. Open any job posting of theirs and look at the URL:
  | URL looks like | add |
  |---|---|
  | `boards.greenhouse.io/<slug>` / `?gh_jid=` | `{name: X, source: greenhouse, slug: <slug>}` |
  | `jobs.lever.co/<slug>` | `{name: X, source: lever, slug: <slug>}` |
  | `jobs.ashbyhq.com/<slug>` | `{name: X, source: ashby, slug: <slug>}` |
  | `jobs.smartrecruiters.com/<Slug>` | `{name: X, source: smartrecruiters, slug: <Slug>}` |
  | `<tenant>.<wdN>.myworkdayjobs.com/<site>` | `{name: X, source: workday, tenant: <tenant>, dc: <wdN>, site: <site>}` |
  | `<host>.oraclecloud.com/hcmUI/CandidateExperience/en/sites/<site>` | `{name: X, source: oracle_hcm, host: <host>.oraclecloud.com, site: <site>}` |
- **Remove one**: add `disabled: true`.
- **Experience**: `filters.max_years` (default 2). Set it to 3 to also see "2–3 years" roles.
- **Titles/locations**: the `title_include`, `title_exclude` and `locations` lists (regexes).

## Known limits

- GitHub's scheduler can start runs a few minutes late, so alerts typically come 15–30 min after posting.
- **Not covered, and what to do instead.** For these, turn on the site's own job alerts (LinkedIn's app alerts are near-instant: search "Software Engineer", location India, Experience level = Entry level, Date posted = Past 24 hours, then turn on alerts):
  - **LinkedIn, Naukri**: their terms forbid scraping. Use their built-in alerts.
  - **Meta**: its careers site needs a per-visitor session token and blocks automated requests. Use metacareers.com job alerts.
  - **Uber**: blocks automated requests (HTTP 403). Use a LinkedIn alert for Uber.
  - **Flipkart**: its careers page (TurboHire) needs an access token from the vendor's API, so it was left out. Use a LinkedIn alert for Flipkart.
  - **Zomato/Blinkit (Eternal)**: no public job list was found. Use a LinkedIn alert.
  - **Walmart Global Tech**: its Workday site didn't answer reliably in testing. To try it, add `{name: Walmart, source: workday, tenant: walmart, dc: wd5, site: WalmartExternal}`.
- Workday sites rate-limit bursts (HTTP 429). Requests to each Workday data center run one at a time with pauses, and an occasional failed run is harmless: the next run catches up.
- Experience is read from the description with patterns like "3+ years" or "2–4 years". When several are stated it keeps the job if *any* is ≤ 2 years, which leans toward showing a borderline job rather than missing one.
