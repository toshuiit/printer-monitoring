#!/usr/bin/env python3

import subprocess

import smtplib

from email.mime.text import MIMEText

from datetime import datetime

 

# Printer list (hostname:IP)

PRINTERS = {

    "lp2": "172.X.X.X",

    "lp3": "172.X.X.X",   # uses string OID

    "lp4": "172.X.X.X",

    "lp5": "172.X.X.X",  # uses HP private OID

    "clp": "172.X.X.X",   # uses string OID

}

 

COMMUNITY = "public"   # SNMP community string

 

# Email server configuration

EMAIL_ADDRESS = "dummy@cse.iitk.ac.in"

EMAIL_PASSWORD = "password"

SMTP_SERVER = "dummy.cse.iitk.ac.in"

SMTP_PORT = 587

EMAIL_TO = "user1@cse.iitk.ac.in"

 

# Default paper tray status codes (for integer OID printers)

TRAY_STATUS_MAP = {

    0: "Paper Available",

    1: "Paper Empty",

    -3: "Unknown/Not Installed"

}

 

def snmp_get(ip, oid):

    """Run snmpwalk for given OID and return values as list of ints."""

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

    """Check tray status for lp3 and clp (string-based)."""

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

    """Convert tray states to human-readable text for integer OID printers."""

    tray_statuses = []

    for i, s in enumerate(tray_states, start=1):

        status = TRAY_STATUS_MAP.get(s, f"Code{s}")

        tray_statuses.append(f"Tray{i}: {status}")

    return "; ".join(tray_statuses)

 

# Collect data

rows = []

for name, ip in PRINTERS.items():

    toner_levels = snmp_get(ip, ".1.3.6.1.2.1.43.11.1.1.9")

 

    # Tray status

    if ip in ["172.27.16.5", "172.27.16.8"]:  # clp & lp3

        tray_states = get_tray_status_lp3_clp(ip, ".1.3.6.1.2.1.43.18.1.1.8")

    elif ip == "172.27.21.95":  # lp5

        tray_states = snmp_get(ip, ".1.3.6.1.4.1.11.2.3.9.1.1.2.8")

    else:

        tray_states = snmp_get(ip, ".1.3.6.1.4.1.11.2.3.9.1.1.2.8")

 

    # Interpret toner

    toner_msg = "Unknown"

    if toner_levels:

        toner_msg = ", ".join([f"{t}%" if t >= 0 else "N/A" for t in toner_levels])

 

    # Interpret tray states

    tray_msg = "Unknown"

    if tray_states:

        if ip in ["172.27.16.5", "172.27.16.8"]:

            tray_msg = "; ".join([f"Tray1: {tray_states[0]}"])

        else:

            tray_msg = interpret_tray_states(ip, tray_states)

 

    # Decide overall status

    if tray_states and any(s == "Paper Empty" or s == 1 for s in tray_states):

        status_txt = "❌"

    elif toner_levels and any(t >= 0 and t < 10 for t in toner_levels):  # low toner <10%

        status_txt = "⚠️"

    else:

        status_txt = "✅"

 

    rows.append([status_txt, name, ip, tray_msg, toner_msg])

 

# Build aligned text (no borders)

header = ["Status", "Printer", "IP", "Tray Status", "Toner Levels"]

col_widths = [max(len(str(row[i])) for row in ([header] + rows)) for i in range(len(header))]

 

def format_row(row):

    return "  ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))

 

table_lines = [f"Printer Status Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]

table_lines.append(format_row(header))

table_lines.append("-" * sum(col_widths) + "-" * (2 * (len(header) - 1)))

for row in rows:

    table_lines.append(format_row(row))

 

REPORT = "\n".join(table_lines)

 

# Create email

msg = MIMEText(REPORT, "plain")

msg["Subject"] = "🖨️ Printer Status Report"

msg["From"] = EMAIL_ADDRESS

msg["To"] = EMAIL_TO

 

# Send email

try:

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:

        server.starttls()

        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        server.sendmail(EMAIL_ADDRESS, [EMAIL_TO], msg.as_string())

    print("Report sent successfully.")

except Exception as e:

    print("Failed to send email:", e)
