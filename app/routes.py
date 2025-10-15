from datetime import datetime, timedelta

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .db import connect, log_op_tx, touch_last_update

bp = Blueprint("laundry", __name__)


def db():
    return connect(current_app.config["DB_PATH"])


@bp.get("/")
def home():
    with db() as c:
        machines = c.execute("SELECT * FROM machine ORDER BY id").fetchall()
        queues = {}
        running_counts = {}
        waiting_counts = {}
        startable_map = {}
        did_mutate = False

        now = datetime.now()
        server_now_ms = int(now.timestamp() * 1000)

        for m in machines:
            rows = c.execute(
                """
              SELECT * FROM reservation
              WHERE machine_id=? AND finished=0
            """,
                (m["id"],),
            ).fetchall()

            running = [r for r in rows if r["start_ts"] is not None]
            waiting = [r for r in rows if r["start_ts"] is None]

            running.sort(key=lambda r: (r["start_ts"] or "9999-12-31", r["id"]))
            waiting.sort(key=lambda r: r["id"])

            running_counts[m["id"]] = len(running)
            waiting_counts[m["id"]] = len(waiting)

            cap = m["max_concurrent"] if "max_concurrent" in m.keys() else 1
            slots = max(0, cap - len(running))
            startable_ids = set([w["id"] for w in waiting[:slots]])

            # maintain front_since_ts
            for w in waiting:
                if (w["id"] in startable_ids) and (w["front_since_ts"] is None):
                    cur = c.execute(
                        "UPDATE reservation SET front_since_ts=? WHERE id=?",
                        (now.isoformat(timespec="seconds"), w["id"]),
                    )
                    if cur.rowcount:
                        did_mutate = True
                if (w["id"] not in startable_ids) and (w["front_since_ts"] is not None):
                    cur = c.execute(
                        "UPDATE reservation SET front_since_ts=NULL WHERE id=?",
                        (w["id"],),
                    )
                    if cur.rowcount:
                        did_mutate = True

            # re-read after updates
            rows2 = c.execute(
                """
              SELECT * FROM reservation
              WHERE machine_id=? AND finished=0
            """,
                (m["id"],),
            ).fetchall()
            running = [r for r in rows2 if r["start_ts"] is not None]
            waiting = [r for r in rows2 if r["start_ts"] is None]
            running.sort(key=lambda r: (r["start_ts"] or "9999-12-31", r["id"]))
            waiting.sort(key=lambda r: r["id"])

            ordered = running + waiting
            q = []
            for r in ordered:
                started = r["start_ts"] is not None
                start = datetime.fromisoformat(r["start_ts"]) if started else None
                end = (
                    (start + timedelta(minutes=r["duration_min"])) if started else None
                )
                grace_end = (end + timedelta(minutes=30)) if started else None
                front_since_str = r["front_since_ts"]
                front_since_dt = (
                    datetime.fromisoformat(front_since_str) if front_since_str else None
                )
                end_ms = int(end.timestamp() * 1000) if end else None
                grace_ms = int(grace_end.timestamp() * 1000) if grace_end else None
                front_since_ms = (
                    int(front_since_dt.timestamp() * 1000) if front_since_dt else None
                )
                remarks = (r["remarks"] or "").strip()
                q.append(
                    {
                        "id": r["id"],
                        "user": r["user"],
                        "started": started,
                        "start": start,
                        "end": end,
                        "grace_end": grace_end,
                        "end_ms": end_ms,
                        "grace_end_ms": grace_ms,
                        "finished": r["finished"],
                        "front_since": r["front_since_ts"]
                        if r["front_since_ts"]
                        else "",
                        "front_since_ms": front_since_ms,
                        "has_remarks": bool(remarks),
                        "remarks": remarks,
                    }
                )
            queues[m["id"]] = q
            startable_map[m["id"]] = startable_ids

        if did_mutate:
            touch_last_update(c)

        meta_row = c.execute(
            "SELECT value FROM meta WHERE key='last_update_ms'"
        ).fetchone()
        try:
            last_update_ms = (
                int(meta_row["value"]) if meta_row and meta_row["value"] else server_now_ms
            )
        except (TypeError, ValueError):
            last_update_ms = server_now_ms

    return render_template(
        "index.html",
        machines=machines,
        queues=queues,
        running_counts=running_counts,
        waiting_counts=waiting_counts,
        startable_map=startable_map,
        server_now_ms=server_now_ms,
        last_update_ms=last_update_ms,
    )


