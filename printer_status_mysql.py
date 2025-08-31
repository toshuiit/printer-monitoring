#!/usr/bin/env python3

import subprocess
import json
from datetime import datetime
import mysql.connector  # pip install mysql-connector-python

# Printer list (hostname:IP)
PRINTERS = {
    "lp2": "172.X.X.X",
    "lp3": "172.X.X.X",   # uses string OID
    "lp4": "172.X.X.X",
    "lp5": "172.X.X.X",   # uses HP private OID
    "clp": "172.X.X.X",   # uses string OID
}

COMMUNITY = "public"   # SNMP community string

TRAY_STATUS_MAP = {0: "Paper Available", 1: "Paper Empty", -3: "Unknown/Not Installed"}

def snmp_get(ip, oid):
    try:
        result = subprocess.run(
            ["snmpwalk", "-v2c", "-c", COMMUNITY, ip, oid],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().splitlines()
        values = []
        for line in lines:
            if "=" in line:
                try:
                    val = int(line.split()[-1])
                    values.append(val)
                except ValueError:
                    pass
        return values
    except Exception:
        return []

def get_tray_status_lp3_clp(ip, oid):
    try:
        result = subprocess.run(
            ["snmpwalk", "-v2c", "-c", COMMUNITY, ip, oid],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.strip()
        if "TRAY EMPTY" in output.upper():
            return ["Paper Empty"]
        elif output == "":
            return ["Paper Available"]
        else:
            return ["Unknown"]
    except Exception:
        return ["Unknown"]

def interpret_tray_states(ip, tray_states):
    tray_statuses = []
    for i, s in enumerate(tray_states, start=1):
        status = TRAY_STATUS_MAP.get(s, f"Code{s}")
        tray_statuses.append(f"Tray{i}: {status}")
    return "; ".join(tray_statuses)

# Collect data
rows = []
for name, ip in PRINTERS.items():
    toner_levels = snmp_get(ip, ".1.3.6.1.2.1.43.11.1.1.9")

    if ip in ["172.27.16.5", "172.27.16.8"]:
        tray_states = get_tray_status_lp3_clp(ip, ".1.3.6.1.2.1.43.18.1.1.8")
    elif ip == "172.27.21.95":
        tray_states = snmp_get(ip, ".1.3.6.1.4.1.11.2.3.9.1.1.2.8")
    else:
        tray_states = snmp_get(ip, ".1.3.6.1.4.1.11.2.3.9.1.1.2.8")

    toner_msg = "Unknown"
    if toner_levels:
        toner_msg = ", ".join([f"{t}%" if t >= 0 else "N/A" for t in toner_levels])

    tray_msg = "Unknown"
    if tray_states:
        if ip in ["172.27.16.5", "172.27.16.8"]:
            tray_msg = "; ".join([f"Tray1: {tray_states[0]}"])
        else:
            tray_msg = interpret_tray_states(ip, tray_states)

    if tray_states and any(s == "Paper Empty" or s == 1 for s in tray_states):
        status_txt = "❌"
    elif toner_levels and any(t >= 0 and t < 10 for t in toner_levels):
        status_txt = "⚠️"
    else:
        status_txt = "✅"

    rows.append({
        "status": status_txt,
        "printer": name,
        "ip": ip,
        "tray_status": tray_msg,
        "toner_levels": toner_msg
    })

report = {"generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "printers": rows}

# Save JSON
with open("printer_status.json", "w") as f:
    json.dump(report, f, indent=4)

print("Report saved to printer_status.json")

# -------------------------
# Insert into MySQL DB
# -------------------------

try:
    conn = mysql.connector.connect(
        host="localhost",       # change to your MySQL host
        database="printers_db", # your DB name
        user="dbuser",          # your DB user
        password="dbpass"       # your DB password
    )
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS printer_status (
            id INT AUTO_INCREMENT PRIMARY KEY,
            generated_at DATETIME,
            printer VARCHAR(50),
            ip VARCHAR(50),
            status VARCHAR(10),
            tray_status TEXT,
            toner_levels TEXT
        )
    """)

    # Insert each printer record
    for p in rows:
        cur.execute("""
            INSERT INTO printer_status
            (generated_at, printer, ip, status, tray_status, toner_levels)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (report["generated_at"], p["printer"], p["ip"], p["status"], p["tray_status"], p["toner_levels"]))

    conn.commit()
    cur.close()
    conn.close()

    print("Report inserted into MySQL successfully.")

except Exception as e:
    print("Database insert failed:", e)
