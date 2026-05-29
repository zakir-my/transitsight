"""Transit data service - fetches GTFS data from data.gov.my APIs."""

import requests
import io
import csv
import zipfile
from typing import Optional
from app.config import settings
from app.database import get_db


class TransitDataService:
    """Handles all data.gov.my GTFS API interactions."""

    GTFS_AGENCIES = {
        "ktmb": "Keretapi Tanah Melayu (KTMB)",
        "prasarana_rail": "Rapid KL (Prasarana) - Rail",
        "prasarana_bus": "Rapid KL (Prasarana) - Bus",
        "rapid_bus_penang": "Rapid Penang",
        "mybas_ipoh": "MyBAS Ipoh",
        "mybas_johor": "MyBAS Johor",
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
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code != 200:
                return {"error": f"API returned status {resp.status_code}"}

            # GTFS data comes as ZIP of CSV files
            try:
                z = zipfile.ZipFile(io.BytesIO(resp.content))
                routes = TransitDataService._parse_csv_in_zip(z, "routes.txt")
                stops = TransitDataService._parse_csv_in_zip(z, "stops.txt")
                trips = TransitDataService._parse_csv_in_zip(z, "trips.txt")
                stop_times = TransitDataService._parse_csv_in_zip(z, "stop_times.txt")
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
            return {"error": str(e)}

    @staticmethod
    def fetch_realtime(agency: str = "ktmb", category: Optional[str] = None) -> dict:
        """Fetch GTFS Realtime data (vehicle positions, arrivals)."""
        url = f"{settings.GTFS_REALTIME_BASE_URL}/{agency}"
        params = {}
        if category:
            params["category"] = category

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                try:
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
        # GTFS route_type: 0=light rail/tram, 1=subway, 2=rail, 3=bus
        prefixes = [
            "Electric Train Service ", "Intercity Ekspres Rakyat Timuran ",
            "Intercity Ekspres Selatan ", "Intercity Shuttle Tebrau ",
            "Intercity Shuttle ", "Intercity ", "KTM Komuter ",
            "KTM ", "Rapid KL ",
        ]
        for p in prefixes:
            if raw_name.startswith(p):
                return raw_name[len(p):]
        return raw_name

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

            # Try fetching live GTFS data for Rapid KL rail
            print("  [transit] Attempting to fetch live GTFS data from data.gov.my...")
            for agency_key in ["prasarana_rail", "ktmb"]:
                try:
                    gtfs = TransitDataService.fetch_static_gtfs(agency_key)
                    if "error" not in gtfs and "routes" in gtfs and gtfs["routes"]:
                        for r in gtfs["routes"][:50]:
                            rid = r.get("route_id", "")
                            rname = r.get("route_long_name") or r.get("route_short_name", "")
                            if not rname:
                                continue
                            rt = r.get("route_type", "")
                            rname = TransitDataService.clean_route_name(rname, rt)
                            conn.execute(
                                "INSERT OR IGNORE INTO routes (route_id, route_name, agency, color, route_type) VALUES (?, ?, ?, ?, ?)",
                                (rid, rname, gtfs.get("agency", [{}])[0].get("agency_name", agency_key) if gtfs.get("agency") else agency_key,
                                 r.get("route_color", "#3b82f6") if r.get("route_color") else "#3b82f6",
                                 r.get("route_type", "")),
                            )
                            routes_seeded += 1

                        # Seed stops
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
                        print(f"  [transit] Seeded {routes_seeded} routes and {stops_seeded} stops from {agency_key}")
                except Exception as e:
                    print(f"  [transit] GTFS fetch failed for {agency_key}: {e}")

            # Fall back to hardcoded defaults if nothing was fetched
            if routes_seeded == 0:
                print("  [transit] GTFS unavailable, seeding default routes")
                for r in TransitDataService.get_default_routes():
                    conn.execute(
                        "INSERT OR IGNORE INTO routes (route_id, route_name, agency, color) VALUES (?, ?, ?, ?)",
                        (r["route_id"], r["route_name"], r["agency"], r["color"]),
                    )
                print(f"  [transit] Seeded {len(TransitDataService.get_default_routes())} default routes.")
