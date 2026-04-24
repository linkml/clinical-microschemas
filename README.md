# clinical-microschemas

Clinical microschemas for composable clinical data elements.

## Overview

This repository contains LinkML microschemas for clinical domains, including:

- `ClinicalMeasurementRecord` — observations, labs, scores
- `ConditionStatusRecord` — diagnoses, signs, symptoms
- `DrugStatusRecord` — medication exposures
- `ProcedureStatusRecord` — clinical procedures

These schemas import and extend the [LinkML Microschema Profile](https://github.com/linkml/linkml-microschema-profile).

## Usage

Install dependencies:

```bash
just install
```

Generate project artifacts:

```bash
just gen-project
```

Run tests:

```bash
just test
```
