from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
import pandas as pd
import argparse

@dataclass
class Business:
    """Holds business data"""

    name: str = None
    address: str = None
    website: str = None
    phone_number: str = None
    reviews_count: int = None
    reviews_average: float = None

@dataclass
class BusinessList:
    business_list: list[Business] = field(default_factory=list)
    
    def dataframe(self):
        return pd.json_normalize((asdict(business) for business in self.business_list), sep="_")

    def save_to_excel(self, filename):
        self.dataframe().to_excel(f"{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        self.dataframe().to_csv(f"{filename}.csv", index=False)

def main(search_for, total, filename):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        page.wait_for_timeout(5000)

        page.locator('//input[@id="searchboxinput"]').fill(search_for)
        page.wait_for_timeout(3000)

        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)

        page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

        previously_counted = 0
        while True:
            page.mouse.wheel(0, 10000)
            page.wait_for_timeout(3000)

            if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() >= total:
                listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:total]
                listings = [listing.locator("xpath=..") for listing in listings]
                print(f"Total Scraped: {len(listings)}")
                break
            else:
                if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() == previously_counted:
                    listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
                    print(f"Arrived at all available listings\nTotal Scraped: {len(listings)}")
                    break
                else:
                    previously_counted = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                    print(f"Currently Scraped: {previously_counted}")

        business_list = BusinessList()

        for listing in listings:
            try:
                listing.click()
                page.wait_for_timeout(5000)  # Wait for the business details to load

                name_xpath = '//h1[contains(@class, "DUwDvf")]'
                address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
                phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                reviews_span_xpath = '//span[@role="img" and contains(@aria-label, "stars")]'

                business = Business()

                if page.locator(name_xpath).count() > 0:
                    business.name = page.locator(name_xpath).inner_text()
                else:
                    business.name = "Unknown"

                if page.locator(address_xpath).count() > 0:
                    business.address = page.locator(address_xpath).inner_text()
                else:
                    business.address = ""
                if page.locator(website_xpath).count() > 0:
                    business.website = page.locator(website_xpath).inner_text()
                else:
                    business.website = ""
                if page.locator(phone_number_xpath).count() > 0:
                    business.phone_number = page.locator(phone_number_xpath).inner_text()
                else:
                    business.phone_number = ""

                # Extract reviews
                page.wait_for_timeout(2000)  # Wait to ensure the reviews are fully loaded
                try:
                    review_element = page.locator(reviews_span_xpath).first
                    aria_label = review_element.get_attribute("aria-label")
                    print(f"DEBUG: Extracted aria-label: {aria_label}")
                    
                    if "stars" in aria_label and "Reviews" in aria_label:
                        business.reviews_average = float(aria_label.split()[0].replace(",", ".").strip())
                        business.reviews_count = int(aria_label.split()[2].replace(",", "").strip())
                except Exception as e:
                    print(f"Could not extract review data: {e}")
                    business.reviews_average = None
                    business.reviews_count = None

                # Print the business object to debug
                print(asdict(business))

                business_list.business_list.append(business)

            except Exception as e:
                print(f"An error occurred: {e}")
        
        business_list.save_to_excel(filename)
        business_list.save_to_csv(filename)

        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str, help="Search query")
    parser.add_argument("-t", "--total", type=int, help="Total number of listings to scrape")
    parser.add_argument("-f", "--filename", type=str, help="Output filename", default="google_maps_data")
    args = parser.parse_args()

    search_for = args.search if args.search else "restaurants Bhubaneshwar"
    total = args.total if args.total else 10
    filename = args.filename

    main(search_for, total, filename)
