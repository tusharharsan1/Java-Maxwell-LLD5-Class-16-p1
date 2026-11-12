"""Tests for app/move_ids.py (standard library only). Run them from the folder that holds `app/` and `tests/`:

    python -m unittest -v          (pytest works too)

The tests check what the README says: every row is kept, every row gets its own new 32-character id made by make_id(),
every link is kept (and a product with no category stays with none), the old tables are thrown away and the new ones
take their names, and the four numbers of `numbers(conn)` are the same before and after."""
import inspect
import os
import random
import re
import sqlite3
import tempfile
import unittest
from unittest import mock

from app import move_ids
from app.move_ids import make_id, numbers, upgrade

ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
OLD_TABLES = """
CREATE TABLE category (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE product (id INTEGER PRIMARY KEY, title TEXT NOT NULL, category_id INTEGER REFERENCES category (id));
"""
# The shop of try_it.py: ids are 1, 2, 7 on purpose (not 1, 2, 3), and one product has no category.
TRY_IT_CATEGORIES = [(1, "watches"), (2, "sunglasses"), (7, "mascara")]
TRY_IT_PRODUCTS = [
    (1, "Gold Watch", 1), (2, "Silver Watch", 1), (3, "Sport Watch", 1),
    (4, "Aviator Glasses", 2), (5, "Round Glasses", 2), (6, "Mystery Box", None),
]
# Fewer names than categories, so that names repeat: two categories can have the same name.
NAMES = ["watches", "sunglasses", "mascara", "bags", "shoes", "perfume", "belts", "wallets"]
# (categories, products): shops of 0, 2, 9 and 500 rows
SIZES = [(0, 0), (1, 1), (3, 6), (40, 460)]
# The state of the connection: foreign keys checked (like try_it.py) and not checked (the default of sqlite3).
FOREIGN_KEYS = [True, False]


