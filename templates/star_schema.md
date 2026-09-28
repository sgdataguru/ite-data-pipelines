# Star schema template

Use this template to sketch a star schema before you build one. Fill it in
by hand or in a text editor.

## Grain

> One row per ______ per ______ per ______

## Fact table

**Name:** `fct_______________`

**Grain:** _______________________________________________________

**Columns**

| Column | Type | Role | Notes |
|---|---|---|---|
| `______________` |  | Business key / surrogate key |  |
| `______________` |  | Foreign key |  |
| `______________` |  | Foreign key |  |
| `______________` |  | Foreign key |  |
| `______________` |  | Measure |  |
| `______________` |  | Measure |  |

## Dimension 1

**Name:** `dim_______________`

| Column | Type | Notes |
|---|---|---|
| `______________` |  |  |
| `______________` |  |  |
| `______________` |  |  |

**Needs history? (Type 1 / Type 2) and why:**
_________________________________________________________________

## Dimension 2

**Name:** `dim_______________`

| Column | Type | Notes |
|---|---|---|
| `______________` |  |  |
| `______________` |  |  |
| `______________` |  |  |

**Needs history? (Type 1 / Type 2) and why:**
_________________________________________________________________

## Dimension 3

**Name:** `dim_______________`

| Column | Type | Notes |
|---|---|---|
| `______________` |  |  |
| `______________` |  |  |
| `______________` |  |  |

**Needs history? (Type 1 / Type 2) and why:**
_________________________________________________________________

## Closing questions

- Which measures live in the fact table? _________________________________
- Which dimension would a HOD's report need history for? _________________
