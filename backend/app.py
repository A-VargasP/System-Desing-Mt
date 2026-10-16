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
                SELECT ISBN, Titulo, Autor, Categoria, Estado 
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
        
        # Soportar 'isbns' (arreglo) y también compatibilidad hacia atrás si llega un solo 'ISBN'
        raw_isbns = data.get("isbns")
        if raw_isbns is None and data.get("ISBN"):
            raw_isbns = [data.get("ISBN")]
            
        if not isinstance(raw_isbns, list):
            return jsonify({
                "success": False,
                "error": "El campo 'isbns' debe ser un arreglo de identificadores ISBN."
            }), 400

        # Limpiar lista de ISBNs y remover vacíos/duplicados preservando orden
        isbns = []
        for x in raw_isbns:
            cleaned = str(x).strip()
            if cleaned and cleaned not in isbns:
                isbns.append(cleaned)

        if not id_carnet or len(isbns) == 0:
            return jsonify({
                "success": False,
                "error": "Los campos 'ID_Carnet' e 'isbns' (al menos un ISBN) son obligatorios."
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

            # 1. Verificar existencia y estado del estudiante (no debe estar 'Bloqueado')
            cursor.execute("SELECT ID_Carnet, Nombre, Estado_Cuenta FROM Estudiantes WHERE ID_Carnet = ?;", (id_carnet,))
            estudiante = cursor.fetchone()
            if not estudiante:
                return jsonify({
                    "success": False,
                    "error": f"El estudiante con carnet '{id_carnet}' no existe en el sistema."
                }), 404

            estado_cuenta = estudiante["Estado_Cuenta"]
            if estado_cuenta == "Bloqueado" or estado_cuenta != "Activo":
                return jsonify({
                    "success": False,
                    "error": f"Préstamo denegado: el estudiante '{id_carnet}' se encuentra en estado '{estado_cuenta}'."
                }), 403

            # 2. Verificar límite de préstamos activos (máximo 5 libros en total)
            cursor.execute("""
                SELECT COUNT(*) FROM Prestamos 
                WHERE ID_Carnet = ? AND Estado_Prestamo = 'Activo';
            """, (id_carnet,))
            prestamos_activos_count = cursor.fetchone()[0]

            if prestamos_activos_count + len(isbns) > 5:
                return jsonify({
                    "success": False,
                    "error": "Límite excedido. El estudiante solo puede tener un máximo de 5 libros prestados en total"
                }), 400

            # 3. Verificar que todos los libros existan y estén en estado 'Disponible'
            libros_info = []
            for item_isbn in isbns:
                cursor.execute("SELECT ISBN, Titulo, Estado FROM Libros WHERE ISBN = ?;", (item_isbn,))
                libro = cursor.fetchone()
                if not libro:
                    return jsonify({
                        "success": False,
                        "error": f"El libro con ISBN '{item_isbn}' no existe en el catálogo."
                    }), 404

                if libro["Estado"] != "Disponible":
                    return jsonify({
                        "success": False,
                        "error": f"Préstamo denegado: el libro '{libro['Titulo']}' no está disponible (Estado actual: '{libro['Estado']}')."
                    }), 409
                libros_info.append(libro)

            # 4. Fechas y registro en transacción atómica (Batch Processing)
            now = datetime.now()
            fecha_prestamo = now.strftime("%Y-%m-%d %H:%M:%S")

            # Aceptar fecha_devolucion / Fecha_Devolucion / Fecha_Limite_Devolucion
            fecha_custom = data.get("fecha_devolucion") or data.get("Fecha_Devolucion") or data.get("Fecha_Limite_Devolucion")
            if fecha_custom:
                fecha_limite = str(fecha_custom).strip()
                if len(fecha_limite) == 10:  # formato YYYY-MM-DD
                    fecha_limite += " 23:59:59"
            else:
                fecha_limite = (now + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")

            # Procesamiento por lotes: bucle para insertar en Prestamos y actualizar Libros
            prestamos_creados = []
            for libro in libros_info:
                cursor.execute("""
                    INSERT INTO Prestamos (ID_Carnet, ISBN, Fecha_Prestamo, Fecha_Limite_Devolucion, Estado_Prestamo)
                    VALUES (?, ?, ?, ?, 'Activo');
                """, (id_carnet, libro["ISBN"], fecha_prestamo, fecha_limite))
                id_prestamo = cursor.lastrowid

                cursor.execute("""
                    UPDATE Libros 
                    SET Estado = 'Prestado' 
                    WHERE ISBN = ?;
                """, (libro["ISBN"],))

                prestamos_creados.append({
                    "ID_Prestamo": id_prestamo,
                    "ISBN": libro["ISBN"],
                    "Titulo": libro["Titulo"]
                })

            conn.commit()

            return jsonify({
                "success": True,
                "message": f"Préstamo de {len(prestamos_creados)} libro(s) registrado exitosamente.",
                "data": {
                    "ID_Carnet": id_carnet,
                    "Estudiante": estudiante["Nombre"],
                    "Libros_Prestados": prestamos_creados,
                    "Total_Libros": len(prestamos_creados),
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
                "error": f"Error al procesar el préstamo múltiple: {str(e)}"
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

    @app.route("/api/estudiantes/<id_carnet>", methods=["DELETE"])
    def eliminar_estudiante(id_carnet):
        """
        Permite borrar registros de estudiantes.
        Antes de hacer el DELETE en la tabla Estudiantes, consulta la tabla Prestamos.
        Si el estudiante tiene libros con Estado_Prestamo = 'Activo', cancela la operación
        y devuelve un error HTTP 400 ('No se puede eliminar al estudiante porque tiene libros pendientes').
        Si no tiene préstamos activos, procede a eliminarlo.
        """
        carnet_clean = str(id_carnet).strip()
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar existencia del estudiante
            cursor.execute("SELECT ID_Carnet, Nombre FROM Estudiantes WHERE ID_Carnet = ?;", (carnet_clean,))
            est = cursor.fetchone()
            if not est:
                return jsonify({
                    "success": False,
                    "error": f"No se encontró el estudiante con carnet '{carnet_clean}'."
                }), 404

            # Consultar préstamos con Estado_Prestamo = 'Activo'
            cursor.execute("""
                SELECT COUNT(*) FROM Prestamos 
                WHERE ID_Carnet = ? AND Estado_Prestamo = 'Activo';
            """, (carnet_clean,))
            prestamos_activos = cursor.fetchone()[0]

            if prestamos_activos > 0:
                return jsonify({
                    "success": False,
                    "error": "No se puede eliminar al estudiante porque tiene libros pendientes"
                }), 400

            # Eliminar historial de préstamos devueltos/cerrados si existen para integridad referencial
            cursor.execute("DELETE FROM Prestamos WHERE ID_Carnet = ?;", (carnet_clean,))

            # Eliminar estudiante
            cursor.execute("DELETE FROM Estudiantes WHERE ID_Carnet = ?;", (carnet_clean,))
            conn.commit()

            return jsonify({
                "success": True,
                "message": f"Estudiante '{est['Nombre']}' eliminado exitosamente."
            }), 200

        except Exception as e:
            if conn:
                conn.rollback()
            return jsonify({
                "success": False,
                "error": f"Error al eliminar estudiante: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/usuarios/gestor", methods=["POST"])
    def crear_gestor():
        """
        Permite al 'Admin_Absoluto' crear nuevos perfiles tipo 'Gestor'.
        Recibe ID_Usuario y Password, y los inserta en Usuarios_Sistema asignando forzosamente el Rol = 'Gestor'.
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

            # Verificar si ya existe el ID_Usuario
            cursor.execute("SELECT ID_Usuario FROM Usuarios_Sistema WHERE ID_Usuario = ?;", (id_usuario,))
            if cursor.fetchone():
                return jsonify({
                    "success": False,
                    "error": f"El usuario '{id_usuario}' ya se encuentra registrado."
                }), 400

            # Forzar Rol = 'Gestor'
            cursor.execute("""
                INSERT INTO Usuarios_Sistema (ID_Usuario, Password, Rol)
                VALUES (?, ?, 'Gestor');
            """, (id_usuario, password))
            conn.commit()

            return jsonify({
                "success": True,
                "message": f"Gestor '{id_usuario}' creado exitosamente.",
                "data": {
                    "ID_Usuario": id_usuario,
                    "Rol": "Gestor"
                }
            }), 201

        except Exception as e:
            if conn:
                conn.rollback()
            return jsonify({
                "success": False,
                "error": f"Error al registrar gestor: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/usuarios/<id_usuario>", methods=["DELETE"])
    def eliminar_usuario(id_usuario):
        """
        Permite al 'Admin_Absoluto' eliminar a un 'Gestor'.
        Verifica que el usuario a eliminar NO sea el propio 'Admin_Absoluto'
        (para no dejar el sistema sin admin principal). Si intenta borrarse a sí mismo, devuelve error 400.
        """
        target_usuario = str(id_usuario).strip()

        # Validación inmediata: impedir eliminar al usuario principal 'admin'
        if target_usuario.lower() == "admin":
            return jsonify({
                "success": False,
                "error": "No se puede eliminar la cuenta de Admin Absoluto del sistema"
            }), 400

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Verificar existencia y rol del usuario objetivo
            cursor.execute("SELECT ID_Usuario, Rol FROM Usuarios_Sistema WHERE ID_Usuario = ?;", (target_usuario,))
            user = cursor.fetchone()

            if not user:
                return jsonify({
                    "success": False,
                    "error": f"No se encontró el usuario '{target_usuario}'."
                }), 404

            # Si el usuario tiene el rol 'Admin_Absoluto', abortar inmediatamente
            if user["Rol"] == "Admin_Absoluto":
                return jsonify({
                    "success": False,
                    "error": "No se puede eliminar la cuenta de Admin Absoluto del sistema"
                }), 400

            # Solo permitir ejecutar la sentencia DELETE si el rol es estrictamente 'Gestor'
            if user["Rol"] != "Gestor":
                return jsonify({
                    "success": False,
                    "error": "Operación denegada: solo se pueden eliminar usuarios con rol 'Gestor'."
                }), 403

            # Proceder a eliminar al Gestor
            cursor.execute("DELETE FROM Usuarios_Sistema WHERE ID_Usuario = ?;", (target_usuario,))
            conn.commit()

            return jsonify({
                "success": True,
                "message": f"Usuario Gestor '{target_usuario}' eliminado exitosamente."
            }), 200

        except Exception as e:
            if conn:
                conn.rollback()
            return jsonify({
                "success": False,
                "error": f"Error al eliminar usuario: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    @app.route("/api/usuarios", methods=["GET"])
    def get_usuarios():
        """
        Devuelve la lista de usuarios del sistema (ID_Usuario y Rol) para la vista de gestión.
        """
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ID_Usuario, Rol FROM Usuarios_Sistema ORDER BY ID_Usuario ASC;")
            usuarios = [dict(row) for row in cursor.fetchall()]
            return jsonify({
                "success": True,
                "usuarios": usuarios,
                "total": len(usuarios)
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Error al obtener usuarios: {str(e)}"
            }), 500
        finally:
            if conn:
                conn.close()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
