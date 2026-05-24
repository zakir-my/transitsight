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
    def seed_default_routes():
        """Seed default routes into database if empty."""
        from app.database import get_db
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
            if count == 0:
                for r in TransitDataService.get_default_routes():
                    conn.execute(
                        "INSERT OR IGNORE INTO routes (route_id, route_name, agency, color) VALUES (?, ?, ?, ?)",
                        (r["route_id"], r["route_name"], r["agency"], r["color"]),
                    )
                print(f"Seeded {len(TransitDataService.get_default_routes())} default routes.")
