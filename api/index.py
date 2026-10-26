import logging
import os
import sys

# Permite importar servicios.py (está en la raíz, un nivel arriba de /api)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from flask import Flask, flash, redirect, render_template, request, session, url_for

from servicios import CServicios

try:  # solo para desarrollo local; en Vercel las variables ya existen
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("La variable de entorno SECRET_KEY no está definida.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),  # HTTPS solo en Vercel
)

servicios = CServicios()
log = logging.getLogger(__name__)


@app.route("/")
def index():
    cedula = session.get("cedula")
    if not cedula:
        return redirect(url_for("login"))

    try:
        usuario = servicios.consultar_usuario(cedula)
    except Exception:
        log.exception("Error consultando el usuario")
        flash("No se pudo consultar la base de datos. Intenta de nuevo.", "error")
        return redirect(url_for("login"))

    if usuario is None:  # el usuario ya no existe en la BD
        session.clear()
        flash("Tu usuario ya no existe. Inicia sesión de nuevo.", "error")
        return redirect(url_for("login"))

    return render_template("index.html", usuario=usuario)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        accion = request.form.get("accion")
        cedula = request.form.get("cedula", "").strip()
        clave = request.form.get("clave", "")

        try:
            if accion == "registro":
                nombre = request.form.get("nombre", "").strip()
                if not cedula or not nombre or not clave:
                    flash("Todos los campos son obligatorios.", "error")
                elif len(cedula) > 20 or len(nombre) > 100:
                    flash("Cédula (máx. 20) o nombre (máx. 100) demasiado largos.", "error")
                elif len(clave) < 6:
                    flash("La contraseña debe tener al menos 6 caracteres.", "error")
                else:
                    ok, mensaje = servicios.registrar_usuario(cedula, nombre, clave)
                    flash(mensaje, "exito" if ok else "error")

            elif accion == "login":
                if not cedula or not clave:
                    flash("Ingresa cédula y contraseña.", "error")
                else:
                    usuario = servicios.iniciar_sesion(cedula, clave)
                    if usuario:
                        session.clear()
                        session["cedula"] = usuario["id_cliente"]
                        return redirect(url_for("index"))
                    flash("Cédula o contraseña incorrectas.", "error")
            else:
                flash("Acción no válida.", "error")

        except Exception:
            log.exception("Error en /login")
            flash("Error de conexión con la base de datos.", "error")

        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "exito")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)