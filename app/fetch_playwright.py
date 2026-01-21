# app/fetch_playwright.py

from playwright.sync_api import sync_playwright
from datetime import datetime
import json

BASE_URL = "https://in-tendhost.co.uk/gggi/aspx/Services/Projects.svc/GetProjects"

def fetch_page_playwright(page_no: int) -> dict:
    url = (
        f"{BASE_URL}"
        f"?strMode=Current"
        f"&searchvalue="
        f"&bUseSearch=false"
        f"&OrderBy=Title"
        f"&OrderDirection=ASC"
        f"&iPage={page_no}"
        f"&iPageSize=50"
        f"&bOnlyWithCorrespondenceAllowed=false"
        f"&iCustomerFilter=0"
        f"&iOptInStatus=-1"
        f"&_={int(datetime.now().timestamp() * 1000)}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        # Important: open the real site first
        page.goto(
            "https://in-tendhost.co.uk/gggi/aspx/Tenders/Current",
            wait_until="networkidle"
        )

        response_text = page.evaluate(
            """async (url) => {
                const res = await fetch(url, {
                    headers: {
                        "Accept": "application/json, text/plain, */*",
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });
                return await res.text();
            }""",
            url
        )

        browser.close()

    if not response_text.strip().startswith("{"):
        raise RuntimeError("Playwright returned non-JSON")

    return json.loads(response_text)
