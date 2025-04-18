# src/libvirt/backend/libvirt_validator.py

import logging
from pathlib import Path
from lxml import etree as LET
from typing import Dict

# --- ОТНОСИТЕЛЬНЫЙ ИМПОРТ КОНФИГА ---
# Поднимаемся на один уровень (из backend в libvirt)
from .. import config
# или from ..config import SCHEMA_FILENAME_MAP (если нужно только это)

# Настройка логгера для этого модуля
validator_logger = logging.getLogger("LibvirtXmlValidator")

# --- Custom Libvirt Validation Exceptions ---
class LibvirtValidationError(Exception): pass
class LibvirtXmlSyntaxError(LibvirtValidationError): pass
class LibvirtXmlSchemaError(LibvirtValidationError): pass
class LibvirtXmlSchemaNotFoundError(LibvirtValidationError): pass
class LibvirtValidatorConfigError(LibvirtValidationError): pass

# --- LibvirtXmlValidator Class ---
class LibvirtXmlValidator:
    def __init__(self, schemas_dir: Path):
        validator_logger.info(f"Initializing LibvirtXmlValidator with schemas_dir: {schemas_dir}")
        if not schemas_dir.is_dir():
            msg = f"Libvirt schemas directory not found or is not a directory: {schemas_dir.resolve()}"
            validator_logger.error(msg)
            raise LibvirtValidatorConfigError(msg)

        self.schemas_dir = schemas_dir
        self._loaded_schemas: Dict[str, LET.RelaxNG] = {}
        loaded_count = 0
        missing_count = 0
        error_count = 0

        # Используем SCHEMA_FILENAME_MAP из импортированного config
        validator_logger.info(f"Attempting to load schemas based on config.SCHEMA_FILENAME_MAP for keys: {list(config.SCHEMA_FILENAME_MAP.keys())}")
        for xml_tag_key, filename_stem in config.SCHEMA_FILENAME_MAP.items():
            schema_file = self.schemas_dir / f"{filename_stem}.rng"
            if schema_file.is_file():
                try:
                    validator_logger.info(f"Loading schema for <{xml_tag_key}> from {schema_file.name}...")
                    parsed_schema = LET.parse(str(schema_file))
                    self._loaded_schemas[xml_tag_key] = LET.RelaxNG(parsed_schema)
                    validator_logger.info(f"Successfully loaded schema for <{xml_tag_key}>.")
                    loaded_count += 1
                except LET.ParseError as e:
                    validator_logger.error(f"Failed to parse schema file '{schema_file.name}' for <{xml_tag_key}>: {e}")
                    error_count += 1
                except Exception as e:
                    validator_logger.error(f"Unexpected error loading schema '{schema_file.name}' for <{xml_tag_key}>: {e}", exc_info=True)
                    error_count += 1
            else:
                validator_logger.warning(f"Schema file '{schema_file.name}' (for <{xml_tag_key}>) not found in {self.schemas_dir.resolve()}. Validation for this type will fail.")
                missing_count += 1

        if loaded_count == 0 and (missing_count > 0 or error_count > 0):
             msg = f"No RNG schemas were successfully loaded from directory: {self.schemas_dir.resolve()}. Validation is impossible."
             validator_logger.error(msg)
             raise LibvirtValidatorConfigError(msg)
        elif error_count > 0 or missing_count > 0:
             validator_logger.warning(f"Schema loading from {self.schemas_dir.resolve()} completed. Loaded: {loaded_count}, Missing: {missing_count}, Errors: {error_count}")
        else:
             validator_logger.info(f"Successfully loaded {loaded_count} mapped RNG schemas from {self.schemas_dir.resolve()}.")
        validator_logger.info(f"Validator initialized. Available schema keys (expected XML root tags): {list(self._loaded_schemas.keys())}")

    def validate(self, xml_content: str) -> str:
        validator_logger.debug(f"--- Starting XML Validation ---")
        validator_logger.debug(f"Input XML (first 150 chars): {xml_content[:150]}...")
        xml_root = None
        root_tag = None
        rng_schema = None
        try:
            validator_logger.debug("Attempting to parse XML...")
            xml_root = self._parse_xml(xml_content)
            root_tag = xml_root.tag
            validator_logger.debug(f"XML Parsed. Root tag: <{root_tag}>")
            validator_logger.debug(f"Looking up schema for key '{root_tag}'...")
            rng_schema = self._loaded_schemas.get(root_tag)
            if not rng_schema:
                supported = ", ".join(self._loaded_schemas.keys())
                msg = f"Schema for root element '<{root_tag}>' not found or not loaded. Loaded schemas: {supported}"
                validator_logger.warning(f"Schema lookup FAILED: {msg}")
                raise LibvirtXmlSchemaNotFoundError(msg)
            else:
                validator_logger.debug(f"Schema found for key '{root_tag}'.")
            validator_logger.debug(f"Attempting schema validation using rng_schema.validate(xml_root)...")
            is_valid = rng_schema.validate(xml_root)
            validator_logger.debug(f"rng_schema.validate(xml_root) returned: {is_valid}")
            if not is_valid:
                error_log = rng_schema.error_log
                error_details = str(error_log).strip() if error_log else "No specific error details available from RelaxNG validator."
                validator_logger.warning(f"Schema validation FAILED for <{root_tag}>: {error_details}")
                raise LibvirtXmlSchemaError(f"XML does not conform to schema for <{root_tag}>: {error_details}")
            else:
                validator_logger.debug(f"Schema validation PASSED for <{root_tag}>.")
            validator_logger.info(f"--- Validation Successful for <{root_tag}> ---")
            return root_tag
        except LET.XMLSyntaxError as e:
             validator_logger.warning(f"XML parsing/syntax FAILED: {e}")
             raise LibvirtXmlSyntaxError(f"XML syntax error: {e}") from e
        except LibvirtValidationError as e:
             validator_logger.warning(f"Validation FAILED due to custom validation error: {type(e).__name__}: {e}")
             raise
        except Exception as e:
             validator_logger.exception("--- Totally unexpected error during validation process! ---")
             raise LibvirtValidationError(f"Unexpected validation error: {e}") from e

    def _parse_xml(self, xml_content: str) -> LET._Element:
        try:
            parser = LET.XMLParser(recover=False, remove_blank_text=True)
            return LET.fromstring(xml_content.encode('utf-8'), parser)
        except LET.XMLSyntaxError as e:
            raise