#!/usr/bin/env python3

import json

from canopy_client import CanopySession
from common import logger
from pydantic import BaseModel, ConfigDict, computed_field


def _not_implemented_lookup() -> str:
    logger.warning("TODO: look this up on Canopy")
    return "TODO look this up on Canopy"


class DraftAssemblyMetadata(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)
    # require a Canopy session at init for lookups
    canopy_session: CanopySession
    assembly_id: str | None

    assembly_tolid: str
    assembly_version: int
    bioplatforms_assembly_id: str
    bpa_package_id: list[str]
    scientific_name: str
    sequence_data_types: list[str]
    taxon_id: int
    bioplatforms_project: str

    @computed_field
    @property
    def canopy_assembly(self) -> dict[str, str]:
        assembly_id = self.assembly_id
        if assembly_id is None:
            raise ValueError(
                "A Canopy assembly_id is required to look up accession information."
            )
        return self.canopy_session.read_assembly(assembly_id=assembly_id).json()

    @computed_field
    @property
    def canopy_project(self) -> dict[str, str]:
        project_id = self.canopy_assembly.get("project_id")
        return self.canopy_session.read_project(project_id=project_id).json()

    @computed_field
    @property
    def insdc_root_bioproject(self) -> str:
        # Umbrella-level BioProject accession
        return self.canopy_project.get("project_accession", "")

    @computed_field
    @property
    def bioproject_title(self) -> str:
        # Umbrella-level BioProject title
        return self.canopy_project.get("title", "")

    @computed_field
    @property
    def bioproject_description(self) -> str:
        # Umbrella-level BioProject description
        return self.canopy_project.get("description", "")

    # easy, do next
    @computed_field
    @property
    def code_repository(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def code_repository_hash(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def insdc_status(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def insdc_hold_date(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def assembly_timestamp(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def assembly_size_primary(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def n50_length_primary(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def assembly_size_secondary(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def n50_length_secondary(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def busco_string_primary(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def busco_string_secondary(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def sequencing_depth(self) -> str:
        return _not_implemented_lookup()

    # hard, procrastinate
    @computed_field
    @property
    def ncbi_common_name(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def ncbi_family(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def ncbi_genus(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def bioplatforms_library_id(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def bioplatforms_sample_id(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def bioplatforms_dataset_id(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def insdc_assembly_accession_primary(self) -> str:
        return _not_implemented_lookup()

    @computed_field
    @property
    def insdc_assembly_accession_secondary(self) -> str:
        return _not_implemented_lookup()
