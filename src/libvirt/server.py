# src/libvirt/server.py

import logging
import argparse
import os # Добавлен импорт os
from pathlib import Path
from typing import Optional, Any

# Импорты MCP
from mcp.server.fastmcp import FastMCP, Context
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

# Относительный импорт валидатора
from .backend.libvirt_validator import (
    LibvirtXmlValidator,
    LibvirtValidationError,
    LibvirtXmlSyntaxError,
    LibvirtXmlSchemaError,
    LibvirtXmlSchemaNotFoundError,
    LibvirtValidatorConfigError
)

# Относительный импорт конфига
from . import config # Используем config из этой же папки

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logging.getLogger("LibvirtXmlValidator").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__) # Логгер для server.py

# --- ОПРЕДЕЛЕНИЕ ПУТЕЙ И ПЕРЕМЕННЫХ НА ГЛОБАЛЬНОМ УРОВНЕ ---
# Чтобы __init__.py мог их импортировать

# 1. Путь к директории со схемами
try:
    _current_dir = Path(__file__).parent
    SCHEMAS_DIRECTORY = _current_dir / config.SCHEMAS_DIR_NAME
    logger.debug(f"Schema directory calculated: {SCHEMAS_DIRECTORY.resolve()}")
except NameError:
    _current_dir = Path(".")
    SCHEMAS_DIRECTORY = _current_dir / config.SCHEMAS_DIR_NAME
    logger.warning(f"Cannot determine schema path automatically. Assuming './{config.SCHEMAS_DIR_NAME}'. Resolved: {SCHEMAS_DIRECTORY.resolve()}")

# 2. Путь для хранения XML (из переменной окружения или по умолчанию из config)
default_xml_path = _current_dir / config.DEFAULT_XML_STORAGE_DIR
XML_STORAGE_DIR = Path(os.getenv("MCP_LIBVIRT_XML_DIR", default_xml_path)).resolve()
logger.info(f"Using XML storage directory: {XML_STORAGE_DIR}")

# Создаем директорию, если ее нет
try:
    XML_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    logger.error(f"Could not create or access XML storage directory {XML_STORAGE_DIR}: {e}")
    # Возможно, стоит добавить exit(1) здесь, если директория критична

# 3. Переменная для пути к схеме (для __init__.py) - ссылается на директорию
LIBVIRT_RNG_SCHEMA_PATH = SCHEMAS_DIRECTORY

# --- MCP Server Setup ---
# mcp теперь тоже глобальная переменная
mcp = FastMCP("LibvirtXmlValidatorService")

# --- Validator Instantiation ---
validator: Optional[LibvirtXmlValidator] = None
try:
    logger.info(f"Attempting to initialize validator using schemas from: {SCHEMAS_DIRECTORY}")
    validator = LibvirtXmlValidator(schemas_dir=SCHEMAS_DIRECTORY)
    logger.info("LibvirtXmlValidator initialized successfully.")
except LibvirtValidatorConfigError as e:
    logger.critical(f"FATAL: Failed to initialize LibvirtXmlValidator: {e}.")
    validator = None
except Exception as e:
    logger.critical(f"FATAL: Unexpected error initializing LibvirtXmlValidator: {e}", exc_info=True)
    validator = None

# --- MCP Tool(s) ---
@mcp.tool()
def validate_libvirt_xml(ctx: Context, xml_content: str) -> str:
    """
    Validates the provided Libvirt XML content against the appropriate RNG schema.
    """
    logger.info(f"Received XML for validation via MCP tool...")
    ctx.info(f"Validating provided XML...")
    if validator is None:
        logger.error("Validator service is unavailable due to initialization failure.")
        ctx.error("Server configuration error: XML Validator is not available.")
        raise McpError(ErrorData(INTERNAL_ERROR, "Server configuration error: XML Validator is not available."))
    try:
        root_tag = validator.validate(xml_content)
        success_message = f"XML validation successful. Detected object type: '<{root_tag}>'."
        logger.info(success_message)
        ctx.info(success_message)
        return success_message
    except (LibvirtXmlSyntaxError, LibvirtXmlSchemaError, LibvirtXmlSchemaNotFoundError) as e:
        logger.warning(f"XML validation failed (Input Error): {e}")
        ctx.error(f"XML validation failed: {e}")
        raise McpError(ErrorData(INVALID_PARAMS, f"Provided XML failed validation: {e}")) from e
    except LibvirtValidationError as e:
        logger.error(f"XML validation failed (Potentially Internal): {e}")
        ctx.error(f"XML validation failed: {e}")
        raise McpError(ErrorData(INVALID_PARAMS, f"XML validation failed: {e}")) from e
    except Exception as e:
        logger.exception(f"Unexpected error during MCP tool execution.")
        ctx.error("An unexpected server error occurred during XML validation.")
        raise McpError(ErrorData(INTERNAL_ERROR, f"Unexpected server error during XML validation: {e}")) from e




    
# --- Код для ЗАПУСКА ИМЕННО ЭТОГО ФАЙЛА как основного скрипта ---
# Этот блок выполняется при запуске `uv run -m src.libvirt.server ...`
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Libvirt XML Validator MCP Server (FastMCP).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--transport", choices=["stdio", "sse"], default="stdio",
        help="Communication transport."
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Host address for SSE server."
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Port for SSE server."
    )
    args = parser.parse_args()

    if validator is None:
         logger.warning("Starting server, but XML Validator is DISABLED. Tool calls will fail.")
    else:
        logger.info("XML Validator is ready.")

    if args.transport == "stdio":
        logger.info(f"Starting MCP Server (stdio)...")
        mcp.run() # Используем глобальный mcp
    elif args.transport == "sse":
        try:
            import uvicorn
            logger.info(f"Starting MCP Server (SSE on http://{args.host}:{args.port})...")
            sse_app = mcp.sse_app() # Используем глобальный mcp
            uvicorn.run(sse_app, host=args.host, port=args.port)
        except ImportError:
            logger.critical("Uvicorn is not installed. pip install uvicorn")
        except Exception as e:
            logger.critical(f"Failed to start SSE server: {e}", exc_info=True)