CREATE TABLE IF NOT EXISTS machine(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS reservation(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  machine_id INTEGER NOT NULL,
  user TEXT NOT NULL,
  start_ts TEXT,               -- NULL if not started
  duration_min INTEGER,        -- NULL if not started
  finished INTEGER NOT NULL DEFAULT 0,
  front_since_ts TEXT,         -- when became "front of queue"
  remarks TEXT,                -- optional memo entered on Start
  FOREIGN KEY(machine_id) REFERENCES machine(id)
);

CREATE TABLE IF NOT EXISTS op_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,            -- ISO timestamp
  user TEXT NOT NULL,          -- actor
  machine TEXT,                -- machine name
  op TEXT NOT NULL,            -- enqueue/start/finish/cancel
  detail TEXT NOT NULL         -- extra message
);

CREATE TABLE IF NOT EXISTS meta(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
