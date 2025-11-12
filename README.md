# Database Python Client

This module provides a `Database` class to connect to multiple MySQL/MariaDB databases, both directly and through SSH tunnels, and to execute queries simply, returning results as `pandas.DataFrame` or number of modified rows.

## 📁 1. Configuration

The module uses a YAML file (`db_config.yaml`) to configure connections.
Each database has a separate section, identified by a name of your choice.

### 1.1 Basic Example
```yaml
my-beautiful-database:
  db:
    user: username
    password: password
    schema: schema-name         # optional
    host: 203.0.113.42          # optional, default 127.0.0.1
    port: 3306                  # optional, default 3306
  ssh-tunnel:                   # optional
    path-pem: path/to/pem
    admin: ssh-admin
    url: 203.0.113.42
    local-host: 127.0.0.1       # optional, default 127.0.0.1
    local-port: 0               # optional, default 0 (random port)
    remote-host: 127.0.0.1      # optional, default DB host
    remote-port: 3306           # optional, default DB port
    port: 22                    # optional, default SSH 22
```

### 1.2 Configuration without SSH

If you don't want to use SSH, you can completely omit the `ssh-tunnel` section:

```yaml
analytics-db:
  db:
    user: analytics
    password: super-secret
    schema: reports
    host: 203.0.113.42
    port: 3306
```

### 1.3 Multiple databases

You can add multiple sections in the same YAML file:

```yaml
my-beautiful-database:
  db:
    user: my-user
    password: my-password
    schema: beautiful-database

analytics-db:
  db:
    user: analytics
    password: super-secret
    schema: reports
```

Each section is independent, and you can create a `Database` instance for each.

## ⚡ 2. API Usage

### 2.1 Import and create the Database object
```python
from sqlconnector import Database

# Connect to the "my-beautiful-database" database
beautiful_db = Database(config_path="db_config.yaml", section="my-beautiful-database")

# Connect to another DB in the same YAML file
analytics_db = Database(config_path="db_config.yaml", section="analytics-db")
```

### 2.2 Execute SELECT queries (fetch)
```python
df = beautiful_db.fetch("SELECT * FROM users WHERE active = :x", params={"x": 1})
print(df.head())
```

Always returns a `pandas.DataFrame`.

`params` is optional and can be a dictionary for parameterized queries.

### 2.3 Execute modifying queries (modify)
```python
rows = analytics_db.modify(
    "UPDATE users SET active = 0 WHERE last_login < DATE_SUB(NOW(), INTERVAL 1 YEAR)"
)
print(f"Modified rows: {rows}")
```

Returns the number of rows actually modified.

Commit mode is automatic for `modify`.
For read-only queries (`fetch`), no commit is performed.

## ⚠️ 3. Cautions and best practices

### Commit
Only queries executed with `modify()` are committed.
Queries executed with `fetch()` do not modify the database.

### SSH Tunnel
The SSH connection uses a random local port by default (`local-port: 0`).
The tunnel is managed within a `with context`: it is opened only for the duration of the query.

### Multi-database
Each `Database(section)` instance is independent.
You can have multiple simultaneous connections to different databases.

### Parameters
Always use `params` for parameterized queries to avoid SQL injection.
Correct example:
```python
db.fetch("SELECT * FROM users WHERE active = :x", params={"x": 1})
```

### Return types
- `fetch()` → `pandas.DataFrame`
- `modify()` → `int` (modified rows)

## 💡 4. Complete Example
```python
from sqlconnector import Database

# Database with SSH
beautiful_db = Database(config_path="db_config.yaml", section="my-beautiful-database")
df = beautiful_db.fetch("SHOW TABLES;")
print(df)

# Database without SSH
analytics_db = Database(config_path="db_config.yaml", section="analytics-db")
rows = analytics_db.modify(
    "UPDATE users SET active = 0 WHERE last_login < DATE_SUB(NOW(), INTERVAL 1 YEAR)"
)
print(f"Modified rows: {rows}")
```
