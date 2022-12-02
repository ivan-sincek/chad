# Chad

Search Google Dorks like Chad. Based on [ivan-sincek/nagooglesearch](https://github.com/ivan-sincek/nagooglesearch).

Tested on Kali Linux v2022.4 (64-bit).

Made for educational purposes. I hope it will help!

Future plans:

* remove `jq` from `chad-extractor` so it can be OS independent.

## Table of Contents

* [How to Install](#how-to-install)
* [How to Build and Install Manually](#how-to-build-and-install-manually)
* [Shortest Possible](#shortest-possible)
* [Basic Example: File Download](#basic-example-file-download)
* [Chad Extractor](#chad-extractor)
* [Advanced Example: Social Media Takover](#advanced-example-social-media-takover)
    * [Basic Use (Single Domain)](#basic-use-single-domain)
    * [Advanced Use (Multiple Domains)](#advanced-use-multiple-domains)
* [Rate Limiting](#rate-limiting)
* [Usage](#usage)

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

python3 -m pip install dist/google_chad-2.6.2-py3-none-any.whl

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

chad -q "ext:pdf OR ext:docx OR ext:xlsx OR ext:pptx" -s *.example.com -tr 200 -d downloads -sos no
```

`-s <site>` is optional. For more information, see [Usage](#usage).

`chad` file download feature is based on Python Requests library.

## Chad Extractor

`chad-extractor` is a powerful tool based on [Playwright](https://playwright.dev/python) Chromium headless browser created to efficiently scrape web, to compensate for Python Requests library which cannot render JavaScript encoded HTML and is easily blocked by anti-bot solutions.

## Advanced Example: Social Media Takover

Prepare Google Dorks as `social_media_dorks.txt` file:

```fundamental
intext:"t.me/"
intext:"discord.com/invite/"
intext:"youtube.com/c/" OR intext:"youtube.com/channel/"
intext:"twitter.com/"
intext:"instagram.com/"
intext:"facebook.com/"
intext:"linkedin.com/in/" OR intext:"linkedin.com/company/"
```

Prepare a template as `social_media_template.json` file:

```json
{
   "telegram":{
      "extract":"t\\.me\\/[\\w\\d\\-\\+]+",
      "extract_prepend":"https://",
      "validate":"<meta property=\"og:title\" content=\"Telegram: Contact .+?\">"
   },
   "discord":{
      "extract":"discord\\.com\\/invite\\/[\\w\\d\\-\\+\\.]+(?<!\\.)",
      "extract_prepend":"https://",
      "validate":"Invite Invalid"
   },
   "youtube":{
      "extract":"youtube\\.com\\/(?:c|channel)\\/[\\w\\d\\-\\+\\.]+(?<!\\.)",
      "extract_prepend":"https://",
      "validate":"This page isn't available\\."
   },
   "twitter":{
      "extract":"(?<!pic\\.)twitter\\.com\\/(?:(?!(?:hashtag|i|intent|share)(?:\\/|\\?)[^\\s]+|[\\w]+\\/(?:privacy|tos)|widgets\\.js)[\\w\\d\\-\\+]+)",
      "extract_prepend":"https://",
      "validate":"This account doesn.?t exist"
   },
   "instagram":{
      "extract":"instagram\\.com\\/(?:(?!(?:p|accounts)(?:\\/|\\?)[^\\s]+)[\\w\\d\\-\\+\\.]+)(?<!\\.)",
      "extract_prepend":"https://",
      "extract_append":"/",
      "validate":"Sorry, this page isn't available\\."
   },
   "facebook":{
      "extract":"facebook\\.com\\/(?:(?!(?:about|groups|sharer)(?:\\/|\\?)[^\\s]+|share\\.php)[\\w\\d\\-\\+\\.]+)(?<!\\.)",
      "extract_prepend":"https://",
      "validate":"This page isn't available"
   },
   "linkedin-company":{
      "extract":"linkedin\\.com\\/company\\/[\\w\\d\\-\\+\\.]+(?<!\\.)",
      "extract_prepend":"https://hr.",
      "validate":"Page not found"
   },
   "linkedin-user":{
      "extract":"linkedin\\.com\\/in\\/[\\w\\d\\-\\+\\.]+(?<!\\.)",
      "extract_prepend":"https://hr.",
      "validate":"An exact match for .+ could not be found\\."
   }
}
```

**Make sure your regular expressions return only one capturing group, e.g. `[1, 2, 3]`; and not touple, e.g. `[(1, 2), (3, 4), (5, 6)]`.**

Make sure to properly escape regular expression specific symbols in your template file, e.g. make sure to escape `.` (dot) as `\.` or as `\\.` if using double quotes, and `/` (forward slash) as `\/` or as `\\/` respectively, etc.

**All regular expression searches are case-insensitive.**

Content fetched from the initial Chad results (i.e. URLs) will be matched against all the regular expressions (`extract` attributes) in the template file in order to find as much relevant information as possible.

To extract information without validating it, omit `validate` attributes from the template as necessary.

### Basic Use (Single Domain)

```bash
chad -q social_media_dorks.txt -s *.example.com -tr 200 -o results.json -sos no

chad-extractor -t social_media_template.json -res results.json -o results_report.json
```

### Advanced Use (Multiple Domains)

Prepare sites as `sites.txt` file:

```fundamental
*.example.com
*.example.com -www
```

Prepare user agents to avoid blocks/bans as `user_agents.txt` file; where `<your-api-key>` is your API key from [scrapeops.io](https://scrapeops.io):

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

To avoid hitting the rate limit, increase minimum and maximum sleep between queries.

Cooling-off period can be from a few hours to a whole day.

## Usage

```fundamental
Chad v2.6.2 ( github.com/ivan-sincek/chad )

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
MINIMUM
    Minimum sleep between queries
    Default: 75
    -min <minimum> - 120 | etc.
MAXIMUM
    Maximum sleep between queries
    Default: minimum + 50
    -max <maximum> - 180 | etc.
AGENTS
    File with user agents to use
    Default: nagooglesearch user agents
    -a <agents> - user_agents.txt | etc.
PROXIES
    File with proxies to use
    -p <proxies> - proxies.txt | etc.
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
Chad Extractor v2.6.2 ( github.com/ivan-sincek/chad )

Usage:   chad-extractor -t template      -res results -o out                 [-th threads] [-r retries] [-w wait] [-a agents         ]
Example: chad-extractor -t template.json -res results -o results_report.json [-th 10     ] [-r 5      ] [-w 10  ] [-a user_agents.txt]

DESCRIPTION
    Extract and validate data from Chad results
TEMPLATE
    JSON template file with extract and validate information
    -t <template> - template.json | etc.
RESULTS FILE/DIRECTORY
    Chad results file/directory
    -res <results> - results | results.json | etc.
THREADS
    Number of parallel headless browsers to run
    Default: 4
    -th <threads> - 10 | etc.
RETRIES
    Number of retries per URL
    Default: 2
    -r <retries> - 5 | etc.
WAIT
    Wait before fetching the page content
    Default: 4
    -w <wait> - 10 | etc.
AGENTS
    File with user agents to use
    Default: nagooglesearch user agents
    -a <agents> - user_agents.txt | etc.
OUT
    Output file
    -o <out> - results_report.json | etc.
VERBOSE
    Create additional supporting output files
    -v <verbose> - yes
```
