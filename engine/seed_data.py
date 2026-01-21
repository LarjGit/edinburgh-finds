import sqlite3
import json
import os
import uuid
from datetime import datetime

# Path to the SQLite database
DB_PATH = os.path.join(os.path.dirname(__file__), '../web/dev.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def seed_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Seeding data...")

    # 1. Create Categories
    categories = [
        {"name": "Padel", "slug": "padel"},
        {"name": "Football", "slug": "football"},
        {"name": "Sports Complex", "slug": "sports-complex"},
        {"name": "Kids Parties", "slug": "kids-parties"}
    ]
    
    category_map = {} # name -> id

    for cat in categories:
        # Check if exists
        cursor.execute("SELECT id FROM Category WHERE slug = ?", (cat['slug'],))
        row = cursor.fetchone()
        if row:
            category_map[cat['name']] = row['id']
            print(f"Category '{cat['name']}' already exists.")
        else:
            cat_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO Category (id, name, slug, updatedAt) VALUES (?, ?, ?, ?)",
                (cat_id, cat['name'], cat['slug'], datetime.now())
            )
            category_map[cat['name']] = cat_id
            print(f"Created Category '{cat['name']}'.")

    # 2. Insert Listing Data
    # Note: EntityType is now an Enum in the schema, not a separate model
    # The JSON data provided by the user
    raw_data = {
      "entity_name": "Powerleague Edinburgh Portobello",
      "entity_type": "VENUE",
      "extraction_timestamp": "2026-01-10T23:39:17.976278",
      "data": {
        "entity_name": "Powerleague Edinburgh Portobello",
        "entity_type": "VENUE",
        "summary": "PowerLeague Edinburgh Portobello is a sports complex specializing in 5-a-side and 7-a-side football with 3 five-a-side pitches and 2 seven-a-side pitches on 3G astroturf. The venue recently invested £600,000 to add 3 covered padel courts, making it Portobello's first padel facility. On-site amenities include a clubhouse bar, Costa Coffee cafe, free parking, and WiFi, with kids' birthday parties and FA-accredited football holiday camps for ages 5-12.",
        "categories": [
          "football",
          "padel",
          "sports complex",
          "kids parties"
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
        "canonical_categories": [
          "football",
          "padel"
        ],
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

    data = raw_data['data']
    
    # 4. Create Listing
    listing_slug = "powerleague-edinburgh-portobello"
    
    # Check if listing exists
    cursor.execute("SELECT id FROM Listing WHERE slug = ?", (listing_slug,))
    row = cursor.fetchone()
    
    if row:
        entity_id = row['id']
        print(f"Listing '{listing_slug}' already exists. Updating...")
        # (Update logic could go here, for now we skip)
    else:
        entity_id = str(uuid.uuid4())
        
        # Serialize JSON fields
        opening_hours_json = json.dumps(data.get('opening_hours'))

        # Build attributes JSON with all venue-specific fields
        attributes = {
            # Tennis
            'tennis_summary': data.get('tennis_summary'),
            'tennis': data.get('tennis'),
            'tennis_total_courts': data.get('tennis_total_courts'),
            'tennis_indoor_courts': data.get('tennis_indoor_courts'),
            'tennis_outdoor_courts': data.get('tennis_outdoor_courts'),
            'tennis_covered_courts': data.get('tennis_covered_courts'),
            'tennis_floodlit_courts': data.get('tennis_floodlit_courts'),
            # Padel
            'padel_summary': data.get('padel_summary'),
            'padel': data.get('padel'),
            'padel_total_courts': data.get('padel_total_courts'),
            # Pickleball
            'pickleball_summary': data.get('pickleball_summary'),
            'pickleball': data.get('pickleball'),
            'pickleball_total_courts': data.get('pickleball_total_courts'),
            # Badminton
            'badminton_summary': data.get('badminton_summary'),
            'badminton': data.get('badminton'),
            'badminton_total_courts': data.get('badminton_total_courts'),
            # Squash
            'squash_summary': data.get('squash_summary'),
            'squash': data.get('squash'),
            'squash_total_courts': data.get('squash_total_courts'),
            'squash_glass_back_courts': data.get('squash_glass_back_courts'),
            # Table Tennis
            'table_tennis_summary': data.get('table_tennis_summary'),
            'table_tennis': data.get('table_tennis'),
            'table_tennis_total_tables': data.get('table_tennis_total_tables'),
            # Football
            'football_summary': data.get('football_summary'),
            'football_5_a_side': data.get('football_5_a_side'),
            'football_5_a_side_total_pitches': data.get('football_5_a_side_total_pitches'),
            'football_7_a_side': data.get('football_7_a_side'),
            'football_7_a_side_total_pitches': data.get('football_7_a_side_total_pitches'),
            'football_11_a_side': data.get('football_11_a_side'),
            'football_11_a_side_total_pitches': data.get('football_11_a_side_total_pitches'),
            # Swimming
            'swimming_summary': data.get('swimming_summary'),
            'indoor_pool': data.get('indoor_pool'),
            'outdoor_pool': data.get('outdoor_pool'),
            'indoor_pool_length_m': data.get('indoor_pool_length_m'),
            'outdoor_pool_length_m': data.get('outdoor_pool_length_m'),
            'family_swim': data.get('family_swim'),
            'adult_only_swim': data.get('adult_only_swim'),
            'swimming_lessons': data.get('swimming_lessons'),
            # Gym
            'gym_summary': data.get('gym_summary'),
            'gym_available': data.get('gym_available'),
            'gym_size': data.get('gym_size'),
            # Classes
            'classes_summary': data.get('classes_summary'),
            'classes_per_week': data.get('classes_per_week'),
            'hiit_classes': data.get('hiit_classes'),
            'yoga_classes': data.get('yoga_classes'),
            'pilates_classes': data.get('pilates_classes'),
            'strength_classes': data.get('strength_classes'),
            'cycling_studio': data.get('cycling_studio'),
            'functional_training_zone': data.get('functional_training_zone'),
            # Spa
            'spa_summary': data.get('spa_summary'),
            'spa_available': data.get('spa_available'),
            'sauna': data.get('sauna'),
            'steam_room': data.get('steam_room'),
            'hydro_pool': data.get('hydro_pool'),
            'hot_tub': data.get('hot_tub'),
            'outdoor_spa': data.get('outdoor_spa'),
            'ice_cold_plunge': data.get('ice_cold_plunge'),
            'relaxation_area': data.get('relaxation_area'),
            # Amenities
            'amenities_summary': data.get('amenities_summary'),
            'restaurant': data.get('restaurant'),
            'bar': data.get('bar'),
            'cafe': data.get('cafe'),
            'childrens_menu': data.get('childrens_menu'),
            'wifi': data.get('wifi'),
            # Family
            'family_summary': data.get('family_summary'),
            'creche_available': data.get('creche_available'),
            'creche_age_min': data.get('creche_age_min'),
            'creche_age_max': data.get('creche_age_max'),
            'kids_swimming_lessons': data.get('kids_swimming_lessons'),
            'kids_tennis_lessons': data.get('kids_tennis_lessons'),
            'holiday_club': data.get('holiday_club'),
            'play_area': data.get('play_area'),
            # Parking
            'parking_and_transport_summary': data.get('parking_and_transport_summary'),
            'parking_spaces': data.get('parking_spaces'),
            'disabled_parking': data.get('disabled_parking'),
            'parent_child_parking': data.get('parent_child_parking'),
            'ev_charging_available': data.get('ev_charging_available'),
            'ev_charging_connectors': data.get('ev_charging_connectors'),
            'public_transport_nearby': data.get('public_transport_nearby'),
            'nearest_railway_station': data.get('nearest_railway_station'),
            # Reviews
            'reviews_summary': data.get('reviews_summary'),
            'review_count': data.get('review_count'),
            'google_review_count': data.get('google_review_count'),
            'facebook_likes': data.get('facebook_likes'),
        }
        # Remove None values
        attributes = {k: v for k, v in attributes.items() if v is not None}
        attributes_json = json.dumps(attributes)

        discovered_attributes_json = json.dumps(data.get('other_attributes', {}))
        source_info_json = json.dumps({
            "extraction_timestamp": raw_data.get('extraction_timestamp'),
            "enrichment_log": data.get('enrichment_log')
        })
        field_confidence_json = json.dumps(data.get('field_confidence'))
        external_ids_json = json.dumps({})
        
        cursor.execute("""
            INSERT INTO Listing (
                id, entity_name, slug, summary,
                attributes, discovered_attributes, street_address, city, postcode, country,
                latitude, longitude, phone, email, website_url,
                instagram_url, facebook_url, twitter_url, linkedin_url,
                opening_hours, source_info, field_confidence, external_ids,
                entityType, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_id,
            data['entity_name'],
            listing_slug,
            data['summary'],
            attributes_json,
            discovered_attributes_json,
            data['street_address'],
            data['city'],
            data['postcode'],
            data['country'],
            data['latitude'],
            data['longitude'],
            data['phone'],
            data['email'],
            data['website_url'],
            data['instagram_url'],
            data['facebook_url'],
            data['twitter_url'],
            data['linkedin_url'],
            opening_hours_json,
            source_info_json,
            field_confidence_json,
            external_ids_json,
            data['entity_type'],  # Use Enum value directly
            datetime.now()
        ))
        print(f"Created Listing '{data['entity_name']}'.")

        # Link Categories to Listing
        for cat_name in data.get('canonical_categories', []):
            # Try to map 'football' -> 'Football' (simple case insensitive match or direct map)
            # In our simple case, we know we created 'Football' and 'Padel'
            matched_id = None
            for name, cid in category_map.items():
                if name.lower() == cat_name.lower():
                    matched_id = cid
                    break
            
            if matched_id:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO _CategoryToListing (A, B) VALUES (?, ?)",
                        (matched_id, entity_id)
                    )
                except sqlite3.OperationalError:
                    print("Warning: Could not link Category to Listing. Prisma implicit table issue.")

    conn.commit()
    conn.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_data()