# ----- Machines -----


@bp.get("/machines/new")
def new_machine():
    return render_template("start.html", is_add_machine=True)


@bp.post("/machines/add")
def add_machine():
    name = request.form["name"].strip()
    try:
        max_concurrent = int(request.form.get("max_concurrent", "1"))
    except ValueError:
        max_concurrent = 1
    if max_concurrent < 1:
        max_concurrent = 1
    if name:
        with db() as c:
            try:
                cur = c.execute(
                    "INSERT INTO machine(name, max_concurrent) VALUES(?,?)",
                    (name, max_concurrent),
                )
                if cur.rowcount:
                    touch_last_update(c)
            except Exception:
                pass
    return redirect(url_for("laundry.home"))


@bp.post("/machines/delete/<int:machine_id>")
def delete_machine(machine_id):
    with db() as c:
        res_deleted = c.execute(
            "DELETE FROM reservation WHERE machine_id=?", (machine_id,)
        ).rowcount
        mach_deleted = c.execute(
            "DELETE FROM machine WHERE id=?", (machine_id,)
        ).rowcount
        if res_deleted or mach_deleted:
            touch_last_update(c)
    return redirect(url_for("laundry.home"))


# ----- Queue ops -----


@bp.post("/enqueue/<int:machine_id>")
def enqueue(machine_id):
    user = request.form["user"].strip()
    if not user:
        return redirect(url_for("laundry.home"))
    with db() as c:
        cur = c.execute(
            """INSERT INTO reservation(machine_id,user,finished)
                     VALUES(?,?,0)""",
            (machine_id, user),
        )
        m = c.execute("SELECT name FROM machine WHERE id=?", (machine_id,)).fetchone()
        log_op_tx(c, user, "enqueue", m["name"], "joined queue")
        if cur.rowcount:
            touch_last_update(c)
    return redirect(url_for("laundry.home"))


@bp.get("/start/<int:res_id>")
def start_form(res_id):
    with db() as c:
        r = c.execute(
            """
            SELECT r.*, m.name AS mname, m.max_concurrent AS cap
            FROM reservation r JOIN machine m ON m.id=r.machine_id
            WHERE r.id=?
        """,
            (res_id,),
        ).fetchone()
        if not r or r["finished"]:
            abort(404)

        running = c.execute(
            """
            SELECT id FROM reservation
            WHERE machine_id=? AND finished=0 AND start_ts IS NOT NULL
            ORDER BY datetime(start_ts) ASC
        """,
            (r["machine_id"],),
        ).fetchall()
        waiting = c.execute(
            """
            SELECT id FROM reservation
            WHERE machine_id=? AND finished=0 AND start_ts IS NULL
            ORDER BY id ASC
        """,
            (r["machine_id"],),
        ).fetchall()

        cap = r["cap"] or 1
        slots = max(0, cap - len(running))
        allowed_ids = [row["id"] for row in waiting[:slots]]

        if r["start_ts"] is not None or res_id not in allowed_ids:
            return redirect(url_for("laundry.home"))

    # reuse start.html to show the Start form (remarks under time fields)
    return render_template(
        "start.html",
        is_add_machine=False,
        res_id=res_id,
        user=r["user"],
        machine=r["mname"],
    )


