import json
from typing import Optional
import os
from mcp.server.fastmcp import FastMCP

from . import db

mcp = FastMCP("slt-customer-service")


@mcp.tool()
def get_broadband_packages(
    max_price: Optional[float] = None,
    min_data: Optional[int] = None,
) -> dict:
    """Look up SLT broadband packages, optionally filtered by maximum price (LKR) or minimum data (GB)."""
    sql = "SELECT id, name, data_limit_gb, price_lkr, speed_mbps FROM packages WHERE 1=1"
    params: list = []
    if max_price is not None:
        sql += " AND price_lkr <= ?"
        params.append(max_price)
    if min_data is not None:
        sql += " AND data_limit_gb >= ?"
        params.append(min_data)
    sql += " ORDER BY price_lkr"

    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
    return {"ok": True, "packages": rows}

@mcp.tool()
def check_account_balance(phone_number: str, nic: str) -> dict:
    """Look up a customer's outstanding bill and remaining data. Requires phone number and NIC."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT c.name, c.outstanding_bill_lkr, c.remaining_data_gb, p.name AS package_name "
            "FROM customers c LEFT JOIN packages p ON p.id = c.current_package_id "
            "WHERE c.phone_number = ? AND c.nic = ?",
            (phone_number, nic.upper()),
        )
        row = cur.fetchone()
    if not row:
        return {"ok": False, "error": f"Authentication failed for {phone_number}. Incorrect NIC or phone number."}
    
    return {
        "ok": True,
        "name": row["name"],
        "outstanding_bill_lkr": row["outstanding_bill_lkr"],
        "remaining_data_gb": row["remaining_data_gb"],
        "current_package": row["package_name"],
    }

@mcp.tool()
def get_payment_history(phone_number: str, nic: str, limit: int = 5) -> dict:
    """Return the most recent payments. Requires phone number and NIC."""
    with db.cursor() as cur:
        # First authorize
        cur.execute("SELECT 1 FROM customers WHERE phone_number = ? AND nic = ?", (phone_number, nic.upper()))
        if not cur.fetchone():
            return {"ok": False, "error": "Authentication failed. Incorrect NIC or phone number."}
            
        cur.execute(
            "SELECT amount_lkr, method, reference, paid_at FROM payments "
            "WHERE phone_number = ? ORDER BY paid_at DESC LIMIT ?",
            (phone_number, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    if not rows:
        return {"ok": True, "payments": [], "note": "No payments on record."}
    return {"ok": True, "payments": rows}

@mcp.tool()
def purchase_data_addon(phone_number: str, nic: str, addon_code: str) -> dict:
    """Buy a data add-on. Requires phone number, NIC, and addon_code."""
    with db.cursor() as cur:
        # First authorize and get remaining data
        cur.execute("SELECT remaining_data_gb FROM customers WHERE phone_number = ? AND nic = ?", (phone_number, nic.upper()))
        cust = cur.fetchone()
        if not cust:
            return {"ok": False, "error": "Authentication failed. Incorrect NIC or phone number."}
            
        cur.execute("SELECT data_gb, name, price_lkr FROM addons WHERE addon_code = ?", (addon_code,))
        addon = cur.fetchone()
        if not addon:
            return {"ok": False, "error": f"Unknown addon: {addon_code}"}
        
        new_data = cust["remaining_data_gb"] + addon["data_gb"]
        cur.execute(
            "UPDATE customers SET remaining_data_gb = ? WHERE phone_number = ?",
            (new_data, phone_number),
        )
        cur.execute(
            "INSERT INTO transactions (phone_number, action, details) VALUES (?, ?, ?)",
            (phone_number, "addon_purchase",
             json.dumps({"addon_code": addon_code, "data_gb": addon["data_gb"],
                         "price_lkr": addon["price_lkr"]})),
        )
    return {
        "ok": True,
        "addon": addon["name"],
        "added_gb": addon["data_gb"],
        "new_remaining_gb": new_data,
        "price_lkr": addon["price_lkr"],
    }

@mcp.tool()
def list_data_addons() -> dict:
    """List all available SLT data add-on packs with prices and validity."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT addon_code, name, data_gb, price_lkr, validity_days FROM addons "
            "ORDER BY price_lkr"
        )
        rows = [dict(r) for r in cur.fetchall()]
    return {"ok": True, "addons": rows}


