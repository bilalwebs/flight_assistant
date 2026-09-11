import asyncio
from datetime import datetime, timedelta
from database.database import AsyncSessionLocal
from services.flight_service import FlightService
from models.flight import CabinClass

async def test_flight_service():
    async with AsyncSessionLocal() as session:
        # Flights are seeded with day_offsets >= 1 from today; search tomorrow.
        test_date = (datetime.utcnow() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"--- Testing Search (KHI -> DXB) on {test_date.date()} ---")
        flights = await FlightService.search_flights(
            session, origin="KHI", destination="DXB", date=test_date
        )
        print(f"Found {len(flights)} flights")

        if flights:
            f = flights[0]
            print(f"Sample Flight: {f.flight_number} | {f.airline} | ${f.base_price}")

            print("\n--- Testing Price Calculation ---")
            breakdown = FlightService.calculate_flight_price(f, 2)
            print(f"Price Breakdown for 2 passengers:")
            print(f"  Base per person: ${breakdown.base_price_per_person}")
            print(f"  Tax per person:  ${breakdown.tax_per_person}")
            print(f"  Grand Total:     ${breakdown.grand_total}")

            print("\n--- Testing Seat Availability ---")
            is_avail = FlightService.check_seat_availability(f, 10)
            print(f"10 seats available for {f.flight_number}? {is_avail}")

            is_too_many = FlightService.check_seat_availability(f, 500)
            print(f"500 seats available for {f.flight_number}? {is_too_many}")

        print("\n--- Testing Search (KHI -> IST) ---")
        ist_flights = await FlightService.search_flights(
            session, origin="KHI", destination="IST", date=test_date
        )
        print(f"Found {len(ist_flights)} flights to Istanbul")
        for f in ist_flights[:2]:
            print(f"  {f.flight_number} | {f.airline} | ${f.base_price}")

        print("\n--- Testing Filtering (Max Stops: 0) ---")
        direct_flights = await FlightService.filter_flights(
            session, origin="KHI", destination="DXB", date=test_date, max_stops=0
        )
        print(f"Found {len(direct_flights)} direct flights")

        print("\n--- Testing Filtering (Price Range: 200-250) ---")
        budget_flights = await FlightService.filter_flights(
            session, origin="KHI", destination="DXB", date=test_date, min_price=200, max_price=250
        )
        print(f"Found {len(budget_flights)} flights between $200 and $250")
        for f in budget_flights:
            print(f"  {f.flight_number} | ${f.base_price}")

        print("\n--- Testing Filtering (Morning Flights) ---")
        morning_flights = await FlightService.filter_flights(
            session, origin="KHI", destination="DXB", date=test_date, time_of_day="morning"
        )
        print(f"Found {len(morning_flights)} morning flights (6 AM - 12 PM)")
        for f in morning_flights:
            print(f"  {f.flight_number} | {f.departure_time.time()}")

        print("\n--- Testing Comparison ---")
        if len(flights) >= 2:
            comparison = FlightService.compare_flights(flights[:3])
            print("Comparison (Sorted by price):")
            for c in comparison:
                print(f"  {c['flight_number']} | {c['airline']} | ${c['price']:.2f} | {c['duration']}m")

        print("\n--- Testing No Results (KHI -> LAX) ---")
        empty = await FlightService.search_flights(
            session, origin="KHI", destination="LAX", date=test_date
        )
        print(f"Found {len(empty)} flights (expected 0)")

        print("\n--- Testing Flight Details ---")
        if flights:
            details = await FlightService.get_flight_details(session, flights[0].id)
            print(f"Retrieved details for {details.id}: {details.flight_number}")

            invalid_details = await FlightService.get_flight_details(session, "invalid-uuid")
            print(f"Retrieved details for invalid-uuid: {invalid_details}")

if __name__ == "__main__":
    asyncio.run(test_flight_service())
