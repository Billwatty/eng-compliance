"""AI document reading with Claude.

AI reads and proposes; it never decides. Every extraction lands as a draft
that a person confirms, and every drafted rule waits for an engineer.
Without API credentials the app still works: users enter values by hand.
"""
from __future__ import annotations

import base64
import mimetypes
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field

from .config import Settings

FALLBACK_BETA = "server-side-fallback-2026-07-01"

PARAMETER_GUIDE = """Use these parameter names where they apply:
- field_density_pct_mdd: field dry density as % of maximum dry density
- mdd_kg_m3, omc_pct: maximum dry density and optimum moisture content
- layer_thickness_mm: compacted layer thickness
- cube_strength_mpa: concrete cube compressive strength
- binder_content_pct, marshall_stability_kn, marshall_flow_mm, core_density_pct
- grading:<sieve size in mm>: percent passing that sieve, e.g. grading:37.5
- yield_strength_mpa, tensile_strength_mpa, elongation_pct, mass_per_metre_kg
Otherwise use a short snake_case name with the unit as a suffix."""


class ExtractionUnavailable(Exception):
    """No credentials or the API rejected them. Fall back to manual entry."""


class ExtractionRefused(Exception):
    pass


class ExtractionFailed(Exception):
    pass


class TestValue(BaseModel):
    parameter: str
    value: float
    unit: str
    method: Optional[str] = None
    sample_tag: Optional[str] = None
    chainage_m: Optional[float] = None


class LabReportExtract(BaseModel):
    report_number: Optional[str] = None
    lab_name: Optional[str] = None
    tested_on: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")
    material: Optional[str] = None
    layer: Optional[str] = None
    sample_tags: List[str] = Field(default_factory=list)
    chainage_from_m: Optional[float] = None
    chainage_to_m: Optional[float] = None
    results: List[TestValue] = Field(default_factory=list)
    unreadable_parts: List[str] = Field(default_factory=list,
                                        description="Anything on the page you could not read with confidence")


class CertificateExtract(BaseModel):
    supplier: Optional[str] = None
    certificate_number: Optional[str] = None
    material: Optional[str] = None
    grade: Optional[str] = None
    standard: Optional[str] = None
    heat_or_batch: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    issue_date: Optional[str] = None
    gsa_mark_mentioned: bool = False
    properties: List[TestValue] = Field(default_factory=list)
    unreadable_parts: List[str] = Field(default_factory=list)


class SieveBand(BaseModel):
    sieve_mm: str
    low: float
    high: float


class RuleDraft(BaseModel):
    rule_code: str
    boq_code: str
    parameter: str
    unit: str
    method: Optional[str] = None
    limit_type: Literal["min", "max", "range", "min_and_mean", "tolerance", "envelope", "concrete_cube"]
    min: Optional[float] = None
    max: Optional[float] = None
    mean_min: Optional[float] = None
    design: Optional[float] = None
    plus: Optional[float] = None
    minus: Optional[float] = None
    sieves: Optional[List[SieveBand]] = None
    fck_cube: Optional[float] = None
    mean_margin: Optional[float] = None
    individual_margin: Optional[float] = None
    frequency_qty: Optional[float] = Field(None, description="one test per this many m2/m3/t of the lot")
    source_ref: str = Field(description="clause or table number, e.g. 'Table 12.2'")
    source_quote: Optional[str] = Field(None, description="the exact limit sentence, at most 200 characters")

    def params(self) -> dict[str, Any]:
        lt = self.limit_type
        if lt == "envelope":
            return {"sieves": {b.sieve_mm: [b.low, b.high] for b in (self.sieves or [])}}
        keys = {"min": ["min"], "max": ["max"], "range": ["min", "max"], "min_and_mean": ["min", "mean_min"],
                "tolerance": ["design", "plus", "minus"],
                "concrete_cube": ["fck_cube", "mean_margin", "individual_margin"]}[lt]
        return {k: getattr(self, k) for k in keys}


class RuleDrafts(BaseModel):
    rules: List[RuleDraft]


def _content_block(data: bytes, filename: str, mime: str | None) -> dict:
    mime = mime or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    b64 = base64.standard_b64encode(data).decode()
    if mime == "application/pdf":
        return {"type": "document", "source": {"type": "base64", "media_type": mime, "data": b64}}
    if mime in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        return {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}}
    if mime.startswith("text/") or filename.lower().endswith((".txt", ".csv", ".md")):
        return {"type": "text", "text": data.decode("utf-8", errors="replace")}
    raise ExtractionFailed(f"Cannot read files of type {mime}. Upload a PDF, photo or text file.")


