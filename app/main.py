from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import pandas as pd
from datetime import datetime
import re
from io import BytesIO

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

BASE_URL = "https://in-tendhost.co.uk/gggi/aspx/Services/Projects.svc/GetProjects"

# -----------------------------
# Helper: Convert ASP.NET date
# -----------------------------
def parse_dotnet_date(value):
    if not value:
        return None
    match = re.search(r"\d+", value)
    if not match:
        return None
    timestamp_ms = int(match.group())
    return datetime.utcfromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")

# -----------------------------
# Fetch one page
# -----------------------------
def fetch_page(page):
    params = {
        "strMode": "Current",
        "searchvalue": "",
        "bUseSearch": "false",
        "OrderBy": "Title",
        "OrderDirection": "ASC",
        "iPage": page,
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

    response = requests.get(
        BASE_URL,
        params=params,
        headers=headers,
        timeout=30
    )

    # 🔍 Defensive debugging
    if response.status_code != 200:
        raise RuntimeError(
            f"Upstream error {response.status_code}: {response.text[:200]}"
        )

    try:
        return response.json()
    except Exception:
        raise RuntimeError(
            f"Non-JSON response received: {response.text[:300]}"
        )


# -----------------------------
# Frontend Page
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# -----------------------------
# Excel Generator Endpoint
# -----------------------------
@app.get("/download-excel")
def download_excel():
    all_rows = []
    seen_ids = set()

    first_page = fetch_page(1)
    total_pages = first_page.get("PageCount", 1)

    for page in range(1, total_pages + 1):
        data = fetch_page(page).get("Data", [])

        for item in data:
            unique_id = item.get("UniqueID")
            if unique_id in seen_ids:
                continue
            seen_ids.add(unique_id)

            all_rows.append({
                "ProjectID": item.get("ProjectID"),
                "UniqueID": unique_id,
                "Reference": item.get("Reference"),
                "Title": item.get("Title"),
                "Customer": item.get("Customer"),
                "Description": item.get("Description"),
                "Deadline": parse_dotnet_date(item.get("DateDocsAvailableUntil")),
                "Type": item.get("Type"),
                "Category": item.get("Category"),
                "UTCTimeZoneName": item.get("UTCTimeZoneName"),
            })

    df = pd.DataFrame(all_rows)

    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="gggi_tenders.xlsx"'
        }
    )
