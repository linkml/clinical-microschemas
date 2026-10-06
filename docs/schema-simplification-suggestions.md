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

## 4. Promote `instrument` to an Enum *(blocked — OWL gen incompatibility)*

The `instrument` slot is typed as `string`, but every record enumerates valid values via inline `equals_string` rules. This is inconsistent with `method` (uses `MethodEnum`), `collected_by` (uses `CollectedByEnum`), etc.

Creating an `InstrumentEnum` would:
- Enable slot-level validation without repeating inline `any_of: equals_string` blocks
- Shorten postcondition rules significantly
- Remove duplicated instrument value lists across records

**BDC impact**: None. BDC does not set `instrument` values directly; it only references Record classes via `instantiates:`.

**Blocker**: Setting `range: InstrumentEnum` on the `instrument` slot causes `gen-owl` to fail with `AssertionError: Object None must be an rdflib term`. The LinkML OWL generator cannot handle `equals_string` constraints (used in postcondition `slot_conditions`) on a slot with an enum range. This is the same root cause as the item 8 blocker. The change was attempted and reverted. Until the LinkML OWL generator is fixed upstream, the `instrument` slot must remain `range: string`.

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

## 7. Audit Unused Slots *(skipped)*

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

## 8. Typed `unit` Slot via `UCUMEnum` *(blocked — two independent blockers)*

`UCUMEnum` exists and is well-maintained, but the `unit` slot is typed as `string`. Changing it to `range: UCUMEnum` would:

- Give free validation of all unit values at the slot level
- Reduce the need for per-record `equals_string` unit constraints in rules

Per-measurement unit restrictions would still stay as rules to constrain which units are valid for each measurement type, but invalid UCUM strings would be caught earlier.

**BDC impact**: None.

**Blockers**:
1. **No canonical UCUM OWL/URI resource**: UCUM is a character-based syntax standard (not an ontology). There is no official OWL file or per-unit canonical URIs. QUDT has `qudt:ucumCode` mappings but is not a drop-in `meaning:` source for all UCUM strings used here.
2. **`equals_string` incompatible with enum range in LinkML schemaloader**: Setting `range: UCUMEnum` causes `gen-project`/`gen-python` to fail with `ValueError: slot: ... 'equals_string' requires range 'string' and not range 'UCUMEnum'`. The `equals_string` constraints in `slot_usage.unit` and postcondition `slot_conditions.unit` across all Record classes are incompatible with an enum-ranged `unit` slot. This would require removing all per-record unit `equals_string` rules and replacing them with a different validation approach.
3. **OWL gen incompatibility** (same root cause as item 4): enum-ranged slots with `equals_string` constraints cause `gen-owl` to fail with `AssertionError`.

---

## 9. Unblock Enum Ranges for `unit` and `instrument` via `slot_conditions` Migration + `meaning:` URIs

Items 4 and 8 are both blocked by LinkML implementation limitations around `equals_string` on enum-ranged slots. This item is an investigation plan to determine whether both can be unblocked by two targeted changes:

1. **Move unit/instrument constraints from `slot_usage` into postcondition `slot_conditions`**
2. **Add `meaning:` URIs to `UCUMEnum` and `InstrumentEnum`**

### Background: why these two changes might work

**Schemaloader blocker (item 8)**: The `ValueError` fires on `slot_usage` constraints — the schemaloader validates `slot_usage` expressions against the slot's declared range and rejects `equals_string` on enum-ranged slots. Postcondition `slot_conditions` constraints appear to follow a different validation path and did not trigger this error (as observed with `instrument: InstrumentEnum`).

**OWL gen blocker (items 4 and 8)**: The `AssertionError: Object None must be an rdflib term` fires because the OWL generator has no URI to use for enum values in a restriction expression. Adding `meaning:` URIs gives the generator concrete RDF terms to emit.

### Plan

#### Step 1: Add `meaning:` URIs to `InstrumentEnum`

Each permissible value in `InstrumentEnum` needs a `meaning:` URI. These can be minted as local CURIEs under the `cms:` prefix (e.g., `cms:stadiometer`) since no external ontology covers all instrument types. Alternatively, where OBO ontologies have terms (e.g., OBI for measurement instruments), use those.

```yaml
InstrumentEnum:
  permissible_values:
    stadiometer:
      meaning: OBI:0002445   # example — verify actual OBI terms
    scale:
      meaning: OBI:0000weighing_device  # etc.
```

