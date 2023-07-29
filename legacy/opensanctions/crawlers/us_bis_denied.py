import csv
from followthemoney.types import registry

from zavod import Context
from zavod import helpers as h

FORMATS = ("%m/%d/%Y",)


def parse_row(context: Context, row):
    entity = context.make("LegalEntity")
    entity.id = context.make_slug(row.get("Effective_Date"), row.get("Name"))
    entity.add("name", row.get("Name"))
    entity.add("notes", row.get("Action"))
    entity.add("country", row.get("Country"))
    entity.add("modifiedAt", row.get("Last_Update"))

    country_code = registry.country.clean(row.get("Country"))
    address = h.make_address(
        context,
        street=row.get("Street_Address"),
        postal_code=row.get("Postal_Code"),
        city=row.get("City"),
        region=row.get("State"),
        country_code=country_code,
    )
    h.apply_address(context, entity, address)
    context.emit(entity, target=True)

    citation = row.get("FR_Citation")
    sanction = h.make_sanction(context, entity, key=citation)
    sanction.add("program", citation)
    sanction.add("startDate", h.parse_date(row.get("Effective_Date"), FORMATS))
    sanction.add("endDate", h.parse_date(row.get("Expiration_Date"), FORMATS))
    # pprint(row)
    context.emit(sanction)


def crawl(context: Context):
    path = context.fetch_resource("source.tsv", context.data_url)
    context.export_resource(path, "text/tsv", title=context.SOURCE_TITLE)
    with open(path, "r") as csvfile:
        for row in csv.DictReader(csvfile, delimiter="\t"):
            parse_row(context, row)
