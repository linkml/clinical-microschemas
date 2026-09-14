# Schema Simplification Suggestions

This document captures suggestions for simplifying `clinical_microschemas.yaml` without losing detail or semantic precision.

## BDC Variable Library Dependency

The [BDC variable library](https://github.com/linkml/bdc-variable-library) imports clinical-microschemas as a remote schema dependency (pinned to `v0.0.5`) and uses it via the `instantiates:` keyword. Each BDC `CompoundVariable` or `IntegratedVariable` points to a specific numbered Record class as a measurement recipe:

```yaml
CompoundHeight001:
  is_a: CompoundVariable
  instantiates:
    - HumanBodyHeightRecord001   # encodes: height in cm, measured by stadiometer
```

The BDC library contains **45+ direct `instantiates:` references** to numbered Record variants:

| Variant suffix | BDC references |
|---|---|
| `...Record001` | 23 |
| `...Record002` | 15 |
| `...Record003` | 4 |
| `...Record004` | 2 |
| `...Record005` | 1 |

BDC does **not** create its own Record or Quantity subclasses — it only references existing numbered classes from clinical-microschemas. This makes the numbered class structure a hard dependency.

---

## 1. Collapse Numbered `Quantity` Subclasses

There are ~100+ Quantity classes of the form `HumanBodyHeightQuantity001`, `...002`, `...003`, `...004` — each differing only in min/max bounds per unit. These bounds could instead be expressed as rules on the parent Quantity class:

```yaml
# Instead of 4 separate classes (001–004), use rules on the parent:
HumanBodyHeightQuantity:
  is_a: Quantity
  rules:
    - preconditions:
        slot_conditions:
          unit: {equals_string: cm}
      postconditions:
        slot_conditions:
          quantity_value: {minimum_value: 30, maximum_value: 273}
    - preconditions:
        slot_conditions:
          unit: {equals_string: "[in_i]"}
      postconditions:
        slot_conditions:
          quantity_value: {minimum_value: 20, maximum_value: 108}
```

This could eliminate ~100 classes while preserving all constraints.

**Trade-off**: The numbered Quantity classes are referenced by `calculated_from` expressions in BMI/ratio records. Collapsing them requires rethinking how those expressions reference unit-typed inputs (see suggestion 3).

**BDC impact**: None directly. BDC does not reference numbered Quantity classes — only numbered Record classes. Safe to do independently.

---

## 2. Collapse Numbered `Record` Variants

`HumanBodyHeightRecord001–004`, `AdultHumanBodyWeightRecord001–002`, `ChildHumanBodyWeightRecord001–004`, etc. each only pin a specific unit via `slot_usage.unit: equals_string`. These are redundant with the rules already on the parent record.

If `calculated_from` expressions were written in unit-agnostic form or simplified, these numbered variants could be removed entirely. The parent record with its rules already enforces valid units.

**BDC impact**: **Breaking change.** All 45+ `instantiates:` references in BDC would fail. The numbered variants carry semantic meaning in BDC: `HumanBodyHeightRecord001` is a specific measurement recipe (height in cm), distinct from `HumanBodyHeightRecord002` (height in inches). Collapsing these classes removes the named targets that BDC relies on.

**Recommended approach instead of elimination**: Rename numbered classes to semantic names that encode the unit (e.g., `HumanBodyHeightRecord_cm`, `HumanBodyHeightRecord_inches`). This preserves the BDC `instantiates:` pattern while removing the opaque numbering scheme. BDC references would need a one-time update.

---

## 3. Simplify `calculated_from` Explosion

The BMI `AdultBodyMassIndexRecord` has **8 expressions** and `ChildBodyMassIndexRecord` has **16 expressions** — one per weight-unit × height-unit combination. `HumanAlbuminCreatinineRatioUrineRecord` also has 5.

This combinatorial explosion is a direct consequence of unit-pinned record classes. Two options:

- **Option A**: Normalize in the formula — reference the parent record and specify unit conversions in a single expression, or require SI-unit inputs.
- **Option B**: If `calculated_from` is documentation rather than an enforceable constraint, move it to a `description` or `comment` annotation rather than a validation rule.

**BDC impact**: None. BDC does not use `calculated_from` or `equals_expression` itself. However, resolving this is a prerequisite for suggestion 2, so it unblocks the larger structural simplification.

---

## 4. Promote `instrument` to an Enum

The `instrument` slot is typed as `string`, but every record enumerates valid values via inline `equals_string` rules. This is inconsistent with `method` (uses `MethodEnum`), `collected_by` (uses `CollectedByEnum`), etc.

Creating an `InstrumentEnum` would:
- Enable slot-level validation without repeating inline `any_of: equals_string` blocks
- Shorten postcondition rules significantly
- Remove duplicated instrument value lists across records

**BDC impact**: None. BDC does not set `instrument` values directly; it only references Record classes via `instantiates:`.

---

## 5. Remove Redundant `data_type` Postconditions

Nearly every record has:

```yaml
postconditions:
  slot_conditions:
    data_type:
      equals_string: decimal
```

But `data_type` is already implied by the `range` of the Quantity class (`quantity_value` is `decimal` or `integer`). This postcondition adds no logical constraint beyond what the type system already enforces. Consider:

- Removing `data_type` from validation rules entirely, setting it as a fixed default on the Quantity parent
- Or making it a fixed slot annotation on each Quantity class rather than a repeated postcondition rule

**BDC impact**: None.

---

## 6. Fix Duplicate Descriptions on Numbered Variants

Several numbered variants have identical descriptions to their parent. For example, `HumanBasophilCountRecord001` and `002` both say "Concentration of basophil cells in whole blood" — indistinguishable from each other or from the parent.

Descriptions on numbered variants should differentiate by unit:

```yaml
HumanBasophilCountRecord001:
  description: Concentration of basophil cells in whole blood in 10*3/uL
HumanBasophilCountRecord002:
  description: Concentration of basophil cells in whole blood in {#}/uL
```

**BDC impact**: None.

---

## 7. Audit Unused Slots

The following slots are defined in the `slots:` section but do not appear in any class's `slots:` list:

- `predicted_value`
- `lower_limit_normal` (description: "placeholder")
- `upper_limit_normal` (description: "placeholder")
- `percent_predicted_value`
- `activity_type`
- `relative_timing`

If these are aspirational or planned for future use, document them as such with a comment. If they are legacy, remove them to reduce schema noise.

**BDC impact**: None. BDC does not reference any of these slots.

---

## 8. Typed `unit` Slot via `UCUMEnum`

`UCUMEnum` exists and is well-maintained, but the `unit` slot is typed as `string`. Changing it to `range: UCUMEnum` would:

- Give free validation of all unit values at the slot level
- Reduce the need for per-record `equals_string` unit constraints in rules

Per-measurement unit restrictions would still stay as rules to constrain which units are valid for each measurement type, but invalid UCUM strings would be caught earlier.

**BDC impact**: None.

---

## Summary by Priority

| # | Suggestion | Approx. Classes/Rules Removed | BDC Impact | Effort |
|---|---|---|---|---|
| 1 | Collapse Quantity subclasses | ~100 classes | None | High |
| 3 | Simplify `calculated_from` | ~20 rules | None | Medium |
| 4 | `instrument` enum | ~50 rules shortened | None | Low–Medium |
| 8 | `unit` → `UCUMEnum` range | 0 classes | None | Low |
| 5 | Remove `data_type` postconditions | ~40 rules | None | Low |
| 6 | Fix duplicate descriptions | 0 classes | None | Trivial |
| 7 | Remove unused slots | 6 slots | None | Trivial |
| 2 | Collapse/rename Record variants | ~30 classes | **Breaking — requires BDC coordination** | High |

### Recommended sequencing

1. **Do now** (safe, no BDC impact): suggestions 1, 3–8
2. **Coordinate with BDC** (breaking change): suggestion 2 — rename numbered Record classes to semantic unit-based names (e.g., `_cm`, `_inches`) and update all BDC `instantiates:` references in the same release
