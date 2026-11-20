import os
import re
import secrets
import sqlite3
from datetime import date, datetime
from functools import wraps
from pathlib import Path

import click
from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    send_from_directory,
    url_for,
)
from flask_wtf.csrf import CSRFProtect
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from models import get_db, init_app as init_db_app, init_db

csrf = CSRFProtect()
REPORT_CATEGORIES = (
    "Juegos infantiles dañados",
    "Iluminación defectuosa",
    "Basura acumulada",
    "Bancos rotos",
    "Árboles en mal estado",
    "Problemas de limpieza",
    "Veredas deterioradas",
    "Otros",
)
REPORT_STATUSES = ("Pendiente", "En revisión", "En proceso", "Solucionado")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["PRIVATE_UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    csrf.init_app(app)
    init_db_app(app)

    with app.app_context():
        init_db()

    @app.context_processor
    def inject_shared_data():
        return {
            "today": date.today().isoformat(),
            "statuses_index": lambda status: REPORT_STATUSES.index(status),
        }

    def admin_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("admin_id"):
                flash("Iniciá sesión para acceder al panel.", "info")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        return wrapped

    def save_image(upload, private=False):
        if not upload or not upload.filename:
            return None
        extension = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError("La fotografía debe ser JPG, PNG o WEBP.")
        try:
            image = Image.open(upload.stream)
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("El archivo no contiene una imagen JPG, PNG o WEBP válida.")
            if image.width * image.height > 20_000_000:
                raise ValueError("La imagen es demasiado grande. Reducí sus dimensiones e intentá nuevamente.")
            if (image.format == "JPEG" and extension not in {"jpg", "jpeg"}) or (
                image.format != "JPEG" and image.format.lower() != extension
            ):
                raise ValueError("La extensión del archivo no coincide con su formato de imagen.")
            image.verify()
            upload.stream.seek(0)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValueError("No se pudo leer la imagen adjunta.")
        filename = f"{secrets.token_hex(16)}.{extension}"
        destination = app.config["PRIVATE_UPLOAD_FOLDER"] if private else app.config["UPLOAD_FOLDER"]
        upload.save(Path(destination) / filename)
        return filename

    @app.route("/")
    def index():
        db = get_db()
        stats = {
            "reports": db.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
            "plazas": db.execute("SELECT COUNT(*) FROM plazas").fetchone()[0],
            "solved": db.execute(
                "SELECT COUNT(*) FROM reports WHERE status = 'Solucionado'"
            ).fetchone()[0],
        }
        recent_reports = db.execute(
            """SELECT r.tracking_code, r.category, r.status, r.reported_at, p.name AS plaza_name
               FROM reports r JOIN plazas p ON p.id = r.plaza_id
               ORDER BY r.id DESC LIMIT 3"""
        ).fetchall()
        return render_template("index.html", stats=stats, recent_reports=recent_reports)

    @app.route("/reclamos", methods=["GET", "POST"])
    def complaints():
        db = get_db()
        plazas = db.execute("SELECT id, name, address FROM plazas ORDER BY name").fetchall()
        selected_plaza = request.args.get("plaza", type=int)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            plaza_id = request.form.get("plaza_id", type=int)
            category = request.form.get("category", "")
            description = request.form.get("description", "").strip()
            reported_at = request.form.get("reported_at", "")
            errors = []

            if len(name) > 100:
                errors.append("El nombre no puede superar los 100 caracteres.")
            if email and (len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
                errors.append("Ingresá un correo electrónico válido.")
            if not plaza_id or not db.execute("SELECT 1 FROM plazas WHERE id = ?", (plaza_id,)).fetchone():
                errors.append("Seleccioná una plaza registrada.")
            if category not in REPORT_CATEGORIES:
                errors.append("Seleccioná una categoría válida.")
            if len(description) < 10 or len(description) > 3000:
                errors.append("La descripción debe tener entre 10 y 3000 caracteres.")
            try:
                parsed_date = datetime.strptime(reported_at, "%Y-%m-%d").date()
                if parsed_date > date.today():
                    errors.append("La fecha no puede ser futura.")
            except ValueError:
                errors.append("Ingresá una fecha válida.")

            image_name = None
            if not errors:
                try:
                    image_name = save_image(request.files.get("photo"), private=True)
                except ValueError as error:
                    errors.append(str(error))

            if errors:
                for error in errors:
                    flash(error, "error")
            else:
                tracking_code = None
                for _ in range(5):
                    candidate = secrets.token_hex(8).upper()
                    if not db.execute(
                        "SELECT 1 FROM reports WHERE tracking_code = ?", (candidate,)
                    ).fetchone():
                        tracking_code = candidate
                        break
                if tracking_code is None:
                    abort(500)
                db.execute(
                    """INSERT INTO reports
                       (tracking_code, citizen_name, email, plaza_id, category, description,
                        photo, reported_at, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')""",
                    (
                        tracking_code,
                        name or None,
                        email or None,
                        plaza_id,
                        category,
                        description,
                        image_name,
                        reported_at,
                    ),
                )
                db.commit()
                return redirect(url_for("complaint_confirmation", code=tracking_code))
            selected_plaza = plaza_id

        return render_template(
            "reclamos.html",
            plazas=plazas,
            categories=REPORT_CATEGORIES,
            selected_plaza=selected_plaza,
        )

    @app.route("/reclamos/confirmacion/<code>")
    def complaint_confirmation(code):
        report = get_db().execute(
            "SELECT tracking_code FROM reports WHERE tracking_code = ?", (code.upper(),)
        ).fetchone()
        if not report:
            abort(404)
        return render_template("confirmacion.html", tracking_code=report["tracking_code"])

    @app.route("/mapa")
    def map_view():
        db = get_db()
        plazas = db.execute(
            """SELECT p.id, p.name, p.address, p.latitude, p.longitude, p.description, p.photo,
                      COUNT(r.id) AS report_count,
                      COALESCE(SUM(CASE WHEN r.status = 'Pendiente' THEN 1 ELSE 0 END), 0) AS pending_count,
                      COALESCE(SUM(CASE WHEN r.status = 'En revisión' THEN 1 ELSE 0 END), 0) AS review_count,
                      COALESCE(SUM(CASE WHEN r.status = 'En proceso' THEN 1 ELSE 0 END), 0) AS process_count,
                      COALESCE(SUM(CASE WHEN r.status = 'Solucionado' THEN 1 ELSE 0 END), 0) AS solved_count
               FROM plazas p LEFT JOIN reports r ON r.plaza_id = p.id
               GROUP BY p.id ORDER BY p.name"""
        ).fetchall()
        return render_template("mapa.html", plazas=[dict(row) for row in plazas])

    @app.route("/seguimiento", methods=["GET", "POST"])
    def tracking():
        report = None
        if request.method == "POST":
            code = request.form.get("tracking_code", "").strip().upper()
            report = get_db().execute(
                """SELECT r.tracking_code, r.category, r.description, r.reported_at, r.status,
                          p.name AS plaza_name
                   FROM reports r JOIN plazas p ON p.id = r.plaza_id
                   WHERE r.tracking_code = ?""",
                (code,),
            ).fetchone()
            if not report:
                flash("No encontramos un reclamo con ese código. Revisá los datos e intentá nuevamente.", "error")
        return render_template("seguimiento.html", report=report)

    @app.route("/admin/login", methods=["GET", "POST"])
    def login():
        if session.get("admin_id"):
            return redirect(url_for("admin"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            admin = get_db().execute(
                "SELECT id, username, password_hash FROM admins WHERE username = ?",
                (username,),
            ).fetchone()
            if admin and check_password_hash(admin["password_hash"], password):
                session.clear()
                session["admin_id"] = admin["id"]
                session["admin_username"] = admin["username"]
                session.permanent = True
                return redirect(url_for("admin"))
            flash("Usuario o contraseña incorrectos.", "error")
        return render_template("login.html")

    @app.post("/admin/logout")
    @admin_required
    def logout():
        session.clear()
        flash("Se cerró la sesión.", "success")
        return redirect(url_for("index"))

    @app.get("/admin/reclamos/<int:report_id>/fotografia")
    @admin_required
    def report_photo(report_id):
        report = get_db().execute(
            "SELECT photo FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
        if not report or not report["photo"]:
            abort(404)
        response = send_from_directory(
            current_app.config["PRIVATE_UPLOAD_FOLDER"], report["photo"]
        )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.route("/admin", methods=["GET", "POST"])
    @admin_required
    def admin():
        db = get_db()
        if request.method == "POST":
            report_id = request.form.get("report_id", type=int)
            status = request.form.get("status", "")
            if status not in REPORT_STATUSES:
                flash("El estado seleccionado no es válido.", "error")
            elif not report_id or not db.execute(
                "SELECT 1 FROM reports WHERE id = ?", (report_id,)
            ).fetchone():
                flash("No se encontró el reclamo seleccionado.", "error")
            else:
                db.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
                db.commit()
                flash("Se actualizó el estado del reclamo.", "success")
            return redirect(url_for("admin", **request.args))

        plaza_filter = request.args.get("plaza", type=int)
        category_filter = request.args.get("category", "")
        status_filter = request.args.get("status", "")
        clauses = []
        params = []
        if plaza_filter:
            clauses.append("r.plaza_id = ?")
            params.append(plaza_filter)
        if category_filter in REPORT_CATEGORIES:
            clauses.append("r.category = ?")
            params.append(category_filter)
        if status_filter in REPORT_STATUSES:
            clauses.append("r.status = ?")
            params.append(status_filter)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        reports = db.execute(
            f"""SELECT r.*, p.name AS plaza_name FROM reports r
                JOIN plazas p ON p.id = r.plaza_id {where}
                ORDER BY r.id DESC LIMIT 200""",
            params,
        ).fetchall()
        stats = {
            "reports": db.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
            "plazas": db.execute("SELECT COUNT(*) FROM plazas").fetchone()[0],
            "pending": db.execute(
                "SELECT COUNT(*) FROM reports WHERE status = 'Pendiente'"
            ).fetchone()[0],
            "solved": db.execute(
                "SELECT COUNT(*) FROM reports WHERE status = 'Solucionado'"
            ).fetchone()[0],
        }
        plazas = db.execute("SELECT * FROM plazas ORDER BY name").fetchall()
        return render_template(
            "admin.html",
            reports=reports,
            plazas=plazas,
            stats=stats,
            categories=REPORT_CATEGORIES,
            statuses=REPORT_STATUSES,
            plaza_filter=plaza_filter,
            category_filter=category_filter,
            status_filter=status_filter,
        )

    @app.post("/admin/plazas")
    @admin_required
    def create_plaza():
        name, address, description = (
            request.form.get(field, "").strip()
            for field in ("name", "address", "description")
        )
        try:
            latitude = float(request.form.get("latitude", ""))
            longitude = float(request.form.get("longitude", ""))
        except ValueError:
            latitude, longitude = None, None
        if not name or len(name) > 150 or not address or len(address) > 250:
            flash("El nombre y la dirección de la plaza son obligatorios.", "error")
        elif latitude is None or longitude is None or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            flash("Ingresá coordenadas geográficas válidas.", "error")
        elif len(description) > 1500:
            flash("La descripción no puede superar los 1500 caracteres.", "error")
        else:
            try:
                photo = save_image(request.files.get("photo"))
                db = get_db()
                db.execute(
                    """INSERT INTO plazas (name, address, latitude, longitude, description, photo)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (name, address, latitude, longitude, description or None, photo),
                )
                db.commit()
                flash("La plaza se registró correctamente.", "success")
            except ValueError as error:
                flash(str(error), "error")
        return redirect(url_for("admin") + "#plazas")

    @app.post("/admin/plazas/<int:plaza_id>")
    @admin_required
    def update_plaza(plaza_id):
        db = get_db()
        existing = db.execute("SELECT * FROM plazas WHERE id = ?", (plaza_id,)).fetchone()
        if not existing:
            abort(404)
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()
        description = request.form.get("description", "").strip()
        try:
            latitude = float(request.form.get("latitude", ""))
            longitude = float(request.form.get("longitude", ""))
        except ValueError:
            latitude, longitude = None, None
        if not name or not address or latitude is None or longitude is None or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            flash("Completá nombre, dirección y coordenadas válidas.", "error")
        elif len(name) > 150 or len(address) > 250 or len(description) > 1500:
            flash("Revisá los límites de longitud de los campos.", "error")
        else:
            try:
                photo = save_image(request.files.get("photo"))
            except ValueError as error:
                flash(str(error), "error")
            else:
                db.execute(
                    """UPDATE plazas SET name = ?, address = ?, latitude = ?, longitude = ?,
                       description = ?, photo = ? WHERE id = ?""",
                    (
                        name,
                        address,
                        latitude,
                        longitude,
                        description or None,
                        photo or existing["photo"],
                        plaza_id,
                    ),
                )
                db.commit()
                flash("Se actualizaron los datos de la plaza.", "success")
        return redirect(url_for("admin") + "#plazas")

    @app.post("/admin/plazas/<int:plaza_id>/eliminar")
    @admin_required
    def delete_plaza(plaza_id):
        db = get_db()
        try:
            cursor = db.execute("DELETE FROM plazas WHERE id = ?", (plaza_id,))
            if cursor.rowcount:
                db.commit()
                flash("La plaza se eliminó.", "success")
            else:
                flash("No se encontró esa plaza.", "error")
        except sqlite3.IntegrityError:
            db.rollback()
            flash("No se puede eliminar una plaza que tiene reclamos asociados.", "error")
        return redirect(url_for("admin") + "#plazas")

    @app.cli.command("create-admin")
    @click.option("--username", prompt="Usuario administrador")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, password):
        """Create or update an administrator account."""
        username = username.strip()
        if not username or len(username) > 80 or len(password) < 12:
            raise click.ClickException("El usuario es obligatorio y la contraseña debe tener al menos 12 caracteres.")
        db = get_db()
        db.execute(
            """INSERT INTO admins (username, password_hash) VALUES (?, ?)
               ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash""",
            (username, generate_password_hash(password)),
        )
        db.commit()
        click.echo(f"Administrador '{username}' creado o actualizado.")

    @app.errorhandler(413)
    def too_large(_error):
        flash("La imagen supera el tamaño máximo permitido (5 MB).", "error")
        return redirect(request.referrer or url_for("complaints"), code=303)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
