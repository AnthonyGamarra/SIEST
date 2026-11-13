import os
import pyodbc


def get_sqlserver_connection():
    host = os.environ["SQLSERVER_HOST"].strip()
    port = os.getenv("SQLSERVER_PORT", "1433").strip()
    database = os.environ["SQLSERVER_DATABASE"].strip()
    user = os.environ["SQLSERVER_USER"].strip()
    password = os.environ["SQLSERVER_PASSWORD"]
    driver = os.environ["SQLSERVER_DRIVER"].strip()

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )

    return pyodbc.connect(
        connection_string,
        timeout=10,
    )