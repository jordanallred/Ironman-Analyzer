import datetime

import requests
from bs4 import BeautifulSoup
import time
import os
import json
import re
import argparse
from urllib.parse import urljoin
from rich.console import Console
from rich.logging import RichHandler
import logging


console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console)],
)
log = logging.getLogger("rich")

BASE_URL = "https://www.ironman.com"
RACES_URL = f"{BASE_URL}/races"
RESULTS_API = "https://labs-v2.competitor.com/api/results"
EVENTS_API = "https://labs-v2.competitor.com/results/event"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRONMANResultsBot/1.0; +https://www.ironman.com)"
}

RACE_TYPES = [
    "IRONMAN 70.3",
    "IRONMAN",
    "Short Course Tri",
    "Pro Series",
    "World Championship",
    "5150 and International",
]

REGIONS = [
    "Europe",
    "North America",
    "Latin America",
    "Asia",
    "Oceania",
    "Africa",
    "Canada",
    "Middle East",
]


def build_filter_url(race_types=None, regions=None, page=1):
    """
    Build a URL with the appropriate filter parameters

    Args:
        race_types (list): List of race types to filter by
        regions (list): List of regions to filter by
        page (int): Page number

    Returns:
        str: URL with filter parameters
    """
    params = []

    if race_types:
        for idx, race_type in enumerate(race_types):
            params.append(f"facet[{idx}]=race:{race_type}")

    if regions:
        start_idx = len(params)
        for idx, region in enumerate(regions):
            params.append(f"facet[{idx + start_idx}]=region:{region}")

    if page > 0:
        params.append(f"page={page}")

    if params:
        return f"{RACES_URL}?{'&'.join(params)}"
    else:
        return RACES_URL


def get_race_links(race_types=None, regions=None, max_pages=None):
    """
    Fetch race links from the IRONMAN website with optional filters

    Args:
        race_types (list): List of race types to filter by
        regions (list): List of regions to filter by
        max_pages (int): Maximum number of pages to fetch (None for all)

    Returns:
        list: List of race URLs
    """
    race_links = []
    page = 0

    while True:
        if max_pages and page > max_pages:
            log.debug(f"Reached maximum page limit ({max_pages})")
            break

        url = build_filter_url(race_types, regions, page)
        log.debug(f"Fetching race list page {page}...")
        log.debug(f"URL: {url}")

        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            log.warning(
                f"Failed to fetch page {page}. Status code: {response.status_code}"
            )
            break

        soup = BeautifulSoup(response.text, "html.parser")
        race_cards = soup.select("div.races-search-view__cards-row article")

        if not race_cards:
            log.debug("No more races found.")
            break

        found_races = 0
        for card in race_cards:
            link_tag = card.find("a", href=True)
            if link_tag:
                race_url = urljoin(BASE_URL, link_tag["href"])
                race_links.append(race_url)
                found_races += 1

        log.debug(f"Found {found_races} races on page {page}")
        if found_races == 0:
            break

        page += 1
        time.sleep(1)

    log.info(f"Total races found: {len(race_links)}")
    return race_links


def extract_competitor_api_url(race_url):
    """
    Get the competitor API URL by monitoring network requests when accessing the race page

    Workflow:
    1. Visit the race results page
    2. Extract the competitor API URL from the HTML or network requests
    """
    results_url = f"{race_url}/results"
    log.debug(f"Visiting race page to extract competitor API URL: {results_url}")

    response = requests.get(results_url, headers=HEADERS)
    if response.status_code != 200:
        log.warning(
            f"Failed to fetch race page: {results_url}. Status code: {response.status_code}"
        )
        return None

    html = response.text

    match = re.search(
        r"https://labs-v2\.competitor\.com/results/event/([a-f0-9-]{36})", html
    )
    if match:
        event_id = match.group(1)
        log.info(f"Found latest event ID: {event_id}")
        return f"https://labs-v2.competitor.com/results/event/{event_id}"


def fetch_subevents(competitor_api_url, years):
    """
    Fetch subevents from the competitor API
    """
    response = requests.get(competitor_api_url)
    soup = BeautifulSoup(response.text, "html.parser")

    script_tag = soup.find("script", id="__NEXT_DATA__")
    next_data = json.loads(script_tag.string)

    subevents = next_data["props"]["pageProps"]["subevents"]

    if years:
        filtered_subevents = []
        for subevent in subevents:
            event_date = subevent.get("wtc_eventdate_formatted", "")
            if datetime.datetime.strptime(event_date, "%m/%d/%Y").year in years:
                filtered_subevents.append(subevent)

        return filtered_subevents

    return subevents


