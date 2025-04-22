import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

load_dotenv()

SESSION_PATH = "session_storage.json"
LOGIN_URL = "https://hiring.idenhq.com/"
USERNAME = os.getenv("IDEN_EMAIL")
PASSWORD = os.getenv("IDEN_PASSWORD")

def save_storage(context):
    context.storage_state(path=SESSION_PATH)

def load_or_login(playwright):
    browser = playwright.chromium.launch(headless=False)

    if os.path.exists(SESSION_PATH):
        context = browser.new_context(storage_state=SESSION_PATH)
        print("Session loaded")
    else:
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL)

        page.fill('input[type="email"]', USERNAME)
        page.fill('input[type="password"]', PASSWORD)
        page.click('button:has-text("Login")')
        page.wait_for_url("**/dashboard", timeout=10000)

        save_storage(context)
        print("Logged in and session saved")

    return context

def navigate_to_table(page):
    try:
        page.click("text=Dashboard")
        page.click("text=Inventory")
        page.click("text=Catalog")
        page.click("text=View Complete Data")
        page.wait_for_selector("div[data-testid='product-card']")
        print("Navigation complete")
    except PlaywrightTimeoutError:
        print("Navigation failed - element not found")

def extract_product_data(page):
    product_data = []
    page.wait_for_timeout(1000)

    while True:
        cards = page.query_selector_all("div[data-testid='product-card']")
        print(f"Found {len(cards)} cards on current page")

        for card in cards:
            try:
                title = card.query_selector("div >> nth=0").inner_text()
                props = card.query_selector_all("div >> nth=1 >> div")
                data = {
                    "title": title.strip(),
                    "id": props[0].inner_text().split(":")[-1].strip(),
                    "color": props[1].inner_text().split(":")[-1].strip(),
                    "manufacturer": props[2].inner_text().split(":")[-1].strip(),
                    "description": props[3].inner_text().split(":")[-1].strip()
                }
                product_data.append(data)
            except Exception as e:
                print("Error parsing card:", e)

        # Handle pagination if "Next" exists
        next_button = page.query_selector("button:has-text('Next')")
        if next_button and next_button.is_enabled():
            next_button.click()
            page.wait_for_timeout(1000)
        else:
            break

    return product_data

def export_to_json(data, filename="product_inventory.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Exported {len(data)} products to {filename}")

def main():
    with sync_playwright() as playwright:
        context = load_or_login(playwright)
        page = context.new_page()
        page.goto("https://hiring.idenhq.com/challenge")

        navigate_to_table(page)
        product_data = extract_product_data(page)
        export_to_json(product_data)

        context.close()

if __name__ == "__main__":
    main()
