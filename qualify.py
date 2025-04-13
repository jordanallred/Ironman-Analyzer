import requests
from bs4 import BeautifulSoup
import json
import re


urls = [
    "https://www.ironman.com/races/im-world-championship-kona/qualifying-events-2025",
    "https://www.ironman.com/races/im703-world-championship-2025/qualfying-events-2025",
]


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


output_data = {
    "slots": {},
}


def clean_text(text):
    """Remove extra whitespace and non-breaking spaces from text."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ").strip())


def scrape_table(url):
    """Scrape qualifying slots from the table at the given URL."""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table")
        if not table:
            print(f"No table found at {url}")
            return

        rows = table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            race_name = clean_text(cells[0].get_text())
            race_date = clean_text(cells[1].get_text())
            location = clean_text(cells[2].get_text())
            women_slots = clean_text(cells[3].get_text())
            men_slots = clean_text(cells[4].get_text())

            men_slots = int(men_slots) if men_slots.isdigit() else 0
            women_slots = int(women_slots) if women_slots.isdigit() else 0

            output_data["slots"][race_name] = {
                "date": race_date,
                "location": location,
                "men_slots": men_slots,
                "women_slots": women_slots,
            }

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
    except Exception as e:
        print(f"Error processing {url}: {e}")


if __name__ == "__main__":
    scrape_table(urls[0])
    scrape_table(urls[1])

    try:
        with open("qualifying_slots.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4)
        print("Data saved to qualifying_slots.json")
    except Exception as e:
        print(f"Error saving JSON: {e}")