@bp.post("/start/<int:res_id>")
def start_job(res_id):
    hours = int(request.form.get("hours", "0"))
    minutes = int(request.form.get("minutes", "0"))
    total = hours * 60 + minutes
    remarks = (request.form.get("remarks", "") or "").strip()
    if total <= 0:
        return redirect(url_for("laundry.start_form", res_id=res_id))
    now_iso = datetime.now().isoformat(timespec="seconds")
    with db() as c:
        r = c.execute(
            """
            SELECT r.*, m.name AS mname, m.max_concurrent AS cap
            FROM reservation r JOIN machine m ON m.id=r.machine_id
            WHERE r.id=?
        """,
            (res_id,),
        ).fetchone()
        if not r or r["finished"]:
            abort(404)

        running = c.execute(
            """
            SELECT id FROM reservation
            WHERE machine_id=? AND finished=0 AND start_ts IS NOT NULL
            ORDER BY datetime(start_ts) ASC
        """,
            (r["machine_id"],),
        ).fetchall()
        waiting = c.execute(
            """
            SELECT id FROM reservation
            WHERE machine_id=? AND finished=0 AND start_ts IS NULL
            ORDER BY id ASC
        """,
            (r["machine_id"],),
        ).fetchall()

        cap = r["cap"] or 1
        slots = max(0, cap - len(running))
        allowed_ids = [row["id"] for row in waiting[:slots]]

        if r["start_ts"] is not None or res_id not in allowed_ids:
            return redirect(url_for("laundry.home"))

        cur = c.execute(
            "UPDATE reservation SET start_ts=?, duration_min=?, front_since_ts=NULL, remarks=? WHERE id=?",
            (now_iso, total, remarks, res_id),
        )

        detail = f"duration_min={total}"
        if remarks:
            detail += f"; remarks={remarks}"
        log_op_tx(c, r["user"], "start", r["mname"], detail)
        if cur.rowcount:
            touch_last_update(c)

    return redirect(url_for("laundry.home"))


@bp.post("/finish/<int:res_id>")
def finish_res(res_id):
    with db() as c:
        r = c.execute(
            """
            SELECT r.*, m.name AS mname
            FROM reservation r JOIN machine m ON m.id=r.machine_id
            WHERE r.id=?
        """,
            (res_id,),
        ).fetchone()
        if not r:
            return redirect(url_for("laundry.home"))
        cur = c.execute("UPDATE reservation SET finished=1 WHERE id=?", (res_id,))
        log_op_tx(c, r["user"], "finish", r["mname"], "marked done")
        if cur.rowcount:
            touch_last_update(c)
    return redirect(url_for("laundry.home"))


@bp.post("/cancel/<int:res_id>")
def cancel_res(res_id):
    with db() as c:
        r = c.execute(
            """
            SELECT r.*, m.name AS mname
            FROM reservation r JOIN machine m ON m.id=r.machine_id
            WHERE r.id=?
        """,
            (res_id,),
        ).fetchone()
        if not r or r["finished"]:
            return redirect(url_for("laundry.home"))
        if r["start_ts"] is not None:
            return redirect(url_for("laundry.home"))
        cur = c.execute("DELETE FROM reservation WHERE id=?", (res_id,))
        log_op_tx(c, r["user"], "cancel", r["mname"], "cancelled before start")
        if cur.rowcount:
            touch_last_update(c)
    return redirect(url_for("laundry.home"))


# ----- Logs (last 7 days) -----


@bp.get("/logs")
def logs_page():
    since = datetime.now() - timedelta(days=7)
    since_iso = since.isoformat(timespec="seconds")
    with db() as c:
        logs = c.execute(
            """
            SELECT * FROM op_log
            WHERE datetime(ts) >= datetime(?)
            ORDER BY datetime(ts) DESC, id DESC
            LIMIT 500
        """,
            (since_iso,),
        ).fetchall()
    return render_template(
        "logs.html", logs=logs, since_human=since.strftime("%Y-%m-%d %H:%M:%S")
    )


@bp.get("/sync-state")
def sync_state():
    now = datetime.now()
    server_now_ms = int(now.timestamp() * 1000)
    with db() as c:
        meta_row = c.execute(
            "SELECT value FROM meta WHERE key='last_update_ms'"
        ).fetchone()
    try:
        last_update_ms = (
            int(meta_row["value"]) if meta_row and meta_row["value"] else server_now_ms
        )
    except (TypeError, ValueError):
        last_update_ms = server_now_ms
    return jsonify(
        {
            "server_now_ms": server_now_ms,
            "last_update_ms": last_update_ms,
        }
    )
