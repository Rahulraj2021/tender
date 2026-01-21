# app/main.py

from fastapi import FastAPI, Response, HTTPException
import pandas as pd
from io import BytesIO

from app.fetch_requests import fetch_page_requests
from app.fetch_playwright import fetch_page_playwright

app = FastAPI()

def fetch_page(page_no: int) -> dict:
    try:
        return fetch_page_requests(page_no)
    except Exception:
        return fetch_page_playwright(page_no)

@app.get("/download-excel")
def download_excel():
    try:
        first_page = fetch_page(1)
        total_pages = first_page.get("PageCount", 1)

        rows = []
        seen = set()

        for p in range(1, total_pages + 1):
            data = fetch_page(p).get("Data", [])
            for item in data:
                uid = item.get("UniqueID")
                if uid in seen:
                    continue
                seen.add(uid)

                rows.append({
                    "ProjectID": item.get("ProjectID"),
                    "UniqueID": uid,
                    "Reference": item.get("Reference"),
                    "Title": item.get("Title"),
                    "Customer": item.get("Customer"),
                    "Deadline": item.get("DateDocsAvailableUntil"),
                    "Type": item.get("Type"),
                    "Category": item.get("Category"),
                    "UTCTimeZoneName": item.get("UTCTimeZoneName"),
                })

        df = pd.DataFrame(rows)
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        return Response(
            buffer.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=gggi_tenders.xlsx"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=str(e)
        )
