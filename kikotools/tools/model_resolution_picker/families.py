"""Model family table for the Model Resolution Picker node.

Plain data: sizes are literals, authored once with ``logic.generate_size`` and
official lists. Every list is sorted by pixel count and mirrored exactly.
"""

from typing import Any, Dict, List, NamedTuple, Optional, Tuple

CHIPS: Tuple[str, ...] = (
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
MIRROR: Dict[str, str] = {
    "1:1": "1:1",
    "4:5": "5:4",
    "5:4": "4:5",
    "3:4": "4:3",
    "4:3": "3:4",
    "2:3": "3:2",
    "3:2": "2:3",
    "9:16": "16:9",
    "16:9": "9:16",
    "21:9": "9:21",
    "9:21": "21:9",
}
Size = Tuple[int, int]


class Family(NamedTuple):
    """One model family: grid constraints, size tiers and the chip size lists."""

    label: str
    aliases: Tuple[str, ...]
    models: str
    group: str
    vae_ratio: int
    step: int
    megapixels: Tuple[float, ...]
    default: Size
    sizes: Dict[str, Tuple[Size, ...]]


FAMILIES: Tuple[Family, ...] = (
    # generated at tiers 0.25, 0.5 MP, step 64, plus the 512/768 native sizes
    Family(
        label="SD 1.5",
        aliases=(),
        models="SD 1.5 and SD 1.5 finetunes",
        group="image",
        vae_ratio=8,
        step=64,
        megapixels=(
            0.25,
            0.5,
        ),
        default=(512, 512),
        sizes={
            "1:1": (
                (512, 512),
                (704, 704),
                (768, 768),
            ),
            "4:5": (
                (448, 576),
                (640, 832),
            ),
            "5:4": (
                (576, 448),
                (832, 640),
            ),
            "3:4": (
                (448, 576),
                (640, 832),
            ),
            "4:3": (
                (576, 448),
                (832, 640),
            ),
            "2:3": (
                (448, 640),
                (512, 768),
                (576, 896),
            ),
            "3:2": (
                (640, 448),
                (768, 512),
                (896, 576),
            ),
            "9:16": (
                (384, 704),
                (512, 960),
            ),
            "16:9": (
                (704, 384),
                (960, 512),
            ),
            "21:9": (
                (768, 320),
                (1088, 448),
            ),
            "9:21": (
                (320, 768),
                (448, 1088),
            ),
        },
    ),
    # SDXL model card / community bucket list
    Family(
        label="SDXL",
        aliases=(),
        models="SDXL, Pony and other SDXL finetunes",
        group="image",
        vae_ratio=8,
        step=64,
        megapixels=(1.0,),
        default=(1024, 1024),
        sizes={
            "1:1": ((1024, 1024),),
            "4:5": ((832, 1024),),
            "5:4": ((1024, 832),),
            "3:4": ((896, 1152),),
            "4:3": ((1152, 896),),
            "2:3": ((832, 1216),),
            "3:2": ((1216, 832),),
            "9:16": ((768, 1344),),
            "16:9": ((1344, 768),),
            "21:9": ((1536, 640),),
            "9:21": ((640, 1536),),
        },
    ),
    # Illustrious XL v1.0 release notes resolution list (SDXL list plus larger buckets)
    Family(
        label="Illustrious XL",
        aliases=(),
        models="Illustrious XL v1.0 and later, NoobAI, WAI and other Illustrious finetunes",
        group="image",
        vae_ratio=8,
        step=32,
        megapixels=(
            1.0,
            1.5,
            2.25,
        ),
        default=(1024, 1024),
        sizes={
            "1:1": (
                (1024, 1024),
                (1536, 1536),
            ),
            "4:5": (
                (832, 1024),
                (1248, 1536),
            ),
            "5:4": (
                (1024, 832),
                (1536, 1248),
            ),
            "3:4": (
                (896, 1152),
                (1344, 1792),
            ),
            "4:3": (
                (1152, 896),
                (1792, 1344),
            ),
            "2:3": (
                (832, 1216),
                (1024, 1536),
                (1248, 1824),
            ),
            "3:2": (
                (1216, 832),
                (1536, 1024),
                (1824, 1248),
            ),
            "9:16": (
                (768, 1344),
                (1152, 2048),
            ),
            "16:9": (
                (1344, 768),
                (2048, 1152),
            ),
            "21:9": ((1536, 640),),
            "9:21": ((640, 1536),),
        },
    ),
    # generated at tiers 0.5, 1.0, 1.5 MP, step 16, sides 512-1536
    Family(
        label="Anima",
        aliases=(),
        models="Anima",
        group="image",
        vae_ratio=8,
        step=16,
        megapixels=(
            0.5,
            1.0,
            1.5,
        ),
        default=(1024, 1024),
        sizes={
            "1:1": (
                (720, 720),
                (1024, 1024),
                (1248, 1248),
            ),
            "4:5": (
                (640, 816),
                (912, 1152),
                (1120, 1408),
            ),
            "5:4": (
                (816, 640),
                (1152, 912),
                (1408, 1120),
            ),
            "3:4": (
                (624, 832),
                (880, 1184),
                (1088, 1456),
            ),
            "4:3": (
                (832, 624),
                (1184, 880),
                (1456, 1088),
            ),
            "2:3": (
                (592, 880),
                (832, 1248),
                (1024, 1536),
            ),
            "3:2": (
                (880, 592),
                (1248, 832),
                (1536, 1024),
            ),
            "9:16": (
                (544, 960),
                (768, 1360),
            ),
            "16:9": (
                (960, 544),
                (1360, 768),
            ),
            "21:9": (),
            "9:21": (),
        },
    ),
    # generated at tiers 0.5, 1.0, 1.5, 2.0 MP, step 16; 16:9 2.0 MP set to 1920x1088
    Family(
        label="Flux.1",
        aliases=(),
        models="Flux.1 dev / schnell / Krea, Chroma, HiDream I1, SD3.5, Lumina 2",
        group="image",
        vae_ratio=8,
        step=16,
        megapixels=(
            0.5,
            1.0,
            1.5,
            2.0,
        ),
        default=(1024, 1024),
        sizes={
            "1:1": (
                (720, 720),
                (1024, 1024),
                (1248, 1248),
                (1456, 1456),
            ),
            "4:5": (
                (640, 816),
                (912, 1152),
                (1120, 1408),
                (1296, 1616),
            ),
            "5:4": (
                (816, 640),
                (1152, 912),
                (1408, 1120),
                (1616, 1296),
            ),
            "3:4": (
                (624, 832),
                (880, 1184),
                (1088, 1456),
                (1248, 1680),
            ),
            "4:3": (
                (832, 624),
                (1184, 880),
                (1456, 1088),
                (1680, 1248),
            ),
            "2:3": (
                (592, 880),
                (832, 1248),
                (1024, 1536),
                (1184, 1776),
            ),
            "3:2": (
                (880, 592),
                (1248, 832),
                (1536, 1024),
                (1776, 1184),
            ),
            "9:16": (
                (544, 960),
                (768, 1360),
                (944, 1680),
                (1088, 1920),
            ),
            "16:9": (
                (960, 544),
                (1360, 768),
                (1680, 944),
                (1920, 1088),
            ),
            "21:9": (
                (1104, 480),
                (1568, 672),
                (1920, 816),
                (2208, 944),
            ),
            "9:21": (
                (480, 1104),
                (672, 1568),
                (816, 1920),
                (944, 2208),
            ),
        },
    ),
    # Z-Image model card resolution list
    Family(
        label="Z-Image",
        aliases=(),
        models="Z-Image Turbo and Z-Image Base",
        group="image",
        vae_ratio=8,
        step=16,
        megapixels=(
            1.0,
            1.6,
        ),
        default=(1024, 1024),
        sizes={
            "1:1": (
                (1024, 1024),
                (1280, 1280),
            ),
            "4:5": (),
            "5:4": (),
            "3:4": (
                (864, 1152),
                (896, 1152),
                (1120, 1440),
                (1104, 1472),
            ),
            "4:3": (
                (1152, 864),
                (1152, 896),
                (1440, 1120),
                (1472, 1104),
            ),
            "2:3": (
                (832, 1248),
                (1024, 1536),
            ),
            "3:2": (
                (1248, 832),
                (1536, 1024),
            ),
            "9:16": (
                (720, 1280),
                (896, 1600),
            ),
            "16:9": (
                (1280, 720),
                (1600, 896),
            ),
            "21:9": (
                (1344, 576),
                (1680, 720),
            ),
            "9:21": (
                (576, 1344),
                (720, 1680),
            ),
        },
    ),
    # Qwen-Image model card resolution list
    Family(
        label="Qwen-Image",
        aliases=(),
        models="Qwen-Image and Qwen-Image 2512",
        group="image",
        vae_ratio=8,
        step=16,
        megapixels=(1.76,),
        default=(1328, 1328),
        sizes={
            "1:1": ((1328, 1328),),
            "4:5": (),
            "5:4": (),
            "3:4": ((1104, 1472),),
            "4:3": ((1472, 1104),),
            "2:3": ((1056, 1584),),
            "3:2": ((1584, 1056),),
            "9:16": ((928, 1664),),
            "16:9": ((1664, 928),),
            "21:9": (),
            "9:21": (),
        },
    ),
    # generated at tiers 1.0, 2.0, 4.0 MP, step 16; 16:9 2.0 MP set to 1920x1088
    Family(
        label="Flux.2 / Klein / MOSS",
        aliases=(),
        models="Flux.2 dev, Flux.2 Klein, Flux.3 Klein, MOSS-Image, Ideogram 4",
        group="image",
        vae_ratio=16,
        step=16,
        megapixels=(
            1.0,
            2.0,
            4.0,
        ),
        default=(1024, 1024),
        sizes={
            "1:1": (
                (1024, 1024),
                (1456, 1456),
                (2048, 2048),
            ),
            "4:5": (
                (912, 1152),
                (1296, 1616),
                (1824, 2288),
            ),
            "5:4": (
                (1152, 912),
                (1616, 1296),
                (2288, 1824),
            ),
            "3:4": (
                (880, 1184),
                (1248, 1680),
                (1776, 2368),
            ),
            "4:3": (
                (1184, 880),
                (1680, 1248),
                (2368, 1776),
            ),
            "2:3": (
                (832, 1248),
                (1184, 1776),
                (1680, 2512),
            ),
            "3:2": (
                (1248, 832),
                (1776, 1184),
                (2512, 1680),
            ),
            "9:16": (
                (768, 1360),
                (1088, 1920),
                (1536, 2736),
            ),
            "16:9": (
                (1360, 768),
                (1920, 1088),
                (2736, 1536),
            ),
            "21:9": (
                (1568, 672),
                (2208, 944),
                (3136, 1344),
            ),
            "9:21": (
                (672, 1568),
                (944, 2208),
                (1344, 3136),
            ),
        },
    ),
    # Qwen-Image 2.1 model card list, plus generated at tier 1.0 MP, step 32
    Family(
        label="Qwen-Image 2.1",
        aliases=(),
        models="Qwen-Image 2.1 and 2.1 Turbo",
        group="image",
        vae_ratio=16,
        step=32,
        megapixels=(
            1.0,
            4.0,
        ),
        default=(1024, 1024),
        sizes={
            "1:1": (
                (1024, 1024),
                (2048, 2048),
            ),
            "4:5": ((928, 1152),),
            "5:4": ((1152, 928),),
            "3:4": (
                (896, 1184),
                (1792, 2400),
            ),
            "4:3": (
                (1184, 896),
                (2400, 1792),
            ),
            "2:3": (
                (832, 1248),
                (1696, 2528),
            ),
            "3:2": (
                (1248, 832),
                (2528, 1696),
            ),
            "9:16": (
                (768, 1376),
                (1536, 2752),
            ),
            "16:9": (
                (1376, 768),
                (2752, 1536),
            ),
            "21:9": ((1568, 672),),
            "9:21": ((672, 1568),),
        },
    ),
    # HunyuanImage 2.1 model card resolution list
    Family(
        label="HunyuanImage 2.1",
        aliases=(),
        models="HunyuanImage 2.1",
        group="image",
        vae_ratio=32,
        step=32,
        megapixels=(4.0,),
        default=(2048, 2048),
        sizes={
            "1:1": ((2048, 2048),),
            "4:5": (),
            "5:4": (),
            "3:4": ((1792, 2304),),
            "4:3": ((2304, 1792),),
            "2:3": ((1664, 2496),),
            "3:2": ((2496, 1664),),
            "9:16": ((1536, 2560),),
            "16:9": ((2560, 1536),),
            "21:9": (),
            "9:21": (),
        },
    ),
    # Wan 2.2 official sizes plus generated at tiers 0.4, 0.9 MP, step 16
    Family(
        label="Wan 2.2 (keyframes)",
        aliases=(),
        models="Wan 2.2 keyframes: frame sizes for first/last-frame generation; the latent output is an image latent",
        group="video",
        vae_ratio=16,
        step=16,
        megapixels=(
            0.4,
            0.9,
        ),
        default=(1280, 720),
        sizes={
            "1:1": (
                (640, 640),
                (960, 960),
                (976, 976),
            ),
            "4:5": (
                (576, 720),
                (864, 1088),
            ),
            "5:4": (
                (720, 576),
                (1088, 864),
            ),
            "3:4": (
                (560, 752),
                (848, 1120),
            ),
            "4:3": (
                (752, 560),
                (1120, 848),
            ),
            "2:3": (
                (528, 800),
                (800, 1184),
            ),
            "3:2": (
                (800, 528),
                (1184, 800),
            ),
            "9:16": (
                (480, 832),
                (480, 864),
                (704, 1280),
                (720, 1280),
                (736, 1296),
            ),
            "16:9": (
                (832, 480),
                (864, 480),
                (1280, 704),
                (1280, 720),
                (1296, 736),
            ),
            "21:9": (
                (992, 416),
                (1488, 640),
            ),
            "9:21": (
                (416, 992),
                (640, 1488),
            ),
        },
    ),
    # LTX-2 official sizes plus generated at tiers 0.4, 0.9 MP, step 32
    Family(
        label="LTX-2 (keyframes)",
        aliases=(),
        models="LTX-2 keyframes: frame sizes for first/last-frame generation; the latent output is an image latent",
        group="video",
        vae_ratio=32,
        step=32,
        megapixels=(
            0.4,
            0.9,
        ),
        default=(768, 512),
        sizes={
            "1:1": (
                (640, 640),
                (960, 960),
            ),
            "4:5": (
                (576, 736),
                (864, 1088),
            ),
            "5:4": (
                (736, 576),
                (1088, 864),
            ),
            "3:4": (
                (576, 736),
                (832, 1120),
            ),
            "4:3": (
                (736, 576),
                (1120, 832),
            ),
            "2:3": (
                (512, 768),
                (544, 800),
                (800, 1184),
            ),
            "3:2": (
                (768, 512),
                (800, 544),
                (1184, 800),
            ),
            "9:16": (
                (480, 864),
                (544, 960),
                (736, 1280),
            ),
            "16:9": (
                (864, 480),
                (960, 544),
                (1280, 736),
            ),
            "21:9": (
                (992, 416),
                (1472, 640),
            ),
            "9:21": (
                (416, 992),
                (640, 1472),
            ),
        },
    ),
    # HunyuanVideo 1.5 official sizes plus generated at tiers 0.4, 0.9 MP, step 16
    Family(
        label="HunyuanVideo 1.5 (keyframes)",
        aliases=(),
        models="HunyuanVideo 1.5 keyframes: frame sizes for first/last-frame generation; the latent output is an image latent",
        group="video",
        vae_ratio=16,
        step=16,
        megapixels=(
            0.4,
            0.9,
        ),
        default=(1280, 720),
        sizes={
            "1:1": (
                (640, 640),
                (976, 976),
            ),
            "4:5": (
                (576, 720),
                (864, 1088),
            ),
            "5:4": (
                (720, 576),
                (1088, 864),
            ),
            "3:4": (
                (560, 752),
                (848, 1120),
            ),
            "4:3": (
                (752, 560),
                (1120, 848),
            ),
            "2:3": (
                (528, 800),
                (800, 1184),
            ),
            "3:2": (
                (800, 528),
                (1184, 800),
            ),
            "9:16": (
                (480, 848),
                (480, 864),
                (720, 1280),
                (736, 1296),
            ),
            "16:9": (
                (848, 480),
                (864, 480),
                (1280, 720),
                (1296, 736),
            ),
            "21:9": (
                (992, 416),
                (1488, 640),
            ),
            "9:21": (
                (416, 992),
                (640, 1488),
            ),
        },
    ),
    # generated at tiers 0.4, 1.0 MP, step 32, plus the 864x480 default
    Family(
        label="MiniMax H3 (keyframes)",
        aliases=(),
        models="MiniMax H3 keyframes: frame sizes for first/last-frame generation; the latent output is an image latent",
        group="video",
        vae_ratio=16,
        step=32,
        megapixels=(
            0.4,
            1.0,
        ),
        default=(864, 480),
        sizes={
            "1:1": (
                (640, 640),
                (1024, 1024),
            ),
            "4:5": (
                (576, 736),
                (928, 1152),
            ),
            "5:4": (
                (736, 576),
                (1152, 928),
            ),
            "3:4": (
                (576, 736),
                (896, 1184),
            ),
            "4:3": (
                (736, 576),
                (1184, 896),
            ),
            "2:3": (
                (544, 800),
                (832, 1248),
            ),
            "3:2": (
                (800, 544),
                (1248, 832),
            ),
            "9:16": (
                (480, 864),
                (768, 1376),
            ),
            "16:9": (
                (864, 480),
                (1376, 768),
            ),
            "21:9": (
                (992, 416),
                (1568, 672),
            ),
            "9:21": (
                (416, 992),
                (672, 1568),
            ),
        },
    ),
)

DEFAULT_FAMILY = "SDXL"


def family_labels() -> List[str]:
    """Return every family label in display order."""
    return [family.label for family in FAMILIES]


def resolve_family(label: str) -> Optional[Family]:
    """Return the family matching ``label`` or one of its aliases, else None."""
    for family in FAMILIES:
        if label == family.label or label in family.aliases:
            return family
    return None


def families_payload() -> Dict[str, Any]:
    """Return the JSON-shaped table the frontend consumes."""
    return {
        "chips": list(CHIPS),
        "mirror": dict(MIRROR),
        "default": DEFAULT_FAMILY,
        "families": [
            {
                "label": family.label,
                "aliases": list(family.aliases),
                "models": family.models,
                "group": family.group,
                "vaeRatio": family.vae_ratio,
                "step": family.step,
                "megapixels": list(family.megapixels),
                "default": list(family.default),
                "sizes": {
                    chip: [list(size) for size in family.sizes.get(chip, ())]
                    for chip in CHIPS
                },
            }
            for family in FAMILIES
        ],
    }