Test after this step: run `gen-owl` with `instrument: range: InstrumentEnum` and verify the AssertionError is gone.

#### Step 2: Change `instrument` slot to `range: InstrumentEnum` and test

Restore `range: InstrumentEnum` on the `instrument` slot. Run `gen-python` and `gen-owl`. If no errors, item 4 is unblocked and can be marked done.

#### Step 3: Migrate `unit` constraints from `slot_usage` to postcondition `slot_conditions`

Currently, numbered Record variants pin their unit via `slot_usage`:

```yaml
HumanBodyHeightRecord001:
  slot_usage:
    unit:
      equals_string: cm
```

Migrate this to a postcondition rule on each variant:

```yaml
HumanBodyHeightRecord001:
  rules:
    - postconditions:
        slot_conditions:
          unit:
            equals_string: cm
```

This removes the `slot_usage` constraint that triggers the schemaloader ValueError. The parent `HumanBodyHeightRecord` already has a rule with `any_of` unit constraints, so the postcondition on the numbered variant is an additional narrowing constraint — semantically equivalent.

**Scope**: ~45 numbered Record classes (matching the BDC reference count), each with one `slot_usage.unit` block to migrate.

#### Step 4: Add `meaning:` URIs to `UCUMEnum`

UCUM has no official OWL file. Use QUDT as the `meaning:` source where available — QUDT has `qudt:ucumCode` annotations that map QUDT unit URIs to UCUM strings. For example:

```yaml
UCUMEnum:
  permissible_values:
    cm:
      meaning: QUDT:CentiM      # http://qudt.org/vocab/unit/CentiM
    "[in_i]":
      meaning: QUDT:IN          # http://qudt.org/vocab/unit/IN
    kg:
      meaning: QUDT:KiloGM
```

Not all UCUM strings used in this schema will have QUDT equivalents — document gaps. Strings without a QUDT match can use a locally minted `cms:` URI as a placeholder.

#### Step 5: Change `unit` slot to `range: UCUMEnum` and test

Restore `range: UCUMEnum` on the `unit` slot. Run `gen-python`, `gen-owl`, and `just lint`. If all pass, items 4 and 8 are both unblocked.

### Success criteria

- `just lint` passes with no `standard_naming` or other warnings
- `gen-python` completes without `ValueError`
- `gen-owl` completes without `AssertionError`
- `uv run pytest tests/ -v` passes (6/6)

### Rollback

If step 3 or 5 fails, revert:
- `unit` slot back to `range: string`
- `instrument` slot back to `range: string`
- Numbered Record `slot_conditions` back to `slot_usage`

The `meaning:` additions to the enums are harmless and can be kept regardless.

### Risk

- The QUDT mapping for all 47 UCUM values in `UCUMEnum` requires manual research — some may not have QUDT equivalents
- If the schemaloader validates postcondition `slot_conditions` the same way as `slot_usage`, step 3 will not fix the blocker and a different approach is needed
- Migrating `slot_usage` to postcondition rules changes validation semantics slightly (postconditions are conditional; `slot_usage` always applies) — verify that the parent record's preconditions correctly scope the postcondition

**BDC impact**: None. These are internal schema structural changes only.

---

## Summary by Priority

| # | Suggestion | Approx. Classes/Rules Removed | BDC Impact | Effort |
|---|---|---|---|---|
| 1 | Collapse Quantity subclasses | ~100 classes | None | High |
| 3 | Simplify `calculated_from` | ~20 rules | None | Medium |
| 4 | `instrument` enum | ~50 rules shortened | None | ~~Low–Medium~~ **Blocked** |
| 8 | `unit` → `UCUMEnum` range | 0 classes | None | ~~Low~~ **Blocked** |
| 9 | Unblock 4 + 8 via `slot_conditions` migration + `meaning:` URIs | — | None | Medium |
| 5 | Remove `data_type` postconditions | ~40 rules | None | Low |
| 6 | Fix duplicate descriptions | 0 classes | None | Trivial |
| 7 | ~~Remove unused slots~~ *(skipped)* | 6 slots | None | Trivial |
| 2 | Collapse/rename Record variants | ~30 classes | **Breaking — requires BDC coordination** | High |

### Recommended sequencing

1. **Do now** (safe, no BDC impact): suggestions 1, 3–8
2. **Coordinate with BDC** (breaking change): suggestion 2 — rename numbered Record classes to semantic unit-based names (e.g., `_cm`, `_inches`) and update all BDC `instantiates:` references in the same release
