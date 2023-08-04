from typing import List, Type

from zavod.logs import get_logger
from zavod.store import View, get_store
from zavod.context import Context
from zavod.meta import Dataset, get_catalog
from zavod.exporters.common import Exporter
from zavod.exporters.ftm import FtMExporter
from zavod.exporters.nested import NestedJSONExporter
from zavod.exporters.names import NamesExporter
from zavod.exporters.simplecsv import SimpleCSVExporter
from zavod.exporters.senzing import SenzingExporter
from zavod.exporters.statistics import StatisticsExporter
from zavod.exporters.metadata import write_dataset_index
from zavod.util import write_json

log = get_logger(__name__)

EXPORTERS: List[Type[Exporter]] = [
    FtMExporter,
    NestedJSONExporter,
    NamesExporter,
    StatisticsExporter,
    SimpleCSVExporter,
    SenzingExporter,
]

__all__ = ["export_dataset"]


def export_data(context: Context, view: View) -> None:
    clazzes = EXPORTERS
    if not context.dataset.export:
        clazzes = [StatisticsExporter]
    exporters = [clz(context, view) for clz in clazzes]
    log.info(
        "Exporting dataset...",
        dataset=context.dataset.name,
        exporters=len(exporters),
    )

    for exporter in exporters:
        exporter.setup()

    for idx, entity in enumerate(view.entities()):
        if idx > 0 and idx % 10000 == 0:
            log.info("Exported %s entities..." % idx, dataset=context.dataset.name)
        for exporter in exporters:
            exporter.feed(entity)

    for exporter in exporters:
        exporter.finish()


def write_issues(context: Context) -> None:
    # Export list of data issues from crawl stage
    issues_path = context.get_resource_path("issues.json")
    context.log.info("Writing dataset issues list", path=issues_path)
    with open(issues_path, "wb") as fh:
        issues = list(context.issues.all())
        data = {"issues": issues}
        write_json(data, fh)


def export_dataset(dataset: Dataset, view: View) -> None:
    """Dump the contents of the dataset to the output directory."""
    try:
        context = Context(dataset)
        context.begin(clear=False)
        export_data(context, view)

        write_issues(context)

        # Export full metadata
        write_dataset_index(context, dataset)

    finally:
        context.close()


def export(scope_name: str, recurse: bool = False) -> None:
    """Export dump files for all datasets in the given scope."""
    scope = get_catalog().require(scope_name)
    store = get_store(scope)
    exports = scope.datasets if recurse else [scope]
    for dataset_ in exports:
        view = store.view(dataset_)
        export_dataset(dataset_, view)