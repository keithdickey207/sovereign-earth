#!/usr/bin/env python3
"""
Sovereign Earth Engine — planetary operations core for the Global Neural System.
Unifies worldwide ISR, defense posture, and neural mesh under 04901 command anchor.

Keith Alan Dickey — WSDS / 04901 Studio
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import sys

from neural_system import GlobalNeuralSystem
from satellite_tracking import SatelliteTracker
from maritime_tracking import MaritimeTracker

DISTRICT_ROOT = Path.home() / "projects" / "district_04901_grid"
if DISTRICT_ROOT.exists():
    sys.path.insert(0, str(DISTRICT_ROOT))

try:
    from capability.geographic_registry import GeographicRegistry
except ImportError:
    GeographicRegistry = None

CONFIG = Path(__file__).resolve().parent / "config" / "earth_nodes.json"
DEFENSE_MAP_CONFIG = Path(__file__).resolve().parent / "config" / "global_defense_map.json"
SHM_BUS = Path("/dev/shm/sovereign_earth.json")
EARTH_RADIUS_M = 6_371_000.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a)) / 1000


def latlon_offset(lat: float, lon: float, dx_km: float, dy_km: float) -> tuple[float, float]:
    dlat = (dy_km * 1000) / EARTH_RADIUS_M * (180 / math.pi)
    dlon = (dx_km * 1000) / (EARTH_RADIUS_M * math.cos(math.radians(lat))) * (180 / math.pi)
    return lat + dlat, lon + dlon


@dataclass
class EarthEntity:
    entity_id: str
    entity_type: str
    lat: float
    lon: float
    confidence: float
    source: str
    region: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["lat"] = round(d["lat"], 6)
        d["lon"] = round(d["lon"], 6)
        d["confidence"] = round(d["confidence"], 3)
        return d


@dataclass
class EarthScan:
    lat: float
    lon: float
    timestamp: float
    location_name: str
    region: str
    humans: int
    animals: int
    entities: list[dict]
    satellites: list[str]
    resolution_m: float
    confidence: float
    neural_activation: float
    nearest_node: str
    distance_to_anchor_km: float
    in_maine: bool
    seq: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EarthEngine:
    """Planetary engine — global ISR + neural mesh orchestration."""

    def __init__(self):
        with open(CONFIG, encoding="utf-8") as f:
            self.config = json.load(f)
        self.anchor = self.config.get("primary_anchor", {})
        self.earth_bbox = self.config.get("earth_bbox", {})
        self.regions = self.config.get("regions", [])
        self.neural = GlobalNeuralSystem()
        self.satellites = SatelliteTracker()
        self.maritime = MaritimeTracker()
        with open(DEFENSE_MAP_CONFIG, encoding="utf-8") as f:
            self.defense_map = json.load(f)
        self._seq = 0
        self._geo = GeographicRegistry() if GeographicRegistry else None

    def in_earth(self, lat: float, lon: float) -> bool:
        b = self.earth_bbox
        return b.get("south", -90) <= lat <= b.get("north", 90) and b.get("west", -180) <= lon <= b.get("east", 180)

    def region_for(self, lat: float, lon: float) -> str:
        for r in self.regions:
            if r["lat_min"] <= lat <= r["lat_max"] and r["lon_min"] <= lon <= r["lon_max"]:
                return r["label"]
        return "Open Ocean / Polar"

    def _nearest_node(self, lat: float, lon: float) -> tuple[str, float]:
        best_id, best_dist = "04901_anchor", 99999.0
        for n in self.neural._nodes.values():
            d = haversine_km(lat, lon, n.lat, n.lon)
            if d < best_dist:
                best_dist, best_id = d, n.node_id
        return best_id, best_dist

    def scan(self, lat: float, lon: float) -> EarthScan | None:
        if not self.in_earth(lat, lon):
            return None

        self._seq += 1
        seed = hash(f"{round(lat, 3)}_{round(lon, 3)}_{int(time.time()) // 20}") % 10000
        rng = random.Random(seed)

        region = self.region_for(lat, lon)
        geo = self._geo.nearest_place(lat, lon) if self._geo else {}
        location_name = geo.get("location_name") or f"{region} — {round(lat, 2)}°N {round(lon, 2)}°E"
        nearest, dist = self._nearest_node(lat, lon)
        anchor_dist = haversine_km(lat, lon, self.anchor.get("lat", 44.552), self.anchor.get("lon", -69.632))

        resolution = 0.5 if anchor_dist < 50 else (10 if anchor_dist < 500 else 30)
        sats = ["planet_skysat", "sentinel_2b"] if resolution <= 10 else ["landsat_9", "goes_18", "sentinel_2b"]

        land = "urban" if rng.random() > 0.6 else ("forest" if rng.random() > 0.4 else "coastal")
        humans = max(0, int(rng.uniform(0, 8) * (1.5 if land == "urban" else 0.5)))
        animals = max(0, int(rng.uniform(0, 12) * (1.5 if land == "forest" else 0.4)))

        entities: list[EarthEntity] = []
        for i in range(humans):
            angle = rng.uniform(0, 360)
            d = rng.uniform(0.05, 2.0)
            elat, elon = latlon_offset(lat, lon, d * math.cos(math.radians(angle)), d * math.sin(math.radians(angle)))
            entities.append(EarthEntity(
                f"earth_h_{i}", "human", elat, elon,
                rng.uniform(0.5, 0.9), "satellite_lwir", region,
            ))
        for i in range(animals):
            angle = rng.uniform(0, 360)
            d = rng.uniform(0.1, 3.0)
            elat, elon = latlon_offset(lat, lon, d * math.cos(math.radians(angle)), d * math.sin(math.radians(angle)))
            entities.append(EarthEntity(
                f"earth_a_{i}", "animal", elat, elon,
                rng.uniform(0.4, 0.85), "satellite_mwir", region,
            ))

        signal = min(1.0, (humans + animals) * 0.08 + 0.2)
        self.neural.ingest_sensory(signal, source="earth_isr")

        maine_region = any(
            r["id"] == "maine_207" and r["lat_min"] <= lat <= r["lat_max"] and r["lon_min"] <= lon <= r["lon_max"]
            for r in self.regions
        )

        return EarthScan(
            lat=round(lat, 6), lon=round(lon, 6),
            timestamp=time.time(),
            location_name=location_name,
            region=region,
            humans=humans, animals=animals,
            entities=[e.to_dict() for e in entities],
            satellites=sats,
            resolution_m=resolution,
            confidence=round(rng.uniform(0.55, 0.92), 3),
            neural_activation=round(self.neural._nodes.get(nearest, self.neural._nodes["04901_anchor"]).activation, 3),
            nearest_node=nearest,
            distance_to_anchor_km=round(anchor_dist, 1),
            in_maine=maine_region,
            seq=self._seq,
        )

    def ingest_defense(self, posture: dict) -> None:
        self.neural.ingest_full_posture(posture)
        self.neural.ingest_cognitive(0.5, ollama_ok=True)
        self.neural.ingest_gns(True)

    def ingest_air_defense(self, air_msg: dict) -> None:
        tracks = int(air_msg.get("aircraft_count", 0)) + int(air_msg.get("missile_count", 0)) + int(air_msg.get("drone_count", 0))
        self.neural.ingest_air_defense(tracks, int(air_msg.get("hostile_count", 0)))

    def publish_bus(self, payload: dict) -> None:
        try:
            SHM_BUS.write_text(json.dumps(payload, indent=2))
        except OSError:
            pass

    def ws_neural(self) -> dict[str, Any]:
        msg = self.neural.ws_message()
        self.publish_bus(msg)
        return msg

    def ws_satellite_tracks(self) -> dict[str, Any]:
        return self.satellites.ws_message()

    def ws_maritime_tracks(self) -> dict[str, Any]:
        return self.maritime.ws_message()

    def ws_global_defense_map(self) -> dict[str, Any]:
        installations = self.defense_map.get("installations", [])
        return {
            "type": "global_defense_map",
            "version": self.defense_map.get("version", "1.0"),
            "layer_groups": self.defense_map.get("layer_groups", []),
            "installations": installations,
            "installation_count": len(installations),
        }

    def ws_earth_meta(self) -> dict[str, Any]:
        return {
            "type": "earth_meta",
            "engine": "Sovereign Earth Engine v3",
            "version": "3.0",
            "primary_anchor": self.anchor,
            "earth_bbox": self.earth_bbox,
            "regions": self.regions,
            "node_count": len(self.neural._nodes),
            "link_count": len(self.neural._links),
            "satellite_count": len(self.satellites._catalog),
            "vessel_count": len(self.maritime._vessels),
            "defense_installations": len(self.defense_map.get("installations", [])),
            "airport_count": sum(
                1 for i in self.defense_map.get("installations", []) if i.get("type") == "airport"
            ),
            "backend": {
                "neural_mesh": True,
                "satellite_tracking": True,
                "global_defense_map": True,
                "shm_bus": str(SHM_BUS),
            },
            "default_zoom": 3,
            "min_zoom": 2,
            "max_zoom": 18,
            "anchor_zoom": 8,
        }

    def ws_scan(self, lat: float, lon: float) -> dict[str, Any]:
        scan = self.scan(lat, lon)
        if not scan:
            return {"type": "scan_error", "message": "Outside Earth bounds"}
        d = scan.to_dict()
        d["type"] = "earth_scan"
        d["scan_mode"] = "earth_neural"
        if self._geo:
            d.update(self._geo.nearest_place(lat, lon))
        tracks = self.satellites.tick()
        overhead = [
            t.name for t in tracks
            if haversine_km(t.lat, t.lon, lat, lon) < t.footprint_km / 2
        ]
        d["overhead_satellites"] = overhead[:5]
        return d
