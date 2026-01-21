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
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Language": "en-US,en;q=0.9"
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=headers,
        timeout=30
    )

    print("STATUS:", response.status_code)
    print("HEADERS:", response.headers.get("Content-Type"))
    print("BODY (first 500 chars):", response.text[:500])

    if response.status_code != 200:
        raise RuntimeError("Upstream blocked request")

    if not response.text.strip():
        raise RuntimeError("Empty response from upstream")

    if not response.text.strip().startswith("{"):
        raise RuntimeError("Non-JSON response (HTML / WAF)")

    return response.json()

# -----------------------------
# Frontend Page
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# -----------------------------
# Excel Generator Endpoint
# -----------------------------
from fastapi import HTTPException

@app.get("/download-excel")
def download_excel():
    try:
        all_rows = []
        seen_ids = set()

        first_page = fetch_page(1)
        total_pages = first_page.get("PageCount", 1)

        for page in range(1, total_pages + 1):
            data = fetch_page(page).get("Data", [])

            for item in data:
                uid = item.get("UniqueID")
                if uid in seen_ids:
                    continue
                seen_ids.add(uid)

                all_rows.append({
                    "ProjectID": item.get("ProjectID"),
                    "UniqueID": uid,
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
            headers={"Content-Disposition": "attachment; filename=gggi_tenders.xlsx"}
        )

    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(
            status_code=502,
            detail="Upstream procurement site blocked this request from cloud IP"
        )
