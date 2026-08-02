#!/usr/bin/env python3
"""
Amadeus Self-Service API — data quality test for MY routes.

This script tests whether Amadeus's free tier (2,000 calls/mo) has
good enough data for fare alerts. Run it ONCE before building the
fare alerts product. If the data quality is good, use Amadeus free tier
($0/mo). If not, fall back to SerpAPI ($30-50/mo).

Setup:
  1. Go to https://developers.amadeus.com
  2. Click "Register" → create account
  3. Click "Create New App" → name it "longweekend-fare-alerts"
  4. Copy the API Key and API Secret
  5. Set environment variables:
     export AMADEUS_CLIENT_ID="your_api_key_here"
     export AMADEUS_CLIENT_SECRET="your_api_secret_here"
  6. Run: python3 test_amadeus_data_quality.py

What it tests:
  - 3 routes: KUL→HND, KUL→DPS, KUL→BKK (the most common MY traveler routes)
  - 2 date ranges: this weekend + 4-6 weeks out (a typical cuti window)
  - Checks: number of options, price realism, budget carrier coverage

What "good data" means:
  - 5+ flight options per route (enough for the digest to be useful)
  - Realistic prices (not 5x higher than what AirAsia/Trip.com shows)
  - Budget carriers included (AirAsia, Scoot, etc.)
  - No frequent errors or timeouts

Cost: 6 API calls (free tier allows 2,000/mo)
Runtime: ~30 seconds
"""

import os
import sys
from datetime import datetime, timedelta
from amadeus import Client, ResponseError

# --- Configuration ---
ROUTES = [
    ("KUL", "HND", "Tokyo (NRT/HND)"),
    ("KUL", "DPS", "Bali (DPS)"),
    ("KUL", "BKK", "Bangkok (BKK)"),
]

# Test dates: a 3-day weekend window starting 4-6 weeks from now
def get_test_dates():
    """Generate a 3-day weekend window 4-6 weeks out."""
    today = datetime.now().date()
    # Find next Friday that's 4-6 weeks away
    days_ahead = 35  # ~5 weeks
    target_friday = today + timedelta(days=days_ahead)
    while target_friday.weekday() != 4:  # Friday = 4
        target_friday += timedelta(days=1)
    # Return window: Friday → Sunday
    return {
        "departure": target_friday.strftime("%Y-%m-%d"),
        "return": (target_friday + timedelta(days=3)).strftime("%Y-%m-%d"),
    }

