# Chad

Search Google Dorks like Chad. Based on [ivan-sincek/nagooglesearch](https://github.com/ivan-sincek/nagooglesearch).

At the moment, this tool cannot be installed on Windows OS because Python's `jq` library (required by Chad Extractor) is not supported. Although, [Chad](https://github.com/ivan-sincek/chad/blob/main/src/chad/chad.py) does in fact work on Windows OS if you run it as a standalone script.

Tested on Kali Linux v2023.4 (64-bit).

Made for educational purposes. I hope it will help!

Future plans:

* find `jq` alternative so that the whole package can be cross-platform.

## Table of Contents

* [How to Install](#how-to-install)
* [How to Build and Install Manually](#how-to-build-and-install-manually)
* [Shortest Possible](#shortest-possible)
* [Basic Example: File Download](#basic-example-file-download)
* [Chad Extractor](#chad-extractor)
    * [Extracting and Validating Data)](#extracting-and-validating-data)
* [Advanced Example: Social Media Takover](#advanced-example-social-media-takover)
    * [Basic Use (Single Domain)](#basic-use-single-domain)
    * [Advanced Use (Multiple Domains)](#advanced-use-multiple-domains)
* [Rate Limiting](#rate-limiting)
* [Usage](#usage)
* [Images](#images)

## How to Install

```bash
pip3 install google-chad

pip3 install --upgrade google-chad

playwright install chromium
```

## How to Build and Install Manually

Run the following commands:

```bash
git clone https://github.com/ivan-sincek/chad && cd chad

python3 -m pip install --upgrade build

python3 -m build

python3 -m pip install dist/google_chad-5.1-py3-none-any.whl

playwright install chromium
```

## Shortest Possible

```bash
chad -q 'intitle:"index of /" intext:"parent directory"'
```

## Basic Example: File Download

Did you say Metagoofil?!

```bash
mkdir downloads

chad -q "ext:pdf OR ext:docx OR ext:xlsx OR ext:pptx" -s *.example.com -tr 200 -d downloads
```

`-s <site>` is optional. For more information, see [Usage](#usage).

Chad's file download feature is based on Python Requests library.

## Chad Extractor

Chad Extractor is a powerful tool based on [Playwright](https://playwright.dev/python) Chromium headless browser created to efficiently scrape web; in other words, to compensate for Python Requests library which cannot render JavaScript encoded HTML and is easily blocked by anti-bot solutions.

There is a 4 seconds delay between starting each headless browser; otherwise, it would be very resources-intensive.

### Extracting and Validating Data

Chad Extractor was mainly designed to extract and validate data from Chad results; but, you can also use it to extract and validate data from plaintext files by specifying `-pt yes` flag - plaintext files will be treated like server responses and extraction logic will be immediately applied.

## Advanced Example: Social Media Takover

Prepare Google Dorks as [social_media_dorks.txt](https://github.com/ivan-sincek/chad/blob/main/src/dorks/social_media_dorks.txt) file:

```fundamental
intext:"t.me/"
intext:"discord.com/invite/" OR intext:"discord.gg/invite/"
intext:"youtube.com/c/" OR intext:"youtube.com/channel/"
intext:"twitter.com/"
intext:"facebook.com/"
intext:"instagram.com/"
intext:"tiktok.com/"
intext:"linkedin.com/in/" OR intext:"linkedin.com/company/"
```

Prepare a template as [social_media_template.json](https://github.com/ivan-sincek/chad/blob/main/src/templates/social_media_template.json) file:

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
      "validate":"Invite Invalid"
   },
   "youtube":{
      "extract":"youtube\\.com\\/(?:c|channel)\\/[\\w\\d\\.\\_\\-\\+\\@]+(?<!\\.)",
      "extract_prepend":"https://www.",
      "validate":"This page isn't available\\."
   },
   "twitter":{
      "extract":"(?<!pic\\.)twitter\\.com\\/(?:(?!(?:explore|hashtag|home|i|intent|personalization|search|share|tos|widgets\\.js|[\\w]+\\/(?:privacy|tos))(?:$|(?:\\/|\\?)[^\\s]))[\\w\\d\\.\\_\\-\\+\\@]+)(?<!\\.)",
      "extract_prepend":"https://",
      "validate":"This account doesn.?t exist"
   },
   "facebook":{
      "extract":"facebook\\.com\\/(?:(?!(?:about|dialog|gaming|groups|sharer|share\\.php|terms\\.php)(?:$|(?:\\/|\\?)[^\\s]))[\\w\\d\\.\\_\\-\\+\\@]+)(?<!\\.)",
      "extract_prepend":"https://www.",
      "validate":"This page isn't available"
   },
   "instagram":{
      "extract":"instagram\\.com\\/(?:(?!(?:about|accounts|ar|explore|p)(?:$|(?:\\/|\\?)[^\\s]))[\\w\\d\\.\\_\\-\\+\\@]+)(?<!\\.)",
      "extract_prepend":"https://www.",
      "extract_append":"/",
      "validate":"Sorry, this page isn't available\\."
   },
   "tiktok":{
      "extract":"(?<!vt\\.)tiktok\\.com\\/\\@[\\w\\d\\.\\_\\-\\+\\@]+(?<!\\.)",
      "extract_prepend":"https://www.",
      "validate":"<title.*> \\| TikTok<\\/title>"
   },
   "linkedin-company":{
      "extract":"linkedin\\.com\\/company\\/[\\w\\d\\.\\_\\-\\+\\@\\&]+(?<!\\.)",
      "extract_prepend":"https://hr.",
      "validate":"Page not found"
   },
   "linkedin-user":{
      "extract":"linkedin\\.com\\/in\\/[\\w\\d\\.\\_\\-\\+\\@\\&]+(?<!\\.)",
      "extract_prepend":"https://hr.",
      "validate":"An exact match for .+ could not be found\\."
   }
}
```

**Make sure your regular expressions return only one capturing group e.g. `[1, 2, 3, 4]`; and not a touple e.g. `[(1, 2), (3, 4)]`.**

Make sure to properly escape regular expression specific symbols in your template file, e.g. make sure to escape dot `.` as `\\.`, and forward slash `/` as `\\/`, etc.

All regular expression searches are case-insensitive.

Web content fetched from the URLs in Chad results will be matched against all the regular expressions (`extract` attributes) in the template file in order to find as much relevant data as possible.

To extract data without validating it, omit `validate` attributes from the template file as necessary.

### Basic Use (Single Domain)

```bash
chad -q social_media_dorks.txt -s *.example.com -tr 200 -o results.json

chad-extractor -t social_media_template.json -res results.json -o results_report.json
```

Manually check if social media URLs in `summary --> validated` are available for takeover:

```json
{
   "started_at":"2023-12-24 03:30:10",
   "summary":{
      "validated":[
         "https://t.me/does_not_exist"
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

### Advanced Use (Multiple Domains)

Prepare sites/domains/subdomains as `sites.txt` file:

```fundamental
*.example.com
*.example.com -www
```

Prepare bot-safe user agents as `user_agents.txt` file, where `<your-api-key>` is your API key from [scrapeops.io](https://scrapeops.io):

```python
python3 -c 'import json, requests; open("user_agents.txt", "w").write(("\n").join(requests.get("http://headers.scrapeops.io/v1/user-agents?api_key=<your-api-key>&num_results=100", verify = False).json()["result"]))'
```

Automate:

```bash
mkdir results

IFS=$'\n'; count=0; for site in $(cat sites.txt); do count=$((count+1)); echo "#${count} | ${site}"; chad -q social_media_dorks.txt -s "${site}" -tr 200 -a user_agents.txt -o "results/results_${count}.json"; done

chad-extractor -t social_media_template.json -res results -a user_agents.txt -o results_report.json -v yes
```

## Rate Limiting

Google's cooling-off period can be from a few hours to a whole day.

To avoid hitting Google's rate limit with Chad, increase the minimum and maximum sleep between Google queries and/or pages; or use proxies \([1](https://geonode.com/free-proxy-list)\)\([2](https://proxyscrape.com/home)\), although, free proxies are not always stable.

To download a list of free proxies, run:

```bash
curl -s 'https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc' -H 'Referer: https://proxylist.geonode.com/' | jq -r '.data[] | "\(.protocols[])://\(.ip):\(.port)"' > proxies.txt
```

Additionally, to avoid hitting e.g. Instagram's rate limit with Chad Extractor, you might want to isolate it in a separate run, increase the wait time, and use only one thread.

## Usage

```fundamental
Chad v5.1 ( github.com/ivan-sincek/chad )

Usage:   chad -q queries     [-s site         ] [-a agents         ] [-p proxies    ] [-o out         ]
Example: chad -q queries.txt [-s *.example.com] [-a user_agents.txt] [-p proxies.txt] [-o results.json]

DESCRIPTION
    Search Google Dorks like Chad
QUERIES
    File with Google Dorks or a single query to use
    -q <queries> - queries.txt | intext:password | "ext:tar OR ext:zip" | etc.
SITE
    Domain[s] to search
    -s <site> - example.com | sub.example.com | *.example.com | "*.example.com -www" | etc.
TIME
    Get results not older than the specified time in months
    -t <time> - 6 | 12 | 24 | etc.
TOTAL RESULTS
    Total number of unique results
    Default: 100
    -tr <total-results> - 200 | etc.
PAGE RESULTS
    Number of results per page - capped at 100 by Google
    Default: randint(75, 100) per page
    -pr <page-results> - 50 | etc.
MINIMUM QUERIES
    Minimum sleep between Google queries
    Default: 75
    -min-q <minimum-queries> - 120 | etc.
MAXIMUM QUERIES
    Maximum sleep between Google queries
    Default: minimum-queries + 50
    -max-q <maximum-queries> - 180 | etc.
MINIMUM PAGES
    Minimum sleep between Google pages
    Default: 15
    -min-p <minimum-pages> - 30 | etc.
MAXIMUM PAGES
    Maximum sleep between Google pages
    Default: minimum-pages + 10
    -max-p <maximum-pages> - 60 | etc.
AGENTS
    File with user agents to use
    Default: random
    -a <agents> - user_agents.txt | etc.
PROXIES
    File with proxies or a single proxy to use
    -p <proxies> - proxies.txt | http://127.0.0.1:8080 | etc.
DIRECTORY
    Downloads directory
    All downloaded files will be saved in this directory
    -d <directory> - downloads | etc.
THREADS
    Number of parallel files to download
    Default: 5
    -th <threads> - 20 | etc.
OUT
    Output file
    -o <out> - results.json | etc.
SLEEP ON START
    Safety feature to prevent accidental rate limit triggering
    -sos <sleep-on-start> - no 
DEBUG
    Debug output
    -dbg <debug> - yes
```

```fundamental
Chad Extractor v5.1 ( github.com/ivan-sincek/chad )

Usage:   chad-extractor -t template      -res results -o out                 [-th threads] [-r retries] [-w wait] [-a agents         ]
Example: chad-extractor -t template.json -res results -o results_report.json [-th 10     ] [-r 5      ] [-w 10  ] [-a user_agents.txt]

DESCRIPTION
    Extract and validate data from Chad results or plaintext files
TEMPLATE
    JSON template file with extraction and validation information
    -t <template> - template.json | etc.
RESULTS DIRECTORY/FILE
    Directory containing Chad results or plaintext files, or a single file
    Files ending with '.report.json' will be ignored
    -res <results> - results | results.json | urls.txt | etc.
PLAINTEXT
    Treat files as plaintext
    -pt <plaintext> - yes
EXCLUDES
    File with regular expressions or a single expression to exclude the page content
    Applies only on extraction
    -e <excludes> - regexes.txt | "<div id=\"seo\">.+?<\/div>" | etc.
THREADS
    Number of parallel headless browsers to run
    Default: 4
    -th <threads> - 10 | etc.
RETRIES
    Number of retries per URL
    Default: 2
    -r <retries> - 5 | etc.
WAIT
    Wait before returning the page content
    Default: 4
    -w <wait> - 10 | etc.
AGENTS
    File with user agents to use
    Default: random
    -a <agents> - user_agents.txt | etc.
PROXY
    Web proxy to use
    -p <proxy> - http://127.0.0.1:8080 | etc.
OUT
    Output file
    -o <out> - results_report.json | etc.
VERBOSE
    Create additional supporting output files
    -v <verbose> - yes
DEBUG
    Debug output
    -dbg <debug> - yes
```

## Images

<p align="center"><img src="https://github.com/ivan-sincek/chad/blob/main/img/basic_example.png" alt="Basic Example"></p>

<p align="center">Figure 1 - Basic Example</p>

<p align="center"><img src="https://github.com/ivan-sincek/chad/blob/main/img/advanced_example.png" alt="Advanced Example"></p>

<p align="center">Figure 2 - Advanced Example</p>
