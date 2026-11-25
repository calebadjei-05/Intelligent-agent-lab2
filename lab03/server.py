import csv
import os
from datetime import date, timedelta
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pharmacy-stock")

# Data path from the manual. Run commands from inside lab03/ so it resolves.
DATA = "data/pharmacy_stock.csv"
FIELDS = ["item", "strength", "form", "quantity", "unit_price_ghs", "expiry_date"]


def load():
    with open(DATA, newline="") as f:
        return list(csv.DictReader(f))


def save(rows):
    # Write to a temporary file first, then replace, so a crash cannot leave half a CSV
    tmp = DATA + ".tmp"
    with open(tmp, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, DATA)


# ---------- Read tools (percepts / sensors) ----------

@mcp.tool()
def check_stock(item: str, strength: str = "") -> list[dict]:
    """Return stock rows whose item name contains item (and strength, if given).

    Use this to answer "Do we have X?" or "How many X are left?".
    item: medicine name or part of it, e.g. "amoxicillin".
    strength: optional strength, e.g. "500mg". Leave empty to see all strengths.
    Each row has item, strength, form, quantity (packs in stock), unit_price_ghs and expiry_date.
    An empty list means the item is not stocked."""
    rows = [r for r in load() if item.lower() in r["item"].lower()]
    if strength:
        rows = [r for r in rows if strength.lower() in r["strength"].lower()]
    return rows


@mcp.tool()
def search_items(query: str) -> list[dict]:
    """Search the stock list for query in the item name, strength or form.

    Use this when the user's wording is vague or you are not sure of the exact
    medicine name, e.g. "syrup", "inhaler", "cream" or "vitamin".
    It does not know what a medicine treats, only the words in the stock list.
    Returns the matching stock rows (an empty list if nothing matches)."""
    q = query.lower()
    return [r for r in load()
            if q in r["item"].lower() or q in r["strength"].lower() or q in r["form"].lower()]


@mcp.tool()
def list_expiring(days: int = 60) -> list[dict]:
    """List items whose expiry_date is within the next `days` days (default 60).

    Items that have already expired are included too, marked with days_left below 0.
    Rows are sorted by expiry date, soonest first. Each row gets an extra field days_left."""
    today = date.today()
    limit = today + timedelta(days=days)
    result = []
    for r in load():
        expiry = date.fromisoformat(r["expiry_date"])
        if expiry <= limit:
            row = dict(r)
            row["days_left"] = (expiry - today).days
            result.append(row)
    result.sort(key=lambda r: r["expiry_date"])
    return result


# ---------- Write tool (action / actuator) ----------

@mcp.tool()
def record_sale(item: str, strength: str, qty: int) -> str:
    """Record a sale and reduce the quantity in stock. This CHANGES the stock file.

    Only call this when the user clearly says a sale was made (e.g. "Sell 2 packs of ...").
    Do NOT call it just to answer a price or stock question.
    item: medicine name, e.g. "paracetamol". strength: exact strength, e.g. "500mg".
    qty: number of packs sold, a whole number above 0.
    The sale is refused (stock unchanged) if qty is not positive, the item is not
    found, more than one item matches, or there is not enough stock.
    Returns a message saying whether the sale was recorded."""
    # Safety checks: the server checks, it does not trust the model or the prompt
    if not isinstance(qty, int) or qty <= 0:
        return f"REFUSED: quantity must be a whole number above 0 (got {qty}). Stock unchanged."
    if not strength:
        return "REFUSED: give the strength (e.g. 500mg) so the right item is sold. Stock unchanged."

    rows = load()
    matches = [r for r in rows
               if item.lower() in r["item"].lower() and strength.lower() == r["strength"].lower()]
    if len(matches) == 0:
        return f"REFUSED: no item matches '{item}' with strength '{strength}'. Stock unchanged."
    if len(matches) > 1:
        names = ", ".join(r["item"] + " " + r["strength"] for r in matches)
        return f"REFUSED: more than one item matches ({names}). Be more specific. Stock unchanged."

    row = matches[0]
    in_stock = int(row["quantity"])
    if qty > in_stock:
        return (f"REFUSED: only {in_stock} packs of {row['item']} {row['strength']} in stock, "
                f"cannot sell {qty}. Stock unchanged.")

    row["quantity"] = str(in_stock - qty)
    save(rows)
    total = qty * float(row["unit_price_ghs"])
    return (f"SALE RECORDED: {qty} x {row['item']} {row['strength']} ({row['form']}) "
            f"for GHS {total:.2f}. {row['quantity']} packs left.")


if __name__ == "__main__":
    mcp.run()
