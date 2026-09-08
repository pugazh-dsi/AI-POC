"""
The deterministic half of the guardrails pipeline.

Every operator here is a pure function of the extracted payload: same payload,
same verdict, every time. No model is consulted, nothing is inferred — a rule
either has the fields it needs, or it reports NOT_EVALUABLE and the requisition
is held rather than passed.

Fail closed is the rule of the file: a null field never counts as a pass.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Callable, Dict, Iterable, List

from dateutil.relativedelta import relativedelta

from app.services.guardrails.extraction import parse_date

PASS = "pass"
FAIL = "fail"
NOT_EVALUABLE = "not_evaluable"


# --- clinical lookups -------------------------------------------------------
#
# The two tables rules 4 and 5 are evaluated against. Keeping them here (rather
# than inline in the YAML) keeps the pack readable and the clinical knowledge in
# one reviewable place; a pack may still extend either through `extra_*` args.

# A test that is only biologically meaningful for certain genders.
GENDER_RESTRICTED_TESTS: List[Dict[str, Any]] = [
    {
        "label": "Prostate Specific Antigen (PSA)",
        "keywords": ["prostate specific antigen", "psa", "free psa"],
        "allowed_genders": ["male"],
        "reason": "PSA measures a protein produced by the prostate gland.",
    },
    {
        "label": "Semen Analysis",
        "keywords": ["semen analysis", "sperm count", "spermogram"],
        "allowed_genders": ["male"],
        "reason": "Requires a semen specimen.",
    },
    {
        "label": "HCG Pregnancy Test",
        "keywords": [
            "hcg pregnancy",
            "pregnancy test",
            "beta hcg",
            "beta-hcg",
            "b-hcg",
            "serum hcg",
            "urine hcg",
        ],
        "allowed_genders": ["female"],
        "reason": "Pregnancy testing applies to patients with a uterus.",
    },
    {
        "label": "Pap Smear / Cervical Cytology",
        "keywords": ["pap smear", "pap test", "cervical cytology"],
        "allowed_genders": ["female"],
        "reason": "Requires a cervical specimen.",
    },
    {
        "label": "Endometrial Biopsy",
        "keywords": ["endometrial biopsy", "endometrial"],
        "allowed_genders": ["female"],
        "reason": "Requires endometrial tissue.",
    },
]

# A test whose result is only valid on a fasting specimen.
FASTING_DEPENDENT_TESTS: List[Dict[str, Any]] = [
    {"label": "Lipid Panel", "keywords": ["lipid panel", "lipid profile", "cholesterol panel"], "hours": 9},
    {"label": "Fasting Blood Sugar", "keywords": ["fasting blood sugar", "fasting blood glucose", "fasting plasma glucose", "fbs"], "hours": 8},
    {"label": "Glucose Tolerance Test", "keywords": ["glucose tolerance", "ogtt"], "hours": 8},
    {"label": "Triglycerides", "keywords": ["triglyceride"], "hours": 9},
    {"label": "Fasting Insulin", "keywords": ["fasting insulin"], "hours": 8},
    {"label": "Basic Metabolic Panel", "keywords": ["basic metabolic panel", "bmp"], "hours": 8},
    {"label": "Comprehensive Metabolic Panel", "keywords": ["comprehensive metabolic panel", "cmp"], "hours": 8},
    {"label": "Iron Studies", "keywords": ["iron studies", "serum iron", "ferritin panel"], "hours": 8},
]


# --- matching ---------------------------------------------------------------


def normalize_test_name(name: str) -> str:
    """Lowercase, de-punctuate and collapse a test name for comparison."""
    text = str(name or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def test_aliases(name: str) -> List[str]:
    """The name plus anything printed in brackets, so 'CBC' matches too."""
    aliases = [normalize_test_name(name)]
    for inner in re.findall(r"\(([^)]*)\)", str(name or "")):
        alias = normalize_test_name(inner)
        if alias:
            aliases.append(alias)
    # The name with its bracketed part removed ("complete blood count").
    stripped = normalize_test_name(re.sub(r"\([^)]*\)", " ", str(name or "")))
    if stripped:
        aliases.append(stripped)
    return [a for a in dict.fromkeys(aliases) if a]


def _matches(entry: Dict[str, Any], test_name: str) -> bool:
    """Does one catalog entry cover this requested test?

    Multi-word keywords match as substrings ("lipid panel" inside "Fasting Lipid
    Panel"); single-word ones must match a whole alias, so "psa" cannot fire on
    an unrelated word that happens to contain those letters.
    """
    aliases = test_aliases(test_name)
    for keyword in entry.get("keywords", []):
        key = normalize_test_name(keyword)
        if not key:
            continue
        if " " in key:
            if any(key in alias for alias in aliases):
                return True
        elif any(key == alias or re.search(rf"\b{re.escape(key)}\b", alias) for alias in aliases):
            return True
    return False


def find_matches(catalog: Iterable[Dict[str, Any]], tests: Iterable[str]) -> List[Dict[str, Any]]:
    """[{entry, test}] for every requested test covered by the catalog."""
    found = []
    for test in tests or []:
        for entry in catalog:
            if _matches(entry, test):
                found.append({"entry": entry, "test": test})
    return found


# --- age --------------------------------------------------------------------


def calculate_age(dob: date | str | None, on: date | None = None) -> int | None:
    """Whole years between `dob` and `on` (default today), or None.

    relativedelta does the calendar arithmetic, so leap years and month lengths
    are handled by the library rather than by an approximation like days/365.25.
    """
    dob = parse_date(dob)
    if dob is None:
        return None
    reference = parse_date(on) or date.today()
    if dob > reference:
        return None
    return relativedelta(reference, dob).years


# --- operator plumbing ------------------------------------------------------

OPS: Dict[str, Callable[..., Dict[str, Any]]] = {}


def op(name: str):
    """Register a function under the name the YAML pack refers to."""
    def register(fn):
        OPS[name] = fn
        return fn
    return register


def get_op(name: str) -> Callable[..., Dict[str, Any]]:
    if name not in OPS:
        raise KeyError(f"Unknown guardrail operator: {name}")
    return OPS[name]


def _result(status: str, message: str, **details) -> Dict[str, Any]:
    return {"status": status, "message": message, "details": details}


def _missing(payload: Dict[str, Any], fields: Iterable[str]) -> List[str]:
    """Fields that are null / blank / empty in the extraction."""
    missing = []
    for field in fields:
        value = payload.get(field)
        if value is None or (isinstance(value, (str, list)) and not value):
            missing.append(field)
    return missing


def _label(field: str) -> str:
    return field.replace("_", " ").title()


def _list_missing(fields: List[str]) -> str:
    """'Collection Date and Order Date are missing' — readable in a verdict."""
    labels = [_label(f) for f in fields]
    if len(labels) == 1:
        return f"{labels[0]} is missing"
    return ", ".join(labels[:-1]) + f" and {labels[-1]} are missing"


# --- the operators ----------------------------------------------------------


@op("fields_present")
def fields_present(payload: Dict[str, Any], fields: List[str], **_) -> Dict[str, Any]:
    """Rule 1 — mandatory identifiers.

    This is the one rule for which a null IS the finding, so a missing field is
    a FAIL rather than NOT_EVALUABLE.
    """
    missing = _missing(payload, fields)
    present = [f for f in fields if f not in missing]

    if missing:
        return _result(
            FAIL,
            "Missing mandatory identifier(s): " + ", ".join(_label(f) for f in missing) + ".",
            missing_fields=missing,
            present_fields=present,
        )
    return _result(
        PASS,
        "All mandatory identifiers were extracted: " + ", ".join(_label(f) for f in fields) + ".",
        present_fields=present,
    )


@op("minor_requires_consent")
def minor_requires_consent(
    payload: Dict[str, Any],
    dob_field: str = "patient_dob",
    consent_field: str = "parental_consent_on_file",
    minimum_age: int = 18,
    as_of: str | None = None,
    **_,
) -> Dict[str, Any]:
    """Rule 2 — a patient under `minimum_age` needs a parental consent form.

    Age is computed with relativedelta, never estimated. Consent is not printed
    on the requisition, so an absent value means "no consent form was supplied"
    and the order is flagged.
    """
    dob = payload.get(dob_field)
    reference = parse_date(as_of) or date.today()
    age = calculate_age(dob, reference)

    if age is None:
        return _result(
            NOT_EVALUABLE,
            f"Cannot verify age: {_label(dob_field)} is missing or unreadable.",
            missing_fields=[dob_field],
            as_of=reference.isoformat(),
        )

    if age >= minimum_age:
        return _result(
            PASS,
            f"Patient is {age} years old — parental consent is not required.",
            age=age,
            minimum_age=minimum_age,
            as_of=reference.isoformat(),
        )

    if payload.get(consent_field) is True:
        return _result(
            PASS,
            f"Patient is a minor ({age} years old) and a parental consent form is on file.",
            age=age,
            minimum_age=minimum_age,
            consent_on_file=True,
            as_of=reference.isoformat(),
        )

    return _result(
        FAIL,
        f"Patient is a minor ({age} years old, under {minimum_age}) and no parental consent form is on file.",
        age=age,
        minimum_age=minimum_age,
        consent_on_file=payload.get(consent_field),
        as_of=reference.isoformat(),
    )


@op("date_not_before")
def date_not_before(
    payload: Dict[str, Any],
    field: str = "collection_date",
    not_before: str = "order_date",
    **_,
) -> Dict[str, Any]:
    """Rule 3 — timeline integrity: `field` may not precede `not_before`."""
    later = parse_date(payload.get(field))
    earlier = parse_date(payload.get(not_before))

    missing = [name for name, value in ((field, later), (not_before, earlier)) if value is None]
    if missing:
        return _result(
            NOT_EVALUABLE,
            "Cannot check the timeline: " + _list_missing(missing) + ".",
            missing_fields=missing,
        )

    delta = (later - earlier).days
    if delta < 0:
        return _result(
            FAIL,
            f"{_label(field)} ({later.isoformat()}) precedes {_label(not_before)} "
            f"({earlier.isoformat()}) by {abs(delta)} day(s).",
            **{field: later.isoformat(), not_before: earlier.isoformat(), "days_difference": delta},
        )

    return _result(
        PASS,
        f"{_label(field)} ({later.isoformat()}) is on or after {_label(not_before)} ({earlier.isoformat()}).",
        **{field: later.isoformat(), not_before: earlier.isoformat(), "days_difference": delta},
    )


@op("gender_test_compatibility")
def gender_test_compatibility(
    payload: Dict[str, Any],
    gender_field: str = "gender",
    tests_field: str = "requested_tests",
    extra_tests: List[Dict[str, Any]] | None = None,
    **_,
) -> Dict[str, Any]:
    """Rule 4 — biologically incompatible test/gender combinations."""
    gender = payload.get(gender_field)
    tests = payload.get(tests_field)

    missing = _missing(payload, [gender_field, tests_field])
    if missing:
        return _result(
            NOT_EVALUABLE,
            "Cannot check biological compatibility: " + _list_missing(missing) + ".",
            missing_fields=missing,
        )

    catalog = list(GENDER_RESTRICTED_TESTS) + list(extra_tests or [])
    normalized_gender = normalize_test_name(gender)
    conflicts = []
    checked = []

    for match in find_matches(catalog, tests):
        entry, test = match["entry"], match["test"]
        allowed = [normalize_test_name(g) for g in entry.get("allowed_genders", [])]
        checked.append({"test": test, "restricted_to": entry.get("allowed_genders", [])})
        if normalized_gender not in allowed:
            conflicts.append(
                {
                    "test": test,
                    "matched": entry["label"],
                    "restricted_to": entry.get("allowed_genders", []),
                    "reason": entry.get("reason", ""),
                }
            )

    if conflicts:
        listed = "; ".join(
            f"{c['test']} is restricted to {'/'.join(c['restricted_to'])} patients" for c in conflicts
        )
        return _result(
            FAIL,
            f"Gender recorded as {gender}, but {listed}.",
            gender=gender,
            conflicts=conflicts,
        )

    if not checked:
        return _result(
            PASS,
            f"No gender-restricted test was requested ({len(tests)} test(s) checked against "
            f"{len(catalog)} restricted panels).",
            gender=gender,
            tests_checked=len(tests),
        )

    return _result(
        PASS,
        f"Gender-restricted test(s) requested are compatible with a {gender} patient: "
        + ", ".join(c["test"] for c in checked)
        + ".",
        gender=gender,
        restricted_tests=checked,
    )


@op("fasting_protocol")
def fasting_protocol(
    payload: Dict[str, Any],
    fasting_field: str = "fasting_required",
    tests_field: str = "requested_tests",
    extra_tests: List[Dict[str, Any]] | None = None,
    **_,
) -> Dict[str, Any]:
    """Rule 5 — a fasting-dependent test ordered with fasting marked "No"."""
    tests = payload.get(tests_field)
    if not tests:
        return _result(
            NOT_EVALUABLE,
            f"Cannot check the fasting protocol: {_label(tests_field)} is missing.",
            missing_fields=[tests_field],
        )

    catalog = list(FASTING_DEPENDENT_TESTS) + list(extra_tests or [])
    matches = find_matches(catalog, tests)
    required_by = [
        {"test": m["test"], "matched": m["entry"]["label"], "fasting_hours": m["entry"].get("hours")}
        for m in matches
    ]

    fasting = payload.get(fasting_field)

    if not required_by:
        return _result(
            PASS,
            f"None of the {len(tests)} requested test(s) require fasting.",
            fasting_required=fasting,
            tests_checked=len(tests),
        )

    if fasting is None:
        return _result(
            NOT_EVALUABLE,
            f"{', '.join(r['test'] for r in required_by)} require(s) fasting, but "
            f"{_label(fasting_field)} was not recorded on the requisition.",
            missing_fields=[fasting_field],
            fasting_dependent_tests=required_by,
        )

    if fasting is False:
        return _result(
            FAIL,
            f"{', '.join(r['test'] for r in required_by)} require(s) a fasting specimen, "
            f"but {_label(fasting_field)} is marked No.",
            fasting_required=False,
            fasting_dependent_tests=required_by,
        )

    return _result(
        PASS,
        f"Fasting is marked Yes, as required by {', '.join(r['test'] for r in required_by)}.",
        fasting_required=True,
        fasting_dependent_tests=required_by,
    )
