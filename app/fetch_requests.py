# app/fetch_requests.py

import requests
from datetime import datetime

BASE_URL = "https://in-tendhost.co.uk/gggi/aspx/Services/Projects.svc/GetProjects"

def fetch_page_requests(page_no: int) -> dict:
    params = {
        "strMode": "Current",
        "searchvalue": "",
        "bUseSearch": "false",
        "OrderBy": "Title",
        "OrderDirection": "ASC",
        "iPage": page_no,
        "iPageSize": 50,
        "bOnlyWithCorrespondenceAllowed": "false",
        "iCustomerFilter": 0,
        "iOptInStatus": -1,
        "_": int(datetime.now().timestamp() * 1000)
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://in-tendhost.co.uk/gggi/aspx/Tenders/Current",
        "X-Requested-With": "XMLHttpRequest"
    }

    r = requests.get(BASE_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()

    if not r.text.strip().startswith("{"):
        raise RuntimeError("Blocked by upstream")

    return r.json()
