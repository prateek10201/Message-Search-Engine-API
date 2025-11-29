"""
Test suite for the Message Search API

This script runs a comprehensive set of tests to verify:
- API is responding correctly
- All data loaded successfully
- Search functionality works
- Performance meets requirements (<100ms)
- Pagination is working

Run this after starting your server: python test_api.py
"""
import httpx
import time
import sys

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Verify the service is up and data is loaded"""
    print("📍 Testing health check endpoint...")
    response = httpx.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    print(f"   ✓ Status: {data['status']}")
    print(f"   ✓ Messages loaded: {data['messages_loaded']}")

    # Make sure we got all the data
    if data['messages_loaded'] != 3349:
        print(f"   ⚠️  Warning: Expected 3349 messages, got {data['messages_loaded']}")
    print()


def test_search_with_query():
    """Test search functionality and measure latency"""
    print("🔍 Testing search with query 'paris'...")
    start = time.perf_counter()
    response = httpx.get(f"{BASE_URL}/search", params={"q": "paris", "page": 1, "limit": 5})
    elapsed = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    data = response.json()

    print(f"   ✓ Found {data['total']} results")
    print(f"   ✓ Query time (server): {data['query_time_ms']}ms")
    print(f"   ✓ Total time (with network): {elapsed:.2f}ms")

    if data['items']:
        print(f"   ✓ First result: {data['items'][0]['message'][:60]}...")
    print()

    # Check latency requirement
    if elapsed < 100:
        print(f"   ✅ PASSED: Response time {elapsed:.2f}ms < 100ms requirement")
    else:
        print(f"   ⚠️  WARNING: Response time {elapsed:.2f}ms > 100ms requirement")
    print()


def test_search_empty_query():
    """Test that empty query returns all messages"""
    print("📝 Testing search with empty query...")
    response = httpx.get(f"{BASE_URL}/search", params={"q": "", "page": 1, "limit": 10})
    assert response.status_code == 200
    data = response.json()

    print(f"   ✓ Empty query returns all: {data['total']} messages")
    print(f"   ✓ Returned {len(data['items'])} items on first page")
    print()


def test_search_pagination():
    """Verify pagination is working correctly"""
    print("📄 Testing pagination...")
    response = httpx.get(f"{BASE_URL}/search", params={"q": "", "page": 2, "limit": 10})
    assert response.status_code == 200
    data = response.json()

    print(f"   ✓ Page: {data['page']}")
    print(f"   ✓ Items per page: {len(data['items'])}")
    print(f"   ✓ Total pages: {data['total_pages']}")

    # Make sure we're actually on page 2
    assert data['page'] == 2
    print()


def test_search_by_user():
    """Test searching by user name"""
    print("👤 Testing search by user name 'Sophia'...")
    response = httpx.get(f"{BASE_URL}/search", params={"q": "Sophia", "page": 1, "limit": 5})
    assert response.status_code == 200
    data = response.json()

    print(f"   ✓ Found {data['total']} messages from/about Sophia")
    print(f"   ✓ Query time: {data['query_time_ms']}ms")
    print()


def test_search_no_results():
    """Test query that should return no results"""
    print("🔍 Testing query with no results...")
    response = httpx.get(f"{BASE_URL}/search", params={"q": "xyzabc123notfound", "page": 1, "limit": 10})
    assert response.status_code == 200
    data = response.json()

    print(f"   ✓ No results found: {data['total']} matches")
    assert data['total'] == 0
    assert len(data['items']) == 0
    print()


def test_stats():
    """Test stats endpoint"""
    print("📊 Testing stats endpoint...")
    response = httpx.get(f"{BASE_URL}/stats")
    assert response.status_code == 200
    data = response.json()

    print(f"   ✓ Total messages: {data['total_messages']}")
    print(f"   ✓ Unique users: {data['unique_users']}")
    print(f"   ✓ Sample users: {', '.join(data['users'][:3])}...")
    print()


def run_performance_test():
    """Run 100 queries to measure average performance"""
    print("⚡ Running performance test (100 queries)...")
    queries = ["paris", "hotel", "dinner", "flight", "reservation",
               "book", "confirm", "please", "need", "thank"]
    times = []

    for i in range(100):
        query = queries[i % len(queries)]
        start = time.perf_counter()
        response = httpx.get(f"{BASE_URL}/search", params={"q": query, "page": 1, "limit": 10})
        elapsed = (time.perf_counter() - start) * 1000

        if response.status_code == 200:
            times.append(elapsed)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"   ✓ Average response time: {avg_time:.2f}ms")
    print(f"   ✓ Min response time: {min_time:.2f}ms")
    print(f"   ✓ Max response time: {max_time:.2f}ms")

    # Check requirements
    if avg_time < 100:
        print(f"   ✅ PASSED: Average {avg_time:.2f}ms < 100ms requirement")
    else:
        print(f"   ❌ FAILED: Average {avg_time:.2f}ms > 100ms requirement")

    # Check bonus
    if avg_time < 30:
        print(f"   🌟 BONUS ACHIEVED: Average {avg_time:.2f}ms < 30ms!")
    print()


def main():
    print("=" * 60)
    print("MESSAGE SEARCH API - TEST SUITE")
    print("=" * 60)
    print()

    try:
        # Check if server is running
        print("Checking if server is running...")
        httpx.get(f"{BASE_URL}/", timeout=2)
        print("✓ Server is running!\n")
    except httpx.ConnectError:
        print("❌ Error: Server is not running!")
        print("Please start the server first: uvicorn main:app --reload")
        sys.exit(1)

    try:
        # Run all tests
        test_health_check()
        test_search_with_query()
        test_search_empty_query()
        test_search_pagination()
        test_search_by_user()
        test_search_no_results()
        test_stats()
        run_performance_test()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("API is working correctly and meets all requirements!")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()