import pytest
import logging
from doltpy.sql import DoltSQLServerContext, ServerConfig
from tests.sql_sync.helpers.data_helper import (
    TEST_DATA_INITIAL,
    TEST_DATA_APPEND_SINGLE_ROW,
    TEST_DATA_APPEND_MULTIPLE_ROWS,
    TEST_TABLE_METADATA,
    DOLT_TABLE_WITH_ARRAYS,
    get_dolt_update_row_statement,
    get_dolt_drop_pk_query
)
from typing import Tuple
from sqlalchemy import Table, MetaData
import yaml
import os

logger = logging.getLogger(__name__)


@pytest.fixture
def with_db_config(tmp_path):
    conf_path = os.path.join(tmp_path, 'server_conf.yaml')
    conf = {
        'listener': {
            'max_connections': 3
        }
    }

    with open(conf_path, 'w') as f:
        yaml.dump(conf, stream=f)

    return ServerConfig(user='root', config=conf_path)


@pytest.fixture
def db_with_table(request, init_empty_test_repo, with_db_config) -> Tuple[DoltSQLServerContext, Table]:
    dssc = DoltSQLServerContext(init_empty_test_repo, with_db_config)
    return _test_table_helper(dssc, request, TEST_TABLE_METADATA)


@pytest.fixture
def db_with_table_with_arrays(request, init_empty_test_repo, with_db_config) -> Tuple[DoltSQLServerContext, Table]:
    dssc = DoltSQLServerContext(init_empty_test_repo, with_db_config)
    return _test_table_helper(dssc, request, DOLT_TABLE_WITH_ARRAYS)


@pytest.fixture
def empty_db_with_server_process(request, init_empty_test_repo, with_db_config) -> DoltSQLServerContext:
    dssc = DoltSQLServerContext(init_empty_test_repo, with_db_config)
    _server_helper(dssc, request)
    return dssc


def _test_table_helper(dssc: DoltSQLServerContext,
                       request, metadata: MetaData) -> Tuple[DoltSQLServerContext, Table]:
    _server_helper(dssc, request)
    metadata.create(dssc.engine)
    return dssc, metadata


def _server_helper(dssc: DoltSQLServerContext, request):
    dssc.start_server()

    def finalize():
        if dssc.server:
            dssc.stop_server()

    dssc.verify_connection()
    request.addfinalizer(finalize)


@pytest.fixture
def create_dolt_test_data_commits(db_with_table) -> Tuple[DoltSQLServerContext, Table]:
    dssc, table = db_with_table

    dssc.write_rows(str(table.name), TEST_DATA_INITIAL, commit=True)
    dssc.write_rows(str(table.name), TEST_DATA_APPEND_SINGLE_ROW, commit=True)
    dssc.write_rows(str(table.name), TEST_DATA_APPEND_MULTIPLE_ROWS, commit=True)

    # TODO: we currently do not support ON DUPLICATE KEY syntax, so this does the update
    # write_to_table(db, table, TEST_DATA_UPDATE_SINGLE_ROW, commit=True)
    dssc.execute(get_dolt_update_row_statement(table), True, 'Updated a row')
    dssc.execute(get_dolt_drop_pk_query(table), True, 'Dropped a row')

    return dssc, table
