# src/libvirt/config.py
"""
Конфигурационный файл для сервиса валидации Libvirt XML.
"""
from pathlib import Path

# --- Константы Валидатора ---

# Имя директории, где хранятся схемы RelaxNG
SCHEMAS_DIR_NAME = "schemas"

# Карта соответствия ожидаемых корневых тегов XML
# и базовых имен файлов схем .rng (без расширения)
SCHEMA_FILENAME_MAP = {
    'domain': 'domain',
    'network': 'network',
    'pool': 'storagepool',
    'volume': 'storagevol',
    'secret': 'secret',
    'interface': 'interface',
    'nodedev': 'nodedev',
    'domainsnapshot': 'domainsnapshot',
    'capability': 'capability',
    'networkport': 'networkport',
    'nwfilter': 'nwfilter',
    'nwfilterbinding': 'nwfilterbinding',
    'domainbackup': 'domainbackup',
    'domaincheckpoint': 'domaincheckpoint',
}

# --- Константы Сервера ---
# Имя директории по умолчанию для хранения XML-файлов ВМ
DEFAULT_XML_STORAGE_DIR = "libvirt_xml_definitions"

# Можно добавить и другие настройки по умолчанию, если нужно
# DEFAULT_HOST = "127.0.0.1"
# DEFAULT_PORT = 8000
# DEFAULT_TRANSPORT = "stdio"