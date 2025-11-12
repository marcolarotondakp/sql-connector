from pathlib import Path
from typing import Any, Literal, overload
from urllib.parse import quote_plus

import yaml
from sqlalchemy import create_engine, text
from sshtunnel import SSHTunnelForwarder
import pandas as pd


class Database:
    def __init__(self, config_path: str, section: str) -> None:
        """
         Initialize a Database instance with configuration from a YAML file.

        Args:
            config_path (str): Path to the YAML configuration file
            section (str): The section name in the config file to use

        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the specified section is not found in the config file
        """
        path = Path(config_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as file:
            config = yaml.safe_load(file)
        if section not in config:
            raise ValueError(f"Section {section} not found in config file")
        self.config = config[section]

    @overload
    def _execute_query(
        self,
        query: str,
        params: dict[str, Any] | list[dict[str, Any]] | None = None,
        *,
        commit: Literal[False] = False,
        schema: str | None,
    ) -> pd.DataFrame: ...

    @overload
    def _execute_query(
        self,
        query: str,
        params: dict[str, Any] | list[dict[str, Any]] | None = None,
        *,
        commit: Literal[True],
        schema: str | None = None,
    ) -> int: ...

    def _execute_query(
        self,
        query: str,
        params: dict | list[dict] | None = None,
        commit: bool = False,
        schema: str | None = None,
    ) -> pd.DataFrame | int:
        ssh_config = self.config.get("ssh-tunnel")
        db_config = self.config["db"]
        db_host = db_config.get("host", "127.0.0.1")
        db_port = db_config.get("port", 3306)
        schema = schema or db_config.get("schema")

        if ssh_config:
            local_host = ssh_config.get("local-host", "127.0.0.1")
            local_port = ssh_config.get("local-port", 0)
            remote_host = ssh_config.get("remote-host", db_host)
            remote_port = ssh_config.get("remote-port", db_port)
            ssh_port = ssh_config.get("port", 22)

            with SSHTunnelForwarder(
                ssh_address_or_host=(ssh_config["url"], ssh_port),
                ssh_username=ssh_config["admin"],
                ssh_pkey=ssh_config["path-pem"],
                remote_bind_address=(remote_host, remote_port),
                local_bind_address=(local_host, local_port),
            ) as tunnel:
                assert isinstance(tunnel, SSHTunnelForwarder)
                assigned_local_port = tunnel.local_bind_port
                connection_url = f"mysql+pymysql://{db_config['user']}:{quote_plus(db_config['password'])}@{local_host}:{assigned_local_port}"

                return self._run_query(
                    connection_url=connection_url,
                    commit=commit,
                    query=query,
                    params=params,
                    schema=schema,
                )

        else:
            connection_url = f"mysql+pymysql://{db_config['user']}:{quote_plus(db_config['password'])}@{db_host}:{db_port}"

            return self._run_query(
                connection_url=connection_url,
                commit=commit,
                query=query,
                params=params,
                schema=schema,
            )

    def _run_query(
        self,
        connection_url: str,
        commit: bool,
        query: str,
        params: dict | list[dict] | None,
        schema: str | None,
    ) -> pd.DataFrame | int:
        if schema is not None:
            connection_url += f"/{schema}"
        with create_engine(connection_url).connect() as connection:
            result = connection.execute(text(query), params)
            if commit:
                connection.commit()
                return result.rowcount
            dataframe = pd.DataFrame(result.fetchall(), columns=pd.Index(result.keys()))
            return dataframe

    def fetch(
        self, query: str, params: dict | None = None, schema: str | None = None
    ) -> pd.DataFrame:
        """
         Execute a SELECT query and return results as a DataFrame.

        This method is designed for read-only queries that fetch data from the database.
        No database modifications or commits are performed.

        Args:
            query (str): The SQL SELECT query to execute
            params (dict | None, optional): Parameters for the query. Defaults to None.
            schema (str | None, optional): Database schema to use. If None, uses the schema
                                          from the configuration. Defaults to None.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the query results, where columns
                         correspond to the selected fields and rows to the returned records.
        """
        return self._execute_query(query=query, params=params, schema=schema)

    def modify(
        self,
        query: str,
        params: dict | list[dict] | None = None,
        schema: str | None = None,
    ) -> int:
        """
         Execute a query that modifies the database and return the number of affected rows.

        This method is designed for queries that change data (INSERT, UPDATE, DELETE).
        Changes are automatically committed to the database.

        Args:
            query (str): The SQL modification query to execute
            params (dict | list[dict] | None, optional): Parameters for the query.
                                                        Can be a single dict or a list of dicts for
                                                        bulk operations. Defaults to None.
            schema (str | None, optional): Database schema to use. If None, uses the schema
                                          from the configuration. Defaults to None.

        Returns:
            int: The number of rows affected by the query
        """
        return self._execute_query(
            query=query, params=params, commit=True, schema=schema
        )
