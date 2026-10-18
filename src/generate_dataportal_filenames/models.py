#!/usr/bin/env python3

from functools import cached_property
import json

from canopy_client import CanopySession
from common import logger
from pydantic import BaseModel, ConfigDict, Field, computed_field


class DraftAssemblyMetadata(BaseModel):

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    # require a Canopy session at init for lookups
    canopy_session: CanopySession = Field(exclude=True)
    assembly_id: str | None = Field(exclude=True)

    # output fields that are passed e.g. from the Manifest
    assembly_size_primary: int
    assembly_size_secondary: int
    assembly_tolid: str
    assembly_version: int
    bioplatforms_assembly_id: str
    bioplatforms_project: str
    bpa_package_id: list[str]
    busco_string_primary: str
    busco_string_secondary: str
    n50_length_primary: int
    n50_length_secondary: int
    scientific_name: str
    sequence_data_types: list[str]
    sequencing_depth: int
    taxon_id: int

    # Lookups (don't print these)
    @cached_property
    def canopy_assembly(self) -> dict[str, str]:
        assembly_id = self.assembly_id
        if assembly_id is None:
            raise ValueError(
                "A Canopy assembly_id is required to look up accession information."
            )
        logger.info(f"Looking up assembly {assembly_id}.")
        return self.canopy_session.read_assembly(assembly_id=assembly_id).json()

    @cached_property
    def canopy_assembly_run(self) -> dict[str, str] | None:
        logger.info(f"Looking up assembly_run for {self.assembly_id}.")
        assembly_run = self.canopy_session.get_assembly_run_by_stage_name(
            assembly_id=self.assembly_id, stage_name="genomeassembly"
        )
        if assembly_run is None:
            raise ValueError(
                (
                    f"No assembly_run for assembly_id {self.assembly_id} "
                    "and stage genomeassembly on Canopy."
                )
            )
        return assembly_run

    @cached_property
    def canopy_experiment_ids(self) -> list[str | None]:
        logger.info("Looking up experiment_id values.")
        return [
            self.canopy_session.get_experiment_id(bpa_package_id=x)
            for x in self.bpa_package_id
        ]

    @cached_property
    def canopy_experiments(self) -> list[dict[str, str]]:
        logger.info("Looking up experiments.")
        return [
            self.canopy_session.read_experiment(experiment_id=x).json()
            for x in self.canopy_experiment_ids
            if x is not None
        ]

    @cached_property
    def canopy_project(self) -> dict[str, str]:
        project_id = self.canopy_assembly.get("project_id")
        logger.info(f"Looking up project {project_id}.")
        return self.canopy_session.read_project(project_id=project_id).json()

    @cached_property
    def canopy_read_ids(self) -> list[str]:
        read_ids = []
        for experiment_id in self.canopy_experiment_ids:
            logger.info(f"Looking up reads for experiment_id {experiment_id}.")
            experiment_read_ids = self.canopy_session.get_read_ids(
                experiment_id=experiment_id
            )
            for id in experiment_read_ids:
                read_ids.append(id)
        return sorted(set(read_ids))

    @cached_property
    def canopy_reads(self) -> list[dict[str, str]]:
        logger.info(f"Looking up reads.")
        return [
            self.canopy_session.read_read(read_id=x).json()
            for x in self.canopy_read_ids
            if x is not None
        ]

    @cached_property
    def canopy_sample_ids(self) -> list[str]:
        logger.info(f"Looking up sample_id values.")
        return [
            self.canopy_session.get_sample_id(bpa_package_id=x)
            for x in self.bpa_package_id
        ]

    @cached_property
    def canopy_samples(self) -> list[dict[str, str]]:
        logger.info(f"Looking up samples.")
        return [
            self.canopy_session.read_sample(sample_id=x).json()
            for x in self.canopy_sample_ids
            if x is not None
        ]

    @cached_property
    def canopy_taxonomy_info(self) -> dict[str, str]:
        logger.info(f"Looking up taxonomy for taxon_id {self.taxon_id}.")
        taxonomy_response = self.canopy_session.get_taxonomy_info(
            taxon_id=self.taxon_id
        )
        taxonomy_response.raise_for_status()
        return taxonomy_response.json()

    # Metadata fields - registered in Canopy
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

    @computed_field
    @property
    def code_repository(self) -> str:
        return self.canopy_assembly_run.get("github_repo", "")

    @computed_field
    @property
    def code_repository_hash(self) -> str:
        return self.canopy_assembly_run.get("git_commit", "")

    @computed_field
    @property
    def assembly_timestamp(self) -> str:
        return self.canopy_assembly_run.get("updated_at", "")

    @computed_field
    @property
    def ncbi_common_name(self) -> str:
        return self.canopy_taxonomy_info.get("ncbi_common_name", "")

    @computed_field
    @property
    def ncbi_family(self) -> str:
        return self.canopy_taxonomy_info.get("ncbi_family", "")

    @computed_field
    @property
    def ncbi_genus(self) -> str:
        ncbi_lineage = self.canopy_taxonomy_info.get("ncbi_lineage")
        for rank in ncbi_lineage:
            if rank.get("rank") == "genus":
                return rank.get("name", "")
        return ""

    @computed_field
    @property
    def insdc_status(self) -> str:
        return self.canopy_project.get("status", "")

    @computed_field
    @property
    def insdc_hold_date(self) -> str:
        # TODO. Currently not possible to retrieve from Canopy. See
        # https://github.com/AustralianBioCommons/atol-canopy/issues/75
        return "TODO. Currently not possible to retrieve from Canopy"

    @computed_field
    @property
    def insdc_assembly_accession_primary(self) -> str:
        # TODO: Currently not possible to retrieve from ENA
        return "TODO: Currently not possible to retrieve from ENA"

    @computed_field
    @property
    def insdc_assembly_accession_secondary(self) -> str:
        # TODO: Currently not possible to retrieve from ENA
        return "TODO: Currently not possible to retrieve from ENA"

    # Metadata fields - might/should be registered in Canopy
    @computed_field
    @property
    def bioplatforms_library_id(self) -> list[str]:
        return sorted(set(x.get("bpa_library_id", "") for x in self.canopy_experiments))

    @computed_field
    @property
    def bioplatforms_sample_id(self) -> list[str]:
        return sorted(set(x.get("bpa_sample_id", "") for x in self.canopy_samples))

    @computed_field
    @property
    def bioplatforms_dataset_id(self) -> str:
        return sorted(set(x.get("bpa_dataset_id", "") for x in self.canopy_reads))