def _client():
    import anthropic
    try:
        return anthropic.Anthropic()
    except anthropic.AnthropicError as e:  # missing credentials
        raise ExtractionUnavailable(
            "AI reading is off: set ANTHROPIC_API_KEY or run `ant auth login`. You can enter values by hand."
        ) from e


def _parse(settings: Settings, schema: type[BaseModel], content: list[dict], effort: str, client=None):
    import anthropic
    client = client or _client()
    kwargs: dict[str, Any] = dict(
        model=settings.model,
        max_tokens=16000,
        output_format=schema,
        output_config={"effort": effort},
        messages=[{"role": "user", "content": content}],
    )
    try:
        if settings.use_fallbacks:
            resp = client.beta.messages.parse(betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
        else:
            resp = client.messages.parse(**kwargs)
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
        raise ExtractionUnavailable(f"AI reading is off: {e.message}") from e
    except anthropic.RateLimitError as e:
        raise ExtractionFailed("Claude is rate-limited right now. Try again in a minute.") from e
    except anthropic.BadRequestError as e:
        raise ExtractionFailed(f"Claude rejected the request: {e.message}") from e
    except anthropic.APIStatusError as e:
        raise ExtractionFailed(f"Claude API error {e.status_code}. Try again later.") from e
    except anthropic.APIConnectionError as e:
        raise ExtractionFailed("Could not reach the Claude API. Check the internet connection.") from e
    if resp.stop_reason == "refusal":
        cat = getattr(getattr(resp, "stop_details", None), "category", None)
        raise ExtractionRefused(f"Claude declined to read this document (category: {cat}). Enter values by hand.")
    if resp.stop_reason == "max_tokens" or resp.parsed_output is None:
        raise ExtractionFailed("The document was too long to read in one pass. Split it or enter values by hand.")
    return resp.parsed_output


def extract_lab_report(settings: Settings, data: bytes, filename: str, mime: str | None,
                       known_parameters: list[str], client=None) -> LabReportExtract:
    prompt = (
        "This is a materials laboratory test report from a road construction contract in Ghana. "
        "Extract every test result exactly as printed. Do not compute, round or infer values that are not on the page; "
        "list anything you cannot read in unreadable_parts. Chainages like 12+350 mean 12350 metres.\n\n"
        f"{PARAMETER_GUIDE}\n\nParameters already used on this contract: {', '.join(sorted(set(known_parameters))) or 'none yet'}."
    )
    return _parse(settings, LabReportExtract, [_content_block(data, filename, mime), {"type": "text", "text": prompt}],
                  settings.extraction_effort, client)


def extract_certificate(settings: Settings, data: bytes, filename: str, mime: str | None,
                        client=None) -> CertificateExtract:
    prompt = (
        "This is a supplier or mill certificate for construction material delivered to a road project in Ghana "
        "(for example reinforcing steel, cement or bitumen). Extract the fields exactly as printed. "
        "Record the heat or batch number exactly, character for character. Set gsa_mark_mentioned only if the "
        "certificate states Ghana Standards Authority certification or marking. List anything unreadable.\n\n"
        f"{PARAMETER_GUIDE}"
    )
    return _parse(settings, CertificateExtract, [_content_block(data, filename, mime), {"type": "text", "text": prompt}],
                  settings.extraction_effort, client)


def draft_rules(settings: Settings, data: bytes, filename: str, mime: str | None, boq_items: list[dict],
                client=None) -> RuleDrafts:
    boq = "\n".join(f"- {b['code']}: {b['description']} ({b['unit']})" for b in boq_items)
    prompt = (
        "This is part of the specification for a road contract. Draft rule cards for every measurable acceptance "
        "limit that applies to the BOQ items below. Each rule must cite its clause or table in source_ref and quote "
        "the limit sentence in source_quote (at most 200 characters). Use limit types:\n"
        "- min / max / range: each result against a limit\n"
        "- min_and_mean: each result >= min and lot average >= mean_min\n"
        "- tolerance: measured vs design value, allowed +plus / -minus\n"
        "- envelope: grading bands per sieve\n"
        "- concrete_cube: characteristic cube strength fck_cube with mean and individual margins\n"
        "Set frequency_qty when the clause sets a testing frequency per area or volume. Skip anything that is not a "
        "numeric acceptance limit. An engineer will check every draft against the page before it is used.\n\n"
        f"{PARAMETER_GUIDE}\n\nBOQ items:\n{boq}"
    )
    return _parse(settings, RuleDrafts, [_content_block(data, filename, mime), {"type": "text", "text": prompt}],
                  settings.rule_draft_effort, client)
