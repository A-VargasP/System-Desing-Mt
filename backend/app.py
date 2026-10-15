from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import os
import sys

# Asegurar path para imports locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_db_connection

def create_app():
    app = Flask(__name__)
    CORS(app)

    with app.app_context():
        init_db()

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Verificación básica de salud del sistema."""
        conn = None
        try:
            conn = get_db_connection()
            user_count = conn.execute("SELECT COUNT(*) FROM Usuarios_Sistema;").fetchone()[0]
            book_count = conn.execute("SELECT COUNT(*) FROM Libros;").fetchone()[0]
            return jsonify({
                "status": "online",
                "message": "Sistema de Gestión de Préstamos de Biblioteca API activo",
                "stats": {
                    "usuarios_registrados": user_count,
                    "libros_registrados": book_count
                }
            }), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/libros", methods=["GET"])
    def get_libros():
        """Devuelve la lista de todos los libros ordenados alfabéticamente por título."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ISBN, Titulo, Autor, Estado 
                FROM Libros 
                ORDER BY Titulo ASC;
            """)
            libros = [dict(row) for row in cursor.fetchall()]
            return jsonify({
                "success": True,
                "total": len(libros),
                "data": libros
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Error al obtener libros: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/login", methods=["POST"])
    def login():
        """
        Recibe ID_Usuario y Password.
        Verifica estas credenciales en la tabla Usuarios_Sistema.
        Si son correctas, devuelve un mensaje de éxito con el Rol del usuario.
        Si fallan, devuelve error 401.
        """
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "success": False,
                "error": "El cuerpo de la solicitud debe ser un JSON válido."
            }), 400

        id_usuario = str(data.get("ID_Usuario", "")).strip()
        password = str(data.get("Password", "")).strip()

        if not id_usuario or not password:
            return jsonify({
                "success": False,
                "error": "Los campos 'ID_Usuario' y 'Password' son obligatorios."
            }), 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ID_Usuario, Password, Rol 
                FROM Usuarios_Sistema 
                WHERE ID_Usuario = ?;
            """, (id_usuario,))
            usuario = cursor.fetchone()

            if not usuario or usuario["Password"] != password:
                return jsonify({
                    "success": False,
                    "error": "Credenciales incorrectas. Verifique ID_Usuario y Password."
                }), 401

            return jsonify({
                "success": True,
                "message": "Inicio de sesión exitoso.",
                "data": {
                    "ID_Usuario": usuario["ID_Usuario"],
                    "Rol": usuario["Rol"]
                }
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Error al procesar el inicio de sesión: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/estudiantes/registro", methods=["POST"])
    def registrar_estudiante():
        """
        Recibe Nombre, ID_Carnet y Telefono.
        - Validación estricta: Verifica que ID_Carnet sea numérico (.isdigit()) y tenga exactamente 8 dígitos.
        - Inserta el nuevo estudiante en la tabla Estudiantes con Estado_Cuenta = 'Activo'.
        - Si el ID ya existe, devuelve un error 400.
        """
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "success": False,
                "error": "El cuerpo de la solicitud debe ser un JSON válido."
            }), 400

        nombre = str(data.get("Nombre", "")).strip()
        id_carnet = str(data.get("ID_Carnet", "")).strip()
        telefono = str(data.get("Telefono", "")).strip()

        if not nombre or not id_carnet or not telefono:
            return jsonify({
                "success": False,
                "error": "Los campos 'Nombre', 'ID_Carnet' y 'Telefono' son obligatorios."
            }), 400

        # Validación estricta: numérico y longitud exacta de 8 dígitos
        if not id_carnet.isdigit() or len(id_carnet) != 8:
            return jsonify({
                "success": False,
                "error": "El ID debe ser un número de exactamente 8 dígitos."
            }), 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar si el carnet ya existe
            cursor.execute("SELECT ID_Carnet FROM Estudiantes WHERE ID_Carnet = ?;", (id_carnet,))
            if cursor.fetchone():
                return jsonify({
                    "success": False,
                    "error": f"El carnet '{id_carnet}' ya se encuentra registrado."
                }), 400

            cursor.execute("""
                INSERT INTO Estudiantes (ID_Carnet, Nombre, Telefono, Estado_Cuenta)
                VALUES (?, ?, ?, 'Activo');
            """, (id_carnet, nombre, telefono))
            conn.commit()

            return jsonify({
                "success": True,
                "message": "Estudiante registrado exitosamente.",
                "data": {
                    "ID_Carnet": id_carnet,
                    "Nombre": nombre,
                    "Telefono": telefono,
                    "Estado_Cuenta": "Activo"
                }
            }), 201
        except Exception as e:
            if conn:
                conn.rollback()
            return jsonify({
                "success": False,
                "error": f"Error al registrar estudiante: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/estudiantes/<id_carnet>", methods=["GET"])
    def get_estudiante_detalle(id_carnet):
        """
        Revisa el estado del estudiante:
        - Busca al estudiante por su ID de 8 dígitos y devuelve sus datos básicos (Nombre, Teléfono, Estado_Cuenta).
        - JOIN con Prestamos y Libros para buscar préstamos activos (Estado_Prestamo = 'Activo').
        - Devuelve todo en un solo JSON estructurado.
        """
        carnet_clean = str(id_carnet).strip()

        # Validación del formato de carnet
        if not carnet_clean.isdigit() or len(carnet_clean) != 8:
            return jsonify({
                "success": False,
                "error": "El ID debe ser un número de exactamente 8 dígitos."
            }), 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 1. Obtener datos básicos del estudiante
            cursor.execute("""
                SELECT ID_Carnet, Nombre, Telefono, Estado_Cuenta 
                FROM Estudiantes 
                WHERE ID_Carnet = ?;
            """, (carnet_clean,))
            estudiante = cursor.fetchone()

            if not estudiante:
                return jsonify({
                    "success": False,
                    "error": f"No se encontró ningún estudiante con el carnet '{carnet_clean}'."
                }), 404

            # 2. JOIN con Prestamos y Libros para los préstamos con Estado_Prestamo = 'Activo'
            cursor.execute("""
                SELECT 
                    p.ID_Prestamo,
                    l.ISBN,
                    l.Titulo,
                    l.Autor,
                    p.Fecha_Prestamo,
                    p.Fecha_Limite_Devolucion,
                    p.Estado_Prestamo
                FROM Prestamos p
                INNER JOIN Libros l ON p.ISBN = l.ISBN
                WHERE p.ID_Carnet = ? AND p.Estado_Prestamo = 'Activo'
                ORDER BY p.Fecha_Limite_Devolucion ASC;
            """, (carnet_clean,))
            prestamos_activos = [dict(row) for row in cursor.fetchall()]

            return jsonify({
                "success": True,
                "estudiante": {
                    "ID_Carnet": estudiante["ID_Carnet"],
                    "Nombre": estudiante["Nombre"],
                    "Telefono": estudiante["Telefono"],
                    "Estado_Cuenta": estudiante["Estado_Cuenta"]
                },
                "total_prestamos_activos": len(prestamos_activos),
                "prestamos_activos": prestamos_activos
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Error al consultar información del estudiante: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/estudiantes", methods=["POST"])
    def create_estudiante():
        """Alias para mantener compatibilidad con POST /api/estudiantes."""
        return registrar_estudiante()

    @app.route("/api/prestamos", methods=["POST"])
    def create_prestamo():
        """
        Endpoint crítico para registro de préstamos:
        - Verifica que Estado_Cuenta del estudiante sea 'Activo' (si es 'Bloqueado', deniega).
        - Verifica que el estudiante no tenga más de 5 préstamos activos (máximo 5 permitidos).
        - Verifica que el libro esté 'Disponible'.
        - Calcula Fecha_Limite_Devolucion sumando 14 días a la fecha actual.
        - Registra el préstamo y actualiza el Estado del libro a 'Prestado' en una transacción atómica.
        """
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "success": False,
                "error": "El cuerpo de la solicitud debe ser un JSON válido."
            }), 400

        id_carnet = str(data.get("ID_Carnet", "")).strip()
        isbn = str(data.get("ISBN", "")).strip()

        if not id_carnet or not isbn:
            return jsonify({
                "success": False,
                "error": "Los campos 'ID_Carnet' e 'ISBN' son obligatorios."
            }), 400

        # Validación de negocio: ID_Carnet debe ser numérico y tener exactamente 8 dígitos
        if not id_carnet.isdigit() or len(id_carnet) != 8:
            return jsonify({
                "success": False,
                "error": "El ID debe ser un número de exactamente 8 dígitos."
            }), 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 1. Verificar existencia y estado del estudiante
            cursor.execute("SELECT ID_Carnet, Nombre, Estado_Cuenta FROM Estudiantes WHERE ID_Carnet = ?;", (id_carnet,))
            estudiante = cursor.fetchone()
            if not estudiante:
                return jsonify({
                    "success": False,
                    "error": f"El estudiante con carnet '{id_carnet}' no existe en el sistema."
                }), 404

            estado_cuenta = estudiante["Estado_Cuenta"]
            if estado_cuenta != "Activo":
                return jsonify({
                    "success": False,
                    "error": f"Préstamo denegado: el estudiante '{id_carnet}' se encuentra en estado '{estado_cuenta}'."
                }), 403

            # 2. Verificar límite de préstamos activos (máximo 5 activos)
            cursor.execute("""
                SELECT COUNT(*) FROM Prestamos 
                WHERE ID_Carnet = ? AND Estado_Prestamo = 'Activo';
            """, (id_carnet,))
            prestamos_activos_count = cursor.fetchone()[0]

            if prestamos_activos_count >= 5:
                return jsonify({
                    "success": False,
                    "error": f"Préstamo denegado: el estudiante ya alcanzó el límite máximo de préstamos activos permitidos ({prestamos_activos_count}/5)."
                }), 403

            # 3. Verificar existencia y estado del libro
            cursor.execute("SELECT ISBN, Titulo, Estado FROM Libros WHERE ISBN = ?;", (isbn,))
            libro = cursor.fetchone()
            if not libro:
                return jsonify({
                    "success": False,
                    "error": f"El libro con ISBN '{isbn}' no existe en el catálogo."
                }), 404

            if libro["Estado"] != "Disponible":
                return jsonify({
                    "success": False,
                    "error": f"Préstamo denegado: el libro '{libro['Titulo']}' no está disponible (Estado actual: '{libro['Estado']}')."
                }), 409

            # 4. Fechas y registro en transacción atómica
            now = datetime.now()
            fecha_prestamo = now.strftime("%Y-%m-%d %H:%M:%S")

            # Aceptar Fecha_Devolucion / Fecha_Limite_Devolucion enviada por el frontend
            fecha_custom = data.get("Fecha_Devolucion") or data.get("Fecha_Limite_Devolucion")
            if fecha_custom:
                fecha_limite = str(fecha_custom).strip()
                if len(fecha_limite) == 10:  # formato YYYY-MM-DD
                    fecha_limite += " 23:59:59"
            else:
                fecha_limite = (now + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO Prestamos (ID_Carnet, ISBN, Fecha_Prestamo, Fecha_Limite_Devolucion, Estado_Prestamo)
                VALUES (?, ?, ?, ?, 'Activo');
            """, (id_carnet, isbn, fecha_prestamo, fecha_limite))
            id_prestamo = cursor.lastrowid

            cursor.execute("""
                UPDATE Libros 
                SET Estado = 'Prestado' 
                WHERE ISBN = ?;
            """, (isbn,))

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Préstamo registrado exitosamente.",
                "data": {
                    "ID_Prestamo": id_prestamo,
                    "ID_Carnet": id_carnet,
                    "Estudiante": estudiante["Nombre"],
                    "ISBN": isbn,
                    "Libro": libro["Titulo"],
                    "Fecha_Prestamo": fecha_prestamo,
                    "Fecha_Limite_Devolucion": fecha_limite,
                    "Estado_Prestamo": "Activo"
                }
            }), 201

        except Exception as e:
            if conn:
                conn.rollback()
            return jsonify({
                "success": False,
                "error": f"Error al procesar el préstamo: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/prestamos/activos", methods=["GET"])
    def get_prestamos_activos():
        """
        Devuelve una lista (JOIN) con:
        - Nombre del estudiante
        - ID (ID_Prestamo y ID_Carnet)
        - Título del Libro
        - ISBN
        - Teléfono
        - Fecha_Limite_Devolucion
        de todos los préstamos que estén activos.
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.ID_Prestamo AS ID,
                    e.Nombre AS Nombre_Estudiante,
                    e.ID_Carnet,
                    l.Titulo AS Titulo_Libro,
                    l.ISBN,
                    e.Telefono,
                    p.Fecha_Prestamo,
                    p.Fecha_Limite_Devolucion,
                    p.Estado_Prestamo
                FROM Prestamos p
                INNER JOIN Estudiantes e ON p.ID_Carnet = e.ID_Carnet
                INNER JOIN Libros l ON p.ISBN = l.ISBN
                WHERE p.Estado_Prestamo = 'Activo'
                ORDER BY p.Fecha_Limite_Devolucion ASC;
            """)
            prestamos = [dict(row) for row in cursor.fetchall()]

            return jsonify({
                "success": True,
                "total": len(prestamos),
                "data": prestamos
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Error al obtener préstamos activos: {str(e)}"
            }), 500
    @app.route("/api/estudiantes/todos", methods=["GET"])
    def get_todos_estudiantes():
        """Devuelve la lista de todos los estudiantes registrados ordenados por Nombre."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ID_Carnet, Nombre, Telefono, Estado_Cuenta 
                FROM Estudiantes 
                ORDER BY Nombre ASC;
            """)
            estudiantes = [dict(row) for row in cursor.fetchall()]
            return jsonify({
                "success": True,
                "total": len(estudiantes),
                "data": estudiantes
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Error al obtener estudiantes: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/devolucion", methods=["POST"])
    def devolver_libro():
        """
        Recibe ISBN (o ID_Prestamo).
        Busca el préstamo activo correspondiente, actualiza Estado_Prestamo a 'Devuelto'
        y actualiza el Estado del libro a 'Disponible' en una transacción atómica.
        """
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "success": False,
                "error": "El cuerpo de la solicitud debe ser un JSON válido."
            }), 400

        isbn = str(data.get("ISBN", "")).strip()
        id_prestamo = data.get("ID_Prestamo")

        if not isbn and not id_prestamo:
            return jsonify({
                "success": False,
                "error": "Debe proporcionar al menos el 'ISBN' o el 'ID_Prestamo'."
            }), 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Buscar préstamo activo
            if id_prestamo:
                cursor.execute("""
                    SELECT ID_Prestamo, ISBN, ID_Carnet, Estado_Prestamo 
                    FROM Prestamos 
                    WHERE ID_Prestamo = ? AND Estado_Prestamo = 'Activo';
                """, (id_prestamo,))
            else:
                cursor.execute("""
                    SELECT ID_Prestamo, ISBN, ID_Carnet, Estado_Prestamo 
                    FROM Prestamos 
                    WHERE ISBN = ? AND Estado_Prestamo = 'Activo'
                    ORDER BY ID_Prestamo DESC LIMIT 1;
                """, (isbn,))

            prestamo = cursor.fetchone()
            if not prestamo:
                return jsonify({
                    "success": False,
                    "error": "No se encontró ningún préstamo activo para este libro."
                }), 404

            target_prestamo_id = prestamo["ID_Prestamo"]
            target_isbn = prestamo["ISBN"]

            # Actualizar Préstamo a Devuelto
            cursor.execute("""
                UPDATE Prestamos 
                SET Estado_Prestamo = 'Devuelto' 
                WHERE ID_Prestamo = ?;
            """, (target_prestamo_id,))

            # Actualizar Libro a Disponible
            cursor.execute("""
                UPDATE Libros 
                SET Estado = 'Disponible' 
                WHERE ISBN = ?;
            """, (target_isbn,))

            conn.commit()

            return jsonify({
                "success": True,
                "message": "Libro devuelto con éxito.",
                "data": {
                    "ID_Prestamo": target_prestamo_id,
                    "ISBN": target_isbn,
                    "Estado_Libro": "Disponible",
                    "Estado_Prestamo": "Devuelto"
                }
            }), 200

        except Exception as e:
            if conn:
                conn.rollback()
            return jsonify({
                "success": False,
                "error": f"Error al procesar la devolución: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
