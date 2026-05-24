# mcp_server.py
from mcp.server.fastmcp import FastMCP
import sqlite3

# 1. Initialize the MCP Server
mcp = FastMCP("SLT_Voice_Bot_Server")

# 2. Global DB connection
conn = sqlite3.connect('slt_mock_data.db', check_same_thread=False)
cursor = conn.cursor()

# 3. Define Tools using the @mcp.tool() decorator
@mcp.tool()
def get_broadband_packages(max_price: float = None, min_data: int = None) -> str:
    """Use this tool to look up SLT broadband packages based on price or data limits."""
    query = "SELECT name, data_limit_gb, price_lkr FROM packages WHERE 1=1"
    params = []
    
    if max_price:
        query += " AND price_lkr <= ?"
        params.append(max_price)
    if min_data:
        query += " AND data_limit_gb >= ?"
        params.append(min_data)
        
    cursor.execute(query, params)
    results = cursor.fetchall()
    return str(results) if results else "No packages found matching those criteria."

@mcp.tool()
def check_account_balance(phone_number: str) -> str:
    """Use this to check a customer's outstanding bill and remaining data balance."""
    cursor.execute("SELECT name, outstanding_bill_lkr, remaining_data_gb FROM customers WHERE phone_number = ?", (phone_number,))
    result = cursor.fetchone()
    if result:
        return f"Customer {result[0]} owes {result[1]} LKR and has {result[2]} GB data left."
    return f"No account found for phone number {phone_number}."

@mcp.tool()
def report_network_fault(phone_number: str, issue_description: str) -> str:
    """Use this to log a network issue, router problem, or internet outage."""
    cursor.execute(
        "INSERT INTO fault_tickets (phone_number, issue_description, status) VALUES (?, ?, 'OPEN')", 
        (phone_number, issue_description)
    )
    conn.commit()
    return f"Successfully created support ticket #{cursor.lastrowid}."

if __name__ == "__main__":
    # Runs the server using standard input/output (stdio)
    mcp.run()