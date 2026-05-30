"""Transit data service - fetches GTFS data from data.gov.my APIs."""

import requests
import io
import csv
import zipfile
import time
from typing import Optional
from app.config import settings
from app.database import get_db


class TransitDataService:
    """Handles all data.gov.my GTFS API interactions."""

    GTFS_AGENCIES = {
        "ktmb": {"name": "Keretapi Tanah Melayu (KTMB)", "category": None},
        "prasarana": {"name": "Rapid KL (Prasarana)", "categories": [
            "rapid-rail-kl",     # LRT, MRT, Monorail
        ]},
    }

    @staticmethod
    def fetch_static_gtfs(agency: str = "ktmb", category: Optional[str] = None) -> dict:
        """
        Fetch GTFS static data from data.gov.my.
        Returns parsed route and stop data.
        """
        url = f"{settings.GTFS_STATIC_BASE_URL}/{agency}"
        params = {}
        if category:
            params["category"] = category

        try:
            start = time.time()
            resp = requests.get(url, params=params, timeout=30)
            elapsed = int((time.time() - start) * 1000)
            if resp.status_code != 200:
                from app.database import log_api_call
                log_api_call(f"gtfs-static/{agency}", url, f"http_{resp.status_code}", elapsed)
                return {"error": f"API returned status {resp.status_code}"}

            # GTFS data comes as ZIP of CSV files
            try:
                z = zipfile.ZipFile(io.BytesIO(resp.content))
                routes = TransitDataService._parse_csv_in_zip(z, "routes.txt")
                stops = TransitDataService._parse_csv_in_zip(z, "stops.txt")
                trips = TransitDataService._parse_csv_in_zip(z, "trips.txt")
                stop_times = TransitDataService._parse_csv_in_zip(z, "stop_times.txt")
                from app.database import log_api_call
                log_api_call(f"gtfs-static/{agency}", url, "success", elapsed)
                return {
                    "routes": routes[:100] if routes else [],
                    "stops": stops[:200] if stops else [],
                    "trips": trips[:100] if trips else [],
                    "stop_times": stop_times[:200] if stop_times else [],
                    "agency": TransitDataService._parse_csv_in_zip(z, "agency.txt"),
                }
            except zipfile.BadZipFile:
                # Some endpoints return JSON
                data = resp.json()
                return {"raw": data}

        except requests.RequestException as e:
            from app.database import log_api_call
            log_api_call(f"gtfs-static/{agency}", url, "error", 0)
            return {"error": str(e)}

    @staticmethod
    def fetch_realtime(agency: str = "ktmb", category: Optional[str] = None) -> dict:
        """Fetch GTFS Realtime data (vehicle positions, arrivals)."""
        url = f"{settings.GTFS_REALTIME_BASE_URL}/{agency}"
        params = {}
        if category:
            params["category"] = category

        try:
            start = time.time()
            resp = requests.get(url, params=params, timeout=15)
            elapsed = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                try:
                    from app.database import log_api_call
                    log_api_call(f"gtfs-realtime/{agency}", url, "success", elapsed)
                    return resp.json()
                except Exception:
                    return {"raw": "binary protobuf data"}
            return {"error": f"HTTP {resp.status_code}"}
        except requests.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def _parse_csv_in_zip(z: zipfile.ZipFile, filename: str) -> list:
        """Parse a CSV file inside a GTFS ZIP archive."""
        if filename not in z.namelist():
            return []
        with z.open(filename) as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            return [dict(row) for row in reader]

    @staticmethod
    def get_default_routes() -> list:
        """Return hardcoded default routes when API is unavailable."""
        return [
            {"route_id": "KJL001", "route_name": "LRT Kelana Jaya Line", "color": "#E91E63", "agency": "Rapid KL"},
            {"route_id": "KJL002", "route_name": "LRT Ampang Line", "color": "#4CAF50", "agency": "Rapid KL"},
            {"route_id": "KJL003", "route_name": "LRT Sri Petaling Line", "color": "#9C27B0", "agency": "Rapid KL"},
            {"route_id": "MRT01", "route_name": "MRT Kajang Line", "color": "#FF9800", "agency": "Rapid KL"},
            {"route_id": "MRT02", "route_name": "MRT Putrajaya Line", "color": "#2196F3", "agency": "Rapid KL"},
            {"route_id": "KTM01", "route_name": "KTM Komuter (Port Klang)", "color": "#F44336", "agency": "KTMB"},
            {"route_id": "KTM02", "route_name": "KTM Komuter (Seremban)", "color": "#00BCD4", "agency": "KTMB"},
            {"route_id": "KTM03", "route_name": "KTM ETS (KL-Butterworth)", "color": "#FF5722", "agency": "KTMB"},
            {"route_id": "MON01", "route_name": "KL Monorail", "color": "#3F51B5", "agency": "Rapid KL"},
            {"route_id": "BRT01", "route_name": "BRT Sunway Line", "color": "#8BC34A", "agency": "Rapid KL"},
        ]

    @staticmethod
    def clean_route_name(raw_name, route_type):
        """Strip redundant prefixes — the type badge already shows the category."""
        prefixes = [
            # KTMB
            "Electric Train Service ", "Intercity Ekspres Rakyat Timuran ",
            "Intercity Ekspres Selatan ", "Intercity Shuttle Tebrau ",
            "Intercity Shuttle ", "Intercity ", "KTM Komuter ",
            "KTM ",
            # Rapid KL
            "Rapid KL ", "KL ",
            # Generic transit type prefixes (if name starts with them)
            "LRT ", "MRT ",
        ]
        for p in prefixes:
            if raw_name.startswith(p):
                return raw_name[len(p):]
        return raw_name

    @staticmethod
    def get_gtfs_context(route_id: str) -> str:
        """
        Fetch GTFS Static and Realtime data for a route and return
        a text summary suitable for injection into the AI prompt.
        Returns empty string if no data is available.
        """
        parts = []
        agency_key, category = TransitDataService._route_to_agency(route_id)

        # 1. GTFS Static — upcoming departures
        try:
            gtfs = TransitDataService.fetch_static_gtfs(agency_key, category=category)
            if "error" not in gtfs and "trips" in gtfs and "stop_times" in gtfs:
                trips = gtfs.get("trips", [])
                stop_times = gtfs.get("stop_times", [])

                # Count trips for this route
                route_trips = [t for t in trips if t.get("route_id") == route_id]
                trip_ids = {t["trip_id"] for t in route_trips}

                # Get upcoming stop times for this route's trips
                route_times = [st for st in stop_times if st.get("trip_id") in trip_ids]
                # Take the first few departure times
                upcoming = sorted(route_times, key=lambda st: st.get("departure_time", "99:99"))[:8]

                if route_trips:
                    parts.append(
                        f"- 📅 Scheduled trips today: {len(route_trips)} trips\n"
                    )
                    if upcoming:
                        departures = ", ".join(
                            st.get("departure_time", "??")[:5] for st in upcoming
                        )
                        parts.append(f"  Departure times: {departures}")

                routes_data = gtfs.get("routes", [])
                route_info = next((r for r in routes_data if r.get("route_id") == route_id), None)
                if route_info:
                    short = route_info.get("route_short_name", "")
                    long = route_info.get("route_long_name", "")
                    desc = route_info.get("route_desc", "")
                    if desc:
                        parts.append(f"- Route description: {desc}")
                    elif long and long != short:
                        parts.append(f"- Route: {long}")
        except Exception:
            pass

        # 2. GTFS Realtime — active vehicles
        try:
            rt = TransitDataService.fetch_realtime(agency_key, category=category)
            if "error" not in rt:
                # Realtime data may be a list of vehicle positions or entity array
                entities = rt if isinstance(rt, list) else rt.get("entity", rt.get("entities", []))
                if isinstance(entities, list) and entities:
                    parts.append(f"- 🚌 Active vehicles tracked: {len(entities)}")
        except Exception:
            pass

        return "\n".join(parts) if parts else ""

    @staticmethod
    def _route_to_agency(route_id: str) -> tuple:
        """Map a route ID to (agency_key, category) for GTFS API calls."""
        route_prefix = route_id[:3].upper() if len(route_id) >= 3 else route_id.upper()
        if route_prefix in ("KJL", "MRT", "MON", "BRT"):
            return ("prasarana", "rapid-rail-kl")
        elif route_prefix == "KTM":
            return ("ktmb", None)
        return ("prasarana", "rapid-rail-kl")  # default fallback

    @staticmethod
    def seed_default_routes():
        """Seed routes from GTFS API with hardcoded fallback."""
        from app.database import get_db
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
            if count > 0:
                return  # Already seeded

            routes_seeded = 0
            stops_seeded = 0

            # Try fetching live GTFS data for each agency
            print("  [transit] Attempting to fetch live GTFS data from data.gov.my...")
            for agency_key, agency_info in TransitDataService.GTFS_AGENCIES.items():
                categories = agency_info.get("categories") or [None]
                for cat in categories:
                    try:
                        gtfs = TransitDataService.fetch_static_gtfs(agency_key, category=cat)
                        if "error" not in gtfs and "routes" in gtfs and gtfs["routes"]:
                            agency_name = agency_info["name"]
                            for r in gtfs["routes"][:80]:
                                rid = r.get("route_id", "")
                                rname = r.get("route_long_name") or r.get("route_short_name", "")
                                if not rname:
                                    continue
                                rt = r.get("route_type", "")
                                rname = TransitDataService.clean_route_name(rname, rt)
                                conn.execute(
                                    "INSERT OR IGNORE INTO routes (route_id, route_name, agency, color, route_type) VALUES (?, ?, ?, ?, ?)",
                                    (rid, rname, agency_name,
                                     f"#{r['route_color']}" if r.get("route_color") else "#3b82f6",
                                     rt),
                                )
                                routes_seeded += 1

                            for s in gtfs.get("stops", [])[:100]:
                                sid = s.get("stop_id", "")
                                sname = s.get("stop_name", "")
                                if not sname:
                                    continue
                                conn.execute(
                                    "INSERT OR IGNORE INTO stops (stop_id, stop_name, stop_lat, stop_lon) VALUES (?, ?, ?, ?)",
                                    (sid, sname,
                                     float(s.get("stop_lat", 0)) if s.get("stop_lat") else None,
                                     float(s.get("stop_lon", 0)) if s.get("stop_lon") else None),
                                )
                                stops_seeded += 1
                            print(f"  [transit] Seeded {routes_seeded} routes and {stops_seeded} stops from {agency_key}/{cat}")
                    except Exception as e:
                        print(f"  [transit] GTFS fetch failed for {agency_key}/{cat}: {e}")

            # Fall back to hardcoded defaults if nothing was fetched
            if routes_seeded == 0:
                print("  [transit] GTFS unavailable, seeding default routes")
                for r in TransitDataService.get_default_routes():
                    conn.execute(
                        "INSERT OR IGNORE INTO routes (route_id, route_name, agency, color) VALUES (?, ?, ?, ?)",
                        (r["route_id"], r["route_name"], r["agency"], r["color"]),
                    )
                print(f"  [transit] Seeded {len(TransitDataService.get_default_routes())} default routes.")
