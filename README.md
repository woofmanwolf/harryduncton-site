# harryduncton.com: how to put it live (free)

The site runs on GitHub Pages, which hosts it free with HTTPS on your own domain. A small job runs every morning, checks your Google Alert for new bylines, and adds them to "Latest work" on its own.

You'll need a laptop or desktop for the setup. Allow about 45 minutes, plus up to a day for the domain to switch over.

## What's in the folder

| File | What it does |
|---|---|
| `index.html` | The whole website |
| `data/manual.json` | Clips you add by hand. These always show |
| `data/feeds.json` | Where the daily job looks for new clips |
| `scripts/update_clips.py` | The daily job |
| `.github/workflows/update-clips.yml` | Tells GitHub to run the job every morning |

## 1. Make a GitHub account

Sign up at github.com. The free plan is all you need.

## 2. Create the repository

1. Click **New** (top left) to create a repository.
2. Name it `harryduncton-site`.
3. Set it to **Public**. Free hosting needs a public repository, which is fine as it's a public website.
4. Click **Create repository**.

## 3. Upload the files

1. On the new repository page, click **uploading an existing file**.
2. Unzip the folder I sent and drag in `index.html`, `README.md`, and the `data` and `scripts` folders. Click **Commit changes**.
3. The `.github` folder is hidden on most computers, so add it by hand: click **Add file > Create new file**, type `.github/workflows/update-clips.yml` as the name (the slashes create the folders), paste in the contents of that file from the zip, and click **Commit changes**.

## 4. Switch on hosting

1. Go to **Settings > Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**, branch **main**, folder **/ (root)**, then **Save**.
3. After a minute or two the page shows a link like `https://yourname.github.io/harryduncton-site/`. Open it to check the site.

## 5. Set up the byline feed

1. Go to google.com/alerts and type `"Harry Duncton"` with the quote marks.
2. Click **Show options**. Set **How often** to *At most once a day* and **Deliver to** to **RSS feed**. Click **Create Alert**.
3. Click the RSS icon next to the new alert and copy the address from your browser.
4. Back on GitHub, open `data/feeds.json`, click the pencil icon, replace `PASTE_YOUR_GOOGLE_ALERT_RSS_LINK_HERE` with that address, and commit.

## 6. Let the daily job save its changes

1. Go to **Settings > Actions > General**.
2. Under **Workflow permissions**, choose **Read and write permissions** and save.
3. Go to the **Actions** tab, click **Update latest work**, then **Run workflow** to test it. A green tick means it worked.

From now on it runs every morning at about 7am UK time.

## 7. Move your domain across

1. In GitHub, **Settings > Pages > Custom domain**: enter `www.harryduncton.com` and save.
2. In Google Sites, open your site's **Settings > Custom domains** and remove harryduncton.com.
3. Log in to wherever you bought the domain and open its DNS settings:
   - Delete the old record pointing `www` at `ghs.googlehosted.com`.
   - Add a **CNAME** record: name `www`, value `yourname.github.io` (your GitHub username).
   - Add four **A** records for the bare domain (name `@`): `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
4. Wait. It can take anywhere from ten minutes to a day. When GitHub shows the domain as working, tick **Enforce HTTPS**.

## 8. Before you share it

- **Add a share image.** Upload a 1200 x 630 pixel photo called `og-image.jpg` (you with a mower in the garden is ideal). It's what appears when someone shares your link.
- **Check these lines are still true**: "13 lawnmowers in the shed" (taken from your T3 bio), and the brand note "paid work is always labelled and never buys a review verdict".
- **Swap two links** in `data/manual.json` and `index.html` if you have better ones: the Radio 4 episode currently links to Pocket Casts (a BBC Sounds link is better), and the RFS entry links to the awards page rather than your articles.
- **Add LinkedIn** to the contact section if you want it there.
- **Tell Google.** Add the site to Google Search Console (search.google.com/search-console) so it's indexed quickly.

## Day to day

- **Add a clip by hand:** open `data/manual.json` on GitHub, click the pencil, copy an existing entry, change the details, commit. It appears after the next morning run, or straight away if you click **Run workflow**.
- **Check the waiting list:** anything the alert finds on a site outside your usual outlets goes into `data/review.json` instead of the homepage, so a random blog quoting you never appears by mistake. If one is genuinely your work, copy it into `manual.json`. To trust a new outlet permanently, add its domain to `allow_domains` in `feeds.json`.
- **Edit the words:** open `index.html`, click the pencil, change the text, commit. The live site updates within a couple of minutes.
