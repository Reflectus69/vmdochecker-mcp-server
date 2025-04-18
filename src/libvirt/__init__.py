# src/libvirt/__init__.py
import argparse
import os
# Импортируем переменные, которые ТЕПЕРЬ СУЩЕСТВУЮТ в server.py
from .server import mcp, XML_STORAGE_DIR, LIBVIRT_RNG_SCHEMA_PATH

def main():
    """MCP Server for Libvirt VM Management (alternative entry point)."""
    parser = argparse.ArgumentParser(
        description="MCP Server providing tools to generate, validate, save, and start Libvirt VMs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Environment Variables:
  MCP_LIBVIRT_XML_DIR: Directory to store VM XML definitions (default: {XML_STORAGE_DIR})
  MCP_LIBVIRT_RNG_SCHEMA: Path to the Libvirt domain RNG schema directory (default: {LIBVIRT_RNG_SCHEMA_PATH})
"""
    )
    # Этот парсер читает аргументы, но main() их не использует для выбора транспорта
    parser.parse_args()

    print(f"--- Running MCP server via src/libvirt/__init__.py ---")
    print(f"--- NOTE: This entry point ignores --transport/--host/--port arguments and always runs in stdio mode. ---")
    print(f"--- Use 'uv run -m src.libvirt.server ...' to specify transport. ---")
    mcp.run() # Запускает сервер в режиме stdio по умолчанию

# Этот блок позволяет запускать 'uv run -m src.libvirt'
if __name__ == "__main__":
    main()