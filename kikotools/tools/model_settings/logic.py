"""Read a model's recommended sampling settings from its Civitai info."""

import html
import json
import os
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

FIELDS = ("steps", "cfg", "sampler", "scheduler")

# Civitai / A1111 sampler names (lowercase, "++" written as "pp") that do not
# turn into the ComfyUI name by replacing spaces with underscores.
SAMPLER_ALIASES = {
    "euler a": "euler_ancestral",
    "euler ancestral": "euler_ancestral",
    "dpm2": "dpm_2",
    "dpm2 a": "dpm_2_ancestral",
    "dpmpp 2s a": "dpmpp_2s_ancestral",
    "dpmpp 2m sde gpu": "dpmpp_2m_sde_gpu",
    "dpmpp 3m sde gpu": "dpmpp_3m_sde_gpu",
    "unipc": "uni_pc",
}
SCHEDULER_SUFFIXES = (
    "sgm uniform",
    "karras",
    "exponential",
    "simple",
    "beta",
    "normal",
)


def _normalize(name: str) -> str:
    return " ".join(name.strip().lower().replace("++", "pp").replace("_", " ").split())


def map_sampler(name: str) -> Tuple[str, Optional[str]]:
    """Civitai sampler name -> (ComfyUI sampler, scheduler named in it or None).

    "DPM++ 2M Karras" -> ("dpmpp_2m", "karras"). Whether the result is installed
    is checked by resolve(), which reports the ones that are not.
    """
    text = _normalize(name)
    scheduler = None
    for suffix in SCHEDULER_SUFFIXES:
        if text.endswith(" " + suffix):
            text = text[: -len(suffix) - 1]
            scheduler = suffix.replace(" ", "_")
            break
    sampler = SAMPLER_ALIASES.get(text, re.sub(r"[\s-]+", "_", text))
    return sampler, scheduler


def _mode(values: Iterable) -> Any:
    counts = Counter(v for v in values if v not in (None, "", 0))
    return counts.most_common(1)[0][0] if counts else None


def from_images(images: List[dict]) -> Dict[str, Any]:
    """Most common steps / cfg / sampler / scheduler over the example images."""
    steps, cfg, sampler, scheduler = [], [], [], []
    for image in images or []:
        meta = (image or {}).get("meta") or {}
        steps.append(meta.get("steps"))
        cfg.append(meta.get("cfgScale"))
        named = None
        if meta.get("sampler"):
            mapped, named = map_sampler(str(meta["sampler"]))
            sampler.append(mapped)
        if meta.get("scheduler"):
            scheduler.append(_normalize(str(meta["scheduler"])).replace(" ", "_"))
        else:
            scheduler.append(named)
    found = {
        "steps": _mode(steps),
        "cfg": _mode(cfg),
        "sampler": _mode(sampler),
        "scheduler": _mode(scheduler),
    }
    if found["steps"] is not None:
        found["steps"] = int(found["steps"])
    if found["cfg"] is not None:
        found["cfg"] = float(found["cfg"])
    return {k: v for k, v in found.items() if v is not None}


def _plain_text(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return " ".join(text.lower().replace("++", "pp").split())


def _find_phrase(text: str, phrases: Iterable[str]) -> Optional[Tuple[int, int, str]]:
    best = None
    for phrase in phrases:
        m = re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text)
        if m and (best is None or (m.start(), -len(phrase)) < (best[0], -len(best[2]))):
            best = (m.start(), m.end(), phrase)
    return best


