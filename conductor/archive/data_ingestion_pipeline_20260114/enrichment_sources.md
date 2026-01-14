# Enrichment Data Sources Research

This document outlines additional enrichment data sources beyond the primary connectors. These sources can supplement venue listings with contextual information about accessibility, facilities, and official registrations.

**Research Date:** 2026-01-14
**Status:** Research complete, implementation pending

---

## 1. SportScotland Sports Facilities

### Overview
SportScotland maintains a comprehensive dataset of sports facilities across Scotland, including Edinburgh. This official dataset provides verified facility information with detailed attributes captured against Google Maps.

### Data Coverage
**11 Themed Facility Layers:**
- Athletics Tracks (velodromes, training areas, indoor/outdoor)
- Bowling Greens (croquet, petanque, cricket squares)
- Fitness Suites
- Golf Courses
- Ice Rinks (curling rinks)
- Pitches (size, sport type, surface)
- Sports Halls (gyms and other types)
- Squash Courts
- Swimming Pools (diving and other types)
- Indoor Tennis Courts
- Outdoor Tennis Courts

### Access Methods
- **Primary Portal:** [Spatial Hub Scotland](https://data.spatialhub.scot/dataset/sports_facilities-unknown)
- **Format Options:** WFS (Web Feature Service), GeoJSON, Shapefile, CSV
- **Authentication:** Free account registration required
- **License:** UK Open Government Licence (OGL)
- **Last Updated:** 2024-07-26

### API/Service Details
- **Service Type:** OGC Web Feature Service (WFS) + Web Map Service (WMS)
- **Service URL:** Available after registration at Spatial Hub Scotland
- **Query Method:** WFS GetFeature requests with spatial/attribute filters
- **Response Format:** GML/GeoJSON

### Enrichment Value for Edinburgh Finds
**High Value:**
- Official verification of sports facilities
- Detailed facility attributes (size, type, surface)
- Location accuracy validated against Google Maps
- Covers multiple sports including padel (if registered)

**Use Cases:**
- Cross-reference venue listings with official SportScotland records
- Enrich venue profiles with official facility counts and types
- Verify facility existence and operational status
- Identify missing venues not yet in our system

### Implementation Considerations
**Pros:**
- Authoritative source (government-backed)
- Well-structured data with consistent attributes
- Multiple format options (GeoJSON ideal for us)
- Free access with OGL license
- Regular updates (quarterly/annual)

**Cons:**
- Requires registration (manual step)
- May not include newer/private facilities
- WFS queries can be complex
- Rate limits unknown (likely conservative for public service)
- May lag behind real-time changes

### Data Quality
- **Coverage:** Scotland-wide, comprehensive for established facilities
- **Freshness:** Updated 2024-07-26 (semi-annual updates expected)
- **Accuracy:** High (validated against Google Maps)
- **Completeness:** Excellent for public facilities, may miss private clubs

### Contact
- **Email:** facilities@sportscotland.org.uk
- **Purpose:** Report data discrepancies or issues

---

## 2. City of Edinburgh Council Open Spatial Data

### Overview
Edinburgh Council provides an open spatial data portal with datasets covering civic infrastructure, facilities, and community resources across Edinburgh.

### Data Coverage
**Relevant Categories:**
- **Education:** School locations and educational facilities
- **Planning:** Property and development information
- **Retail:** Commercial venue locations
- **Community Safety:** Emergency services and public facilities
- **Environment:** Parks, green spaces, recreational areas
- **Transportation:** Public transit access, parking facilities

### Access Methods
- **Primary Portal:** [City of Edinburgh Council Open Spatial Data Portal](https://data.edinburghcouncilmaps.info/)
- **Alternative:** [Edinburgh Council GitHub](https://github.com/edinburghcouncil/datasets)
- **Format Options:** API access, downloads, online map viewing
- **License:** Open Government License v3.0
- **Attribution Required:** "Copyright City of Edinburgh Council, contains Ordnance Survey data © Crown copyright"

### API/Service Details
- **Platform:** ArcGIS Hub (ESRI platform)
- **Service Type:** ArcGIS REST API (Feature Services)
- **Query Method:** REST API with spatial/attribute queries
- **Response Format:** JSON, GeoJSON, KML, Shapefile
- **Authentication:** Likely public (no key mentioned)

### Enrichment Value for Edinburgh Finds
**Medium to High Value:**
- Hyper-local Edinburgh focus (perfect geographic match)
- Official civic data with legal backing
- Comprehensive coverage of public facilities
- Educational and recreational facility locations

**Use Cases:**
- Identify nearby schools/education facilities for family-oriented venues
- Cross-reference retail/commercial venue locations
- Enrich listings with civic context (ward, neighborhood)
- Identify public facilities near private venues (parking, transit)

### Implementation Considerations
**Pros:**
- Edinburgh-specific (exact geographic match)
- ArcGIS REST API well-documented
- Multiple format options
- Open license (OGL 3.0)
- GitHub repository for additional context
- Active council commitment to open data

**Cons:**
- No dedicated "sports facilities" layer apparent
- Data fragmented across multiple thematic datasets
- Unclear update frequency
- May require multiple API calls for comprehensive data
- Rate limits unknown

### Data Quality
- **Coverage:** Edinburgh city boundaries only
- **Freshness:** Varies by dataset (civic data typically updated quarterly)
- **Accuracy:** High (official council records)
- **Completeness:** Excellent for public/civic facilities, limited for private venues

### Relevant Datasets (Examples)
Based on portal structure, potentially useful datasets include:
- Community centers and civic facilities
- Sports and leisure centers (council-operated)
- Parks and recreation areas
- Retail and commercial zones
- Public parking facilities
- Educational institutions

---

## 3. Additional Potential Sources (Future Research)

### VisitScotland Open Data
- Tourism and attraction data
- Visitor facilities information
- Potential for coach/tour operator listings

### Transport Scotland
- Public transit accessibility
- Park & Ride facilities
- Cycle infrastructure

### Active Places Power (Sport England)
- Sports facility database (UK-wide)
- Includes Scotland coverage
- Comprehensive facility attributes

---

## Implementation Priority & Recommendations

### Priority 1: SportScotland (Recommended Next)
**Why:**
- Direct alignment with sports/padel focus
- Authoritative official data
- Well-structured API (WFS)
- High enrichment value for core use case

**Implementation Approach:**
1. Register for Spatial Hub Scotland account
2. Obtain WFS service URL for sports facilities
3. Implement WFS connector (similar to existing connectors)
4. Filter by Edinburgh boundary (spatial query)
5. Ingest facility layers relevant to platform niches
6. Store raw data for later cross-referencing

**Estimated Effort:** Medium (WFS queries more complex than REST)

### Priority 2: Edinburgh Council (Secondary)
**Why:**
- Hyper-local relevance
- Good for contextual enrichment
- ArcGIS REST API (easier than WFS)
- Multiple valuable datasets

**Implementation Approach:**
1. Explore portal to identify specific relevant datasets
2. Document ArcGIS Feature Service URLs
3. Implement ArcGIS REST connector (generic, reusable)
4. Ingest civic/recreational facility data
5. Cross-reference with venue listings

**Estimated Effort:** Medium (requires dataset discovery phase)

### Implementation Notes
- Both sources provide **official, authoritative data** (higher trust than crowdsourced)
- Both have **open licenses** (no legal barriers)
- Both require **spatial queries** (lat/lng or bounding box)
- Both suitable for **batch ingestion** rather than real-time lookups
- Consider **quarterly refresh cycles** (civic data doesn't change daily)

---

## Connector Architecture Considerations

### WFS Connector (SportScotland)
```python
class SportScotlandWFSConnector(BaseConnector):
    """
    Connector for SportScotland WFS service.

    Query Types:
    - GetCapabilities: List available layers
    - GetFeature: Fetch facilities by spatial filter
    - DescribeFeatureType: Get layer schema

    Spatial Filters:
    - BBOX: Bounding box (Edinburgh boundaries)
    - INTERSECTS: Polygon intersection
    - DWITHIN: Distance-based (radius from point)
    """
    pass
```

### ArcGIS REST Connector (Edinburgh Council)
```python
class ArcGISFeatureServiceConnector(BaseConnector):
    """
    Generic connector for ArcGIS Feature Services.

    Query Types:
    - Query: Attribute and spatial queries
    - Export: Bulk export (GeoJSON, CSV)

    Spatial Filters:
    - geometry + geometryType + spatialRel
    - where clause for attribute filtering

    Reusable for any ESRI-based open data portal.
    """
    pass
```

---

## Data Integration Strategy

### Cross-Referencing Approach
1. **Ingest raw data** from enrichment sources (this track)
2. **Extract structured entities** (future extraction phase)
3. **Match by location** (spatial join: lat/lng proximity)
4. **Match by name** (fuzzy string matching)
5. **Enrich venue profiles** with official attributes

### Example Enrichment
**Venue:** "Edinburgh Padel Club"
- **Primary Data:** Google Places, Serper (name, address, hours)
- **SportScotland:** Official facility count, court surface type
- **Council Data:** Ward location, nearest parking, transit access
- **OpenChargeMap:** Nearby EV charging (already implemented)

---

## References

**SportScotland:**
- [Spatial Hub Scotland - Sports Facilities Dataset](https://data.spatialhub.scot/dataset/sports_facilities-unknown)
- [Spatial Data Gov Scotland - Metadata](https://spatialdata.gov.scot/geonetwork/srv/api/records/6571a242-7345-4e2f-88d7-97f99046dc0d)
- [Open Data Scotland - Sport Scotland](https://opendata.scot/organizations/sport_scotland/)

**Edinburgh Council:**
- [City of Edinburgh Council Open Spatial Data Portal](https://data.edinburghcouncilmaps.info/)
- [Edinburgh Council GitHub - Datasets](https://github.com/edinburghcouncil/datasets)
- [Open Data Scotland - City of Edinburgh Council](https://opendata.scot/organizations/city_of_edinburgh_council/)
- [Council Open Data Strategy](https://www.edinburgh.gov.uk/downloads/download/14251/strategy-for-open-data)

---

## Next Steps

1. ✅ Research completed and documented
2. ⏳ **Pending:** Decide on implementation priority
3. ⏳ **Pending:** Register for SportScotland Spatial Hub account (if proceeding)
4. ⏳ **Pending:** Identify specific Edinburgh Council datasets to target
5. ⏳ **Pending:** Write tests for chosen connector(s)
6. ⏳ **Pending:** Implement connector(s) following TDD workflow

**Recommendation:** Implement SportScotland connector first due to direct alignment with sports venue enrichment goals.
