> **Where the files are:** this branch holds the finished solution in the `solution/` folder: the finished code, and the tests in `solution/tests/`. Every path below (such as `app/move_ids.py` and `try_it.py`) is inside `solution/`. Open a terminal in `solution/` to run the commands. To run the tests, type `python -m unittest -v` (or `pytest`) there. The starter files with the TODO notes are on the `main` branch, in `base/`.

# Move the Ids at ShopNest

## Problem Statement
ShopNest keeps its products and its categories in two tables. Today every row has a **growing number** as its id: 1, 2, 3. The shop wants **long ids** of 32 characters, such as `01a1ce9d8faa7dfeb2c87c1f26f542e2`, because a number column can run out, a number can be guessed, and two databases that count on their own give the same number twice. The change must keep **every row** and **every link** between a product and its category. In class you did this change in MySQL, in three steps: **bring the new in**, **throw the old away**, and **let the new take the old names**. Now you do the same three steps in **SQLite**, a small database that lives inside Python, so there is nothing to install and nothing to start. SQLite cannot change the type of an id in place, so you build two new tables next to the old ones, fill them, and then swap them. You need about 9 lines of code, in 2 small tasks. There is no server, no internet and no key.

## Requirements
### The two tables
| Table | Before | After |
|---|---|---|
| `category` | `id` is a number, and `name` | `id` is text of 32 characters, and `name` |
| `product` | `id` is a number, `title`, and `category_id` (a number, or `None`) | `id` is text of 32 characters, `title`, and `category_id` (text, or `None`) |

### The three steps
| Step | What happens | Written already? |
|---|---|---|
| 1. Bring the new in | The tables `category_new` and `product_new` are made, empty | **yes** (the first lines of `upgrade`) |
| 1. Bring the new in | The new tables are filled: a new id for every row, and every link copied | **no** (Task 1) |
| 2. Throw the old away | The old tables `product` and `category` are dropped | **no** (Task 2) |
| 3. The new takes the old name | `category_new` becomes `category`, and `product_new` becomes `product` | **no** (Task 2) |

### The rules
- **Keep every row.** The same number of products and categories, with the same titles and names.
- **Make the new ids with `make_id()`.** Every row, in both tables, gets its own new id.
- **Keep every link.** A product must point to the **new id** of the same category it pointed to before. In the old tables the link is the old number, and the new tables need the new id. That is why the notebook `new_ids` remembers *old id -> new id*.
- **A product with no category stays with no category.** Its `category_id` is `None` before the change and `None` after it.
- **The order matters.** A product points to a category, so the product (the child) is dropped first, and then the category. The other order stops with `FOREIGN KEY constraint failed`.
- **At the end there are two tables only:** `category` and `product`. No table with `_new` in its name is left.
- **Check with numbers.** The finished function `numbers(conn)` gives four numbers: the products, the categories, the linked (product, category) pairs, and a *fingerprint* of the pairs. The fingerprint is one number made from every (title, category name) pair, so it changes if even one product points to another category. All four numbers must be **the same before and after** the change.

To achieve these requirements we need to do 2 things:
- **Task 1:** fill the two new tables: new ids, and the links.
- **Task 2:** throw the old tables away, and let the new tables take the old names.

## Instructions
1. Open `app/move_ids.py`. We need to finish one function, `upgrade`. It has two TODO notes (`TODO 1` and `TODO 2`). The first lines are already written: they make the two empty new tables and the empty notebook `new_ids`.
2. **Task 1** is `TODO 1`: the new ids and the links. **Task 2** is `TODO 2`: the drops and the renames.
3. Do not modify `make_id`, `numbers`, the names `category_new` and `product_new`, the names of the functions and their parameters, or the lines that are already written. Feel free to add new functions if required.
4. Run `python try_it.py` from this folder (the one that contains `app/` and `try_it.py`) to see what your code does. The ids are random, so `try_it.py` prints only what stays the same on every run. When both tasks are finished, you should see exactly this:
   ```
   Before the change
     the numbers                             : products=6 categories=3 linked pairs=5 fingerprint=8242356370
   Task 1 and Task 2: run upgrade
     upgrade ran without an error
   After the change
     the numbers                             : products=6 categories=3 linked pairs=5 fingerprint=8242356370
     same numbers as before                  : True
     tables                                  : ['category', 'product']
     ids have 32 characters                  : True
     ids are all different                   : True
     Mystery Box still has no category       : True
     links to a category that is missing     : []
   ```
   Before you start, `try_it.py` already runs: the numbers stay the same, the line `tables` shows two extra tables, and the lines about the ids say `False`.
5. Your code will be checked with the test file `tests/test_move_ids.py`. It checks the cases in the Requirements above and the rules, on small shops and on bigger ones. While you write your code, use `python try_it.py` (instruction 4) to check your work.
6. You do not need to install anything, and you do not need a server, the internet or a key. Only Python's standard library is used (`sqlite3` is a part of it). It works with Python 3.8 or newer.

