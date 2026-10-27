import copy
import json
from pathlib import Path
from typing import Any, Callable, Dict

import pytest

from kikotools.tools.model_resolution_picker import families as families_module
from kikotools.tools.model_resolution_picker.table import (
    build_families,
    load_table,
    validate_table,
)

SHIPPED = Path(families_module.__file__).with_name("families.json")


def shipped_data() -> Dict[str, Any]:
    return copy.deepcopy(json.loads(SHIPPED.read_text(encoding="utf-8")))


def family(data: Dict[str, Any], label: str) -> Dict[str, Any]:
    return next(f for f in data["families"] if f["label"] == label)


def off_step(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["sizes"]["1:1"][1] = [700, 700]


def off_ratio(data: Dict[str, Any]) -> None:
    sizes = family(data, "SD 1.5")["sizes"]["1:1"]
    sizes[1:1] = [[576, 704], [704, 576]]


def missing_mirror(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["sizes"]["4:5"].pop()


def unsorted(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["sizes"]["1:1"].reverse()


def duplicate_size(data: Dict[str, Any]) -> None:
    sizes = family(data, "SD 1.5")["sizes"]
    for chip, size in (("3:4", [640, 832]), ("4:3", [832, 640])):
        sizes[chip].append(size)
        sizes[chip].sort(key=lambda s: s[0] * s[1])


def duplicate_label(data: Dict[str, Any]) -> None:
    data["families"][2]["label"] = data["families"][0]["label"]


def missing_chip(data: Dict[str, Any]) -> None:
    del family(data, "SD 1.5")["sizes"]["21:9"]


def default_not_listed(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["default"] = [520, 520]


def bad_vae_ratio(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["vaeRatio"] = 7


def bad_group(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["group"] = "audio"


def bad_step(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["step"] = 0


def empty_megapixels(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["megapixels"] = []


def duplicate_alias(data: Dict[str, Any]) -> None:
    family(data, "SD 1.5")["aliases"] = ["SDXL"]


def test_validate_table_accepts_the_shipped_file():
    assert validate_table(shipped_data()) == []


@pytest.mark.parametrize(
    "mutate, needle, chip, count",
    [
        (off_step, "step", "1:1", 1),
        (off_ratio, "7%", "1:1", 2),
        (missing_mirror, "mirror", "5:4", 1),
        (unsorted, "ascending", "1:1", 1),
        (duplicate_size, "more than one chip", ("3:4", "4:3"), 2),
        (missing_chip, "missing", "21:9", 1),
        (default_not_listed, "default", None, 1),
        (bad_vae_ratio, "vaeRatio", None, 1),
        (bad_group, "group", None, 1),
        (bad_step, "step", None, 1),
        (empty_megapixels, "megapixels", None, 1),
    ],
)
def test_validate_table_reports_each_invariant(
    mutate: Callable[[Dict[str, Any]], None],
    needle: str,
    chip: Any,
    count: int,
):
    data = shipped_data()
    mutate(data)

    problems = validate_table(data)

    assert len(problems) == count, problems
    for problem in problems:
        assert "SD 1.5" in problem and needle in problem
        if chip:
            assert any(
                c in problem for c in ([chip] if isinstance(chip, str) else chip)
            )


@pytest.mark.parametrize(
    "mutate, needle",
    [(duplicate_label, "SD 1.5"), (duplicate_alias, "SDXL")],
)
def test_validate_table_reports_duplicate_names(
    mutate: Callable[[Dict[str, Any]], None], needle: str
):
    data = shipped_data()
    mutate(data)

    problems = validate_table(data)

    assert len(problems) == 1 and "duplicate" in problems[0] and needle in problems[0]


def test_validate_table_checks_top_level_keys():
    data = shipped_data()
    data["version"] = 2
    data["chips"] = data["chips"][:-1]
    data["default"] = "Nope"

    problems = validate_table(data)

    assert any("version" in p for p in problems)
    assert any("chips" in p for p in problems)
    assert any("default" in p for p in problems)


def test_validate_table_never_raises_on_garbage():
    assert validate_table([]) != []  # type: ignore[arg-type]
    assert validate_table({}) != []
    data = shipped_data()
    data["families"][0] = "oops"
    data["families"][1]["sizes"] = {"1:1": [[1, "x"]]}
    assert validate_table(data) != []


def test_validate_table_ignores_unknown_keys():
    data = shipped_data()
    data["extra"] = 1
    family(data, "SD 1.5")["notes"] = "kept for humans"
    family(data, "SD 1.5")["whatever"] = {"a": 1}

    assert validate_table(data) == []
    assert build_families(data)[0].label == "SD 1.5"


def test_load_table_bad_json_names_the_path(tmp_path: Path):
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        load_table(bad)

    assert str(bad) in str(error.value)


def test_load_table_missing_file_names_the_path(tmp_path: Path):
    missing = tmp_path / "absent.json"

    with pytest.raises(ValueError) as error:
        load_table(missing)

    assert str(missing) in str(error.value)


def test_families_module_is_built_from_json():
    data = shipped_data()

    assert [f.label for f in families_module.FAMILIES] == [
        f["label"] for f in data["families"]
    ]
    assert families_module.DEFAULT_FAMILY == data["default"]
    assert families_module.families_payload()["families"][0]["sizes"] == {
        chip: sizes for chip, sizes in data["families"][0]["sizes"].items()
    }


def test_families_module_raises_runtime_error_on_invalid_shipped_file(
    tmp_path: Path,
):
    data = shipped_data()
    bad_vae_ratio(data)
    path = tmp_path / "families.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError) as error:
        families_module.load_shipped_families(path)

    assert "SD 1.5" in str(error.value) and "vaeRatio" in str(error.value)
