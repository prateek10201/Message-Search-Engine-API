"""
Message Search API - Main Application

This service provides fast search over concierge messages by loading all data
into memory on startup. I chose this approach because the dataset is small enough
(~3000 messages) to fit entirely in RAM, which gives us sub-millisecond search times.

The trade-off is that data is only refreshed when the service restarts, but for
this use case that's acceptable since the source data doesn't change frequently.
"""
import asyncio
import time
from typing import List, Optional
from datetime import datetime

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# Data models - using Pydantic for automatic validation
# This makes sure we always get the right data types

class Message(BaseModel):
    id: str
    user_id: str
    user_name: str
    timestamp: str
    message: str


class SearchResponse(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    items: List[Message]
    query_time_ms: float


# The core of our search engine - keeps everything in memory for speed

class MessageSearchEngine:
    def __init__(self):
        self.messages: List[Message] = []
        self.loaded = False

    async def load_data(self):
        """
        Fetch all messages from the source API when the service starts up.

        I'm using pagination to grab 100 messages at a time since that's what
        the API supports. Added retry logic because the API sometimes rate limits,
        especially if you hit it too fast. The 200ms delay between requests helps
        avoid triggering those limits.

        This only runs once at startup, so even though it takes a few seconds,
        it doesn't affect request latency.
        """
        source_url = "https://november7-730026606190.europe-west1.run.app/messages"
        all_messages = []

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            skip = 0
            limit = 100

            while True:
                print(f"Fetching messages: skip={skip}, limit={limit}")
                try:
                    response = await client.get(
                        source_url,
                        params={"skip": skip, "limit": limit}
                    )

                    if response.status_code != 200:
                        print(f"Error fetching data: {response.status_code}")
                        print(f"Response: {response.text[:200]}")
                        break

                    data = response.json()
                    items = data.get("items", [])

                    if not items:
                        print("No more items to fetch")
                        break

                    print(f"  ✓ Fetched {len(items)} messages")
                    all_messages.extend(items)

                    # Check if we got all messages
                    total = data.get("total", 0)
                    if len(all_messages) >= total:
                        break

                    skip += limit

                    # Add small delay to avoid rate limiting
                    await asyncio.sleep(0.1)  # 100ms delay between requests

                except Exception as e:
                    print(f"Exception fetching data: {e}")
                    import traceback
                    traceback.print_exc()
                    break

                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                all_messages.extend(items)

                # Check if we got all messages
                total = data.get("total", 0)
                if len(all_messages) >= total:
                    break

                skip += limit

        self.messages = [Message(**msg) for msg in all_messages]
        self.loaded = True
        print(f"✓ Loaded {len(self.messages)} messages into memory")

    def search(self, query: str, page: int = 1, limit: int = 10) -> dict:
        """
        Search messages by query string
        Searches in: message content and user_name
        """
        start_time = time.perf_counter()

        if not query or not query.strip():
            # No search query means return everything
            filtered_messages = self.messages
        else:
            # Simple substring search - good enough for this use case
            query_lower = query.lower().strip()
            filtered_messages = [
                msg for msg in self.messages
                if query_lower in msg.message.lower() or
                   query_lower in msg.user_name.lower()
            ]

        # Pagination calculations
        total = len(filtered_messages)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit

        # Grab just the page we need
        page_items = filtered_messages[start_idx:end_idx]

        query_time = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "items": page_items,
            "query_time_ms": round(query_time, 2)
        }


# FastAPI setup - chose this framework because it's fast and has great
# automatic documentation (check out /docs when the server is running)

app = FastAPI(
    title="Message Search API",
    description="Fast search engine for concierge messages",
    version="1.0.0"
)

# Global search engine instance
# Create a single instance that will be shared across all requests
search_engine = MessageSearchEngine()


@app.on_event("startup")
async def startup_event():
    """Load data into memory when service starts"""
    print("🚀 Starting up... Loading data from source API")
    await search_engine.load_data()
    print("✓ Ready to serve requests!")


@app.get("/")
async def root():
    """
    Basic health check endpoint.

    Useful for monitoring and making sure the service is up and has loaded data.
    """
    return {
        "status": "ok",
        "service": "Message Search API",
        "messages_loaded": len(search_engine.messages),
        "ready": search_engine.loaded
    }


@app.get("/search", response_model=SearchResponse)
async def search(
        q: str = Query("", description="Search query (searches in message and user_name)"),
        page: int = Query(1, ge=1, description="Page number (starts at 1)"),
        limit: int = Query(10, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Main search endpoint.

    Searches through message content and user names. Case-insensitive, so
    "Paris", "paris", and "PARIS" all work the same.

    Returns paginated results with metadata about how many total results were
    found and how long the search took.

    If the service is still loading data (shouldn't happen in practice since
    loading is fast), returns a 503 error asking the client to retry.
    """
    if not search_engine.loaded:
        return JSONResponse(
            status_code=503,
            content={"error": "Service is still loading data, please try again in a moment"}
        )

    result = search_engine.search(query=q, page=page, limit=limit)
    return result


@app.get("/stats")
async def stats():
    """
    Get some basic statistics about the loaded data.

    Mostly useful for debugging and verifying that all the data loaded correctly.
    """
    if not search_engine.loaded:
        return {"status": "loading"}

    # Calculate some quick stats
    users = set(msg.user_name for msg in search_engine.messages)

    return {
        "total_messages": len(search_engine.messages),
        "unique_users": len(users),
        "users": sorted(list(users)),
        "loaded": search_engine.loaded
    }

# To run locally: uvicorn main:app --reload
# For production: uvicorn main:app --host 0.0.0.0 --port 8000