def make_shop(categories, products, foreign_keys=True, path=":memory:"):
    """A shop in the OLD shape (numbers as ids). categories: [(id, name)]. products: [(id, title, category id or None)]."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = " + ("ON" if foreign_keys else "OFF"))
    conn.executescript(OLD_TABLES)
    conn.executemany("INSERT INTO category (id, name) VALUES (?, ?)", categories)
    conn.executemany("INSERT INTO product (id, title, category_id) VALUES (?, ?, ?)", products)
    conn.commit()
    return conn


def random_shop(seed, category_count, product_count):
    """A new shop for each seed, so that no answer can be written into the code. Ids are not 1, 2, 3...: they are any numbers.
    About one product in seven has no category, and some categories get no product at all."""
    rng = random.Random(seed)
    category_ids = rng.sample(range(1, 100000), category_count)
    categories = [(category_id, rng.choice(NAMES)) for category_id in category_ids]
    products = []
    for number in range(1, product_count + 1):
        link = rng.choice(category_ids) if category_ids and rng.random() > 0.15 else None
        products.append((number * 3, "Product %04d" % number, link))
    return categories, products


def all_ids(conn):
    """Every id of the two tables, categories first."""
    return [row[0] for row in conn.execute("SELECT id FROM category")] + [row[0] for row in conn.execute("SELECT id FROM product")]


def table_names(conn):
    return [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def pairs(conn):
    """The (title, category name) pairs, sorted. A product with no category gives (title, None)."""
    return sorted(conn.execute("SELECT p.title, c.name FROM product p LEFT JOIN category c ON c.id = p.category_id").fetchall(),
                  key=lambda pair: (pair[0], pair[1] or ""))


class ShopTestCase(unittest.TestCase):
    """Helpers for the suites below."""

    def shop(self, categories, products, foreign_keys=True):
        conn = make_shop(categories, products, foreign_keys)
        self.addCleanup(conn.close)
        return conn

    def assert_links_kept(self, conn, categories, products):
        """Every product points to the NEW id of the category it pointed to before. No category is merged with another one
        (even if they have the same name), and no category is split in two."""
        name_of = dict(categories)
        old_link_of = {title: link for _id, title, link in products}
        rows = conn.execute(
            "SELECT p.title, p.category_id, c.id, c.name FROM product p LEFT JOIN category c ON c.id = p.category_id"
        ).fetchall()
        self.assertEqual(len(rows), len(products), "the number of products changed")
        new_id_of_old = {}
        for title, link, found_id, found_name in rows:
            old_link = old_link_of[title]
            if old_link is None:
                self.assertIsNone(link, f"{title} had no category, and now it points to {link!r}")
                continue
            self.assertIsNotNone(link, f"{title} lost its category")
            self.assertIsNotNone(found_id, f"{title} points to {link!r}, and there is no category with that id")
            self.assertEqual(found_name, name_of[old_link], f"{title} points to the wrong category")
            self.assertEqual(new_id_of_old.setdefault(old_link, link), link, "one old category became two new ones")
        self.assertEqual(len(set(new_id_of_old.values())), len(new_id_of_old), "two old categories became one new one")


# ======================================================================================================================
# The lines that are already finished must still be there.
# ======================================================================================================================
class FinishedPartsTests(unittest.TestCase):
    def test_the_names_of_the_functions_and_their_parameters_are_unchanged(self):
        """upgrade(conn), numbers(conn) and make_id() keep their names and their parameters."""
        self.assertEqual(list(inspect.signature(upgrade).parameters), ["conn"])
        self.assertEqual(list(inspect.signature(numbers).parameters), ["conn"])
        self.assertEqual(list(inspect.signature(make_id).parameters), [])

    def test_the_two_new_tables_keep_their_names(self):
        """The new tables are called category_new and product_new, and they have text ids."""
        self.assertIn("category_new", move_ids.CREATE_CATEGORY_NEW)
        self.assertIn("product_new", move_ids.CREATE_PRODUCT_NEW)
        self.assertIn("TEXT", move_ids.CREATE_CATEGORY_NEW)
        self.assertIn("TEXT", move_ids.CREATE_PRODUCT_NEW)

    def test_make_id_makes_a_32_character_version_7_id(self):
        """make_id gives 32 small hex characters, the 13th is 7 (the version), and no id comes twice."""
        made = [make_id() for _ in range(2000)]
        for text in made[:50]:
            self.assertRegex(text, ID_PATTERN)
            self.assertEqual(text[12], "7")
            self.assertIn(text[16], "89ab")
        self.assertEqual(len(set(made)), len(made))

    def test_numbers_gives_the_numbers_of_the_readme(self):
        """On the shop of try_it.py, numbers gives (6 products, 3 categories, 5 linked pairs, fingerprint 8242356370)."""
        conn = make_shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        self.addCleanup(conn.close)
        self.assertEqual(numbers(conn), (6, 3, 5, 8242356370))


# ======================================================================================================================
# The check with numbers: nothing is lost, nothing is moved.
# ======================================================================================================================
class NumbersStayTests(ShopTestCase):
    def test_the_four_numbers_are_the_same_on_the_shop_of_try_it(self):
        """Products, categories, linked pairs and the fingerprint: the same before and after."""
        for foreign_keys in FOREIGN_KEYS:
            with self.subTest(foreign_keys=foreign_keys):
                conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS, foreign_keys)
                before = numbers(conn)
                upgrade(conn)
                self.assertEqual(numbers(conn), before)
                self.assertEqual(before, (6, 3, 5, 8242356370))

    def test_the_four_numbers_are_the_same_on_shops_of_every_size(self):
        """Shops with 0, 2, 9 and 500 rows, with any numbers as ids: the four numbers do not change."""
        for category_count, product_count in SIZES:
            for foreign_keys in FOREIGN_KEYS:
                with self.subTest(categories=category_count, products=product_count, foreign_keys=foreign_keys):
                    categories, products = random_shop(category_count * 7 + product_count, category_count, product_count)
                    conn = self.shop(categories, products, foreign_keys)
                    before = numbers(conn)
                    upgrade(conn)
                    self.assertEqual(numbers(conn), before)
                    self.assertEqual(before[0], product_count)
                    self.assertEqual(before[1], category_count)

    def test_the_fingerprint_would_notice_a_product_in_the_wrong_category(self):
        """A shop with one product moved to another category has another fingerprint. So 'the same fingerprint' means something."""
        moved = [(i, t, 2 if t == "Gold Watch" else link) for i, t, link in TRY_IT_PRODUCTS]
        conn_a = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        conn_b = self.shop(TRY_IT_CATEGORIES, moved)
        self.assertEqual(numbers(conn_a)[:3], numbers(conn_b)[:3])
        self.assertNotEqual(numbers(conn_a)[3], numbers(conn_b)[3])


# ======================================================================================================================
# Task 1: the new ids.
# ======================================================================================================================
class NewIdsTests(ShopTestCase):
    def test_every_id_has_32_small_hex_characters(self):
        """Every id of both tables has 32 characters from 0-9 and a-f, and it is text."""
        for foreign_keys in FOREIGN_KEYS:
            with self.subTest(foreign_keys=foreign_keys):
                conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS, foreign_keys)
                upgrade(conn)
                ids = all_ids(conn)
                self.assertEqual(len(ids), 9)
                for one_id in ids:
                    self.assertIsInstance(one_id, str)
                    self.assertRegex(one_id, ID_PATTERN)
                for table in ("category", "product"):
                    kinds = {row[0] for row in conn.execute(f"SELECT typeof(id) FROM {table}")}
                    self.assertEqual(kinds, {"text"})

    def test_all_the_ids_are_different(self):
        """No id is used twice, in one table or in the two tables together (500 rows)."""
        categories, products = random_shop(11, 40, 460)
        conn = self.shop(categories, products)
        upgrade(conn)
        ids = all_ids(conn)
        self.assertEqual(len(ids), 500)
        self.assertEqual(len(set(ids)), 500)

    def test_the_new_ids_are_not_the_old_numbers(self):
        """An old number, even with zeros in front of it (such as 000...0007, which has 32 characters), is not a new id."""
        categories, products = random_shop(12, 5, 20)
        conn = self.shop(categories, products)
        old_numbers = {str(i) for i, _ in categories} | {str(i) for i, _t, _l in products}
        upgrade(conn)
        for one_id in all_ids(conn):
            self.assertNotIn(one_id.lstrip("0"), old_numbers)
            self.assertNotIn(one_id, old_numbers)

    def test_every_id_is_a_version_7_id_from_make_id(self):
        """The 13th character of every id is 7: they come from make_id(), not from uuid4() or from a counter."""
        categories, products = random_shop(13, 10, 60)
        conn = self.shop(categories, products)
        upgrade(conn)
        for one_id in all_ids(conn):
            self.assertEqual(one_id[12], "7", one_id)

    def test_make_id_is_really_used_for_every_row(self):
        """Replace make_id by a function that counts: every id in the two tables is one that it made (and there are no others)."""
        categories, products = random_shop(14, 6, 30)
        conn = self.shop(categories, products)
        made = []

        def counting_make_id():
            made.append("000000000000" + "7000" + "8000" + "%012x" % (len(made) + 1))  # 32 characters, a different one each time
            return made[-1]

        with mock.patch.object(move_ids, "make_id", side_effect=counting_make_id):
            upgrade(conn)
        ids = all_ids(conn)
        self.assertEqual(len(ids), 36)
        self.assertEqual(len(set(ids)), 36)
        self.assertTrue(set(ids) <= set(made), "some ids were not made by make_id")


# ======================================================================================================================
# Task 1: the links.
# ======================================================================================================================
class LinksTests(ShopTestCase):
    def test_every_link_is_kept_on_the_shop_of_try_it(self):
        """Gold, Silver and Sport Watch share one category, the two glasses share another one, and each name is right."""
        conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        upgrade(conn)
        self.assert_links_kept(conn, TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        self.assertEqual(
            pairs(conn),
            sorted([("Gold Watch", "watches"), ("Silver Watch", "watches"), ("Sport Watch", "watches"),
                    ("Aviator Glasses", "sunglasses"), ("Round Glasses", "sunglasses"), ("Mystery Box", None)],
                   key=lambda pair: (pair[0], pair[1] or "")),
        )

    def test_every_link_is_kept_on_other_shops(self):
        """Many shops with any numbers as ids, with names that repeat: every product still has its own category."""
        for seed in range(1, 13):
            for foreign_keys in FOREIGN_KEYS:
                with self.subTest(seed=seed, foreign_keys=foreign_keys):
                    categories, products = random_shop(seed, 3 + seed * 3, 5 + seed * 12)
                    conn = self.shop(categories, products, foreign_keys)
                    upgrade(conn)
                    self.assert_links_kept(conn, categories, products)

    def test_two_products_of_one_category_share_the_new_id_of_that_category(self):
        """The two watches had the same category id before, so they have the same new category id after."""
        conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        upgrade(conn)
        link_of = dict(conn.execute("SELECT title, category_id FROM product"))
        self.assertEqual(link_of["Gold Watch"], link_of["Silver Watch"])
        self.assertEqual(link_of["Gold Watch"], link_of["Sport Watch"])
        self.assertEqual(link_of["Aviator Glasses"], link_of["Round Glasses"])
        self.assertNotEqual(link_of["Gold Watch"], link_of["Aviator Glasses"])

    def test_a_product_with_no_category_stays_with_no_category(self):
        """category_id is None before and None after: not an empty text, not the text 'None', not a made-up id."""
        conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        upgrade(conn)
        row = conn.execute("SELECT category_id, typeof(category_id) FROM product WHERE title = 'Mystery Box'").fetchone()
        self.assertEqual(row, (None, "null"))

    def test_products_with_no_category_survive_when_there_are_no_categories_at_all(self):
        """No category in the shop, two products with no category: both are still there, still with no category."""
        conn = self.shop([], [(1, "Box", None), (2, "Bag", None)])
        upgrade(conn)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM category").fetchone()[0], 0)
        self.assertEqual(sorted(conn.execute("SELECT title, category_id FROM product")), [("Bag", None), ("Box", None)])

    def test_a_category_with_no_product_stays(self):
        """Categories that nobody points to are still there, with their names."""
        categories = [(1, "empty one"), (2, "full one"), (3, "empty two")]
        conn = self.shop(categories, [(1, "Box", 2)])
        upgrade(conn)
        self.assertEqual(sorted(row[0] for row in conn.execute("SELECT name FROM category")), ["empty one", "empty two", "full one"])
        self.assert_links_kept(conn, categories, [(1, "Box", 2)])

    def test_two_categories_with_the_same_name_stay_two_categories(self):
        """The link goes by the old id, not by the name: 'bags' twice gives two different new categories."""
        categories = [(5, "bags"), (9, "bags"), (20, "shoes")]
        products = [(1, "Tote", 5), (2, "Clutch", 9), (3, "Satchel", 5), (4, "Boot", 20)]
        conn = self.shop(categories, products)
        upgrade(conn)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM category").fetchone()[0], 3)
        self.assert_links_kept(conn, categories, products)
        link_of = dict(conn.execute("SELECT title, category_id FROM product"))
        self.assertEqual(link_of["Tote"], link_of["Satchel"])
        self.assertNotEqual(link_of["Tote"], link_of["Clutch"])

    def test_two_products_with_the_same_title_are_two_products(self):
        """The same title twice (in different categories) gives two products, each in its own category."""
        categories = [(1, "watches"), (2, "sunglasses")]
        products = [(1, "Classic", 1), (2, "Classic", 2), (3, "Classic", None)]
        conn = self.shop(categories, products)
        before = numbers(conn)
        upgrade(conn)
        self.assertEqual(numbers(conn), before)
        self.assertEqual(pairs(conn), [("Classic", None), ("Classic", "sunglasses"), ("Classic", "watches")])

    def test_old_ids_that_are_not_small_numbers_work_too(self):
        """Old ids such as 0, 2147483647 and 9223372036854775807 (the biggest number of SQLite) are mapped like any other."""
        categories = [(0, "zero"), (2147483647, "int max"), (9223372036854775807, "biggest")]
        products = [(0, "a", 0), (2147483647, "b", 2147483647), (9223372036854775807, "c", 9223372036854775807), (5, "d", None)]
        conn = self.shop(categories, products)
        upgrade(conn)
        self.assert_links_kept(conn, categories, products)
        self.assertEqual(len(set(all_ids(conn))), 7)

    def test_titles_and_names_are_unchanged(self):
        """The texts are copied as they are: spaces, capital letters, quotes and letters of other languages."""
        categories = [(1, "  spaced  "), (2, "O'Neil's Corner"), (3, "café ☕"), (4, "")]
        products = [(1, 'The "Big" One', 1), (2, "100% cotton", 2), (3, "ショップ", 3), (4, "", 4), (5, "x'); DROP TABLE product; --", None)]
        conn = self.shop(categories, products)
        upgrade(conn)
        self.assertEqual(sorted(row[0] for row in conn.execute("SELECT name FROM category")), sorted(name for _i, name in categories))
        self.assertEqual(sorted(row[0] for row in conn.execute("SELECT title FROM product")), sorted(title for _i, title, _l in products))
        self.assert_links_kept(conn, categories, products)

    def test_titles_and_names_are_not_swapped(self):
        """category.name holds the names and product.title holds the titles (not the other way round)."""
        conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        upgrade(conn)
        self.assertEqual(sorted(row[0] for row in conn.execute("SELECT name FROM category")), ["mascara", "sunglasses", "watches"])
        self.assertIn("Gold Watch", [row[0] for row in conn.execute("SELECT title FROM product")])


# ======================================================================================================================
# Task 2: the old tables are thrown away, and the new ones take their names.
# ======================================================================================================================
class TablesAfterTests(ShopTestCase):
    def test_only_category_and_product_are_left(self):
        """No table with `_new` in its name is left, and no other table."""
        for foreign_keys in FOREIGN_KEYS:
            with self.subTest(foreign_keys=foreign_keys):
                conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS, foreign_keys)
                upgrade(conn)
                self.assertEqual(table_names(conn), ["category", "product"])

    def test_the_tables_have_text_ids(self):
        """The id of category and of product is TEXT now (not INTEGER), and the other columns are where they were."""
        conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        upgrade(conn)
        category = [(row[1], row[2].upper(), row[5]) for row in conn.execute("PRAGMA table_info(category)")]
        product = [(row[1], row[2].upper(), row[5]) for row in conn.execute("PRAGMA table_info(product)")]
        self.assertEqual(category, [("id", "TEXT", 1), ("name", "TEXT", 0)])
        self.assertEqual(product, [("id", "TEXT", 1), ("title", "TEXT", 0), ("category_id", "TEXT", 0)])

    def test_the_old_tables_are_gone_so_no_old_number_is_left(self):
        """No row of the old shape is left: no id that is a number, in either table."""
        conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS)
        upgrade(conn)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM category WHERE typeof(id) != 'text'").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM product WHERE typeof(id) != 'text'").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM product WHERE typeof(category_id) = 'integer'").fetchone()[0], 0)

    def test_the_foreign_key_points_at_category_and_no_link_is_broken(self):
        """product.category_id still has a FOREIGN KEY to category(id), and `PRAGMA foreign_key_check` finds nothing wrong."""
        if sqlite3.sqlite_version_info < (3, 26, 0):
            self.skipTest("this SQLite is older than 3.26 and does not carry the new name into the FOREIGN KEY")
        for foreign_keys in FOREIGN_KEYS:
            with self.subTest(foreign_keys=foreign_keys):
                categories, products = random_shop(21, 12, 80)
                conn = self.shop(categories, products, foreign_keys)
                upgrade(conn)
                links = [(row[2], row[3], row[4]) for row in conn.execute("PRAGMA foreign_key_list(product)")]
                self.assertEqual(links, [("category", "category_id", "id")])
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_the_new_foreign_key_is_checked_when_the_connection_checks_foreign_keys(self):
        """After the change, a product that points to a category that does not exist is refused (the link is a real FOREIGN KEY)."""
        if sqlite3.sqlite_version_info < (3, 26, 0):
            self.skipTest("this SQLite is older than 3.26 and does not carry the new name into the FOREIGN KEY")
        conn = self.shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS, foreign_keys=True)
        upgrade(conn)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO product (id, title, category_id) VALUES ('x', 'Ghost', 'nobody')")

    def test_the_child_is_dropped_before_the_parent_so_no_foreign_key_error_is_raised(self):
        """With foreign keys ON and many links, upgrade ends without an error (dropping `category` first would stop it)."""
        categories, products = random_shop(22, 20, 200)
        conn = self.shop(categories, products, foreign_keys=True)
        try:
            upgrade(conn)
        except sqlite3.IntegrityError as exc:
            self.fail(f"upgrade stopped with a foreign key error: {exc}")
        self.assertEqual(table_names(conn), ["category", "product"])

    def test_the_change_is_saved_so_that_another_connection_sees_it(self):
        """upgrade ends with a commit: a second connection to the same file sees the two new tables with their 32-character ids."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "shop.db")
            first = make_shop(TRY_IT_CATEGORIES, TRY_IT_PRODUCTS, path=path)
            self.addCleanup(first.close)
            upgrade(first)
            second = sqlite3.connect(path, timeout=0.2)
            self.addCleanup(second.close)
            try:
                self.assertEqual(table_names(second), ["category", "product"])
                ids = all_ids(second)
            except sqlite3.OperationalError as exc:
                self.fail(f"another connection cannot read the shop (is the change committed?): {exc}")
            self.assertEqual(len(ids), 9)
            self.assertTrue(all(ID_PATTERN.match(one_id) for one_id in ids))


if __name__ == "__main__":
    unittest.main(verbosity=2)
