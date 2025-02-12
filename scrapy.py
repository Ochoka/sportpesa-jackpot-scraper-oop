# Import needed libraries
import requests
import random
import time
import json
import pandas as pd
from datetime import datetime, timezone
from tqdm import tqdm
from fake_useragent import UserAgent

class SportPesaScraper:
    def __init__(self, start_year, end_year, start_month, end_month):
        """Initialize the scraper with time range and required attributes."""
        self.start_year = start_year
        self.end_year = end_year
        self.start_month = start_month
        self.end_month = end_month

        self.jackpot_data = []
        self.scraped_jackpot_ids = set()
        self.failed_timestamps = []  # List of failed timestamp URLs
        self.failed_jackpots = []  # List of failed jackpot URLs
        self.failed_headers = set()  # Track failed headers
        self.timestamps_for = self.generate_timestamps()

    def get_random_headers(self):
        """Generate a random User-Agent header and ensure it's not from failed headers."""
        ua = UserAgent()
        while True:
            new_header = {"User-Agent": ua.random}
            if new_header["User-Agent"] not in self.failed_headers:
                return new_header

    def timestamps(self, year, month):
        """Generate timestamps for given year and month in UTC+3 (EAT)."""
        if month == 12:
            next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        last_millisecond_utc = int((next_month.timestamp() - 0.001) * 1000)
        last_millisecond_eat = last_millisecond_utc - (3 * 60 * 60 * 1000)
        return last_millisecond_eat

    def generate_timestamps(self):
        """Generate a list of timestamps for the given time range."""
        timestamps_for = []
        for year in range(self.start_year, self.end_year + 1):
            month_range_start = self.start_month if year == self.start_year else 1
            month_range_end = self.end_month if year == self.end_year else 12
            for month in range(month_range_start, month_range_end + 1):
                timestamps_for.append(self.timestamps(year, month))
        return timestamps_for

    def convert_timestamp_to_date(self, timestamp):
        """Convert a timestamp to YYYY-MM format."""
        timestamp = int(timestamp)
        datetime_obj_eat = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
        return datetime_obj_eat.strftime('%Y-%m')

    def fetch_archive(self, timestamp):
        """Fetch the jackpot archive for a given timestamp."""
        url_archive = f"https://jackpot-betslip.ke.sportpesa.com/api/jackpots/history?to={timestamp}&pageNum=0&pageSize=20"
        success = False

        for attempt in range(1, 11):
            headers = self.get_random_headers()
            response = requests.get(url_archive, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                self.failed_headers.add(headers["User-Agent"])

            time.sleep(random.uniform(3, 5))

        self.failed_timestamps.append(url_archive)
        print(f"All 10 header attempts failed for jackpot played on: {self.convert_timestamp_to_date(timestamp)}")
        return None

    def fetch_jackpot_details(self, jackpot_id, timestamp=None):
        """Fetch details for a given jackpot ID."""
        url_details = f"https://jackpot-betslip.ke.sportpesa.com/api/jackpots/history/{jackpot_id}/details"
        success = False

        for attempt in range(1, 11):
            headers = self.get_random_headers()
            response = requests.get(url_details, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                self.failed_headers.add(headers["User-Agent"])

        self.failed_jackpots.append(url_details)
        print(f"All 10 header attempts failed for jackpot ({jackpot_id}) "
              f"on {self.convert_timestamp_to_date(timestamp)}")
        return None

    def scrape(self):
        """Main method to scrape jackpot archives and details."""
        for timestamp in tqdm(self.timestamps_for, desc="Fetching Jackpot Archives"):
            archive_data = self.fetch_archive(timestamp)
            if archive_data is None:
                continue

            jackpot_ids = [item["jackpotId"] for item in archive_data]
            unique_jackpot_ids = [jid for jid in jackpot_ids if jid not in self.scraped_jackpot_ids]

            time.sleep(random.uniform(3, 5))

            for i, jackpot in enumerate(unique_jackpot_ids):
                jackpot_details = self.fetch_jackpot_details(jackpot)
                if jackpot_details is None:
                    continue

                self.scraped_jackpot_ids.add(jackpot)
                events = jackpot_details.get("events", [])

                for event in events:
                    self.jackpot_data.append({
                        "jackpotId": jackpot,
                        "eventNumber": event["eventNumber"],
                        "kickoffTime": event["kickoffTime"],
                        "competitorHome": event["competitorHome"],
                        "competitorAway": event["competitorAway"],
                        "resultPick": event.get("resultPick", ""),
                        "score": event.get("score", "")
                    })

                time.sleep(random.uniform(3, 7))

        self.save_results()

    def save_results(self):
        """Save scraped data and failed URLs to CSV and JSON files."""
        historical_jackpots = pd.DataFrame(self.jackpot_data)
        historical_jackpots.to_csv('hist_jackport17.csv', index=False)

        with open("failed_timestamps.json", "w") as f:
            json.dump(self.failed_timestamps, f, indent=4)

        with open("failed_jackpots.json", "w") as f:
            json.dump(self.failed_jackpots, f, indent=4)

        print("\nScraping complete.")
        print(f"Total failed timestamp URLs: {len(self.failed_timestamps)}")
        print(f"Total failed jackpot URLs: {len(self.failed_jackpots)}")

# Run the scraper
if __name__ == "__main__":
    scraper = SportPesaScraper(start_year=2023, end_year=2023,
                               start_month=3, end_month=6)
    scraper.scrape()
