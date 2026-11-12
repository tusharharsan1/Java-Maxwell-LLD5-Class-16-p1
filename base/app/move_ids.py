import os
import sqlite3
import time
import uuid
import zlib
from typing import Tuple


# Already finished. It makes one new id: 32 characters, such as '01a1ce9d8faa7dfeb2c87c1f26f542e2'. It is your tool in Task 1.
def make_id() -> str:
    """A version 7 UUID without dashes: 6 bytes of time (in milliseconds), then 10 random bytes."""
    time_part = int(time.time() * 1000).to_bytes(6, "big")
    random_part = bytearray(os.urandom(10))
    random_part[0] = (random_part[0] & 0x0F) | 0x70  # the 13th character becomes 7: the version
    random_part[2] = (random_part[2] & 0x3F) | 0x80  # two marker bits that say: a standard UUID
    return uuid.UUID(bytes=time_part + bytes(random_part)).hex


# Already finished. The two NEW tables, with ids that are text. `upgrade` makes them empty, and you fill them.
CREATE_CATEGORY_NEW = "CREATE TABLE category_new (id TEXT NOT NULL PRIMARY KEY, name TEXT NOT NULL)"
CREATE_PRODUCT_NEW = (
    "CREATE TABLE product_new (id TEXT NOT NULL PRIMARY KEY, title TEXT NOT NULL, "
    "category_id TEXT REFERENCES category_new (id))"
)


def numbers(conn: sqlite3.Connection) -> Tuple[int, int, int, int]:
    """Already finished. The check with numbers: (products, categories, linked pairs, fingerprint of the pairs).
    The fingerprint changes if any product points to another category than before."""
    products = conn.execute("SELECT COUNT(*) FROM product").fetchone()[0]
    categories = conn.execute("SELECT COUNT(*) FROM category").fetchone()[0]
    pairs = conn.execute("SELECT p.title, c.name FROM product p JOIN category c ON c.id = p.category_id").fetchall()
    fingerprint = sum(zlib.crc32(f"{title}|{name}".encode()) for title, name in pairs)
    return products, categories, len(pairs), fingerprint


def upgrade(conn: sqlite3.Connection) -> None:
    """Change the ids of `category` and `product` from numbers to 32-character ids. Keep every row and every link."""
    conn.execute(CREATE_CATEGORY_NEW)  # Already finished: step 1 starts with two empty new tables.
    conn.execute(CREATE_PRODUCT_NEW)
    new_ids = {}  # Already finished: your notebook. It remembers: old category id -> new category id.
    # TODO 1 (Task 1): bring the new in. Fill the two new tables.
    #   - for each row of `category` (its id and its name): make a new id with make_id(), write "old id -> new id" in `new_ids`,
    #     and insert (the new id, the name) into `category_new`.
    #   - for each row of `product` (its title and its category_id): insert (a new id, the title, the NEW id of its category) into `product_new`.
    #     A product with no category (category_id is None) must stay with no category.
    # TODO 2 (Task 2): throw the old away, and let the new take the old names.
    #   - drop the table `product` first, and then the table `category` (a product points to a category, so the child goes first).
    #   - rename `category_new` to `category`, and `product_new` to `product`.
    conn.commit()  # Already finished.