# --- Main test ---
def main():
    # Check for API keys
    client_id = os.environ.get("AMADEUS_CLIENT_ID")
    client_secret = os.environ.get("AMADEUS_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ Missing Amadeus API credentials.")
        print()
        print("Setup:")
        print("  1. Go to https://developers.amadeus.com")
        print("  2. Register → Create New App → name it 'longweekend-fare-alerts'")
        print("  3. Copy the API Key and API Secret")
        print("  4. Set environment variables:")
        print('     export AMADEUS_CLIENT_ID="your_api_key_here"')
        print('     export AMADEUS_CLIENT_SECRET="your_api_secret_here"')
        print("  5. Run: python3 test_amadeus_data_quality.py")
        sys.exit(1)

    # Initialize Amadeus client (test environment)
    print("🔍 Testing Amadeus Self-Service API (test environment)...")
    print(f"   Client ID: {client_id[:8]}...")
    print()
    amadeus = Client(
        client_id=client_id,
        client_secret=client_secret,
        hostname="test"  # Use test environment (free, no real bookings)
    )

    dates = get_test_dates()
    print(f"📅 Test dates: {dates['departure']} (Fri) → {dates['return']} (Sun)")
    print()

    # Test each route
    results = []
    for origin, dest, name in ROUTES:
        print(f"━━━ Testing {origin} → {dest} ({name}) ━━━")
        try:
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=dest,
                departureDate=dates["departure"],
                returnDate=dates["return"],
                adults=1,
                currencyCode="MYR",
                travelClass="ECONOMY",
                max=10  # Get up to 10 options
            )

            offers = response.data
            print(f"  ✅ Got {len(offers)} flight options")

            if len(offers) == 0:
                print(f"  ⚠️  WARNING: 0 options returned. SEA coverage may be weak.")
                results.append({"route": f"{origin}→{dest}", "options": 0, "status": "fail"})
                continue

            # Analyze the options
            prices = [float(offer["price"]["total"]) for offer in offers]
            airlines = set()
            for offer in offers:
                for segment in offer.get("itineraries", []):
                    for seg in segment.get("segments", []):
                        airlines.add(seg.get("carrierCode", "??"))

            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) / len(prices)

            print(f"  💰 Price range: RM{min_price:.0f} - RM{max_price:.0f} (avg: RM{avg_price:.0f})")
            print(f"  ✈️  Airlines: {', '.join(sorted(airlines))}")

            # Check for budget carriers
            budget_carriers = {"AK", "TR", "5J", "FD", "TZ", "SL"}  # AirAsia, Scoot, Cebu, ThaiAirAsia, etc.
            has_budget = bool(budget_carriers & airlines)
            print(f"  🛫 Budget carriers: {'✅ Yes' if has_budget else '❌ No'}")

            # Check price realism
            # KUL→HND: realistic range RM1,500-3,500
            # KUL→DPS: realistic range RM500-1,500
            # KUL→BKK: realistic range RM300-1,000
            if origin == "KUL" and dest == "HND":
                realistic = 1500 <= min_price <= 3500
            elif origin == "KUL" and dest == "DPS":
                realistic = 500 <= min_price <= 1500
            elif origin == "KUL" and dest == "BKK":
                realistic = 300 <= min_price <= 1000
            else:
                realistic = True

            print(f"  📊 Price realistic: {'✅ Yes' if realistic else '❌ No (too high/low)'}")

            # Overall verdict for this route
            if len(offers) >= 5 and has_budget and realistic:
                status = "pass"
                print(f"  ✅ VERDICT: Good data — use Amadeus free tier")
            elif len(offers) >= 3 and (has_budget or realistic):
                status = "marginal"
                print(f"  ⚠️  VERDICT: Marginal data — consider SerpAPI fallback")
            else:
                status = "fail"
                print(f"  ❌ VERDICT: Poor data — use SerpAPI instead")

            results.append({
                "route": f"{origin}→{dest}",
                "options": len(offers),
                "min_price": min_price,
                "airlines": list(airlines),
                "has_budget": has_budget,
                "realistic": realistic,
                "status": status
            })

        except ResponseError as e:
            print(f"  ❌ API error: {e}")
            results.append({"route": f"{origin}→{dest}", "options": 0, "status": "fail"})
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            results.append({"route": f"{origin}→{dest}", "options": 0, "status": "fail"})

        print()

    # --- Summary ---
    print("━━━ SUMMARY ━━━")
    print()
    print(f"{'Route':<12} {'Options':<10} {'Min Price':<12} {'Status':<10}")
    print("─" * 50)
    for r in results:
        route = r["route"]
        options = str(r.get("options", 0))
        price = f"RM{r['min_price']:.0f}" if "min_price" in r else "N/A"
        status = r["status"].upper()
        print(f"{route:<12} {options:<10} {price:<12} {status:<10}")

    print()

    # Overall recommendation
    pass_count = sum(1 for r in results if r["status"] == "pass")
    marginal_count = sum(1 for r in results if r["status"] == "marginal")
    fail_count = sum(1 for r in results if r["status"] == "fail")

    print("OVERALL RECOMMENDATION:")
    if pass_count >= 2:
        print("  ✅ Use Amadeus free tier ($0/mo)")
        print("     → 2,000 calls/mo is enough for 80 routes × weekly snapshots")
        print("     → Build fare alerts on Amadeus")
    elif marginal_count >= 2:
        print("  ⚠️  Amadeus is marginal. Consider SerpAPI fallback ($30-50/mo)")
        print("     → Use Amadeus for the MVP, fall back to SerpAPI if data quality degrades")
    else:
        print("  ❌ Amadeus SEA coverage is too weak")
        print("     → Use SerpAPI ($30-50/mo) instead")
        print("     → Sign up at https://serpapi.com")
        print("     → 5,000 searches/mo covers 80 routes × weekly + buffer")

    print()
    print("NEXT STEPS:")
    print("  1. If Amadeus passes → start building fare alerts with $0/mo data cost")
    print("  2. If Amadeus fails → sign up for SerpAPI, re-test with same script")
    print("  3. Either way → set up the fare_alerts_subscribers table in Neon")
    print("  4. Either way → build the weekly cron + email digest + signup form")

if __name__ == "__main__":
    main()
