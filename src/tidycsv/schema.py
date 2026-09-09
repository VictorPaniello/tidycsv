"""Load and represent a tidycsv schema: the mapping from a messy source file's
columns onto a clean, canonical set of fields, with per-field types and
validation rules."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class FieldType(StrEnum):
    STRING = "string"
    EMAIL = "email"
    DATE = "date"
    CURRENCY = "currency"
    INTEGER = "integer"
    PHONE = "phone"


class FieldSpec(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    type: FieldType = FieldType.STRING
    required: bool = False

    def all_names(self) -> list[str]:
        """Every header spelling that should map to this field, canonical name included."""
        return [self.name, *self.aliases]


class Schema(BaseModel):
    fields: list[FieldSpec]
    key_columns: list[str] = Field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> Schema:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return cls.model_validate(raw)

    def field_by_name(self, name: str) -> FieldSpec | None:
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def alias_lookup(self) -> dict[str, str]:
        """Map every known header spelling (normalized) to its canonical field name."""
        lookup: dict[str, str] = {}
        for field in self.fields:
            for alias in field.all_names():
                lookup[_normalize_header(alias)] = field.name
        return lookup


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace("_", " ").replace("-", " ")
