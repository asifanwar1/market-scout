import csv
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.importing.cities import CityMatcher  # noqa: E402
from scripts.seed_data.pakistan import REGIONS  # noqa: E402

USAGE = (
    'Usage: python -m scripts.convert_aedb_pdf "List of Certified Installer C-3.pdf" installers.csv\n'
    "Turns a PPIB (formerly AEDB) certified-installers PDF into a CSV the Imports screen can read. "
    "Needs pdfplumber: pip install -r requirements-dev.txt"
)

COLUMNS = ["Company", "Certificate No", "Valid until", "Technology", "Coverage", "Address", "City", "Phones", "Emails"]

_ROW_NUMBER = re.compile(r"^\d+\.?$")
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_FULL_NUMBER = re.compile(r"\(?(0\d{2,4})\)?[\s\-]*(\d{6,8})")
_BARE_NUMBER = re.compile(r"(?<![\d\-])(\d{6,8})(?![\d])")
_MOBILE = re.compile(r"\b(03\d{2})[\s\-]*(\d{7})\b")


def squash(text: str | None) -> str:
    return " ".join((text or "").split())


def parse_contacts(cell: str | None) -> tuple[list[str], list[str]]:
    text = (cell or "").replace("@\n", "@").replace("\n@", "@")
    emails = list(dict.fromkeys(m.group(0).lower().rstrip(".") for m in _EMAIL.finditer(text)))

    without_emails = _EMAIL.sub(" ", text)
    phones: list[str] = []
    area_code = None
    for line in re.split(r"[\n;]|(?=Cell)|(?=Tel)|(?=Fax)", without_emails):
        label = line.strip().lower()
        if label.startswith("fax"):
            continue
        for mobile in _MOBILE.finditer(line):
            phones.append(f"{mobile.group(1)}-{mobile.group(2)}")
        landline_text = _MOBILE.sub(" ", line)
        for match in _FULL_NUMBER.finditer(landline_text):
            area_code = area_code or match.group(1)
            phones.append(f"{match.group(1)}-{match.group(2)}")
        if area_code:
            for bare in _BARE_NUMBER.finditer(_FULL_NUMBER.sub(" ", landline_text)):
                phones.append(f"{area_code}-{bare.group(1)}")
    return list(dict.fromkeys(phones)), emails


def convert_row(cells: list[str | None], matcher: CityMatcher, cities_by_id: dict[int, str]) -> dict | None:
    if len(cells) < 8 or not _ROW_NUMBER.match(squash(cells[0])):
        return None
    name = squash(cells[1])
    if not name:
        return None
    address = squash(cells[6])
    city_id = matcher.from_address(address)
    phones, emails = parse_contacts(cells[7])
    return {
        "Company": name,
        "Certificate No": squash(cells[2]),
        "Valid until": squash(cells[3]),
        "Technology": squash(cells[4]),
        "Coverage": squash(cells[5]),
        "Address": address,
        "City": cities_by_id.get(city_id, "") if city_id is not None else "",
        "Phones": "; ".join(phones),
        "Emails": "; ".join(emails),
    }


def convert(pdf_path: Path, csv_path: Path) -> tuple[int, int]:
    try:
        import pdfplumber
    except ImportError:
        raise SystemExit("This needs pdfplumber: pip install -r requirements-dev.txt") from None

    names = {name: index for index, (name, *_rest) in enumerate(c for cities in REGIONS.values() for c in cities)}
    matcher = CityMatcher(names)
    cities_by_id = {index: name for name, index in names.items()}

    records = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for cells in table:
                    record = convert_row(cells, matcher, cities_by_id)
                    if record:
                        records.append(record)

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    with_contact = sum(1 for r in records if r["Phones"] or r["Emails"])
    return len(records), with_contact


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(USAGE)
    total, with_contact = convert(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"Wrote {total} companies ({with_contact} with a phone or email) to {sys.argv[2]}")


if __name__ == "__main__":
    main()
