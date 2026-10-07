"""Data test."""
import os
import glob
import pytest
from pathlib import Path

import clinical_microschemas.datamodel.clinical_microschemas
from linkml_runtime.loaders import yaml_loader

DATA_DIR_VALID = Path(__file__).parent / "data" / "valid"
DATA_DIR_INVALID = Path(__file__).parent / "data" / "invalid"

VALID_EXAMPLE_FILES = glob.glob(os.path.join(DATA_DIR_VALID, '*.yaml'))
INVALID_EXAMPLE_FILES = glob.glob(os.path.join(DATA_DIR_INVALID, '*.yaml'))


def _build_schema_name_index():
    """Build a dict from LinkML schema class name -> Python class object."""
    mod = clinical_microschemas.datamodel.clinical_microschemas
    index = {}
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and hasattr(obj, 'class_name'):
            index[obj.class_name] = obj
    return index


_CLASS_INDEX = _build_schema_name_index()


@pytest.mark.parametrize("filepath", VALID_EXAMPLE_FILES)
def test_valid_data_files(filepath):
    """Test loading of all valid data files."""
    target_class_name = Path(filepath).stem.split("-")[0]
    tgt_class = _CLASS_INDEX.get(target_class_name) or getattr(
        clinical_microschemas.datamodel.clinical_microschemas,
        target_class_name,
    )
    obj = yaml_loader.load(filepath, target_class=tgt_class)
    assert obj
