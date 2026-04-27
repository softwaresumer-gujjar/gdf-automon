"""
GDF-AutoMon — complete seed script.
Creates all demo data for every role scenario.

Usage (from backend/):
    python scripts/seed.py
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = (
    "postgresql+asyncpg://gdf:gdf_secure_2024@localhost:5432/gdfautomon"
)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def h(plain: str) -> str:
    return _pwd.hash(plain)


def now() -> datetime:
    return datetime.now(timezone.utc)


async def seed(db: AsyncSession) -> None:
    # ── Wipe existing demo data (idempotent re-runs) ──────────────────────────
    # TRUNCATE with CASCADE handles FK ordering automatically and is fast.
    await db.execute(text(
        "TRUNCATE TABLE locations, users, sensors, sensor_readings, "
        "alert_rules, active_alerts, push_subscriptions, "
        "user_location_permissions, user_sensor_permissions, "
        "notification_preferences, password_reset_tokens, "
        "plans, plan_actions, "
        "tasks, task_assignments, task_attachments, "
        "chat_rooms, chat_room_members, chat_messages, chat_attachments "
        "RESTART IDENTITY CASCADE"
    ))
    await db.commit()

    # ── IDs ───────────────────────────────────────────────────────────────────
    # locations
    loc_barn    = uuid.uuid4()
    loc_milk    = uuid.uuid4()
    loc_pasture = uuid.uuid4()

    # users
    u_super = uuid.uuid4()
    u_admin = uuid.uuid4()
    u_op1   = uuid.uuid4()
    u_op2   = uuid.uuid4()

    # sensors
    # temperature
    s_temp_barn1  = uuid.uuid4()
    s_temp_barn2  = uuid.uuid4()
    s_temp_milk   = uuid.uuid4()
    s_temp_pas    = uuid.uuid4()
    # weight
    s_wt_goat1    = uuid.uuid4()
    s_wt_goat2    = uuid.uuid4()
    s_wt_feed     = uuid.uuid4()
    s_wt_tank     = uuid.uuid4()
    # milk_analyzer
    s_ma_batch1   = uuid.uuid4()
    s_ma_batch2   = uuid.uuid4()
    # camera
    s_cam_barn    = uuid.uuid4()
    s_cam_milk    = uuid.uuid4()
    s_cam_gate    = uuid.uuid4()

    # tasks
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()
    t3 = uuid.uuid4()
    t4 = uuid.uuid4()

    # plans
    p1 = uuid.uuid4()
    p2 = uuid.uuid4()
    p3 = uuid.uuid4()

    # chat rooms
    r_general = uuid.uuid4()
    r_task1   = uuid.uuid4()

    # ── Locations ─────────────────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO locations (id, name, description, address) VALUES
        (:id1, 'Main Barn',      'Primary housing for 120 Boer goats',   'Section A — Farm North'),
        (:id2, 'Milking Parlor', 'Automated milking station, 24 stands', 'Section B — Farm Centre'),
        (:id3, 'Outdoor Pasture','East grazing pasture, 8 acres',        'Section C — Farm East')
    """), {"id1": str(loc_barn), "id2": str(loc_milk), "id3": str(loc_pasture)})

    # ── Users ─────────────────────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO users (id, email, full_name, password_hash, role, is_active) VALUES
        (:id,  :email,  :name,  :pw,  :role, true)
    """), [
        {"id": str(u_super), "email": "superadmin@gdf.farm",
         "name": "Super Admin", "pw": h("Admin@1234"), "role": "super_admin"},
        {"id": str(u_admin), "email": "admin@gdf.farm",
         "name": "Farm Admin",  "pw": h("Admin@1234"), "role": "admin"},
        {"id": str(u_op1),   "email": "operator1@gdf.farm",
         "name": "Alice Operator", "pw": h("Operator@1234"), "role": "operator"},
        {"id": str(u_op2),   "email": "operator2@gdf.farm",
         "name": "Bob Operator",   "pw": h("Operator@1234"), "role": "operator"},
    ])

    # ── User location permissions (admin + operators get specific locations) ──
    await db.execute(text("""
        INSERT INTO user_location_permissions (id, user_id, location_id) VALUES
        (:id, :uid, :lid)
    """), [
        # admin: all three
        {"id": str(uuid.uuid4()), "uid": str(u_admin), "lid": str(loc_barn)},
        {"id": str(uuid.uuid4()), "uid": str(u_admin), "lid": str(loc_milk)},
        {"id": str(uuid.uuid4()), "uid": str(u_admin), "lid": str(loc_pasture)},
        # op1: barn + milking parlour
        {"id": str(uuid.uuid4()), "uid": str(u_op1),   "lid": str(loc_barn)},
        {"id": str(uuid.uuid4()), "uid": str(u_op1),   "lid": str(loc_milk)},
        # op2: milking parlour + pasture
        {"id": str(uuid.uuid4()), "uid": str(u_op2),   "lid": str(loc_milk)},
        {"id": str(uuid.uuid4()), "uid": str(u_op2),   "lid": str(loc_pasture)},
    ])

    # ── Sensors ───────────────────────────────────────────────────────────────
    sensors = [
        # temperature
        {"id": str(s_temp_barn1), "name": "Barn Temp NE",
         "sensor_type": "temperature", "protocol": "mqtt",
         "config": {"topic": f"gdf/{s_temp_barn1}/temperature", "unit": "°C"},
         "location_id": str(loc_barn),
         "description": "North-east corner ambient temperature sensor"},
        {"id": str(s_temp_barn2), "name": "Barn Temp SW",
         "sensor_type": "temperature", "protocol": "mqtt",
         "config": {"topic": f"gdf/{s_temp_barn2}/temperature", "unit": "°C"},
         "location_id": str(loc_barn),
         "description": "South-west corner ambient temperature sensor"},
        {"id": str(s_temp_milk), "name": "Parlour Temp",
         "sensor_type": "temperature", "protocol": "mqtt",
         "config": {"topic": f"gdf/{s_temp_milk}/temperature", "unit": "°C"},
         "location_id": str(loc_milk),
         "description": "Milking parlour ambient temperature"},
        {"id": str(s_temp_pas), "name": "Pasture Temp",
         "sensor_type": "temperature", "protocol": "mqtt",
         "config": {"topic": f"gdf/{s_temp_pas}/temperature", "unit": "°C"},
         "location_id": str(loc_pasture),
         "description": "Outdoor pasture temperature probe"},
        # weight
        {"id": str(s_wt_goat1), "name": "Weigh Scale Alpha",
         "sensor_type": "weight", "protocol": "mqtt",
         "config": {"topic": f"gdf/{s_wt_goat1}/weight", "unit": "kg", "capacity_kg": 150},
         "location_id": str(loc_barn),
         "description": "Platform scale — goat weighing pen A"},
        {"id": str(s_wt_goat2), "name": "Weigh Scale Beta",
         "sensor_type": "weight", "protocol": "mqtt",
         "config": {"topic": f"gdf/{s_wt_goat2}/weight", "unit": "kg", "capacity_kg": 150},
         "location_id": str(loc_barn),
         "description": "Platform scale — goat weighing pen B"},
        {"id": str(s_wt_feed), "name": "Feed Hopper Scale",
         "sensor_type": "weight", "protocol": "mqtt",
         "config": {"topic": f"gdf/{s_wt_feed}/weight", "unit": "kg", "capacity_kg": 500},
         "location_id": str(loc_barn),
         "description": "Main feed hopper load cell"},
        {"id": str(s_wt_tank), "name": "Milk Tank Scale",
         "sensor_type": "weight", "protocol": "mqtt",
         "config": {"topic": f"gdf/{s_wt_tank}/weight", "unit": "kg", "capacity_kg": 1000},
         "location_id": str(loc_milk),
         "description": "Bulk milk cooling tank weight sensor"},
        # milk_analyzer
        {"id": str(s_ma_batch1), "name": "Milk Analyser Line 1",
         "sensor_type": "milk_analyzer", "protocol": "serial",
         "config": {"port": "COM3", "baud_rate": 9600, "unit": "%"},
         "location_id": str(loc_milk),
         "description": "Inline milk quality analyser — fat, protein, lactose"},
        {"id": str(s_ma_batch2), "name": "Milk Analyser Line 2",
         "sensor_type": "milk_analyzer", "protocol": "serial",
         "config": {"port": "COM4", "baud_rate": 9600, "unit": "%"},
         "location_id": str(loc_milk),
         "description": "Secondary analyser for batch validation"},
        # camera
        {"id": str(s_cam_barn), "name": "Barn CCTV",
         "sensor_type": "camera", "protocol": "rtsp",
         "config": {"rtsp_url": "rtsp://192.168.1.50:554/barn", "fps": 5},
         "location_id": str(loc_barn),
         "description": "Wide-angle overhead barn camera"},
        {"id": str(s_cam_milk), "name": "Parlour CCTV",
         "sensor_type": "camera", "protocol": "rtsp",
         "config": {"rtsp_url": "rtsp://192.168.1.51:554/parlour", "fps": 10},
         "location_id": str(loc_milk),
         "description": "Milking station HD camera"},
        {"id": str(s_cam_gate), "name": "Gate CCTV",
         "sensor_type": "camera", "protocol": "rtsp",
         "config": {"rtsp_url": "rtsp://192.168.1.52:554/gate", "fps": 5},
         "location_id": str(loc_pasture),
         "description": "Entrance gate wide-angle camera"},
    ]
    import json as _json
    for s in sensors:
        await db.execute(text("""
            INSERT INTO sensors (id, name, sensor_type, protocol, config, location_id,
                                 description, status)
            VALUES (:id, :name, :sensor_type, :protocol,
                    CAST(:config AS jsonb), :location_id,
                    :description, 'active')
        """), {**s, "config": _json.dumps(s["config"])})

    # ── Alert rules ───────────────────────────────────────────────────────────
    alert_rules = [
        # temperature rules
        {"sensor_id": str(s_temp_barn1), "channel": "temperature",
         "condition": "gt", "threshold": 35.0, "threshold_max": None, "severity": "warning"},
        {"sensor_id": str(s_temp_barn1), "channel": "temperature",
         "condition": "gt", "threshold": 40.0, "threshold_max": None, "severity": "critical"},
        {"sensor_id": str(s_temp_barn1), "channel": "temperature",
         "condition": "lt", "threshold": 5.0,  "threshold_max": None, "severity": "warning"},
        {"sensor_id": str(s_temp_barn2), "channel": "temperature",
         "condition": "gt", "threshold": 35.0, "threshold_max": None, "severity": "warning"},
        {"sensor_id": str(s_temp_milk),  "channel": "temperature",
         "condition": "outside_range", "threshold": 15.0, "threshold_max": 25.0,
         "severity": "warning"},
        {"sensor_id": str(s_temp_pas),   "channel": "temperature",
         "condition": "gt", "threshold": 38.0, "threshold_max": None, "severity": "info"},
        # weight rules
        {"sensor_id": str(s_wt_goat1),  "channel": "weight",
         "condition": "lt", "threshold": 20.0, "threshold_max": None, "severity": "warning"},
        {"sensor_id": str(s_wt_feed),   "channel": "weight",
         "condition": "lt", "threshold": 50.0, "threshold_max": None, "severity": "warning"},
        {"sensor_id": str(s_wt_feed),   "channel": "weight",
         "condition": "lt", "threshold": 20.0, "threshold_max": None, "severity": "critical"},
        {"sensor_id": str(s_wt_tank),   "channel": "weight",
         "condition": "gt", "threshold": 900.0, "threshold_max": None, "severity": "warning"},
        # milk analyzer rules
        {"sensor_id": str(s_ma_batch1), "channel": "fat_pct",
         "condition": "lt", "threshold": 3.0, "threshold_max": None, "severity": "warning"},
        {"sensor_id": str(s_ma_batch1), "channel": "protein_pct",
         "condition": "lt", "threshold": 2.8, "threshold_max": None, "severity": "warning"},
        {"sensor_id": str(s_ma_batch1), "channel": "somatic_cell_count",
         "condition": "gt", "threshold": 400000, "threshold_max": None, "severity": "critical"},
        {"sensor_id": str(s_ma_batch2), "channel": "fat_pct",
         "condition": "lt", "threshold": 3.0, "threshold_max": None, "severity": "warning"},
    ]
    rule_ids = []
    for r in alert_rules:
        rid = str(uuid.uuid4())
        rule_ids.append(rid)
        await db.execute(text("""
            INSERT INTO alert_rules (id, sensor_id, channel, condition, threshold,
                                     threshold_max, severity, enabled)
            VALUES (:id, :sensor_id, :channel, :condition, :threshold,
                    :threshold_max, :severity, true)
        """), {"id": rid, **r})

    # ── Active alerts (diverse sample across severities) ─────────────────────
    # rule_ids index: 0=temp_barn1_gt35_warn, 1=temp_barn1_gt40_crit,
    #   2=temp_barn1_lt5_warn, 3=temp_barn2_gt35_warn, 4=temp_milk_outside_range_warn,
    #   5=temp_pas_gt38_info, 6=weight_goat1_lt20_warn, 7=wt_feed_lt50_warn,
    #   8=wt_feed_lt20_crit, 9=wt_tank_gt900_warn, 10=ma1_fat_lt3_warn,
    #   11=ma1_protein_lt2.8_warn, 12=ma1_scc_gt400k_crit, 13=ma2_fat_lt3_warn

    active_alert_rows = [
        # CRITICAL — barn temp well above critical threshold (41°C)
        {
            "id": str(uuid.uuid4()), "rule_id": rule_ids[1],
            "sensor_id": str(s_temp_barn1), "channel": "temperature",
            "triggered_value": 41.2, "severity": "critical",
            "message": "CRITICAL: Barn Temp NE at 41.2°C — exceeds critical threshold of 40°C. Ventilation failure suspected.",
            "triggered_at": "NOW() - INTERVAL '22 minutes'",
        },
        # WARNING — barn temp above warning threshold (37°C)
        {
            "id": str(uuid.uuid4()), "rule_id": rule_ids[0],
            "sensor_id": str(s_temp_barn1), "channel": "temperature",
            "triggered_value": 37.4, "severity": "warning",
            "message": "Barn Temp NE: 37.4°C exceeds warning threshold of 35°C. Check east ventilation fan.",
            "triggered_at": "NOW() - INTERVAL '45 minutes'",
        },
        # WARNING — parlour temp outside safe range (26.5°C, range is 15-25°C)
        {
            "id": str(uuid.uuid4()), "rule_id": rule_ids[4],
            "sensor_id": str(s_temp_milk), "channel": "temperature",
            "triggered_value": 26.5, "severity": "warning",
            "message": "Parlour Temp: 26.5°C is outside safe range (15–25°C). Cooling system check required.",
            "triggered_at": "NOW() - INTERVAL '1 hour 10 minutes'",
        },
        # CRITICAL — somatic cell count way above threshold (520,000 cells/ml)
        {
            "id": str(uuid.uuid4()), "rule_id": rule_ids[12],
            "sensor_id": str(s_ma_batch1), "channel": "somatic_cell_count",
            "triggered_value": 520000, "severity": "critical",
            "message": "CRITICAL: Milk Analyser Line 1 SCC at 520,000 cells/ml — mastitis indicator. Isolate herd immediately.",
            "triggered_at": "NOW() - INTERVAL '3 hours'",
        },
        # WARNING — feed hopper approaching empty (38.2 kg, threshold 50 kg)
        {
            "id": str(uuid.uuid4()), "rule_id": rule_ids[7],
            "sensor_id": str(s_wt_feed), "channel": "weight",
            "triggered_value": 38.2, "severity": "warning",
            "message": "Feed Hopper Scale: 38.2 kg approaching empty — below warning threshold of 50 kg. Order feed.",
            "triggered_at": "NOW() - INTERVAL '2 hours'",
        },
        # INFO — pasture temperature high (39.2°C, threshold 38°C)
        {
            "id": str(uuid.uuid4()), "rule_id": rule_ids[5],
            "sensor_id": str(s_temp_pas), "channel": "temperature",
            "triggered_value": 39.2, "severity": "info",
            "message": "Pasture Temp: 39.2°C is above 38°C threshold. Consider moving herd to shade.",
            "triggered_at": "NOW() - INTERVAL '30 minutes'",
        },
        # WARNING — milk fat low (2.8%, threshold 3.0%)
        {
            "id": str(uuid.uuid4()), "rule_id": rule_ids[10],
            "sensor_id": str(s_ma_batch1), "channel": "fat_pct",
            "triggered_value": 2.8, "severity": "warning",
            "message": "Milk Analyser Line 1: Fat at 2.8% is below minimum 3.0%. Review herd nutrition.",
            "triggered_at": "NOW() - INTERVAL '4 hours 15 minutes'",
        },
        # WARNING — milk tank weight very high (920 kg, threshold 900 kg)
        {
            "id": str(uuid.uuid4()), "rule_id": rule_ids[9],
            "sensor_id": str(s_wt_tank), "channel": "weight",
            "triggered_value": 920.5, "severity": "warning",
            "message": "Milk Tank Scale: 920.5 kg exceeds 900 kg threshold — schedule collection.",
            "triggered_at": "NOW() - INTERVAL '6 hours'",
        },
    ]

    for row in active_alert_rows:
        triggered_at_expr = row.pop("triggered_at")
        await db.execute(text(f"""
            INSERT INTO active_alerts
                (id, rule_id, sensor_id, channel, triggered_value, severity, message, triggered_at)
            VALUES
            (:id, :rule_id, :sensor_id, :channel, :triggered_value, :severity, :message,
             {triggered_at_expr})
        """), row)

    # ── Plans ─────────────────────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO plans (id, name, description, sensor_id, channel,
                           target_value, target_unit, lower_limit, upper_limit,
                           enabled, created_by_id)
        VALUES
        (:p1, 'Barn Temperature Control',
         'Keep barn ambient temp within safe range for goats',
         :s1, 'temperature', 22.0, '°C', 10.0, 32.0, true, :admin),
        (:p2, 'Milk Fat Quality',
         'Maintain milk fat percentage above industry minimum',
         :s2, 'fat_pct', 3.5, '%', 3.0, 6.0, true, :admin),
        (:p3, 'Feed Hopper Level',
         'Alert when feed drops below safe operating level',
         :s3, 'weight', 100.0, 'kg', 50.0, NULL, true, :admin)
    """), {
        "p1": str(p1), "p2": str(p2), "p3": str(p3),
        "s1": str(s_temp_barn1), "s2": str(s_ma_batch1), "s3": str(s_wt_feed),
        "admin": str(u_admin),
    })

    # ── Plan actions ──────────────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO plan_actions
            (id, plan_id, action_type, trigger_on, message_template, config, enabled)
        VALUES
        (:id1, :p1, 'notification', 'outside_range',
         'ALERT: Barn temperature {value}°C is outside the safe range [{lower}–{upper}°C]',
         '{}', true),
        (:id2, :p1, 'reminder', 'above_upper',
         'High barn temperature reminder: {value}°C. Check ventilation.',
         '{}', true),
        (:id3, :p2, 'notification', 'below_lower',
         'Milk fat {value}% is below minimum {lower}%. Review herd nutrition.',
         '{}', true),
        (:id4, :p3, 'notification', 'below_lower',
         'URGENT: Feed hopper at {value} kg — restock required.',
         '{}', true),
        (:id5, :p3, 'reminder', 'below_lower',
         'Feed running low ({value} kg). Schedule delivery.',
         '{}', true)
    """), {
        "id1": str(uuid.uuid4()), "id2": str(uuid.uuid4()),
        "id3": str(uuid.uuid4()), "id4": str(uuid.uuid4()),
        "id5": str(uuid.uuid4()),
        "p1": str(p1), "p2": str(p2), "p3": str(p3),
    })

    # ── Tasks ─────────────────────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO tasks
            (id, title, description, deadline, status, created_by_id)
        VALUES
        (:t1, 'Calibrate Milk Analyser Line 1',
         'Perform weekly calibration using reference samples. '
         'Document readings in the calibration log.',
         NOW() + INTERVAL '2 days', 'open', :admin),

        (:t2, 'Replace Barn East Ventilation Fan',
         'Fan motor showing intermittent fault. Order part #VN-240A and install. '
         'Ensure barn temp stays below 35°C during repair.',
         NOW() + INTERVAL '5 days', 'open', :admin),

        (:t3, 'Monthly Herd Health Inspection',
         'Full herd inspection: body condition scoring, hoof trimming check, '
         'tag verification. Record weights using Scale Alpha.',
         NOW() + INTERVAL '1 day', 'submitted', :admin),

        (:t4, 'Deep Clean Milking Parlour',
         'End-of-season deep sanitation. Dismantle milk lines, acid wash, '
         're-grease bearings. Log CIP cycle completion.',
         NOW() - INTERVAL '3 days', 'done', :admin)
    """), {"t1": str(t1), "t2": str(t2), "t3": str(t3), "t4": str(t4),
           "admin": str(u_admin)})

    # ── Task assignments ──────────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO task_assignments (id, task_id, user_id) VALUES
        (:a1, :t1, :op1),
        (:a2, :t2, :op1),
        (:a3, :t2, :op2),
        (:a4, :t3, :op1),
        (:a5, :t4, :op2)
    """), {
        "a1": str(uuid.uuid4()), "t1": str(t1), "op1": str(u_op1),
        "a2": str(uuid.uuid4()), "t2": str(t2),
        "a3": str(uuid.uuid4()),                "op2": str(u_op2),
        "a4": str(uuid.uuid4()), "t3": str(t3),
        "a5": str(uuid.uuid4()), "t4": str(t4),
    })

    # update t3/t4 with review data
    await db.execute(text("""
        UPDATE tasks SET
            submitted_by_id = :op1, submitted_at = NOW() - INTERVAL '6 hours',
            completion_note = 'All 120 goats checked. 3 animals flagged for vet follow-up.'
        WHERE id = :t3
    """), {"op1": str(u_op1), "t3": str(t3)})

    await db.execute(text("""
        UPDATE tasks SET
            submitted_by_id = :op2, submitted_at = NOW() - INTERVAL '4 days',
            completion_note = 'CIP cycle completed. All lines clear. Time: 4h 20m.',
            reviewed_by_id  = :admin, reviewed_at = NOW() - INTERVAL '3 days',
            review_note = 'Approved. CIP log filed.', status = 'done'
        WHERE id = :t4
    """), {"op2": str(u_op2), "admin": str(u_admin), "t4": str(t4)})

    # ── Chat rooms ────────────────────────────────────────────────────────────
    await db.execute(text("""
        INSERT INTO chat_rooms (id, name, room_type, task_id, created_by_id) VALUES
        (:r1, 'General', 'general', NULL, :admin),
        (:r2, 'Herd Inspection Chat', 'task', :t3, :admin)
    """), {"r1": str(r_general), "r2": str(r_task1),
           "t3": str(t3), "admin": str(u_admin)})

    # add everyone to general room
    for uid in [u_super, u_admin, u_op1, u_op2]:
        await db.execute(text("""
            INSERT INTO chat_room_members (id, room_id, user_id) VALUES
            (:id, :room, :uid)
        """), {"id": str(uuid.uuid4()), "room": str(r_general), "uid": str(uid)})

    # task room: admin + op1
    for uid in [u_admin, u_op1]:
        await db.execute(text("""
            INSERT INTO chat_room_members (id, room_id, user_id) VALUES
            (:id, :room, :uid)
        """), {"id": str(uuid.uuid4()), "room": str(r_task1), "uid": str(uid)})

    # Sample messages
    await db.execute(text("""
        INSERT INTO chat_messages (id, room_id, user_id, content, created_at) VALUES
        (:m1, :gen, :super,  'Welcome to GDF-AutoMon! All systems are initialised.',
         NOW() - INTERVAL '2 days'),
        (:m2, :gen, :admin,  'Reminder: milk analyser calibration is due this week.',
         NOW() - INTERVAL '1 day'),
        (:m3, :gen, :op1,    'Noted. I will take care of it tomorrow.',
         NOW() - INTERVAL '23 hours'),
        (:m4, :gen, :op2,    'Parlour cleaned and ready for morning session.',
         NOW() - INTERVAL '12 hours'),
        (:m5, :r_t1,:admin,  'Please upload photos of body condition scores when done.',
         NOW() - INTERVAL '7 hours'),
        (:m6, :r_t1,:op1,    'Sure, will attach them to the task submission.',
         NOW() - INTERVAL '6 hours')
    """), {
        "m1": str(uuid.uuid4()), "m2": str(uuid.uuid4()),
        "m3": str(uuid.uuid4()), "m4": str(uuid.uuid4()),
        "m5": str(uuid.uuid4()), "m6": str(uuid.uuid4()),
        "gen": str(r_general), "r_t1": str(r_task1),
        "super": str(u_super), "admin": str(u_admin),
        "op1": str(u_op1),     "op2": str(u_op2),
    })

    # ── Historical telemetry (last 24 h, every 15 min) ────────────────────────
    import math, random
    random.seed(42)
    base = now() - timedelta(hours=24)
    readings = []
    for step in range(96):  # 24h × 4 per hour
        t = base + timedelta(minutes=15 * step)
        hour_frac = (t.hour + t.minute / 60) / 24

        # Temperature — diurnal curve
        temp_barn = 18 + 12 * math.sin(math.pi * hour_frac) + random.gauss(0, 0.5)
        readings.append((t, str(s_temp_barn1), "temperature", round(temp_barn, 2), "°C"))
        readings.append((t, str(s_temp_barn2), "temperature", round(temp_barn - 0.8 + random.gauss(0, 0.3), 2), "°C"))
        readings.append((t, str(s_temp_milk),  "temperature", round(20 + random.gauss(0, 1), 2), "°C"))
        readings.append((t, str(s_temp_pas),   "temperature", round(temp_barn + 3 + random.gauss(0, 1), 2), "°C"))

        # Weight sensors (slow change)
        if step % 4 == 0:
            wt = 38.5 - step * 0.5 + random.gauss(0, 2)   # feed depleting
            readings.append((t, str(s_wt_feed), "weight", max(0, round(wt, 1)), "kg"))
            tank_wt = 200 + step * 3.2 + random.gauss(0, 5)   # tank filling
            readings.append((t, str(s_wt_tank), "weight", round(tank_wt, 1), "kg"))

        # Milk analyser (every hour)
        if step % 4 == 0:
            readings.append((t, str(s_ma_batch1), "fat_pct",     round(3.5 + random.gauss(0, 0.3), 2), "%"))
            readings.append((t, str(s_ma_batch1), "protein_pct", round(3.1 + random.gauss(0, 0.2), 2), "%"))
            readings.append((t, str(s_ma_batch1), "lactose_pct", round(4.6 + random.gauss(0, 0.1), 2), "%"))
            readings.append((t, str(s_ma_batch1), "somatic_cell_count",
                             round(180000 + random.gauss(0, 30000)), "cells/ml"))
            readings.append((t, str(s_ma_batch2), "fat_pct",     round(3.4 + random.gauss(0, 0.3), 2), "%"))
            readings.append((t, str(s_ma_batch2), "protein_pct", round(3.0 + random.gauss(0, 0.2), 2), "%"))

        # Goat scale (twice a day — morning 07:00, afternoon 14:00)
        if t.hour in (7, 14) and t.minute == 0:
            for sensor_id in [str(s_wt_goat1), str(s_wt_goat2)]:
                readings.append((t, sensor_id, "weight", round(32 + random.gauss(0, 4), 1), "kg"))

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
    print("[OK] Seed complete.")
    print()
    print("Users created:")
    print("  super_admin : superadmin@gdf.farm   / Admin@1234")
    print("  admin       : admin@gdf.farm         / Admin@1234")
    print("  operator 1  : operator1@gdf.farm     / Operator@1234")
    print("  operator 2  : operator2@gdf.farm     / Operator@1234")
    print()
    print("Locations : Main Barn | Milking Parlor | Outdoor Pasture")
    print("Sensors   : 4× temperature | 4× weight | 2× milk_analyzer | 3× camera")
    print("Tasks     : 4 tasks in various states (open/submitted/done)")
    print("Plans     : 3 plans with notification + reminder actions")
    print("Alerts    : 8 active alerts (2 critical, 4 warning, 1 info, 1 warning)")
    print("Chat      : General room + task-linked room with sample messages")
    print("Telemetry : 24 h of readings (every 15 min) for all sensor channels")


async def main() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