def from_description(
    text: str, samplers: Sequence[str], schedulers: Sequence[str]
) -> Dict[str, Any]:
    """Settings written in a model description ("8 steps · CFG 1 · ER SDE · Beta").

    A scheduler is only read right after a sampler name or after the word
    "scheduler", so prose words such as "simple" or "normal" are not taken.
    """
    text = _plain_text(text)
    found: Dict[str, Any] = {}
    # "Steps: 25" beats "25 steps"; "cfg 2.5 steps: 25" is not "5 steps"
    m = re.search(r"steps?\s*[:=]\s*(\d{1,3})\b", text) or re.search(
        r"(?<![\d.])(\d{1,3})\s*(?:[-–]\s*\d{1,3}\s*)?-?\s*steps?\b", text
    )
    if m:
        found["steps"] = int(m.group(1))
    m = re.search(r"\bcfg(?:\s*scale)?\s*[:=]?\s*(\d+(?:\.\d+)?)", text)
    if m:
        found["cfg"] = float(m.group(1))

    scheduler_names = {s.replace("_", " "): s for s in schedulers}
    phrases = {s.replace("_", " ") for s in samplers} | set(SAMPLER_ALIASES)
    hit = _find_phrase(text, phrases)
    if hit:
        found["sampler"], named = map_sampler(hit[2])
        after = re.sub(r"^[\s·•,/|:\-–—]+", "", text[hit[1] : hit[1] + 30])
        sched = _find_phrase(after, scheduler_names)
        if sched and sched[0] == 0:
            found["scheduler"] = scheduler_names[sched[2]]
        elif named:
            found["scheduler"] = named
    if "scheduler" not in found:
        m = re.search(r"\bscheduler\s*[:=]?\s*([a-z_ ]+)", text)
        if m:
            sched = _find_phrase(m.group(1), scheduler_names)
            if sched and sched[0] == 0:
                found["scheduler"] = scheduler_names[sched[2]]
    return found


def resolve(
    sources: List[Tuple[str, Dict[str, Any]]],
    widgets: Dict[str, Any],
    use_model: Dict[str, bool],
    samplers: Sequence[str],
    schedulers: Sequence[str],
    substitutions: Dict[str, Dict[str, str]],
) -> Tuple[Dict[str, Any], str]:
    """Pick each field from the first source that has it, else the widget.

    A sampler or scheduler that is not installed is replaced by its entry in
    substitutions["samplers"/"schedulers"] when that one is installed, and by
    the widget value otherwise.
    """
    installed = {"sampler": set(samplers), "scheduler": set(schedulers)}
    values, lines = {}, []
    for field in FIELDS:
        value, origin = widgets[field], "widget"
        if use_model.get(field, True):
            for name, found in sources:
                if found.get(field) is not None:
                    value, origin = found[field], name
                    break
        if field in installed and value not in installed[field]:
            missing = value
            sub = substitutions.get(field + "s", {}).get(missing)
            if sub in installed[field]:
                value = sub
                origin += f": {missing} is not installed, substituted {sub}"
            else:
                value = widgets[field]
                origin += f": {missing} is not installed, using the widget"
        values[field] = value
        lines.append(f"{field} {value} ({origin})")
    return values, "\n".join(lines)


def _load_json(path: str) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def find_sidecar(model_paths: List[str], central_root: Optional[str]) -> Optional[dict]:
    """Civitai info for a model: a sidecar next to it, else LoRA Manager's central store.

    Returns LoRA Manager's .metadata.json layout; a Civitai Helper
    .civitai.info is wrapped as {"civitai": ...}.
    """
    for path in model_paths:
        base = os.path.splitext(path)[0]
        data = _load_json(base + ".metadata.json")
        if data is not None:
            return data
        data = _load_json(base + ".civitai.info")
        if data is not None:
            return {"civitai": data}

    if not central_root or not os.path.isdir(central_root):
        return None
    wanted = {
        os.path.splitext(os.path.basename(p))[0] + ".metadata.json" for p in model_paths
    }
    real = {os.path.normpath(p) for p in model_paths}
    fallback = None
    for root, _, files in os.walk(central_root):
        for name in files:
            if name not in wanted:
                continue
            data = _load_json(os.path.join(root, name))
            if data is None:
                continue
            if os.path.normpath(str(data.get("file_path", ""))) in real:
                return data
            fallback = fallback or data
    return fallback


RECOMMENDED = re.compile(r"recommend|\bsettings?\b")


def sources_from_sidecar(
    sidecar: dict, samplers: Sequence[str], schedulers: Sequence[str]
) -> List[Tuple[str, Dict[str, Any]]]:
    civitai = sidecar.get("civitai") or {}
    description = " ".join(
        str(t)
        for t in (
            civitai.get("description"),
            sidecar.get("modelDescription"),
            (civitai.get("model") or {}).get("description"),
        )
        if t
    )
    images = ("Civitai images", from_images(civitai.get("images") or []))
    stated = ("description", from_description(description, samplers, schedulers))
    # Settings the author calls recommended beat the example images, which are
    # often made with extra passes; otherwise the images are the better guess.
    if RECOMMENDED.search(_plain_text(description)):
        return [stated, images]
    return [images, stated]
