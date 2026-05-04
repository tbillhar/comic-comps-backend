from dataclasses import dataclass


@dataclass(frozen=True)
class OriginalSeriesAuthority:
    canonical_name: str
    start_year: int


_ORIGINAL_SERIES_BY_ALIAS: dict[str, OriginalSeriesAuthority] = {
    "avengers": OriginalSeriesAuthority(canonical_name="Avengers", start_year=1963),
    "captain america": OriginalSeriesAuthority(canonical_name="Captain America", start_year=1968),
    "conan": OriginalSeriesAuthority(canonical_name="Conan", start_year=1970),
    "conan the barbarian": OriginalSeriesAuthority(canonical_name="Conan", start_year=1970),
    "daredevil": OriginalSeriesAuthority(canonical_name="Daredevil", start_year=1964),
    "incredible hulk": OriginalSeriesAuthority(canonical_name="Incredible Hulk", start_year=1962),
    "hulk": OriginalSeriesAuthority(canonical_name="Incredible Hulk", start_year=1962),
    "iron man": OriginalSeriesAuthority(canonical_name="Iron Man", start_year=1968),
    "fantastic four": OriginalSeriesAuthority(canonical_name="Fantastic Four", start_year=1961),
    "x men": OriginalSeriesAuthority(canonical_name="X-Men", start_year=1963),
    "x-men": OriginalSeriesAuthority(canonical_name="X-Men", start_year=1963),
    "tales of suspense": OriginalSeriesAuthority(canonical_name="Tales of Suspense", start_year=1959),
    "tales to astonish": OriginalSeriesAuthority(canonical_name="Tales to Astonish", start_year=1959),
    "sub mariner": OriginalSeriesAuthority(canonical_name="Sub-Mariner", start_year=1968),
    "sub-mariner": OriginalSeriesAuthority(canonical_name="Sub-Mariner", start_year=1968),
    "thor": OriginalSeriesAuthority(canonical_name="Thor", start_year=1966),
    "amazing spiderman": OriginalSeriesAuthority(canonical_name="Amazing Spider-Man", start_year=1963),
    "amazing spider man": OriginalSeriesAuthority(canonical_name="Amazing Spider-Man", start_year=1963),
    "amazing spider-man": OriginalSeriesAuthority(canonical_name="Amazing Spider-Man", start_year=1963),
}


def resolve_original_series(series: str) -> OriginalSeriesAuthority | None:
    normalized = " ".join(series.casefold().replace("-", " ").split())
    return _ORIGINAL_SERIES_BY_ALIAS.get(normalized)
