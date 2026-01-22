import asyncio
import json
from prisma import Prisma
from engine.ingest import ingest_venue

# Sample Data extracted from original seed_data.py
SAMPLE_DATA = {
  "entity_name": "Powerleague Edinburgh Portobello",
  "entity_type": "venue",
  "extraction_timestamp": "2026-01-10T23:39:17.976278",
  "data": {
    "entity_name": "Powerleague Edinburgh Portobello",
    "entity_type": "venue",
    "summary": "PowerLeague Edinburgh Portobello is a sports complex specializing in 5-a-side and 7-a-side football with 3 five-a-side pitches and 2 seven-a-side pitches on 3G astroturf. The venue recently invested £600,000 to add 3 covered padel courts, making it Portobello's first padel facility. On-site amenities include a clubhouse bar, Costa Coffee cafe, free parking, and WiFi, with kids' birthday parties and FA-accredited football holiday camps for ages 5-12.",
    "categories": [
      "football",
      "padel",
      "sports complex",
      "kids parties"
    ],
    "canonical_categories": [
      "football",
      "padel"
    ],
    "other_attributes": {
      "floodlights": True,
      "powerpitch_3g_astroturf": True,
      "kids_camps_price": "£16 per day",
      "kids_camps_ages": "5-12 years",
      "birthday_party_price_from": "£17.50 per child",
      "birthday_party_duration": "90 minutes",
      "padel_investment": "£600,000",
      "padel_opened": "2025",
      "location_description": "Edinburgh's vibrant coastline/seaside suburb",
      "bar_license": "12 a.m. license",
      "dj_service_available": True,
      "kids_welcome": True,
      "coffee_brand": "Costa Coffee"
    },
    "street_address": "10 Westbank St, Edinburgh, EH15 1DR",
    "city": "Edinburgh",
    "postcode": "EH15 1DR",
    "country": "United Kingdom",
    "latitude": 55.9566382,
    "longitude": -3.1178543,
    "phone": "+441316692266",
    "email": "portobello@powerleague.com",
    "website_url": "https://www.powerleague.com/location/edinburgh-portobello",
    "instagram_url": "https://www.instagram.com/powerleagueedinburghportobello/",
    "facebook_url": "https://www.facebook.com/PowerleaguePortobello/",
    "twitter_url": "https://x.com/powerleagueedinburghportobello",
    "linkedin_url": "https://www.linkedin.com/company/powerleague",
    "opening_hours": {
      "monday": {
        "open": "09:00",
        "close": "22:30"
      },
      "tuesday": {
        "open": "09:00",
        "close": "22:30"
      },
      "wednesday": {
        "open": "09:00",
        "close": "22:30"
      },
      "thursday": {
        "open": "09:00",
        "close": "22:30"
      },
      "friday": {
        "open": "09:00",
        "close": "22:30"
      },
      "saturday": {
        "open": "09:00",
        "close": "22:30"
      },
      "sunday": {
        "open": "09:00",
        "close": "22:30"
      }
    },
    "tennis_summary": None,
    "tennis": False,
    "tennis_total_courts": None,
    "tennis_indoor_courts": None,
    "tennis_outdoor_courts": None,
    "tennis_covered_courts": None,
    "tennis_floodlit_courts": None,
    "padel_summary": "3 brand-new, covered, all-weather padel courts opened following £600,000 investment in 2025. This is Portobello's first padel facility, featuring state-of-the-art courts perfect for every level of player.",
    "padel": True,
    "padel_total_courts": 3,
    "pickleball_summary": None,
    "pickleball": False,
    "pickleball_total_courts": None,
    "badminton_summary": None,
    "badminton": False,
    "badminton_total_courts": None,
    "squash_summary": None,
    "squash": False,
    "squash_total_courts": None,
    "squash_glass_back_courts": None,
    "table_tennis_summary": None,
    "table_tennis": False,
    "table_tennis_total_tables": None,
    "football_summary": "3 five-a-side pitches and 2 seven-a-side pitches on 3G astroturf with floodlights. PowerPitch surface available. Venue hosts competitive leagues, tournaments, and social bookings with flexible scheduling including peak and off-peak bookings.",
    "football_5_a_side": True,
    "football_5_a_side_total_pitches": 3,
    "football_7_a_side": True,
    "football_7_a_side_total_pitches": 2,
    "football_11_a_side": False,
    "football_11_a_side_total_pitches": None,
    "swimming_summary": None,
    "indoor_pool": False,
    "outdoor_pool": False,
    "indoor_pool_length_m": None,
    "outdoor_pool_length_m": None,
    "family_swim": False,
    "adult_only_swim": False,
    "swimming_lessons": False,
    "gym_summary": None,
    "gym_available": False,
    "gym_size": None,
    "classes_summary": None,
    "classes_per_week": None,
    "hiit_classes": False,
    "yoga_classes": False,
    "pilates_classes": False,
    "strength_classes": False,
    "cycling_studio": False,
    "functional_training_zone": False,
    "spa_summary": None,
    "spa_available": False,
    "sauna": False,
    "steam_room": False,
    "hydro_pool": False,
    "hot_tub": False,
    "outdoor_spa": False,
    "ice_cold_plunge": False,
    "relaxation_area": False,
    "amenities_summary": "On-site clubhouse with bar (12 a.m. license with DJ service available) and Costa Coffee cafe serving coffee, snacks, and light refreshments. Free WiFi available via Sky WiFi. Changing rooms available. Kids welcome at bar facilities.",
    "restaurant": False,
    "bar": True,
    "cafe": True,
    "childrens_menu": True,
    "wifi": True,
    "family_summary": "Kids' football birthday parties available from £17.50 per child for 90-minute sessions including cake, medals, and fun activities. FA-accredited football holiday camps for ages 5-12 during school breaks at £16 per day. Also hosts Nerf parties for kids. Junior football coaching available with expert-led training.",
    "creche_available": False,
    "creche_age_min": None,
    "creche_age_max": None,
    "kids_swimming_lessons": False,
    "kids_tennis_lessons": False,
    "holiday_club": True,
    "play_area": False,
    "parking_and_transport_summary": "Free parking available on-site. Additional parking options available via JustPark from £0.20 per hour. Public transport nearby in Portobello's seaside area. Venue offers warm workspace with high-speed WiFi and free parking for some flexible workspace use.",
    "parking_spaces": None,
    "disabled_parking": None,
    "parent_child_parking": None,
    "ev_charging_available": False,
    "ev_charging_connectors": None,
    "public_transport_nearby": True,
    "nearest_railway_station": None,
    "reviews_summary": "Highly rated sports complex with 4.3/5 stars on Google from 287 reviews. Strong community presence with active Facebook following. Venue is well-regarded for its excellent facilities and family-friendly atmosphere.",
    "review_count": 287,
    "google_review_count": 287,
    "facebook_likes": None,
    "field_confidence": {
      "entity_name": 1.0,
      "entity_type": 1.0,
    },
    "enrichment_log": {
      "timestamp": "2026-01-11T14:50:34.188303",
      "enrichments": [],
      "enrichment_count": 4
    }
  },
  "enrichment_timestamp": "2026-01-11T14:50:34.189310"
}

async def run_test():
    # Flatten/Prepare data
    payload = SAMPLE_DATA["data"].copy()

    # TEMP: Skip discovered_attributes to test core entity ingestion
    if "other_attributes" in payload:
        payload.pop("other_attributes")
    if "discovered_attributes" in payload:
        payload.pop("discovered_attributes")
        
    print(f"Starting ingestion for {payload['entity_name']}...")
    listing = await ingest_venue(payload)
    
    # Verification
    print(f"VERIFICATION:")
    print(f"ID: {listing.id}")
    print(f"Name: {listing.entity_name}")
    print(f"Slug: {listing.slug}")
    print(f"Attributes (JSON): {listing.attributes}")
    print(f"Discovered (JSON): {listing.discovered_attributes}")
    
    # Check attributes content
    attrs = json.loads(listing.attributes)
    if attrs.get("padel_total_courts") == 3:
        print("PASS: Attributes contain padel_total_courts=3")
    else:
        print("FAIL: Attributes missing padel_total_courts")

if __name__ == "__main__":
    asyncio.run(run_test())