"""
GDF-AutoMon — complete seed script (v3).
91 sensors across 7 locations, full RBAC, alert rules + actions, plans, tasks, telemetry.

Usage (from backend/):
    python scripts/seed.py
"""
import asyncio
import json as _json
import math
import random
import uuid
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://gdf:gdf_secure_2024@localhost:5432/gdfautomon"

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def h(plain: str) -> str:
    return _pwd.hash(plain)


def now() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return str(uuid.uuid4())


async def seed(db: AsyncSession) -> None:

    # ── Wipe everything (idempotent) ──────────────────────────────────────────
    await db.execute(text(
        "TRUNCATE TABLE locations, users, sensors, sensor_readings, "
        "alert_rules, alert_rule_actions, active_alerts, push_subscriptions, "
        "user_location_permissions, user_sensor_permissions, "
        "notification_preferences, password_reset_tokens, "
        "plans, plan_actions, "
        "tasks, task_assignments, task_attachments, "
        "chat_rooms, chat_room_members, chat_messages, chat_attachments "
        "RESTART IDENTITY CASCADE"
    ))
    await db.commit()

    # ══════════════════════════════════════════════════════════════════════════
    # IDs — locations
    # ══════════════════════════════════════════════════════════════════════════
    loc_barn       = uid()
    loc_milk       = uid()
    loc_pasture    = uid()
    loc_feed       = uid()
    loc_vet        = uid()
    loc_processing = uid()   # NEW: Processing & Packaging Plant
    loc_utilities  = uid()   # NEW: Water & Utility Station

    # ── users ─────────────────────────────────────────────────────────────────
    u_super = uid()
    u_admin = uid()
    u_op1   = uid()   # Alice — barn + parlor
    u_op2   = uid()   # Bob   — parlor + pasture + feed
    u_op3   = uid()   # Carol — processing + utilities (NEW)

    # ══════════════════════════════════════════════════════════════════════════
    # Sensor IDs
    # ══════════════════════════════════════════════════════════════════════════

    # ── MAIN BARN (18) ────────────────────────────────────────────────────────
    # temperature_humidity (8)
    s_temp_barn_ne      = uid()
    s_temp_barn_nw      = uid()
    s_temp_barn_se      = uid()
    s_temp_barn_sw      = uid()
    s_temp_barn_center  = uid()
    s_temp_barn_loft    = uid()
    s_temp_barn_kid     = uid()   # kidding pen
    s_temp_barn_medprep = uid()   # medical prep area
    # weight_hx711 (6)
    s_wt_goat_a    = uid()
    s_wt_goat_b    = uid()
    s_wt_goat_c    = uid()
    s_wt_goat_d    = uid()
    s_wt_feed_main = uid()
    s_wt_kidding   = uid()   # newborn kid scale
    # ip_camera_rtsp (4)
    s_cam_barn_ne       = uid()
    s_cam_barn_nw       = uid()
    s_cam_barn_south    = uid()
    s_cam_barn_overhead = uid()

    # ── MILKING PARLOR (21) ───────────────────────────────────────────────────
    # temperature_humidity (5)
    s_temp_milk_entry   = uid()
    s_temp_milk_center  = uid()
    s_temp_milk_wash    = uid()
    s_temp_milk_chiller = uid()
    s_temp_milk_freezer = uid()   # freezer room
    # weight_hx711 (6)
    s_wt_tank_1    = uid()
    s_wt_tank_2    = uid()
    s_wt_tank_3    = uid()
    s_wt_trough_1  = uid()
    s_wt_trough_2  = uid()
    s_wt_cream_sep = uid()   # cream separator output
    # milk_analyzer_lactoscan (7)
    s_ma_line1 = uid()
    s_ma_line2 = uid()
    s_ma_line3 = uid()
    s_ma_line4 = uid()
    s_ma_line5 = uid()
    s_ma_line6 = uid()
    s_ma_line7 = uid()   # additional line
    # ip_camera_rtsp (3)
    s_cam_milk_main  = uid()
    s_cam_milk_entry = uid()
    s_cam_milk_exit  = uid()

    # ── OUTDOOR PASTURE (10) ──────────────────────────────────────────────────
    # temperature_humidity (4)
    s_temp_pas_north   = uid()
    s_temp_pas_center  = uid()
    s_temp_pas_south   = uid()
    s_temp_pas_shelter = uid()   # shade shelter
    # weight_hx711 (1)
    s_wt_pas_trough = uid()   # outdoor water trough
    # ip_camera_rtsp (5)
    s_cam_pas_north = uid()
    s_cam_pas_east  = uid()
    s_cam_pas_south = uid()
    s_cam_gate      = uid()
    s_cam_pas_west  = uid()   # west perimeter

    # ── FEED STORE (12) ───────────────────────────────────────────────────────
    # temperature_humidity (5)
    s_temp_feed_silo1   = uid()
    s_temp_feed_silo2   = uid()
    s_temp_hay_loft     = uid()
    s_temp_feed_ambient = uid()
    s_temp_feed_proc    = uid()   # processing / mixing area
    # weight_hx711 (5)
    s_wt_silo_1  = uid()
    s_wt_silo_2  = uid()
    s_wt_hay     = uid()
    s_wt_pellet  = uid()
    s_wt_mineral = uid()   # mineral supplement bin
    # ip_camera_rtsp (2)
    s_cam_feed_entry    = uid()
    s_cam_feed_interior = uid()

    # ── VETERINARY BAY (10) ───────────────────────────────────────────────────
    # temperature_humidity (4)
    s_temp_vet_exam  = uid()
    s_temp_vet_iso_a = uid()
    s_temp_vet_iso_b = uid()
    s_temp_vet_lab   = uid()   # laboratory room
    # weight_hx711 (2)
    s_wt_vet_table  = uid()
    s_wt_vet_supply = uid()
    # milk_analyzer_lactoscan (2)
    s_ma_vet1 = uid()
    s_ma_vet2 = uid()
    # ip_camera_rtsp (2)
    s_cam_vet_reception = uid()
    s_cam_vet_iso       = uid()   # isolation pen camera

    # ── PROCESSING & PACKAGING PLANT (12 — NEW) ───────────────────────────────
    # temperature_humidity (3)
    s_temp_proc_hall = uid()   # packaging hall
    s_temp_proc_cold = uid()   # cold-store exit corridor
    s_temp_proc_fill = uid()   # filling / bottling room
    # weight_hx711 (2)
    s_wt_bottle_scale = uid()   # filled-bottle line scale
    s_wt_carton_scale = uid()   # carton packing scale
    # milk_analyzer_lactoscan (4)
    s_ma_proc_qa1 = uid()   # post-pasteurisation QC 1
    s_ma_proc_qa2 = uid()   # post-pasteurisation QC 2
    s_ma_proc_qa3 = uid()   # bottled-milk spot-check
    s_ma_proc_qa4 = uid()   # end-of-line validation
    # ip_camera_rtsp (3)
    s_cam_proc_line = uid()   # production line overview
    s_cam_proc_cold = uid()   # cold-storage loading
    s_cam_proc_exit = uid()   # loading dock exit

    # ── WATER & UTILITIES STATION (8 — NEW) ──────────────────────────────────
    # temperature_humidity (3)
    s_temp_pump_room   = uid()
    s_temp_boiler_room = uid()
    s_temp_cool_tower  = uid()   # cooling tower ambient
    # weight_hx711 (3)
    s_wt_water_main  = uid()   # main water tank (10 000 L)
    s_wt_water_sec   = uid()   # secondary water tank (5 000 L)
    s_wt_diesel_tank = uid()   # diesel fuel storage
    # ip_camera_rtsp (2)
    s_cam_pump_room   = uid()
    s_cam_water_tower = uid()

    # ── misc ──────────────────────────────────────────────────────────────────
    p1 = uid(); p2 = uid(); p3 = uid()
    t1 = uid(); t2 = uid(); t3 = uid(); t4 = uid(); t5 = uid(); t6 = uid()
    r_general = uid(); r_task1 = uid()

    # ══════════════════════════════════════════════════════════════════════════
    # Locations (7)
    # ══════════════════════════════════════════════════════════════════════════
    await db.execute(text("""
        INSERT INTO locations (id, name, description, address) VALUES
        (:l1, 'Main Barn',                  'Primary housing for 180 Boer goats, 6 zones',          'Section A — Farm North'),
        (:l2, 'Milking Parlor',             'Automated 6-line milking station, 36 stands',           'Section B — Farm Centre'),
        (:l3, 'Outdoor Pasture',            'East + West grazing fields, 14 acres total',             'Section C — Farm East'),
        (:l4, 'Feed Store',                 'Grain silos, hay loft and pellet bins',                 'Section D — Farm West'),
        (:l5, 'Veterinary Bay',             'Examination rooms, 2 isolation pens, laboratory',       'Section E — Farm South'),
        (:l6, 'Processing & Packaging',     'Pasteurisation plant, bottling lines, cold storage',    'Section F — Farm Centre-East'),
        (:l7, 'Water & Utilities Station',  'Pump rooms, boiler, cooling tower, fuel storage',       'Section G — Farm North-West')
    """), {"l1": loc_barn, "l2": loc_milk, "l3": loc_pasture, "l4": loc_feed,
           "l5": loc_vet, "l6": loc_processing, "l7": loc_utilities})

    # ══════════════════════════════════════════════════════════════════════════
    # Users (5)  — include profile fields added in migration 003
    # ══════════════════════════════════════════════════════════════════════════
    await db.execute(text("""
        INSERT INTO users
            (id, email, full_name, password_hash, role, is_active,
             phone, working_hours, duty, current_location)
        VALUES
            (:id, :email, :name, :pw, :role, true, :phone, :wh, :duty, :cloc)
    """), [
        {"id": u_super, "email": "superadmin@gdf.farm",
         "name": "Super Admin",    "pw": h("Admin@1234"),    "role": "super_admin",
         "phone": "+92-300-0000001", "wh": "24/7",
         "duty": "Platform Administration",  "cloc": "Head Office"},
        {"id": u_admin, "email": "admin@gdf.farm",
         "name": "Farm Admin",     "pw": h("Admin@1234"),    "role": "admin",
         "phone": "+92-300-0000002", "wh": "06:00–18:00",
         "duty": "Farm Operations Management", "cloc": "Admin Building"},
        {"id": u_op1, "email": "operator1@gdf.farm",
         "name": "Alice Operator", "pw": h("Operator@1234"), "role": "operator",
         "phone": "+92-300-0000003", "wh": "06:00–14:00",
         "duty": "Barn & Parlour Operations", "cloc": "Main Barn"},
        {"id": u_op2, "email": "operator2@gdf.farm",
         "name": "Bob Operator",   "pw": h("Operator@1234"), "role": "operator",
         "phone": "+92-300-0000004", "wh": "14:00–22:00",
         "duty": "Pasture & Feed Operations", "cloc": "Outdoor Pasture"},
        {"id": u_op3, "email": "operator3@gdf.farm",
         "name": "Carol Operator", "pw": h("Operator@1234"), "role": "operator",
         "phone": "+92-300-0000005", "wh": "08:00–16:00",
         "duty": "Processing & Quality Control", "cloc": "Processing Plant"},
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # User location permissions
    # ══════════════════════════════════════════════════════════════════════════
    loc_perms = [
        # admin: all 7 locations
        (u_admin, loc_barn), (u_admin, loc_milk), (u_admin, loc_pasture),
        (u_admin, loc_feed), (u_admin, loc_vet),
        (u_admin, loc_processing), (u_admin, loc_utilities),
        # Alice: barn + parlor
        (u_op1, loc_barn), (u_op1, loc_milk),
        # Bob: parlor + pasture + feed
        (u_op2, loc_milk), (u_op2, loc_pasture), (u_op2, loc_feed),
        # Carol: processing + utilities
        (u_op3, loc_processing), (u_op3, loc_utilities),
    ]
    for user_id, loc_id in loc_perms:
        await db.execute(text(
            "INSERT INTO user_location_permissions (id, user_id, location_id) "
            "VALUES (:id, :uid, :lid)"
        ), {"id": uid(), "uid": user_id, "lid": loc_id})

    # ══════════════════════════════════════════════════════════════════════════
    # Sensors — 91 total
    # Sensor type slugs MUST match the registered plugin sensor_type values:
    #   temperature_humidity | weight_hx711 | milk_analyzer_lactoscan | ip_camera_rtsp
    # ══════════════════════════════════════════════════════════════════════════
    sensors = [

        # ────────────────────────── MAIN BARN (18) ───────────────────────────

        # temperature_humidity × 8
        {"id": s_temp_barn_ne,     "name": "Barn Temp NE",           "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_barn_ne}",     "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "North-east corner ambient temperature & humidity"},
        {"id": s_temp_barn_nw,     "name": "Barn Temp NW",           "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_barn_nw}",     "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "North-west corner ambient temperature & humidity"},
        {"id": s_temp_barn_se,     "name": "Barn Temp SE",           "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_barn_se}",     "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "South-east corner ambient temperature & humidity"},
        {"id": s_temp_barn_sw,     "name": "Barn Temp SW",           "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_barn_sw}",     "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "South-west corner ambient temperature & humidity"},
        {"id": s_temp_barn_center, "name": "Barn Temp Center",       "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_barn_center}", "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Central aisle ambient temperature & humidity"},
        {"id": s_temp_barn_loft,   "name": "Barn Loft Temp",         "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_barn_loft}",   "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Hay loft temperature probe — fire-risk monitoring"},
        {"id": s_temp_barn_kid,    "name": "Kidding Pen Temp",        "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_barn_kid}",    "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Kidding pen temperature & humidity — newborn welfare"},
        {"id": s_temp_barn_medprep,"name": "Medical Prep Area Temp",  "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_barn_medprep}","temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Medical preparation area ambient temp & humidity"},

        # weight_hx711 × 6
        {"id": s_wt_goat_a,    "name": "Weigh Scale Alpha",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_goat_a}",    "capacity_kg": 150, "unit": "kg"},
         "desc": "Platform scale — pen A, adult goat weighing"},
        {"id": s_wt_goat_b,    "name": "Weigh Scale Beta",   "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_goat_b}",    "capacity_kg": 150, "unit": "kg"},
         "desc": "Platform scale — pen B, adult goat weighing"},
        {"id": s_wt_goat_c,    "name": "Weigh Scale Gamma",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_goat_c}",    "capacity_kg": 150, "unit": "kg"},
         "desc": "Platform scale — pen C, adult goat weighing"},
        {"id": s_wt_goat_d,    "name": "Weigh Scale Delta",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_goat_d}",    "capacity_kg": 150, "unit": "kg"},
         "desc": "Platform scale — pen D, adult goat weighing"},
        {"id": s_wt_feed_main, "name": "Feed Hopper Main",   "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_feed_main}", "capacity_kg": 600, "unit": "kg"},
         "desc": "Primary feed hopper load cell — barn central aisle"},
        {"id": s_wt_kidding,   "name": "Kidding Scale",       "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_barn,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_kidding}",   "capacity_kg": 30,  "unit": "kg"},
         "desc": "Precision newborn kid scale — birth weight tracking"},

        # ip_camera_rtsp × 4
        {"id": s_cam_barn_ne,       "name": "Barn Cam NE",          "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_barn,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.40:554/stream1",
                    "hls_host": "192.168.1.10", "hls_port": 8090,
                    "mqtt_topic_prefix": f"gdf/{s_cam_barn_ne}", "record_motion_events": True},
         "desc": "North-east corner wide-angle camera"},
        {"id": s_cam_barn_nw,       "name": "Barn Cam NW",          "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_barn,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.41:554/stream1",
                    "hls_host": "192.168.1.10", "hls_port": 8091,
                    "mqtt_topic_prefix": f"gdf/{s_cam_barn_nw}", "record_motion_events": True},
         "desc": "North-west corner wide-angle camera"},
        {"id": s_cam_barn_south,    "name": "Barn South Entrance",  "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_barn,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.42:554/stream1",
                    "hls_host": "192.168.1.10", "hls_port": 8092,
                    "mqtt_topic_prefix": f"gdf/{s_cam_barn_south}", "record_motion_events": True},
         "desc": "South entrance HD security camera"},
        {"id": s_cam_barn_overhead, "name": "Barn Overhead Cam",    "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_barn,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.43:554/stream1",
                    "hls_host": "192.168.1.10", "hls_port": 8093,
                    "mqtt_topic_prefix": f"gdf/{s_cam_barn_overhead}", "record_motion_events": False},
         "desc": "Overhead panoramic camera covering central aisle"},

        # ─────────────────────── MILKING PARLOR (21) ─────────────────────────

        # temperature_humidity × 5
        {"id": s_temp_milk_entry,   "name": "Parlour Entry Temp",    "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_milk_entry}",   "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Entry foyer ambient temperature & humidity"},
        {"id": s_temp_milk_center,  "name": "Parlour Centre Temp",   "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_milk_center}",  "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Milking floor central ambient temperature & humidity"},
        {"id": s_temp_milk_wash,    "name": "Wash Bay Temp",         "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_milk_wash}",    "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "CIP wash bay temperature & humidity probe"},
        {"id": s_temp_milk_chiller, "name": "Chiller Room Temp",     "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_milk_chiller}", "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Bulk milk chiller room temperature (target 4°C)"},
        {"id": s_temp_milk_freezer, "name": "Freezer Room Temp",     "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_milk_freezer}", "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Frozen dairy products room (target -18°C)"},

        # weight_hx711 × 6
        {"id": s_wt_tank_1,    "name": "Milk Tank 1 Scale",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_tank_1}",    "capacity_kg": 1200, "unit": "kg"},
         "desc": "Bulk milk cooling tank 1 weight sensor"},
        {"id": s_wt_tank_2,    "name": "Milk Tank 2 Scale",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_tank_2}",    "capacity_kg": 1200, "unit": "kg"},
         "desc": "Bulk milk cooling tank 2 weight sensor"},
        {"id": s_wt_tank_3,    "name": "Milk Tank 3 Scale",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_tank_3}",    "capacity_kg": 800,  "unit": "kg"},
         "desc": "Overflow bulk tank 3 weight sensor"},
        {"id": s_wt_trough_1,  "name": "Feed Trough 1",      "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_trough_1}",  "capacity_kg": 200,  "unit": "kg"},
         "desc": "Parlour feed trough 1 — east side"},
        {"id": s_wt_trough_2,  "name": "Feed Trough 2",      "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_trough_2}",  "capacity_kg": 200,  "unit": "kg"},
         "desc": "Parlour feed trough 2 — west side"},
        {"id": s_wt_cream_sep, "name": "Cream Separator Scale","sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_cream_sep}", "capacity_kg": 500,  "unit": "kg"},
         "desc": "Cream separator output collection scale"},

        # milk_analyzer_lactoscan × 7
        {"id": s_ma_line1, "name": "Milk Analyser Line 1", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_line1}", "scc_alert_threshold": 200000, "fat_min": 2.5, "fat_max": 5.5},
         "desc": "Primary inline milk quality analyser — fat, protein, lactose, SCC"},
        {"id": s_ma_line2, "name": "Milk Analyser Line 2", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_line2}", "scc_alert_threshold": 200000, "fat_min": 2.5, "fat_max": 5.5},
         "desc": "Secondary analyser for batch validation"},
        {"id": s_ma_line3, "name": "Milk Analyser Line 3", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_line3}", "scc_alert_threshold": 200000, "fat_min": 2.5, "fat_max": 5.5},
         "desc": "Third inline analyser — morning session"},
        {"id": s_ma_line4, "name": "Milk Analyser Line 4", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_line4}", "scc_alert_threshold": 200000, "fat_min": 2.5, "fat_max": 5.5},
         "desc": "Fourth inline analyser — evening session"},
        {"id": s_ma_line5, "name": "Milk Analyser Line 5", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_line5}", "scc_alert_threshold": 250000, "fat_min": 2.5, "fat_max": 5.5},
         "desc": "Spot-check analyser — random sampling"},
        {"id": s_ma_line6, "name": "Milk Analyser Line 6", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_line6}", "scc_alert_threshold": 250000, "fat_min": 2.5, "fat_max": 5.5},
         "desc": "End-of-day batch consolidation analyser"},
        {"id": s_ma_line7, "name": "Milk Analyser Line 7", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_milk,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_line7}", "scc_alert_threshold": 200000, "fat_min": 2.5, "fat_max": 5.5},
         "desc": "Additional analyser — peak season overflow line"},

        # ip_camera_rtsp × 3
        {"id": s_cam_milk_main,  "name": "Parlour Main Floor Cam",  "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_milk,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.50:554/stream1",
                    "hls_host": "192.168.1.11", "hls_port": 8090,
                    "mqtt_topic_prefix": f"gdf/{s_cam_milk_main}", "record_motion_events": True},
         "desc": "Main milking floor overhead HD camera"},
        {"id": s_cam_milk_entry, "name": "Parlour Entry Cam",       "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_milk,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.51:554/stream1",
                    "hls_host": "192.168.1.11", "hls_port": 8091,
                    "mqtt_topic_prefix": f"gdf/{s_cam_milk_entry}", "record_motion_events": True},
         "desc": "Parlour entry lane camera — goat flow monitoring"},
        {"id": s_cam_milk_exit,  "name": "Parlour Exit Cam",        "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_milk,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.52:554/stream1",
                    "hls_host": "192.168.1.11", "hls_port": 8092,
                    "mqtt_topic_prefix": f"gdf/{s_cam_milk_exit}", "record_motion_events": True},
         "desc": "Parlour exit lane camera — throughput counting"},

        # ─────────────────────── OUTDOOR PASTURE (10) ────────────────────────

        # temperature_humidity × 4
        {"id": s_temp_pas_north,   "name": "Pasture North Temp",    "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_pasture,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_pas_north}",   "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "North pasture weather-station temperature & humidity"},
        {"id": s_temp_pas_center,  "name": "Pasture Centre Temp",   "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_pasture,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_pas_center}",  "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Central pasture temperature near water trough"},
        {"id": s_temp_pas_south,   "name": "Pasture South Temp",    "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_pasture,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_pas_south}",   "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "South pasture boundary temperature probe"},
        {"id": s_temp_pas_shelter, "name": "Shade Shelter Temp",    "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_pasture,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_pas_shelter}", "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Shade shelter ambient temp & humidity — heat-stress refuge"},

        # weight_hx711 × 1
        {"id": s_wt_pas_trough, "name": "Pasture Water Trough Scale","sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_pasture,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_pas_trough}", "capacity_kg": 500, "unit": "kg"},
         "desc": "Outdoor water trough fill-level sensor"},

        # ip_camera_rtsp × 5
        {"id": s_cam_pas_north,  "name": "Pasture North Fence Cam",  "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_pasture,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.60:554/stream1",
                    "hls_host": "192.168.1.12", "hls_port": 8090,
                    "mqtt_topic_prefix": f"gdf/{s_cam_pas_north}", "record_motion_events": True},
         "desc": "North pasture perimeter camera"},
        {"id": s_cam_pas_east,   "name": "Pasture East Fence Cam",   "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_pasture,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.61:554/stream1",
                    "hls_host": "192.168.1.12", "hls_port": 8091,
                    "mqtt_topic_prefix": f"gdf/{s_cam_pas_east}", "record_motion_events": True},
         "desc": "East pasture fence line camera"},
        {"id": s_cam_pas_south,  "name": "Pasture South Fence Cam",  "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_pasture,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.62:554/stream1",
                    "hls_host": "192.168.1.12", "hls_port": 8092,
                    "mqtt_topic_prefix": f"gdf/{s_cam_pas_south}", "record_motion_events": True},
         "desc": "South pasture boundary camera"},
        {"id": s_cam_gate,       "name": "Main Gate CCTV",           "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_pasture,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.63:554/stream1",
                    "hls_host": "192.168.1.12", "hls_port": 8093,
                    "mqtt_topic_prefix": f"gdf/{s_cam_gate}", "record_motion_events": True},
         "desc": "Farm main gate wide-angle security camera"},
        {"id": s_cam_pas_west,   "name": "Pasture West Fence Cam",   "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_pasture,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.64:554/stream1",
                    "hls_host": "192.168.1.12", "hls_port": 8094,
                    "mqtt_topic_prefix": f"gdf/{s_cam_pas_west}", "record_motion_events": True},
         "desc": "West perimeter fence camera"},

        # ────────────────────────── FEED STORE (12) ──────────────────────────

        # temperature_humidity × 5
        {"id": s_temp_feed_silo1,   "name": "Grain Silo 1 Temp",    "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_feed_silo1}",   "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Grain silo 1 core temperature — spoilage detection"},
        {"id": s_temp_feed_silo2,   "name": "Grain Silo 2 Temp",    "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_feed_silo2}",   "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Grain silo 2 core temperature — spoilage detection"},
        {"id": s_temp_hay_loft,     "name": "Hay Loft Temp",        "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_hay_loft}",     "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Hay loft temperature & humidity — fire-risk monitoring"},
        {"id": s_temp_feed_ambient, "name": "Feed Store Ambient",   "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_feed_ambient}", "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Feed store building ambient temperature & humidity"},
        {"id": s_temp_feed_proc,    "name": "Feed Mixing Area Temp","sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_feed_proc}",    "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Feed mixing and processing area ambient temperature"},

        # weight_hx711 × 5
        {"id": s_wt_silo_1,  "name": "Grain Silo 1 Scale",     "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_silo_1}",  "capacity_kg": 5000, "unit": "kg"},
         "desc": "Grain silo 1 load-cell inventory scale"},
        {"id": s_wt_silo_2,  "name": "Grain Silo 2 Scale",     "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_silo_2}",  "capacity_kg": 5000, "unit": "kg"},
         "desc": "Grain silo 2 load-cell inventory scale"},
        {"id": s_wt_hay,     "name": "Hay Bale Platform Scale","sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_hay}",     "capacity_kg": 2000, "unit": "kg"},
         "desc": "Hay bale receiving platform scale"},
        {"id": s_wt_pellet,  "name": "Pellet Bin Scale",       "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_pellet}",  "capacity_kg": 1000, "unit": "kg"},
         "desc": "Compressed pellet feed bin load cell"},
        {"id": s_wt_mineral, "name": "Mineral Supplement Bin", "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_feed,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_mineral}", "capacity_kg": 500,  "unit": "kg"},
         "desc": "Mineral and vitamin supplement storage bin scale"},

        # ip_camera_rtsp × 2
        {"id": s_cam_feed_entry,    "name": "Feed Store Entry Cam",    "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_feed,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.70:554/stream1",
                    "hls_host": "192.168.1.13", "hls_port": 8090,
                    "mqtt_topic_prefix": f"gdf/{s_cam_feed_entry}", "record_motion_events": True},
         "desc": "Feed store entrance security camera"},
        {"id": s_cam_feed_interior, "name": "Feed Store Interior Cam", "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_feed,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.71:554/stream1",
                    "hls_host": "192.168.1.13", "hls_port": 8091,
                    "mqtt_topic_prefix": f"gdf/{s_cam_feed_interior}", "record_motion_events": False},
         "desc": "Feed store interior overview camera"},

        # ──────────────────────── VETERINARY BAY (10) ────────────────────────

        # temperature_humidity × 4
        {"id": s_temp_vet_exam,  "name": "Vet Exam Room Temp",    "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_vet,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_vet_exam}",  "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Examination room controlled ambient temperature"},
        {"id": s_temp_vet_iso_a, "name": "Vet Isolation A Temp",  "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_vet,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_vet_iso_a}", "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Isolation pen A temperature — sick animal monitoring"},
        {"id": s_temp_vet_iso_b, "name": "Vet Isolation B Temp",  "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_vet,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_vet_iso_b}", "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Isolation pen B temperature — quarantine monitoring"},
        {"id": s_temp_vet_lab,   "name": "Vet Laboratory Temp",   "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_vet,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_vet_lab}",   "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Laboratory room temperature & humidity — reagent storage compliance"},

        # weight_hx711 × 2
        {"id": s_wt_vet_table,  "name": "Vet Treatment Scale",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_vet,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_vet_table}",  "capacity_kg": 200, "unit": "kg"},
         "desc": "Precision treatment table scale — medication dosing"},
        {"id": s_wt_vet_supply, "name": "Medical Supply Scale",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_vet,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_vet_supply}", "capacity_kg": 50,  "unit": "kg"},
         "desc": "Medical consumables inventory weight sensor"},

        # milk_analyzer_lactoscan × 2
        {"id": s_ma_vet1, "name": "Lab Analyser 1", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_vet,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_vet1}", "scc_alert_threshold": 400000, "fat_min": 2.0, "fat_max": 6.0},
         "desc": "Veterinary lab milk quality analyser — diagnostic testing"},
        {"id": s_ma_vet2, "name": "Lab Analyser 2", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_vet,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_vet2}", "scc_alert_threshold": 400000, "fat_min": 2.0, "fat_max": 6.0},
         "desc": "Secondary lab analyser — confirmatory testing"},

        # ip_camera_rtsp × 2
        {"id": s_cam_vet_reception, "name": "Vet Reception Cam",   "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_vet,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.80:554/stream1",
                    "hls_host": "192.168.1.14", "hls_port": 8090,
                    "mqtt_topic_prefix": f"gdf/{s_cam_vet_reception}", "record_motion_events": True},
         "desc": "Veterinary bay reception and waiting area camera"},
        {"id": s_cam_vet_iso,       "name": "Vet Isolation Pen Cam","sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_vet,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.81:554/stream1",
                    "hls_host": "192.168.1.14", "hls_port": 8091,
                    "mqtt_topic_prefix": f"gdf/{s_cam_vet_iso}", "record_motion_events": True},
         "desc": "Isolation pen combined overview camera"},

        # ─────────────── PROCESSING & PACKAGING PLANT (12) ───────────────────

        # temperature_humidity × 3
        {"id": s_temp_proc_hall, "name": "Packaging Hall Temp",    "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_proc_hall}", "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Packaging hall ambient temperature & humidity"},
        {"id": s_temp_proc_cold, "name": "Cold Store Exit Temp",   "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_proc_cold}", "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Cold-store exit corridor — temperature compliance (target 4°C)"},
        {"id": s_temp_proc_fill, "name": "Filling Room Temp",      "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_proc_fill}", "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Bottling and filling room temperature control"},

        # weight_hx711 × 2
        {"id": s_wt_bottle_scale, "name": "Bottle Line Scale",     "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_bottle_scale}", "capacity_kg": 50, "unit": "kg"},
         "desc": "Filled bottle checkweigher on production line 1"},
        {"id": s_wt_carton_scale, "name": "Carton Packing Scale",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_carton_scale}", "capacity_kg": 100, "unit": "kg"},
         "desc": "Finished carton packing station scale"},

        # milk_analyzer_lactoscan × 4
        {"id": s_ma_proc_qa1, "name": "Post-Pasteurisation QC 1", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_proc_qa1}", "scc_alert_threshold": 100000, "fat_min": 3.0, "fat_max": 5.0},
         "desc": "Post-pasteurisation quality control analyser — line 1"},
        {"id": s_ma_proc_qa2, "name": "Post-Pasteurisation QC 2", "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_proc_qa2}", "scc_alert_threshold": 100000, "fat_min": 3.0, "fat_max": 5.0},
         "desc": "Post-pasteurisation quality control analyser — line 2"},
        {"id": s_ma_proc_qa3, "name": "Bottled Milk Spot Check",  "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_proc_qa3}", "scc_alert_threshold": 100000, "fat_min": 3.0, "fat_max": 5.0},
         "desc": "Random bottled-milk quality spot-check analyser"},
        {"id": s_ma_proc_qa4, "name": "End-of-Line Validation",   "sensor_type": "milk_analyzer_lactoscan",
         "protocol": "mqtt", "loc": loc_processing,
         "config": {"mqtt_topic_prefix": f"gdf/{s_ma_proc_qa4}", "scc_alert_threshold": 100000, "fat_min": 3.0, "fat_max": 5.0},
         "desc": "End-of-line final validation analyser before dispatch"},

        # ip_camera_rtsp × 3
        {"id": s_cam_proc_line, "name": "Production Line Cam",    "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_processing,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.90:554/stream1",
                    "hls_host": "192.168.1.15", "hls_port": 8090,
                    "mqtt_topic_prefix": f"gdf/{s_cam_proc_line}", "record_motion_events": True},
         "desc": "Production line overview — bottling and filling"},
        {"id": s_cam_proc_cold, "name": "Cold Storage Cam",       "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_processing,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.91:554/stream1",
                    "hls_host": "192.168.1.15", "hls_port": 8091,
                    "mqtt_topic_prefix": f"gdf/{s_cam_proc_cold}", "record_motion_events": False},
         "desc": "Cold storage and dispatch staging area camera"},
        {"id": s_cam_proc_exit, "name": "Loading Dock Exit Cam",  "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_processing,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.92:554/stream1",
                    "hls_host": "192.168.1.15", "hls_port": 8092,
                    "mqtt_topic_prefix": f"gdf/{s_cam_proc_exit}", "record_motion_events": True},
         "desc": "Loading dock exit and vehicle tracking camera"},

        # ──────────────────── WATER & UTILITIES STATION (8) ──────────────────

        # temperature_humidity × 3
        {"id": s_temp_pump_room,   "name": "Pump Room Temp",       "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_utilities,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_pump_room}",   "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Pump room ambient temperature & humidity"},
        {"id": s_temp_boiler_room, "name": "Boiler Room Temp",     "sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_utilities,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_boiler_room}", "temperature_unit": "°C", "poll_interval_seconds": 30},
         "desc": "Boiler room temperature — safety critical (max 60°C)"},
        {"id": s_temp_cool_tower,  "name": "Cooling Tower Ambient","sensor_type": "temperature_humidity",
         "protocol": "mqtt", "loc": loc_utilities,
         "config": {"mqtt_topic_prefix": f"gdf/{s_temp_cool_tower}",  "temperature_unit": "°C", "poll_interval_seconds": 60},
         "desc": "Cooling tower ambient air temperature & humidity"},

        # weight_hx711 × 3
        {"id": s_wt_water_main,  "name": "Main Water Tank Scale", "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_utilities,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_water_main}",  "capacity_kg": 10000, "unit": "kg"},
         "desc": "Main water storage tank (10 000 L capacity) level sensor"},
        {"id": s_wt_water_sec,   "name": "Secondary Water Tank",  "sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_utilities,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_water_sec}",   "capacity_kg": 5000,  "unit": "kg"},
         "desc": "Secondary water storage tank (5 000 L capacity) level sensor"},
        {"id": s_wt_diesel_tank, "name": "Diesel Fuel Tank Scale","sensor_type": "weight_hx711",
         "protocol": "mqtt", "loc": loc_utilities,
         "config": {"mqtt_topic_prefix": f"gdf/{s_wt_diesel_tank}", "capacity_kg": 2000,  "unit": "kg"},
         "desc": "Diesel fuel storage tank weight sensor"},

        # ip_camera_rtsp × 2
        {"id": s_cam_pump_room,   "name": "Pump Room Cam",        "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_utilities,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.100:554/stream1",
                    "hls_host": "192.168.1.16", "hls_port": 8090,
                    "mqtt_topic_prefix": f"gdf/{s_cam_pump_room}", "record_motion_events": True},
         "desc": "Pump room security and operations camera"},
        {"id": s_cam_water_tower, "name": "Water Tower Cam",      "sensor_type": "ip_camera_rtsp",
         "protocol": "rtsp", "loc": loc_utilities,
         "config": {"rtsp_url": "rtsp://admin:gdf2024@192.168.1.101:554/stream1",
                    "hls_host": "192.168.1.16", "hls_port": 8091,
                    "mqtt_topic_prefix": f"gdf/{s_cam_water_tower}", "record_motion_events": False},
         "desc": "Water tower and tank yard overview camera"},
    ]

    for s in sensors:
        await db.execute(text("""
            INSERT INTO sensors (id, name, sensor_type, protocol, config,
                                 location_id, description, status)
            VALUES (:id, :name, :sensor_type, :protocol,
                    CAST(:config AS jsonb), :loc, :desc, 'active')
        """), {**s, "config": _json.dumps(s["config"])})

    print(f"  Sensors inserted: {len(sensors)}")

    # ══════════════════════════════════════════════════════════════════════════
    # User sensor permissions (granular cross-location grants)
    # ══════════════════════════════════════════════════════════════════════════
    sensor_grants = [
        # Alice (barn+parlor) → pasture fence cameras + feed store ambient
        (u_op1, s_cam_pas_north), (u_op1, s_cam_pas_east),
        (u_op1, s_cam_pas_south), (u_op1, s_cam_gate),
        (u_op1, s_temp_feed_ambient), (u_op1, s_cam_feed_entry),
        (u_op1, s_cam_proc_line),   # processing line overview
        # Bob (parlor+pasture+feed) → barn overview + vet isolation temps
        (u_op2, s_temp_barn_center), (u_op2, s_temp_barn_ne),
        (u_op2, s_wt_feed_main),
        (u_op2, s_temp_vet_iso_a), (u_op2, s_temp_vet_iso_b),
        (u_op2, s_wt_water_main),   # water level awareness
        # Carol (processing+utilities) → chiller temp + parlour milk analyser 1&2
        (u_op3, s_temp_milk_chiller),
        (u_op3, s_ma_line1), (u_op3, s_ma_line2),
        (u_op3, s_wt_tank_1), (u_op3, s_wt_tank_2),  # raw milk tank levels
    ]
    for user_id, sensor_id in sensor_grants:
        await db.execute(text(
            "INSERT INTO user_sensor_permissions (id, user_id, sensor_id) "
            "VALUES (:id, :uid, :sid)"
        ), {"id": uid(), "uid": user_id, "sid": sensor_id})

    # ══════════════════════════════════════════════════════════════════════════
    # Alert rules (45 rules across sensors + severities)
    # Channel names match plugin data_channels exactly:
    #   temperature_humidity → temperature, humidity
    #   weight_hx711         → weight
    #   milk_analyzer_lactoscan → fat, protein, lactose, somatic_cells, milk_temp
    # ══════════════════════════════════════════════════════════════════════════
    alert_rule_defs = [
        # ── Barn temperature ──────────────────────────────────────────────────
        {"sid": s_temp_barn_ne,     "ch": "temperature", "cond": "gt",           "thr": 35.0, "tmax": None, "sev": "warning"},
        {"sid": s_temp_barn_ne,     "ch": "temperature", "cond": "gt",           "thr": 40.0, "tmax": None, "sev": "critical"},
        {"sid": s_temp_barn_ne,     "ch": "temperature", "cond": "lt",           "thr":  4.0, "tmax": None, "sev": "warning"},
        {"sid": s_temp_barn_center, "ch": "temperature", "cond": "gt",           "thr": 35.0, "tmax": None, "sev": "warning"},
        {"sid": s_temp_barn_loft,   "ch": "temperature", "cond": "gt",           "thr": 45.0, "tmax": None, "sev": "critical"},
        {"sid": s_temp_barn_kid,    "ch": "temperature", "cond": "outside_range","thr": 18.0, "tmax": 30.0, "sev": "warning"},
        # ── Milking parlor temperature ────────────────────────────────────────
        {"sid": s_temp_milk_center, "ch": "temperature", "cond": "outside_range","thr": 15.0, "tmax": 25.0, "sev": "warning"},
        {"sid": s_temp_milk_chiller,"ch": "temperature", "cond": "gt",           "thr":  6.0, "tmax": None, "sev": "critical"},
        {"sid": s_temp_milk_chiller,"ch": "temperature", "cond": "lt",           "thr":  2.0, "tmax": None, "sev": "warning"},
        {"sid": s_temp_milk_freezer,"ch": "temperature", "cond": "gt",           "thr":-15.0, "tmax": None, "sev": "warning"},
        # ── Pasture temperature ───────────────────────────────────────────────
        {"sid": s_temp_pas_north,   "ch": "temperature", "cond": "gt",           "thr": 38.0, "tmax": None, "sev": "info"},
        {"sid": s_temp_pas_center,  "ch": "temperature", "cond": "gt",           "thr": 38.0, "tmax": None, "sev": "info"},
        # ── Feed store temperature ────────────────────────────────────────────
        {"sid": s_temp_feed_silo1,  "ch": "temperature", "cond": "gt",           "thr": 28.0, "tmax": None, "sev": "warning"},
        {"sid": s_temp_hay_loft,    "ch": "temperature", "cond": "gt",           "thr": 40.0, "tmax": None, "sev": "critical"},
        {"sid": s_temp_hay_loft,    "ch": "humidity",    "cond": "gt",           "thr": 80.0, "tmax": None, "sev": "warning"},
        # ── Vet bay temperature ───────────────────────────────────────────────
        {"sid": s_temp_vet_iso_a,   "ch": "temperature", "cond": "outside_range","thr": 15.0, "tmax": 28.0, "sev": "warning"},
        {"sid": s_temp_vet_iso_b,   "ch": "temperature", "cond": "outside_range","thr": 15.0, "tmax": 28.0, "sev": "warning"},
        {"sid": s_temp_vet_lab,     "ch": "temperature", "cond": "outside_range","thr": 18.0, "tmax": 25.0, "sev": "warning"},
        # ── Processing plant temperature ──────────────────────────────────────
        {"sid": s_temp_proc_cold,   "ch": "temperature", "cond": "gt",           "thr":  6.0, "tmax": None, "sev": "critical"},
        {"sid": s_temp_proc_cold,   "ch": "temperature", "cond": "outside_range","thr":  2.0, "tmax":  6.0, "sev": "warning"},
        {"sid": s_temp_proc_hall,   "ch": "temperature", "cond": "outside_range","thr": 15.0, "tmax": 25.0, "sev": "warning"},
        # ── Utilities temperature ─────────────────────────────────────────────
        {"sid": s_temp_boiler_room, "ch": "temperature", "cond": "gt",           "thr": 60.0, "tmax": None, "sev": "critical"},
        {"sid": s_temp_boiler_room, "ch": "temperature", "cond": "outside_range","thr": 20.0, "tmax": 55.0, "sev": "warning"},
        # ── Barn weight scales ────────────────────────────────────────────────
        {"sid": s_wt_goat_a,        "ch": "weight",      "cond": "lt",           "thr": 18.0, "tmax": None, "sev": "warning"},
        {"sid": s_wt_feed_main,     "ch": "weight",      "cond": "lt",           "thr": 80.0, "tmax": None, "sev": "warning"},
        {"sid": s_wt_feed_main,     "ch": "weight",      "cond": "lt",           "thr": 30.0, "tmax": None, "sev": "critical"},
        # ── Milk tanks ────────────────────────────────────────────────────────
        {"sid": s_wt_tank_1,        "ch": "weight",      "cond": "gt",           "thr":1050.0,"tmax": None, "sev": "warning"},
        {"sid": s_wt_tank_2,        "ch": "weight",      "cond": "gt",           "thr":1050.0,"tmax": None, "sev": "warning"},
        {"sid": s_wt_trough_1,      "ch": "weight",      "cond": "lt",           "thr": 20.0, "tmax": None, "sev": "info"},
        # ── Feed store weight ─────────────────────────────────────────────────
        {"sid": s_wt_silo_1,        "ch": "weight",      "cond": "lt",           "thr":1000.0,"tmax": None, "sev": "warning"},
        {"sid": s_wt_silo_1,        "ch": "weight",      "cond": "lt",           "thr": 500.0,"tmax": None, "sev": "critical"},
        {"sid": s_wt_silo_2,        "ch": "weight",      "cond": "lt",           "thr":1000.0,"tmax": None, "sev": "warning"},
        {"sid": s_wt_pellet,        "ch": "weight",      "cond": "lt",           "thr": 150.0,"tmax": None, "sev": "warning"},
        # ── Utilities weight ──────────────────────────────────────────────────
        {"sid": s_wt_water_main,    "ch": "weight",      "cond": "lt",           "thr":2000.0,"tmax": None, "sev": "warning"},
        {"sid": s_wt_water_main,    "ch": "weight",      "cond": "lt",           "thr": 500.0,"tmax": None, "sev": "critical"},
        {"sid": s_wt_diesel_tank,   "ch": "weight",      "cond": "lt",           "thr": 400.0,"tmax": None, "sev": "warning"},
        {"sid": s_wt_diesel_tank,   "ch": "weight",      "cond": "lt",           "thr": 150.0,"tmax": None, "sev": "critical"},
        # ── Milk analyzers (parlour) — channels: fat, protein, somatic_cells ──
        {"sid": s_ma_line1,         "ch": "fat",          "cond": "lt",  "thr": 3.0,    "tmax": None, "sev": "warning"},
        {"sid": s_ma_line1,         "ch": "protein",      "cond": "lt",  "thr": 2.8,    "tmax": None, "sev": "warning"},
        {"sid": s_ma_line1,         "ch": "somatic_cells","cond": "gt",  "thr": 400000, "tmax": None, "sev": "critical"},
        {"sid": s_ma_line2,         "ch": "fat",          "cond": "lt",  "thr": 3.0,    "tmax": None, "sev": "warning"},
        {"sid": s_ma_line2,         "ch": "somatic_cells","cond": "gt",  "thr": 400000, "tmax": None, "sev": "critical"},
        {"sid": s_ma_vet1,          "ch": "somatic_cells","cond": "gt",  "thr": 600000, "tmax": None, "sev": "critical"},
        # ── Milk analyzers (processing QC) — stricter thresholds ─────────────
        {"sid": s_ma_proc_qa1,      "ch": "somatic_cells","cond": "gt",  "thr": 100000, "tmax": None, "sev": "critical"},
        {"sid": s_ma_proc_qa1,      "ch": "fat",          "cond": "lt",  "thr": 3.2,    "tmax": None, "sev": "warning"},
    ]

    all_rule_ids: list[str] = []
    for r in alert_rule_defs:
        rid = uid()
        all_rule_ids.append(rid)
        await db.execute(text("""
            INSERT INTO alert_rules
                (id, sensor_id, channel, condition, threshold, threshold_max, severity, enabled)
            VALUES (:id, :sid, :ch, :cond, :thr, :tmax, :sev, true)
        """), {"id": rid, "sid": r["sid"], "ch": r["ch"], "cond": r["cond"],
               "thr": r["thr"], "tmax": r["tmax"], "sev": r["sev"]})

    # Rule index map (by position in alert_rule_defs):
    # 0=barn_ne_gt35_warn, 1=barn_ne_gt40_crit, 2=barn_ne_lt4_warn,
    # 3=barn_center_gt35_warn, 4=loft_gt45_crit, 5=kidding_outside_warn,
    # 6=milk_center_outside_warn, 7=chiller_gt6_crit, 8=chiller_lt2_warn,
    # 9=freezer_gt-15_warn, 10=pas_north_gt38_info, 11=pas_center_gt38_info,
    # 12=silo1_gt28_warn, 13=hay_gt40_crit, 14=hay_hum_gt80_warn,
    # 15=vet_iso_a_outside_warn, 16=vet_iso_b_outside_warn, 17=vet_lab_outside_warn,
    # 18=proc_cold_gt6_crit, 19=proc_cold_outside_warn, 20=proc_hall_outside_warn,
    # 21=boiler_gt60_crit, 22=boiler_outside_warn,
    # 23=goat_a_lt18_warn, 24=feed_main_lt80_warn, 25=feed_main_lt30_crit,
    # 26=tank1_gt1050_warn, 27=tank2_gt1050_warn, 28=trough1_lt20_info,
    # 29=silo1_lt1000_warn, 30=silo1_lt500_crit, 31=silo2_lt1000_warn, 32=pellet_lt150_warn,
    # 33=water_main_lt2000_warn, 34=water_main_lt500_crit,
    # 35=diesel_lt400_warn, 36=diesel_lt150_crit,
    # 37=ma1_fat_warn, 38=ma1_protein_warn, 39=ma1_scc_crit,
    # 40=ma2_fat_warn, 41=ma2_scc_crit,
    # 42=vet1_scc_crit,
    # 43=proc_qa1_scc_crit, 44=proc_qa1_fat_warn

    # ══════════════════════════════════════════════════════════════════════════
    # Alert rule actions (demonstrate all action types on critical rules)
    # ══════════════════════════════════════════════════════════════════════════
    rule_actions = [
        # Barn NE temp critical (rule 1) → push notification + SMS
        {"rid": all_rule_ids[1],  "type": "notification",
         "cfg": {"message": "CRITICAL: Barn NE temperature exceeded 40°C. Check ventilation immediately."}},
        {"rid": all_rule_ids[1],  "type": "sms",
         "cfg": {"to": "+92-300-0000002", "body": "GDF ALERT: Barn temp CRITICAL (>40°C). Action required now."}},

        # Hay loft fire risk (rule 4) → notification + SMS + call
        {"rid": all_rule_ids[4],  "type": "notification",
         "cfg": {"message": "FIRE RISK: Hay loft temperature exceeded 45°C. Evacuate and call fire services."}},
        {"rid": all_rule_ids[4],  "type": "sms",
         "cfg": {"to": "+92-300-0000002", "body": "FIRE RISK: Hay loft >45°C. Check for spontaneous combustion."}},
        {"rid": all_rule_ids[4],  "type": "call",
         "cfg": {"to": "+92-300-0000002", "message": "Critical fire risk alert in hay loft."}},

        # Chiller room too warm (rule 7) → notification + email + SMS
        {"rid": all_rule_ids[7],  "type": "notification",
         "cfg": {"message": "CRITICAL: Milk chiller above 6°C — milk spoilage risk. Inspect immediately."}},
        {"rid": all_rule_ids[7],  "type": "email",
         "cfg": {"to": "admin@gdf.farm", "subject": "Chiller Alarm", "body": "Chiller room temp above 6°C. Immediate inspection required."}},
        {"rid": all_rule_ids[7],  "type": "sms",
         "cfg": {"to": "+92-300-0000003", "body": "GDF: Parlour chiller CRITICAL. Temp above 6°C — milk at risk."}},

        # Silo 1 warning (rule 29) → notification + reminder
        {"rid": all_rule_ids[29], "type": "notification",
         "cfg": {"message": "Grain Silo 1 below 1000 kg. Schedule restocking soon."}},
        {"rid": all_rule_ids[29], "type": "reminder",
         "cfg": {"message": "Reminder: Order grain for Silo 1 before stock falls critical."}},

        # Silo 1 critical (rule 30) → notification + SMS + email
        {"rid": all_rule_ids[30], "type": "notification",
         "cfg": {"message": "CRITICAL: Grain Silo 1 below 500 kg. Emergency restock required!"}},
        {"rid": all_rule_ids[30], "type": "sms",
         "cfg": {"to": "+92-300-0000002", "body": "CRITICAL: Grain Silo 1 < 500 kg. Contact Agri-Feed Ltd immediately."}},
        {"rid": all_rule_ids[30], "type": "email",
         "cfg": {"to": "admin@gdf.farm", "subject": "Emergency: Grain Critically Low", "body": "Silo 1 is critically low. Arrange same-day delivery."}},

        # Boiler room critical (rule 21) → notification + call
        {"rid": all_rule_ids[21], "type": "notification",
         "cfg": {"message": "CRITICAL: Boiler room temperature exceeded 60°C — safety hazard!"}},
        {"rid": all_rule_ids[21], "type": "call",
         "cfg": {"to": "+92-300-0000002", "message": "Emergency: Boiler room temperature exceeds safe limit. Inspect now."}},

        # Water main critically low (rule 34) → notification + SMS
        {"rid": all_rule_ids[34], "type": "notification",
         "cfg": {"message": "CRITICAL: Main water tank below 500 kg. Farm water supply at risk!"}},
        {"rid": all_rule_ids[34], "type": "sms",
         "cfg": {"to": "+92-300-0000005", "body": "GDF: Water main tank critically low (<500 kg). Schedule refill urgently."}},

        # Diesel critically low (rule 36) → notification + email
        {"rid": all_rule_ids[36], "type": "notification",
         "cfg": {"message": "CRITICAL: Diesel tank below 150 kg. Generator at risk of shutdown."}},
        {"rid": all_rule_ids[36], "type": "email",
         "cfg": {"to": "admin@gdf.farm", "subject": "Diesel Critical", "body": "Diesel tank critically low. Order fuel to prevent generator failure."}},

        # Processing QC SCC critical (rule 43) → notification + email + whatsapp
        {"rid": all_rule_ids[43], "type": "notification",
         "cfg": {"message": "CRITICAL: Post-pasteurisation SCC above 100,000 cells/mL. Batch hold required!"}},
        {"rid": all_rule_ids[43], "type": "email",
         "cfg": {"to": "admin@gdf.farm", "subject": "QC Failure: SCC Alert", "body": "Processing QC Line 1 detected SCC >100,000. Quarantine batch immediately."}},
        {"rid": all_rule_ids[43], "type": "whatsapp",
         "cfg": {"to": "+92-300-0000005", "message": "QC ALERT: SCC exceeded threshold in processing. Hold all batches pending review."}},

        # Milk analyser line 1 SCC critical (rule 39) → notification + email
        {"rid": all_rule_ids[39], "type": "notification",
         "cfg": {"message": "CRITICAL: Milk Line 1 SCC above 400,000 cells/mL. Mastitis risk — isolate affected animals."}},
        {"rid": all_rule_ids[39], "type": "email",
         "cfg": {"to": "admin@gdf.farm", "subject": "Mastitis Alert: High SCC", "body": "Line 1 SCC reading exceeds 400,000. Schedule veterinary examination."}},
    ]

    for ra in rule_actions:
        await db.execute(text("""
            INSERT INTO alert_rule_actions (id, rule_id, action_type, config, enabled)
            VALUES (:id, :rid, :atype, CAST(:cfg AS jsonb), true)
        """), {"id": uid(), "rid": ra["rid"], "atype": ra["type"], "cfg": _json.dumps(ra["cfg"])})

    print(f"  Alert rules: {len(alert_rule_defs)}  |  Rule actions: {len(rule_actions)}")

    # ══════════════════════════════════════════════════════════════════════════
    # Active alerts (10 — diverse severities across locations)
    # ══════════════════════════════════════════════════════════════════════════
    active_alerts = [
        # CRITICAL — barn NE temp at 41.2°C
        {"rid": all_rule_ids[1],  "sid": s_temp_barn_ne,     "ch": "temperature",
         "val": 41.2,    "sev": "critical",
         "msg": "CRITICAL: Barn Temp NE at 41.2°C — exceeds 40°C threshold. Ventilation failure suspected.",
         "ago": "22 minutes"},
        # CRITICAL — milk chiller too warm
        {"rid": all_rule_ids[7],  "sid": s_temp_milk_chiller, "ch": "temperature",
         "val": 6.8,     "sev": "critical",
         "msg": "CRITICAL: Chiller Room at 6.8°C — above safe limit of 6°C. Milk spoilage risk.",
         "ago": "1 hour 5 minutes"},
        # CRITICAL — Grain Silo 1 critically low
        {"rid": all_rule_ids[30], "sid": s_wt_silo_1,         "ch": "weight",
         "val": 420.0,   "sev": "critical",
         "msg": "CRITICAL: Grain Silo 1 at 420 kg — below critical threshold of 500 kg. Order feed immediately.",
         "ago": "3 hours 30 minutes"},
        # CRITICAL — Boiler room temperature spike
        {"rid": all_rule_ids[21], "sid": s_temp_boiler_room,  "ch": "temperature",
         "val": 63.5,    "sev": "critical",
         "msg": "CRITICAL: Boiler Room at 63.5°C — exceeds 60°C safety limit. Shutdown and inspect.",
         "ago": "15 minutes"},
        # WARNING — barn center temp rising
        {"rid": all_rule_ids[3],  "sid": s_temp_barn_center,  "ch": "temperature",
         "val": 36.1,    "sev": "warning",
         "msg": "Barn Centre Temp: 36.1°C exceeds 35°C warning threshold. Check ventilation.",
         "ago": "45 minutes"},
        # WARNING — milk centre outside safe range
        {"rid": all_rule_ids[6],  "sid": s_temp_milk_center,  "ch": "temperature",
         "val": 26.3,    "sev": "warning",
         "msg": "Parlour Centre Temp: 26.3°C is outside safe range (15–25°C). Cooling needed.",
         "ago": "2 hours"},
        # WARNING — Feed main hopper low
        {"rid": all_rule_ids[24], "sid": s_wt_feed_main,      "ch": "weight",
         "val": 72.5,    "sev": "warning",
         "msg": "Feed Hopper Main: 72.5 kg — below 80 kg warning threshold. Refill soon.",
         "ago": "4 hours 15 minutes"},
        # WARNING — Milk Tank 1 nearly full
        {"rid": all_rule_ids[26], "sid": s_wt_tank_1,         "ch": "weight",
         "val": 1082.0,  "sev": "warning",
         "msg": "Milk Tank 1 Scale: 1,082 kg — approaching capacity of 1,200 kg. Schedule collection.",
         "ago": "6 hours"},
        # WARNING — Diesel fuel low
        {"rid": all_rule_ids[35], "sid": s_wt_diesel_tank,    "ch": "weight",
         "val": 380.0,   "sev": "warning",
         "msg": "Diesel Tank: 380 kg — below 400 kg warning threshold. Order fuel delivery.",
         "ago": "5 hours"},
        # INFO — Pasture north temp high
        {"rid": all_rule_ids[10], "sid": s_temp_pas_north,    "ch": "temperature",
         "val": 39.4,    "sev": "info",
         "msg": "Pasture North Temp: 39.4°C above 38°C threshold. Consider moving herd to shade.",
         "ago": "30 minutes"},
    ]

    for a in active_alerts:
        await db.execute(text(f"""
            INSERT INTO active_alerts
                (id, rule_id, sensor_id, channel, triggered_value, severity, message, triggered_at)
            VALUES (:id, :rid, :sid, :ch, :val, :sev, :msg,
                    NOW() - INTERVAL '{a["ago"]}')
        """), {"id": uid(), "rid": a["rid"], "sid": a["sid"], "ch": a["ch"],
               "val": a["val"], "sev": a["sev"], "msg": a["msg"]})

    # ══════════════════════════════════════════════════════════════════════════
    # Plans (3)
    # ══════════════════════════════════════════════════════════════════════════
    await db.execute(text("""
        INSERT INTO plans (id, name, description, sensor_id, channel,
                           target_value, target_unit, lower_limit, upper_limit,
                           enabled, created_by_id)
        VALUES
        (:p1, 'Barn Temperature Control',
         'Keep barn ambient temperature within safe range for Boer goats',
         :s1, 'temperature', 22.0, '°C', 10.0, 32.0, true, :admin),
        (:p2, 'Milk Quality — Fat Content',
         'Maintain milk fat percentage above industry minimum',
         :s2, 'fat', 3.5, '%', 3.0, 6.0, true, :admin),
        (:p3, 'Grain Silo 1 Inventory',
         'Maintain grain silo 1 above safe operating level — restock triggers',
         :s3, 'weight', 2500.0, 'kg', 1000.0, NULL, true, :admin)
    """), {"p1": p1, "p2": p2, "p3": p3,
           "s1": s_temp_barn_ne, "s2": s_ma_line1, "s3": s_wt_silo_1,
           "admin": u_admin})

    await db.execute(text("""
        INSERT INTO plan_actions
            (id, plan_id, action_type, trigger_on, message_template, config, enabled)
        VALUES
        (:a1, :p1, 'notification', 'outside_range',
         'ALERT: Barn temperature {value}°C is outside the safe range [{lower}–{upper}°C]',
         '{}', true),
        (:a2, :p1, 'reminder', 'above_upper',
         'High barn temperature reminder: {value}°C. Check ventilation and fans.',
         '{}', true),
        (:a3, :p2, 'notification', 'below_lower',
         'Milk fat {value}% is below minimum {lower}%. Review herd nutrition plan.',
         '{}', true),
        (:a4, :p3, 'notification', 'below_lower',
         'URGENT: Grain Silo 1 at {value} kg — restock required (min {lower} kg).',
         '{}', true),
        (:a5, :p3, 'reminder', 'below_lower',
         'Grain Silo 1 running low ({value} kg). Schedule delivery.',
         '{}', true)
    """), {"a1": uid(), "a2": uid(), "a3": uid(), "a4": uid(), "a5": uid(),
           "p1": p1, "p2": p2, "p3": p3})

    # ══════════════════════════════════════════════════════════════════════════
    # Tasks (6 — various states)
    # ══════════════════════════════════════════════════════════════════════════
    await db.execute(text("""
        INSERT INTO tasks (id, title, description, deadline, status, created_by_id) VALUES
        (:t1, 'Calibrate Milk Analyser Lines 1–3',
         'Perform weekly calibration on all active analyser lines using reference samples. '
         'Document fat%, protein%, and SCC readings in calibration log.',
         NOW() + INTERVAL '2 days', 'open', :admin),

        (:t2, 'Replace Barn NE Ventilation Fan',
         'Fan motor showing intermittent fault (sensor exceeding 40°C). Order part #VN-240A, '
         'install, and verify barn temp drops below 35°C within 2 hours.',
         NOW() + INTERVAL '1 day', 'open', :admin),

        (:t3, 'Monthly Herd Health Inspection',
         'Full herd inspection: body condition scoring, hoof trimming check, tag verification. '
         'Record weights using Scales Alpha–Delta.',
         NOW() + INTERVAL '3 days', 'open', :admin),

        (:t4, 'Grain Silo 1 — Emergency Restock',
         'Silo 1 critically low at 420 kg. Contact supplier Agri-Feed Ltd, arrange same-day '
         'delivery, and update inventory system.',
         NOW() + INTERVAL '8 hours', 'submitted', :admin),

        (:t5, 'Chiller Room Maintenance',
         'Chiller temp rising above threshold. Inspect refrigerant lines, clean condenser coils, '
         'test thermostat, and log chiller service record.',
         NOW() - INTERVAL '1 day', 'submitted', :admin),

        (:t6, 'Deep Clean Milking Parlour',
         'End-of-month deep sanitation. Dismantle milk lines, acid wash, re-grease bearings. '
         'Log CIP cycle completion time and chemical batch numbers.',
         NOW() - INTERVAL '5 days', 'done', :admin)
    """), {"t1": t1, "t2": t2, "t3": t3, "t4": t4, "t5": t5, "t6": t6,
           "admin": u_admin})

    task_assignments = [
        (t1, u_op1),
        (t2, u_op1), (t2, u_op2),
        (t3, u_op1), (t3, u_op2),
        (t4, u_op2),
        (t5, u_op1),
        (t6, u_op2),
    ]
    for task_id, user_id in task_assignments:
        await db.execute(text(
            "INSERT INTO task_assignments (id, task_id, user_id) VALUES (:id, :tid, :uid)"
        ), {"id": uid(), "tid": task_id, "uid": user_id})

    await db.execute(text("""
        UPDATE tasks SET
            submitted_by_id = :op2, submitted_at = NOW() - INTERVAL '3 hours',
            completion_note = 'Contacted Agri-Feed Ltd. Delivery confirmed for 14:00 today.'
        WHERE id = :t4
    """), {"op2": u_op2, "t4": t4})

    await db.execute(text("""
        UPDATE tasks SET
            submitted_by_id = :op1, submitted_at = NOW() - INTERVAL '6 hours',
            completion_note = 'Condenser coils cleaned, thermostat replaced. Temp now at 4.2°C.'
        WHERE id = :t5
    """), {"op1": u_op1, "t5": t5})

    await db.execute(text("""
        UPDATE tasks SET
            submitted_by_id = :op2, submitted_at = NOW() - INTERVAL '4 days',
            completion_note = 'CIP cycle completed. All 6 lines clear. Time: 5h 10m.',
            reviewed_by_id  = :admin, reviewed_at = NOW() - INTERVAL '3 days',
            review_note = 'Approved. CIP log filed in maintenance folder.', status = 'done'
        WHERE id = :t6
    """), {"op2": u_op2, "admin": u_admin, "t6": t6})

    # ══════════════════════════════════════════════════════════════════════════
    # Chat
    # ══════════════════════════════════════════════════════════════════════════
    await db.execute(text("""
        INSERT INTO chat_rooms (id, name, room_type, task_id, created_by_id) VALUES
        (:r1, 'General',           'general', NULL, :admin),
        (:r2, 'Barn Maintenance',  'task',    :t2,  :admin)
    """), {"r1": r_general, "r2": r_task1, "t2": t2, "admin": u_admin})

    for uid_ in [u_super, u_admin, u_op1, u_op2, u_op3]:
        await db.execute(text(
            "INSERT INTO chat_room_members (id, room_id, user_id) VALUES (:id, :room, :uid)"
        ), {"id": uid(), "room": r_general, "uid": uid_})

    for uid_ in [u_admin, u_op1, u_op2]:
        await db.execute(text(
            "INSERT INTO chat_room_members (id, room_id, user_id) VALUES (:id, :room, :uid)"
        ), {"id": uid(), "room": r_task1, "uid": uid_})

    await db.execute(text("""
        INSERT INTO chat_messages (id, room_id, user_id, content, created_at) VALUES
        (:m1, :gen, :super, 'Welcome to GDF-AutoMon! 91 sensors across 7 locations are now online.', NOW() - INTERVAL '3 days'),
        (:m2, :gen, :admin, 'Chiller alarm triggered — Alice please check Parlour temps.', NOW() - INTERVAL '7 hours'),
        (:m3, :gen, :op1,   'On it. Condenser coils were clogged, cleaned and thermostat replaced.', NOW() - INTERVAL '6 hours'),
        (:m4, :gen, :op2,   'Grain Silo 1 critically low — I have contacted the supplier.', NOW() - INTERVAL '3 hours'),
        (:m5, :gen, :op3,   'Processing QC line 1 running nominal. SCC readings in range.', NOW() - INTERVAL '2 hours'),
        (:m6, :gen, :admin, 'Good work all. Keep an eye on barn NE temp — fan replacement due.', NOW() - INTERVAL '1 hour'),
        (:m7, :r_t, :admin, 'Alice and Bob — fan part #VN-240A is in the storeroom. Safety off first.', NOW() - INTERVAL '2 hours'),
        (:m8, :r_t, :op1,   'Understood. We will tackle it first thing tomorrow morning.', NOW() - INTERVAL '1 hour 30 minutes')
    """), {
        "m1": uid(), "m2": uid(), "m3": uid(), "m4": uid(),
        "m5": uid(), "m6": uid(), "m7": uid(), "m8": uid(),
        "gen": r_general, "r_t": r_task1,
        "super": u_super, "admin": u_admin,
        "op1": u_op1, "op2": u_op2, "op3": u_op3,
    })

    # ══════════════════════════════════════════════════════════════════════════
    # Telemetry — 24 h at 15-min intervals
    # Both temperature AND humidity channels for temperature_humidity sensors
    # Correct milk analyzer channels: fat, protein, lactose, somatic_cells, milk_temp
    # ══════════════════════════════════════════════════════════════════════════
    random.seed(42)
    base = now() - timedelta(hours=24)
    readings: list[tuple] = []

    # (sensor_id, mean_temp_C, diurnal_amp, mean_humidity_pct, humidity_amp)
    temp_humidity_profiles = [
        # ── Main Barn
        (s_temp_barn_ne,      20, 10, 65, 8),
        (s_temp_barn_nw,      19,  9, 67, 7),
        (s_temp_barn_se,      21, 10, 63, 8),
        (s_temp_barn_sw,      20,  9, 64, 7),
        (s_temp_barn_center,  20, 10, 66, 8),
        (s_temp_barn_loft,    25, 12, 55, 5),
        (s_temp_barn_kid,     22,  6, 70, 5),
        (s_temp_barn_medprep, 21,  4, 60, 4),
        # ── Milking Parlour
        (s_temp_milk_entry,   20,  4, 62, 5),
        (s_temp_milk_center,  21,  3, 60, 4),
        (s_temp_milk_wash,    23,  5, 75, 6),
        (s_temp_milk_chiller,  4,  1, 90, 3),
        (s_temp_milk_freezer, -18, 1, 85, 2),
        # ── Outdoor Pasture
        (s_temp_pas_north,    22, 14, 55, 10),
        (s_temp_pas_center,   23, 15, 52, 10),
        (s_temp_pas_south,    22, 14, 54,  9),
        (s_temp_pas_shelter,  20, 10, 60,  8),
        # ── Feed Store
        (s_temp_feed_silo1,   18,  6, 58, 5),
        (s_temp_feed_silo2,   18,  6, 57, 5),
        (s_temp_hay_loft,     22, 10, 62, 6),
        (s_temp_feed_ambient, 19,  7, 60, 5),
        (s_temp_feed_proc,    20,  5, 58, 4),
        # ── Vet Bay
        (s_temp_vet_exam,     20,  2, 50, 3),
        (s_temp_vet_iso_a,    21,  3, 55, 3),
        (s_temp_vet_iso_b,    21,  3, 55, 3),
        (s_temp_vet_lab,      22,  2, 48, 2),
        # ── Processing Plant
        (s_temp_proc_hall,    18,  3, 55, 4),
        (s_temp_proc_cold,     4,  1, 88, 2),
        (s_temp_proc_fill,    16,  3, 58, 4),
        # ── Water & Utilities
        (s_temp_pump_room,    28,  4, 55, 4),
        (s_temp_boiler_room,  40,  8, 45, 5),
        (s_temp_cool_tower,   25, 10, 70, 8),
    ]

    all_milk_sids = [
        s_ma_line1, s_ma_line2, s_ma_line3, s_ma_line4,
        s_ma_line5, s_ma_line6, s_ma_line7,
        s_ma_vet1, s_ma_vet2,
        s_ma_proc_qa1, s_ma_proc_qa2, s_ma_proc_qa3, s_ma_proc_qa4,
    ]

    for step in range(96):   # 24 h × 4 per hour
        t = base + timedelta(minutes=15 * step)
        hour_frac = (t.hour + t.minute / 60) / 24

        # Temperature + Humidity (all temp_humidity sensors)
        for sid, t_mean, t_amp, h_mean, h_amp in temp_humidity_profiles:
            temp_val = t_mean + t_amp * math.sin(math.pi * hour_frac) + random.gauss(0, 0.4)
            # humidity inversely correlated with temperature during day
            hum_val  = h_mean - h_amp * math.sin(math.pi * hour_frac) + random.gauss(0, 1.0)
            hum_val  = max(20.0, min(99.0, hum_val))
            readings.append((t, sid, "temperature", round(temp_val, 2), "°C"))
            readings.append((t, sid, "humidity",    round(hum_val,  1), "%RH"))

        # Weight — every 4 steps (hourly)
        if step % 4 == 0:
            h_hour = t.hour

            # Feed hopper: depleting over day
            feed_main_w = max(0, 420 - step * 0.6 + random.gauss(0, 3))
            readings.append((t, s_wt_feed_main, "weight", round(feed_main_w, 1), "kg"))

            # Milk tanks: filling during milking sessions (06–09, 14–17)
            tank_fill = 1 if 6 <= h_hour <= 9 or 14 <= h_hour <= 17 else 0
            for sid, base_w, cap in [
                (s_wt_tank_1, 600, 1200), (s_wt_tank_2, 300, 1200), (s_wt_tank_3, 150, 800)
            ]:
                w = min(cap, base_w + step * 2.5 * tank_fill + random.gauss(0, 5))
                readings.append((t, sid, "weight", round(w, 1), "kg"))

            # Feed troughs: twice-daily refill cycle
            for sid in [s_wt_trough_1, s_wt_trough_2]:
                phase = math.sin(2 * math.pi * hour_frac * 2)
                w = max(0, 80 + 60 * phase + random.gauss(0, 5))
                readings.append((t, sid, "weight", round(w, 1), "kg"))

            # Cream separator: fills during milking sessions
            cream_w = min(500, step * 1.8 * tank_fill + random.gauss(0, 3))
            readings.append((t, s_wt_cream_sep, "weight", round(max(0, cream_w), 1), "kg"))

            # Pasture water trough: slowly depletes, refilled at 08:00 and 16:00
            trough_phase = math.sin(2 * math.pi * hour_frac * 2)
            pas_trough_w = max(0, 250 + 150 * trough_phase + random.gauss(0, 8))
            readings.append((t, s_wt_pas_trough, "weight", round(pas_trough_w, 1), "kg"))

            # Grain silos: slow depletion
            silo1_w = max(0, 1800 - step * 2.8 + random.gauss(0, 10))
            silo2_w = max(0, 3200 - step * 1.5 + random.gauss(0, 10))
            readings.append((t, s_wt_silo_1, "weight", round(silo1_w, 1), "kg"))
            readings.append((t, s_wt_silo_2, "weight", round(silo2_w, 1), "kg"))

            # Hay + pellet + mineral: slow depletion
            readings.append((t, s_wt_hay,     "weight", round(max(0, 800 - step * 1.2 + random.gauss(0, 8)), 1), "kg"))
            readings.append((t, s_wt_pellet,  "weight", round(max(0, 480 - step * 0.8 + random.gauss(0, 4)), 1), "kg"))
            readings.append((t, s_wt_mineral, "weight", round(max(0, 300 - step * 0.4 + random.gauss(0, 3)), 1), "kg"))

            # Processing scales: active during production hours (07–17)
            if 7 <= h_hour <= 17:
                readings.append((t, s_wt_bottle_scale, "weight", round(random.uniform(0.9, 1.1), 3), "kg"))
                readings.append((t, s_wt_carton_scale, "weight", round(random.uniform(8.5, 12.5), 2), "kg"))

            # Water tanks: slow depletion, refilled on demand
            water_main_w = max(0, 8500 - step * 15.0 + random.gauss(0, 50))
            water_sec_w  = max(0, 3800 - step * 8.0  + random.gauss(0, 30))
            diesel_w     = max(0, 1600 - step * 1.5  + random.gauss(0, 10))
            readings.append((t, s_wt_water_main,  "weight", round(water_main_w, 1), "kg"))
            readings.append((t, s_wt_water_sec,   "weight", round(water_sec_w,  1), "kg"))
            readings.append((t, s_wt_diesel_tank, "weight", round(diesel_w,     1), "kg"))

            # Medical supply scale (vet)
            if h_hour in (9, 11, 15):
                readings.append((t, s_wt_vet_table,  "weight", round(35 + random.gauss(0, 8), 1), "kg"))
                readings.append((t, s_wt_vet_supply, "weight", round(18 + random.gauss(0, 2), 1), "kg"))

            # Milk analyzers: active during day (05–22)
            # Channels: fat, protein, lactose, somatic_cells, milk_temp
            if 5 <= h_hour < 22:
                for sid in all_milk_sids:
                    # Post-processing QC analyzers have tighter spec (lower SCC)
                    if sid in (s_ma_proc_qa1, s_ma_proc_qa2, s_ma_proc_qa3, s_ma_proc_qa4):
                        scc_mean, scc_std = 80000, 15000
                    else:
                        scc_mean, scc_std = 180000, 30000
                    readings.append((t, sid, "fat",          round(3.5 + random.gauss(0, 0.3), 2), "%"))
                    readings.append((t, sid, "protein",      round(3.1 + random.gauss(0, 0.2), 2), "%"))
                    readings.append((t, sid, "lactose",      round(4.6 + random.gauss(0, 0.1), 2), "%"))
                    readings.append((t, sid, "somatic_cells",round(max(0, scc_mean + random.gauss(0, scc_std))), "cells/mL"))
                    readings.append((t, sid, "milk_temp",    round(4.0 + random.gauss(0, 0.5), 1), "°C"))

        # Goat scales — morning 07:00 and afternoon 14:00
        if t.hour in (7, 14) and t.minute == 0:
            for sid in [s_wt_goat_a, s_wt_goat_b, s_wt_goat_c, s_wt_goat_d]:
                readings.append((t, sid, "weight", round(32 + random.gauss(0, 4), 1), "kg"))
            # Kidding scale: lighter goats (kids and lactating does)
            readings.append((t, s_wt_kidding, "weight", round(4.5 + random.gauss(0, 1.2), 2), "kg"))

    # Bulk insert
    if readings:
        rows = ", ".join(
            f"('{r[0].isoformat()}', '{r[1]}', '{r[2]}', {r[3]}, '{r[4]}')"
            for r in readings
        )
        await db.execute(text(f"""
            INSERT INTO sensor_readings (time, sensor_id, channel, value, unit)
            VALUES {rows}
            ON CONFLICT DO NOTHING
        """))

    await db.commit()

    # ── Summary ──────────────────────────────────────────────────────────────
    type_counts = {}
    for s in sensors:
        type_counts[s["sensor_type"]] = type_counts.get(s["sensor_type"], 0) + 1

    print()
    print("=" * 60)
    print("[OK] GDF-AutoMon seed complete (v3)")
    print("=" * 60)
    print()
    print("Credentials:")
    print("  super_admin : superadmin@gdf.farm   / Admin@1234")
    print("  admin       : admin@gdf.farm         / Admin@1234")
    print("  operator 1  : operator1@gdf.farm     / Operator@1234  (barn + parlour)")
    print("  operator 2  : operator2@gdf.farm     / Operator@1234  (parlour + pasture + feed)")
    print("  operator 3  : operator3@gdf.farm     / Operator@1234  (processing + utilities)")
    print()
    print(f"Locations : 7")
    print(f"  Main Barn | Milking Parlour | Outdoor Pasture | Feed Store")
    print(f"  Veterinary Bay | Processing & Packaging | Water & Utilities")
    print()
    print(f"Sensors   : {len(sensors)} total")
    for t_name, count in sorted(type_counts.items()):
        print(f"  {t_name}: {count}")
    print()
    print(f"Alert rules       : {len(alert_rule_defs)}")
    print(f"Alert rule actions: {len(rule_actions)}")
    print(f"Active alerts     : {len(active_alerts)}  (4 critical · 5 warning · 1 info)")
    print(f"Plans             : 3  (all enabled)")
    print(f"Tasks             : 6  (3 open · 2 submitted · 1 done)")
    print(f"Telemetry         : {len(readings):,} readings  (24 h, 15-min intervals)")
    print()


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
