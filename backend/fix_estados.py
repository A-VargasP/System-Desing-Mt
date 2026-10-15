import sqlite3
import os
from datetime import datetime

DB_NAME = "biblioteca.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

def fix_estudiantes_estados():
    """
    Actualiza Estado_Cuenta = 'Activo' para estudiantes que quedaron bloqueados
    pero que NO tienen préstamos activos con fecha de devolución vencida.
    """
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No se encontro la base de datos en: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # UPDATE condicional: cambia a 'Activo' solo si el estudiante:
        # 1. Actualmente NO esta 'Activo'
        # 2. NO tiene ningun prestamo 'Activo' cuya Fecha_Limite_Devolucion sea anterior a la fecha actual (vencido)
        query = """
            UPDATE Estudiantes
            SET Estado_Cuenta = 'Activo'
            WHERE Estado_Cuenta != 'Activo'
              AND ID_Carnet NOT IN (
                  SELECT DISTINCT ID_Carnet
                  FROM Prestamos
                  WHERE Estado_Prestamo = 'Activo'
                    AND Fecha_Limite_Devolucion < ?
              );
        """

        cursor.execute(query, (now_str,))
        filas_actualizadas = cursor.rowcount
        conn.commit()

        print(f"[OK] Estudiantes corregidos y actualizados a 'Activo': {filas_actualizadas}")

        # Mostrar estado actual de los estudiantes
        cursor.execute("SELECT ID_Carnet, Nombre, Estado_Cuenta FROM Estudiantes ORDER BY Nombre ASC;")
        estudiantes = cursor.fetchall()
        print("\nEstado actual de todos los estudiantes:")
        for carnet, nombre, estado in estudiantes:
            print(f" - [{carnet}] {nombre}: {estado}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error al corregir los estados: {str(e)}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    fix_estudiantes_estados()