def fetch_results(wtc_eventid):
    """
    Fetch results for a specific event ID from the results API
    """
    log.debug(f"Fetching results for event ID: {wtc_eventid}")
    params = {"wtc_eventid": wtc_eventid}
    response = requests.get(RESULTS_API, params=params, headers=HEADERS)
    if response.status_code != 200:
        log.warning(
            f"Failed to fetch results for event ID: {wtc_eventid}. Status code: {response.status_code}"
        )
        return None
    return response.json()


def save_results(data, event_id, event_name=None):
    """
    Save results to a JSON file
    """
    os.makedirs("results", exist_ok=True)

    if event_name:
        event_name = event_name.replace(" ", "_")
        sanitized_name = "".join(c for c in event_name if c.isascii())
        filename = os.path.join("results", f"{sanitized_name}_{event_id}.json")
    else:
        filename = os.path.join("results", f"{event_id}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    log.info(f"Results saved to '{filename}'")


def parse_arguments():
    """
    Parse command-line arguments
    """
    parser = argparse.ArgumentParser(description="IRONMAN Race Results Scraper")

    parser.add_argument(
        "--race",
        help="Specific race URL or path to scrape (e.g., '70.3-coeur-d-alene')",
    )

    parser.add_argument(
        "--race-types",
        nargs="+",
        choices=RACE_TYPES,
        help="Filter by race types (e.g., 'IRONMAN 70.3' 'IRONMAN')",
    )

    parser.add_argument(
        "--regions",
        nargs="+",
        choices=REGIONS,
        help="Filter by regions (e.g., 'North America' 'Europe')",
    )

    parser.add_argument(
        "--years", nargs="+", type=int, help="Filter by years (e.g., '2021' '2024'')"
    )

    parser.add_argument(
        "--max-pages", type=int, help="Maximum number of pages to scrape"
    )

    parser.add_argument(
        "--list-options",
        action="store_true",
        help="List available race types and regions",
    )

    return parser.parse_args()


def main():
    """
    Main function that implements the workflow:
    1. Parse command-line arguments
    2. Fetch races based on filters
    3. For each race, query ironman.com to get the request to labs-v2.competitor.com
    4. Manually perform the query to labs-v2.competitor.com to get all subevents
    5. For each subevent, query the API endpoint for results
    """
    args = parse_arguments()

    if args.list_options:
        log.info(f"Available Race Types:\n- {"\n- ".join(RACE_TYPES)}")

        log.info(f"Available Regions:\n- {"\n- ".join(REGIONS)}")
        return

    log.info(
        f"Fetching races with filters:\n\trace_types={args.race_types}\n\trace_regions={args.regions}\n\tmax_pages={args.max_pages}\n\tyears={args.years}"
    )

    if args.race:
        race_url = args.race
        if not race_url.startswith("http"):
            race_url = f"{BASE_URL}/{race_url}"

        race_links = [race_url]
        log.info(f"Processing single race: {race_url}")
    else:
        race_links = get_race_links(args.race_types, args.regions, args.max_pages)

        if not race_links:
            log.info("No races found with the specified filters.")
            return

    total_subevents = 0
    successful_fetches = 0

    for race_url in race_links:
        try:
            log.info(f"Processing race: {race_url}")

            competitor_api_url = extract_competitor_api_url(race_url)
            if not competitor_api_url:
                log.warning(
                    f"Skipping race, could not determine competitor API URL: {race_url}"
                )
                continue

            subevents = fetch_subevents(competitor_api_url, args.years)
            if subevents:
                total_subevents += len(subevents)
            else:
                log.info(f"No subevents found for race: {race_url}")
                continue

            for subevent in subevents:
                wtc_eventid = subevent.get("wtc_eventid")
                wtc_name = subevent.get("wtc_name")
                event_date = subevent.get("wtc_eventdate_formatted", "")

                if not wtc_eventid:
                    log.info(f"Missing wtc_eventid for subevent: {wtc_name}, skipping.")
                    continue

                log.info(
                    f"Processing subevent:\n\tName: {wtc_name}\n\tDate: {event_date}\n\tID: {wtc_eventid}"
                )

                results = fetch_results(wtc_eventid)
                if results:
                    save_results(results, wtc_eventid, wtc_name)
                    successful_fetches += 1

                time.sleep(1.5)
        except KeyboardInterrupt:
            exit(1)
        except Exception:
            log.warning(f"Failed to fetch results for race: {race_url}", exc_info=True)

    log.info("Scraping completed.")
    log.info(f"Total races processed: {len(race_links)}")
    log.info(f"Total subevents found: {total_subevents}")
    log.info(f"Successfully fetched results: {successful_fetches}")


if __name__ == "__main__":
    main()