@mcp.tool()
def check_outage(district: str, service_type: str = "fibre") -> dict:
    """Look up known network outages in a district. service_type is 'fibre', 'mobile_data', or 'voice'."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT district, area, service_type, status, started_at, eta_resolution "
            "FROM outages WHERE LOWER(district) = LOWER(?) AND service_type = ? "
            "AND status != 'resolved' ORDER BY started_at",
            (district, service_type),
        )
        rows = [dict(r) for r in cur.fetchall()]
    if not rows:
        return {"ok": True, "outages": [], "note": f"No active {service_type} outages in {district}."}
    return {"ok": True, "outages": rows}


@mcp.tool()
def report_network_fault(phone_number: str, issue_description: str) -> dict:
    """Create a network fault ticket for a customer. Requires phone number and a short issue description."""
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO fault_tickets (phone_number, issue_description) VALUES (?, ?)",
            (phone_number, issue_description),
        )
        ticket_id = cur.lastrowid
    return {"ok": True, "ticket_id": ticket_id, "status": "open"}


@mcp.tool()
def record_payment(
    phone_number: str,
    amount_lkr: float,
    method: str,
    reference: Optional[str] = None,
) -> dict:
    """Record a bill payment. method must be 'card', 'ezcash', 'bank_transfer', or 'reload_card'. Confirm amount with the caller before calling this."""
    if method not in {"card", "ezcash", "bank_transfer", "reload_card"}:
        return {"ok": False, "error": f"Unsupported payment method: {method}"}
    with db.cursor() as cur:
        cur.execute("SELECT outstanding_bill_lkr FROM customers WHERE phone_number = ?", (phone_number,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": f"No account found for {phone_number}"}
        new_balance = max(0.0, row["outstanding_bill_lkr"] - amount_lkr)
        cur.execute(
            "INSERT INTO payments (phone_number, amount_lkr, method, reference) VALUES (?, ?, ?, ?)",
            (phone_number, amount_lkr, method, reference),
        )
        payment_id = cur.lastrowid
        cur.execute(
            "UPDATE customers SET outstanding_bill_lkr = ? WHERE phone_number = ?",
            (new_balance, phone_number),
        )
    return {
        "ok": True,
        "payment_id": payment_id,
        "amount_lkr": amount_lkr,
        "new_balance_lkr": new_balance,
    }

@mcp.tool()
def change_package(phone_number: str, new_package_id: int) -> dict:
    """Switch a customer to a new broadband package. new_package_id comes from get_broadband_packages. Confirm with the caller before calling this."""
    with db.cursor() as cur:
        cur.execute("SELECT id, name, data_limit_gb, price_lkr FROM packages WHERE id = ?", (new_package_id,))
        pkg = cur.fetchone()
        if not pkg:
            return {"ok": False, "error": f"Unknown package id: {new_package_id}"}
        cur.execute("SELECT phone_number FROM customers WHERE phone_number = ?", (phone_number,))
        if not cur.fetchone():
            return {"ok": False, "error": f"No account found for {phone_number}"}
        cur.execute(
            "UPDATE customers SET current_package_id = ?, remaining_data_gb = ? "
            "WHERE phone_number = ?",
            (new_package_id, pkg["data_limit_gb"], phone_number),
        )
        cur.execute(
            "INSERT INTO transactions (phone_number, action, details) VALUES (?, ?, ?)",
            (phone_number, "package_change",
             json.dumps({"new_package_id": new_package_id, "new_package_name": pkg["name"]})),
        )
    return {
        "ok": True,
        "new_package": pkg["name"],
        "data_limit_gb": pkg["data_limit_gb"],
        "monthly_price_lkr": pkg["price_lkr"],
    }

@mcp.tool()
def search_technical_faq(query: str) -> dict:
    """
    Search the SLT technical troubleshooting guide for solutions to hardware or network issues. 
    Pass a short string of keywords describing the user's issue (e.g., 'red light on router' or 'slow internet').
    """
    # Load the FAQ document
    file_path = os.path.join(os.path.dirname(__file__), "tech_faqs.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            faqs = json.load(f)
    except FileNotFoundError:
        return {"ok": False, "error": "FAQ document not found on the server."}

    query_words = set(query.lower().split())
    best_match = None
    highest_score = 0

    # Simple keyword matching algorithm
    for faq in faqs:
        score = sum(1 for keyword in faq["keywords"] if keyword in query_words or keyword in query.lower())
        if score > highest_score:
            highest_score = score
            best_match = faq

    if best_match:
        return {
            "ok": True,
            "issue_identified": best_match["issue"],
            "resolution_steps": best_match["resolution"]
        }
    
    return {
        "ok": True, 
        "note": "No specific troubleshooting steps found for that issue. Advise the customer to report a network fault."
    }

def main() -> None:
    db.bootstrap()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
