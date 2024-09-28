# Chad

Search Google Dorks like Chad. Based on [ivan-sincek/nagooglesearch](https://github.com/ivan-sincek/nagooglesearch).

Tested on Kali Linux v2024.2 (64-bit).

Made for educational purposes. I hope it will help!

## Table of Contents

* [How to Install](#how-to-install)
	* [Install Playwright and Chromium](#install-playwright-and-chromium)
	* [Standard Install](#standard-install)
	* [Build and Install From the Source](#build-and-install-from-the-source)
* [Shortest Possible](#shortest-possible)
* [File Download](#file-download)
* [Chad Extractor](#chad-extractor)
* [Social Media Takeover](#social-media-takeover)
    * [Single Site](#single-site)
    * [Multiple Sites](#multiple-sites)
    * [Analyzing the Report](#analyzing-the-report)
* [Rate Limiting](#rate-limiting)
* [Usage](#usage)
* [Images](#images)

## How to Install

### Install Playwright and Chromium

```bash
pip3 install --upgrade playwright

playwright install chromium
```

Make sure each time you upgrade your Playwright dependency to re-install Chromium; otherwise, you might get an error using the headless browser in Chad Extractor.

### Standard Install

```bash
pip3 install --upgrade google-chad
```

### Build and Install From the Source

```bash
git clone https://github.com/ivan-sincek/chad && cd chad

python3 -m pip install --upgrade build

python3 -m build

python3 -m pip install dist/google_chad-6.6-py3-none-any.whl
```

## Shortest Possible

```bash
chad -q 'intitle:"index of /" intext:"parent directory"'
```

## File Download

Did you say Metagoofil?!

```bash
mkdir downloads

chad -q "ext:pdf OR ext:docx OR ext:xlsx OR ext:pptx" -s *.example.com -tr 200 -dir downloads
```

_Chad's file download feature is based on Python Requests library._

## Chad Extractor

Chad Extractor is a powerful tool based on [Scrapy's](https://scrapy.org) web crawler and [Playwright's](https://playwright.dev/python) Chromium headless browser, designed to efficiently scrape web content; unlike Python Requests library, which cannot render JavaScript encoded HTML and is easily blocked by anti-bot solutions.

Primarily, Chad Extractor is designed to extract and validate data from Chad results files. However, it can also be used to extract and validate data from plaintext files by using the `-pt` option.

If the `-pt` option is used, plaintext files will be immediately treated like server responses, and the extraction logic will be applied, followed by validation. This is also useful if you want to re-test previous Chad Extractor's reports, e.g., by using `-res chad_extractor_report.json -pt`.

## Social Media Takeover

Prepare the Google Dorks as [social_media_dorks.txt](https://github.com/ivan-sincek/chad/blob/main/src/dorks/social_media_dorks.txt) file:

```fundamental
intext:"t.me/"
intext:"discord.com/invite/" OR intext:"discord.gg/invite/"
intext:"youtube.com/c/" OR intext:"youtube.com/channel/"
intext:"twitter.com/" OR intext:"x.com/"
intext:"facebook.com/"
intext:"instagram.com/"
intext:"tiktok.com/"
intext:"linkedin.com/in/" OR intext:"linkedin.com/company/"
```

Prepare the template as [social_media_template.json](https://github.com/ivan-sincek/chad/blob/main/src/templates/social_media_template.json) file:

```json
{
   "telegram":{
      "extract":"t\\.me\\/(?:(?!(?:share)(?:$|(?:\\/|\\?)[^\\s]))[\\w\\d\\.\\_\\-\\+\\@]+)(?<!\\.)",
      "extract_prepend":"https://",
      "validate":"<meta property=\"og:title\" content=\"Telegram: Contact .+?\">"
   },
   "discord":{
      "extract":"discord\\.(?:com|gg)\\/invite\\/[\\w\\d\\.\\_\\-\\+\\@]+(?<!\\.)",
      "extract_prepend":"https://",
      "validate":"Invite Invalid",
      "validate_browser":true,
      "validate_browser_wait":6
   },
   "youtube":{
      "extract":"youtube\\.com\\/(?:c|channel)\\/[\\w\\d\\.\\_\\-\\+\\@]+(?<!\\.)",
      "extract_prepend":"https://www.",
      "validate":"<iframe.+?src=\"\\/error\\?src=404.+?\">",
      "validate_cookies":{
         "SOCS":"CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjQwOTEwLjA4X3AxGgJkZSACGgYIgLCotwY"
      }
   },
   "twitter":{
      "extract":"(?<=(?<!pic\\.)twitter|x)\\.com\\/(?:(?!(?:explore|hashtag|home|i|intent|library|media|personalization|search|share|tos|widgets\\.js|[\\w]+\\/(?:privacy|tos))(?:$|(?:\\/|\\?)[^\\s]))[\\w\\d\\.\\_\\-\\+\\@]+)(?<!\\.)",
      "extract_prepend":"https://x",
      "validate":"This account doesn.?t exist",
      "validate_browser":true,
      "validate_cookies":{
         "night_mode":"2"
      }
   },
   "facebook":{
      "extract":"facebook\\.com\\/(?:(?!(?:about|dialog|gaming|groups|public|sharer|share\\.php|terms\\.php)(?:$|(?:\\/|\\?)[^\\s]))[\\w\\d\\.\\_\\-\\+\\@]+)(?<!\\.)",
      "extract_prepend":"https://www.",
      "validate":"This (?:content|page) isn't available",
      "validate_browser":true
   },
   "instagram":{
      "extract":"instagram\\.com\\/(?:(?!(?:about|accounts|ar|explore|p)(?:$|(?:\\/|\\?)[^\\s]))[\\w\\d\\.\\_\\-\\+\\@]+)(?<!\\.)",
      "extract_prepend":"https://www.",
      "extract_append":"/",
      "validate":"Sorry, this page isn't available\\.",
      "validate_browser":true
   },
   "tiktok":{
      "extract":"(?<!vt\\.)tiktok\\.com\\/\\@[\\w\\d\\.\\_\\-\\+\\@]+(?<!\\.)",
      "extract_prepend":"https://www.",
      "validate":"Couldn't find this account"
   },
   "linkedin-company":{
      "extract":"linkedin\\.com\\/company\\/[\\w\\d\\.\\_\\-\\+\\@\\&]+(?<!\\.)",
      "extract_prepend":"https://www.",
      "validate":"Page not found",
      "validate_cookies":{
         "bcookie":"v=2",
         "lang":"v=2&lang=en-us"
      }
   },
   "linkedin-user":{
      "extract":"linkedin\\.com\\/in\\/[\\w\\d\\.\\_\\-\\+\\@\\&]+(?<!\\.)",
      "extract_prepend":"https://www.",
      "validate":"An exact match for .+ could not be found\\."
   }
}
```

_At the moment, I am unable to bypass the auth. wall to validate LinkedIn users, i.e., for `linkedin-user`._

**Make sure your regular expressions return only one capturing group, e.g., `[1, 2, 3, 4]`; and not a touple, e.g., `[(1, 2), (3, 4)]`.**

Make sure to properly escape regular expression specific symbols in your template file, e.g., make sure to escape dot `.` as `\\.`, and forward slash `/` as `\\/`, etc.

All regular expression searches are case-insensitive.

Web content fetched from the URLs in Chad results files will be matched against all the regular expressions (defined by the `extract` attributes) in the template file to find as much relevant data as possible.

To extract data without validation, simply omit the `validate` attributes from the template file as necessary.

| Scope | Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| extraction | extract | text | yes | Regular expression query. |
| extraction | extract_prepend | text | no | String to prepend to all extracted data. |
| extraction | extract_append | text | no | String to append to extracted data. |
| validation | validate | text | no | Regular expression query. |
| validation | validate_browser | boolean | no | Whether to use the headless browser or not. |
| validation | validate_browser_wait | float | no | Wait time in seconds before fetching the content from the headless browser's page. |
| validation | validate_cookies | dict | no | HTTP request cookies in key-value format. |

<p align="center">Table 1 - Template Attributes</p>

### Single Site

```bash
chad -q social_media_dorks.txt -s *.example.com -tr 200 -pr 100 -o results.json

chad-extractor -t social_media_template.json -res results.json -o results_report.json
```

### Multiple Sites

Prepare the domains / subdomains as `sites.txt` file, the same way you would use them with the `site:` option in Google:

```fundamental
*.example.com
*.example.com -www
```

\[Optional\] Prepare bot-safe user agents as `user_agents.txt` file, where `<your-api-key>` is your API key from [scrapeops.io](https://scrapeops.io):

```python
python3 -c 'import json, requests; open("user_agents.txt", "w").write(("\n").join(requests.get("http://headers.scrapeops.io/v1/user-agents?api_key=<your-api-key>&num_results=100", verify = False).json()["result"]))'
```

_Twitter/X might not work well with some of the user agents._

Run:

```bash
mkdir chad_results

IFS=$'\n'; count=0; for site in $(cat sites.txt); do count=$((count+1)); echo "#${count} | ${site}"; chad -q social_media_dorks.txt -s "${site}" -tr 200 -pr 100 -a user_agents.txt -o "chad_results/results_${count}.json"; done

chad-extractor -t social_media_template.json -res chad_results -a user_agents.txt -o results_report.json -v
```

## Analyzing the Report

Manually verify if the social media URLs in `results[summary][validated]` are vulnerable to takeover:

```json
{
   "started_at":"2023-12-23 03:30:10",
   "ended_at":"2023-12-23 04:20:00",
   "summary":{
      "validated":[
         "https://t.me/does_not_exist" // might be vulnerable to takeover
      ],
      "extracted":[
         "https://discord.com/invite/exists",
         "https://t.me/does_not_exist",
         "https://t.me/exists"
      ]
   },
   "failed":{
      "validation":[],
      "extraction":[]
   },
   "full":[
      {
         "url":"https://example.com/about",
         "results":{
            "telegram":[
               "https://t.me/does_not_exist",
               "https://t.me/exists"
            ],
            "discord":[
               "https://discord.com/invite/exists"
            ]
         }
      }
   ]
}
```

## Rate Limiting

Google's cooling-off period can range from a few hours to a whole day.

To avoid hitting Google's rate limits with Chad, increase the minimum and maximum sleep between Google queries and/or pages; or use free or paid proxies. However, free proxies are often blocked and unstable.

To download a list of free proxies, run:

```bash
curl -s 'https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc' -H 'Referer: https://proxylist.geonode.com/' | jq -r '.data[] | "\(.protocols[])://\(.ip):\(.port)"' > proxies.txt
```

**If you are using proxies, you might want to increase the request timeout, as responses will need longer time to arrive.**

Additionally, to avoid hitting rate limits on platforms like [Instagram's](https://www.instagram.com) while using Chad Extractor, consider decreasing the number of concurrent requests per domain and increasing the sleep and wait times.

## Usage

```fundamental
Chad v6.6 ( github.com/ivan-sincek/chad )

Usage:   chad -q queries     [-s site         ] [-x proxies    ] [-o out         ]
Example: chad -q queries.txt [-s *.example.com] [-x proxies.txt] [-o results.json]

DESCRIPTION
    Search Google Dorks like Chad
QUERIES
    File with Google Dorks or a single query to use
    -q, --queries = queries.txt | intext:password | "ext:tar OR ext:zip" | etc.
SITE
    Domain[s] to search
    -s, --site = example.com | sub.example.com | *.example.com | "*.example.com -www" | etc.
TIME
    Get results not older than the specified time in months
    -t, --time =  6 | 12 | 24 | etc.
TOTAL RESULTS
    Total number of unique results
    Default: 100
    -tr, --total-results = 200 | etc.
PAGE RESULTS
    Number of results per page - capped at 100 by Google
    Default: randint(75, 100)
    -pr, --page-results = 50 | etc.
MINIMUM QUERIES
    Minimum sleep time in seconds between Google queries
    Default: 75
    -min-q, --minimum-queries = 120 | etc.
MAXIMUM QUERIES
    Maximum sleep time between Google queries
    Default: minimum + 50
    -max-q, --maximum-queries = 180 | etc.
MINIMUM PAGES
    Minimum sleep time between Google pages
    Default: 15
    -min-p, --minimum-pages = 30 | etc.
MAXIMUM PAGES
    Maximum sleep time between Google pages
    Default: minimum + 10
    -max-p, --maximum-pages = 60 | etc.
USER AGENTS
    User agents to use
    Default: random-all
    -a, --user-agents = curl/3.30.1 | user_agents.txt | random[-all] | etc.
PROXIES
    File with proxies or a single proxy to use
    -x, --proxies = proxies.txt | http://127.0.0.1:8080 | etc.
DIRECTORY
    Downloads directory
    All downloaded files will be saved in this directory
    -dir, --directory = downloads | etc.
THREADS
    Number of files to download in parallel
    Default: 5
    -th, --threads = 20 | etc.
OUT
    Output file
    -o, --out = results.json | etc.
NO SLEEP ON START
    Safety feature to prevent triggering rate limits accidentally, enabled by default
    -nsos, --no-sleep-on-start
DEBUG
    Debug output
    -dbg, --debug
```

```fundamental
Chad Extractor v6.6 ( github.com/ivan-sincek/chad )

Usage:   chad-extractor -t template      -res results      -o out         [-s sleep] [-rs random-sleep]
Example: chad-extractor -t template.json -res chad_results -o report.json [-s 1.5  ] [-rs             ]

DESCRIPTION
    Extract and validate data from Chad results or plaintext files
TEMPLATE
    Template file with extraction and validation details
    -t, --template = template.json | etc.
RESULTS
    Directory with Chad results or plaintext files, or a single file
    If directory, files ending with '.report.json' will be ignored
    -res, --results = chad_results | results.json | urls.txt | etc.
PLAINTEXT
    Treat all the results as plaintext files
    -pt, --plaintext
EXCLUDES
    File with regular expressions or a single regular expression to exclude the content from the page
    Applies only for extraction
    -e, --excludes = regexes.txt | "<div id=\"seo\">.+?<\/div>" | etc.
PLAYWRIGHT
    Use Playwright's headless browser
    Applies only for extraction
    For validation, use the template file
    -p, --playwright
PLAYWRIGHT WAIT
    Wait time in seconds before fetching the content from the page
    Applies only for extraction and if Playwright's headless browser is used
    For validation, use the template file
    -pw, --playwright-wait = 2 | 4 | etc.
CONCURRENT REQUESTS
    Number of concurrent requests
    Default: 15
    -cr, --concurrent-requests = 30 | 45 | etc.
CONCURRENT REQUESTS PER DOMAIN
    Number of concurrent requests per domain
    Default: 5
    -crd, --concurrent-requests-domain = 10 | 15 | etc.
SLEEP
    Sleep time in seconds between two consecutive requests to the same domain
    -s, --sleep = 1.5 | 3 | etc.
RANDOM SLEEP
    Randomize the sleep time on each request to vary between '0.5 * sleep' and '1.5 * sleep'
    -rs, --random-sleep
AUTO THROTTLE
    Auto throttle concurrent requests based on the load and latency
    Sleep time is still respected
    -at, --auto-throttle = 0.5 | 10 | 15 | 45 | etc.
RETRIES
    Number of retries per URL
    Default: 2
    -r, --retries = 0 | 4 | etc.
REQUEST TIMEOUT
    Request timeout in seconds
    Default: 60
    -rt, --request-timeout = 30 | 90 | etc.
USER AGENTS
    User agents to use
    Default: random-all
    -a, --user-agents = curl/3.30.1 | user_agents.txt | random[-all] | etc.
PROXY
    Web proxy to use
    -x, --proxy = http://127.0.0.1:8080 | etc.
OUT
    Output file
    -o, --out = report.json | etc.
VERBOSE
    Create additional supporting output files that end with '.report.json'
    -v, --verbose
DEBUG
    Debug output
    -dbg, --debug
```

## Images

<p align="center"><img src="https://github.com/ivan-sincek/chad/blob/main/img/single_dork.png" alt="(Chad) Single File Download Google Dork"></p>

<p align="center">Figure 1 - (Chad) Single File Download Google Dork</p>

<p align="center"><img src="https://github.com/ivan-sincek/chad/blob/main/img/multiple_dorks.png" alt="(Chad) Multiple Social Media Google Dorks"></p>

<p align="center">Figure 2 - (Chad) Multiple Social Media Google Dorks</p>

<p align="center"><img src="https://github.com/ivan-sincek/chad/blob/main/img/extraction.png" alt="Extraction"></p>

<p align="center">Figure 3 - (Chad Extractor) Extraction</p>

<p align="center"><img src="https://github.com/ivan-sincek/chad/blob/main/img/validation.png" alt="Validation"></p>

<p align="center">Figure 4 - (Chad Extractor) Validation</p>
