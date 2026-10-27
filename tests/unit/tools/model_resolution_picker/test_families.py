from kikotools.tools.model_resolution_picker.families import (
    CHIPS,
    DEFAULT_FAMILY,
    FAMILIES,
    MIRROR,
    families_payload,
    family_labels,
    resolve_family,
)

CHIP_RATIO = {c: int(c.split(":")[0]) / int(c.split(":")[1]) for c in CHIPS}


def test_chip_order_and_mirrors():
    assert CHIPS == (
        "1:1",
        "4:5",
        "5:4",
        "3:4",
        "4:3",
        "2:3",
        "3:2",
        "9:16",
        "16:9",
        "21:9",
        "9:21",
    )
    assert all(MIRROR[MIRROR[c]] == c for c in CHIPS)


def test_every_size_is_on_step_and_within_seven_percent_of_its_chip():
    for family in FAMILIES:
        for chip, entries in family.sizes.items():
            for w, h in entries:
                assert w % family.step == 0 and h % family.step == 0, (
                    family.label,
                    w,
                    h,
                )
                assert abs(w / h - CHIP_RATIO[chip]) / CHIP_RATIO[chip] <= 0.07, (
                    family.label,
                    chip,
                    w,
                    h,
                )


def test_every_entry_has_its_mirror_and_lists_are_sorted():
    for family in FAMILIES:
        for chip, entries in family.sizes.items():
            assert list(entries) == sorted(entries, key=lambda s: s[0] * s[1])
            for w, h in entries:
                assert (h, w) in family.sizes.get(MIRROR[chip], ()), (
                    family.label,
                    chip,
                    w,
                    h,
                )


def test_defaults_labels_and_must_includes():
    labels = family_labels()
    assert labels[0] == "SD 1.5" and "SDXL" in labels and DEFAULT_FAMILY == "SDXL"
    assert len(set(labels)) == len(labels)
    for family in FAMILIES:
        assert any(
            family.default in entries for entries in family.sizes.values()
        ), family.label
    must = {
        "SDXL": ("16:9", (1344, 768)),
        "Flux.1": ("16:9", (1920, 1088)),
        "Flux.2 / Klein / MOSS": ("3:2", (1248, 832)),
        "Z-Image": ("21:9", (1680, 720)),
        "Qwen-Image": ("16:9", (1664, 928)),
        "Qwen-Image 2.1": ("16:9", (2752, 1536)),
        "HunyuanImage 2.1": ("16:9", (2560, 1536)),
        "Illustrious XL": ("2:3", (1248, 1824)),
        "Wan 2.2 (keyframes)": ("16:9", (1280, 704)),
        "MiniMax H3 (keyframes)": ("16:9", (864, 480)),
    }
    for label, (chip, size) in must.items():
        assert size in resolve_family(label).sizes[chip], label


def test_resolve_family_by_alias_and_unknown():
    assert resolve_family("SDXL").step == 64
    assert resolve_family("nope") is None


def test_payload_is_json_shaped():
    payload = families_payload()
    assert payload["default"] == "SDXL" and payload["chips"] == list(CHIPS)
    sdxl = next(f for f in payload["families"] if f["label"] == "SDXL")
    assert (
        sdxl["sizes"]["3:2"] == [[1216, 832]]
        and sdxl["vaeRatio"] == 8
        and sdxl["group"] == "image"
    )
