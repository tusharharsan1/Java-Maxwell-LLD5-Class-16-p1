"""Run this file to see what your migration does:   python try_it.py
It builds a small shop in memory (the old tables, with numbers as ids), runs `upgrade`, and prints the numbers before and after.
Nothing is saved on disk, and nothing needs the internet. Do not change this file."""
import sqlite3

try:
    from app.move_ids import numbers, upgrade
except Exception as exc:  # a mistake in the file above would stop the import
    raise SystemExit(f"a file has a problem -> {type(exc).__name__}: {exc}")

conn = sqlite3.connect(":memory:")
conn.execute("PRAGMA foreign_keys = ON")  # SQLite checks the links between tables only when this is ON
conn.executescript(
    """
    CREATE TABLE category (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
    CREATE TABLE product (id INTEGER PRIMARY KEY, title TEXT NOT NULL, category_id INTEGER REFERENCES category (id));
    INSERT INTO category (id, name) VALUES (1, 'watches'), (2, 'sunglasses'), (7, 'mascara');
    INSERT INTO product (id, title, category_id) VALUES
        (1, 'Gold Watch', 1), (2, 'Silver Watch', 1), (3, 'Sport Watch', 1),
        (4, 'Aviator Glasses', 2), (5, 'Round Glasses', 2), (6, 'Mystery Box', NULL);
    """
)


def show(label, make_text):
    try:
        print(f"  {label:<40}: {make_text()}")
    except Exception as exc:
        print(f"  {label:<40}: something is wrong -> {type(exc).__name__}: {exc}")


def text_numbers():
    products, categories, pairs, fingerprint = numbers(conn)
    return f"products={products} categories={categories} linked pairs={pairs} fingerprint={fingerprint}"


print("Before the change")
show("the numbers", text_numbers)
before = numbers(conn)

print("Task 1 and Task 2: run upgrade")
try:
    upgrade(conn)
    print("  upgrade ran without an error")
except Exception as exc:
    print(f"  upgrade stopped -> {type(exc).__name__}: {exc}")

print("After the change")
show("the numbers", text_numbers)
show("same numbers as before", lambda: numbers(conn) == before)
show("tables", lambda: [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")])
show("ids have 32 characters", lambda: all(len(str(r[0])) == 32 for r in conn.execute("SELECT id FROM category UNION ALL SELECT id FROM product")))
show("ids are all different", lambda: len({r[0] for r in conn.execute("SELECT id FROM category UNION ALL SELECT id FROM product")}) == 9)
show("Mystery Box still has no category", lambda: conn.execute("SELECT category_id FROM product WHERE title = 'Mystery Box'").fetchone()[0] is None)
show("links to a category that is missing", lambda: conn.execute("PRAGMA foreign_key_check").fetchall())
