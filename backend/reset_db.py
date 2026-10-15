import sqlite3
import os

DB_NAME = "biblioteca.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def reset_and_expand_db():
    print(f"Iniciando mantenimiento sobre: {DB_PATH}")
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # -------------------------------------------------------------
        # PASO 1: LIMPIEZA (WIPE)
        # -------------------------------------------------------------
        print("\n--- PASO 1: Limpieza del entorno de pruebas ---")

        # 1.1 Eliminar todos los registros de préstamos
        cursor.execute("DELETE FROM Prestamos;")
        prestamos_eliminados = cursor.rowcount
        print(f"[OK] Registros eliminados de 'Prestamos': {prestamos_eliminados}")

        # Reiniciar contador autoincremental de préstamos si existe sqlite_sequence
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'Prestamos';")

        # 1.2 Regresar todos los libros existentes a 'Disponible'
        cursor.execute("UPDATE Libros SET Estado = 'Disponible';")
        libros_actualizados = cursor.rowcount
        print(f"[OK] Libros actualizados a 'Disponible': {libros_actualizados}")

        # 1.3 Eliminar estudiantes con ID_Carnet inválido (que no sean exactamente 8 dígitos numéricos)
        # En SQLite: LENGTH(ID_Carnet) != 8 OR ID_Carnet GLOB '*[^0-9]*'
        cursor.execute("""
            DELETE FROM Estudiantes 
            WHERE LENGTH(ID_Carnet) != 8 OR ID_Carnet GLOB '*[^0-9]*';
        """)
        estudiantes_eliminados = cursor.rowcount
        print(f"[OK] Estudiantes invalidos depurados (con letras o != 8 digitos): {estudiantes_eliminados}")

        # -------------------------------------------------------------
        # PASO 2: EXPANSIÓN DEL CATÁLOGO (50+ Libros en total)
        # -------------------------------------------------------------
        print("\n--- PASO 2: Expansion del catalogo de libros ---")

        nuevos_libros = [
            # Requisitos Obligatorios
            ('978-0156012195', 'El Principito', 'Antoine de Saint-Exupery', 'Disponible'),
            ('978-8420674217', 'Azul...', 'Ruben Dario', 'Disponible'),
            ('978-8437604329', 'Cantos de vida y esperanza', 'Ruben Dario', 'Disponible'),

            # Literatura Clásica e Hispanoamericana
            ('978-8420685626', 'Cien anos de soledad', 'Gabriel Garcia Marquez', 'Disponible'),
            ('978-8424116286', 'Don Quijote de la Mancha', 'Miguel de Cervantes', 'Disponible'),
            ('978-8437604947', 'Pedro Paramo', 'Juan Rulfo', 'Disponible'),
            ('978-8437606606', 'La ciudad y los perros', 'Mario Vargas Llosa', 'Disponible'),
            ('978-8466332521', 'Rayuela', 'Julio Cortazar', 'Disponible'),
            ('978-8437601199', 'Ficciones', 'Jorge Luis Borges', 'Disponible'),
            ('978-8437601663', 'El Aleph', 'Jorge Luis Borges', 'Disponible'),
            ('978-0141439518', 'Pride and Prejudice', 'Jane Austen', 'Disponible'),
            ('978-0141439556', 'Wuthering Heights', 'Emily Bronte', 'Disponible'),
            ('978-0141439600', 'Great Expectations', 'Charles Dickens', 'Disponible'),
            ('978-0140449136', 'Crime and Punishment', 'Fyodor Dostoevsky', 'Disponible'),
            ('978-0140449174', 'The Brothers Karamazov', 'Fyodor Dostoevsky', 'Disponible'),
            ('978-0140449242', 'War and Peace', 'Leo Tolstoy', 'Disponible'),
            ('978-0140449181', 'Anna Karenina', 'Leo Tolstoy', 'Disponible'),
            ('978-0140447934', 'The Odyssey', 'Homer', 'Disponible'),
            ('978-0140447941', 'The Iliad', 'Homer', 'Disponible'),
            ('978-0140449266', 'The Divine Comedy', 'Dante Alighieri', 'Disponible'),
            ('978-0140440393', 'Hamlet', 'William Shakespeare', 'Disponible'),

            # Ciencia Ficción y Distopías
            ('978-0451524935', '1984', 'George Orwell', 'Disponible'),
            ('978-0451526342', 'Animal Farm', 'George Orwell', 'Disponible'),
            ('978-0060883287', 'Fahrenheit 451', 'Ray Bradbury', 'Disponible'),
            ('978-0060850524', 'Brave New World', 'Aldous Huxley', 'Disponible'),
            ('978-0441172719', 'Dune', 'Frank Herbert', 'Disponible'),
            ('978-0553293357', 'Foundation', 'Isaac Asimov', 'Disponible'),
            ('978-0553294385', 'I, Robot', 'Isaac Asimov', 'Disponible'),
            ('978-0345391803', 'The Hitchhiker\'s Guide to the Galaxy', 'Douglas Adams', 'Disponible'),
            ('978-0441569595', 'Neuromancer', 'William Gibson', 'Disponible'),
            ('978-0765382030', 'The Three-Body Problem', 'Cixin Liu', 'Disponible'),
            ('978-0345339683', 'The Hobbit', 'J.R.R. Tolkien', 'Disponible'),

            # Programación e Ingeniería de Software
            ('978-0132350884', 'Clean Code: A Handbook of Agile Software Craftsmanship', 'Robert C. Martin', 'Disponible'),
            ('978-0137081073', 'The Clean Coder: A Code of Conduct for Professional Programmers', 'Robert C. Martin', 'Disponible'),
            ('978-0134494166', 'Clean Architecture: A Craftsman\'s Guide to Software Structure', 'Robert C. Martin', 'Disponible'),
            ('978-0201616224', 'The Pragmatic Programmer: From Journeyman to Master', 'Andrew Hunt, David Thomas', 'Disponible'),
            ('978-0262033848', 'Introduction to Algorithms (CLRS)', 'Thomas H. Cormen et al.', 'Disponible'),
            ('978-0131103627', 'The C Programming Language', 'Brian W. Kernighan, Dennis M. Ritchie', 'Disponible'),
            ('978-0596007126', 'Head First Design Patterns', 'Eric Freeman, Elisabeth Robson', 'Disponible'),
            ('978-0201633610', 'Design Patterns: Elements of Reusable Object-Oriented Software', 'Erich Gamma et al.', 'Disponible'),
            ('978-0134685991', 'Effective Java', 'Joshua Bloch', 'Disponible'),
            ('978-1491957660', 'Designing Data-Intensive Applications', 'Martin Kleppmann', 'Disponible'),
            ('978-0134757599', 'Refactoring: Improving the Design of Existing Code', 'Martin Fowler', 'Disponible'),
            ('978-0321125217', 'Domain-Driven Design: Tackling Complexity in the Heart of Software', 'Eric Evans', 'Disponible'),
            ('978-1593279288', 'Python Crash Course', 'Eric Matthes', 'Disponible'),
            ('978-1492051367', 'Fluent Python', 'Luciano Ramalho', 'Disponible'),
            ('978-0135957059', 'The Pragmatic Programmer (20th Anniversary Edition)', 'David Thomas, Andrew Hunt', 'Disponible'),
            ('978-0596517748', 'JavaScript: The Good Parts', 'Douglas Crockford', 'Disponible'),

            # Historia, Ciencia y Divulgación
            ('978-0062316097', 'Sapiens: De animales a dioses', 'Yuval Noah Harari', 'Disponible'),
            ('978-0062464316', 'Homo Deus: Breve historia del manana', 'Yuval Noah Harari', 'Disponible'),
            ('978-0345539434', 'Cosmos', 'Carl Sagan', 'Disponible'),
            ('978-0553380163', 'A Brief History of Time', 'Stephen Hawking', 'Disponible')
        ]

        cursor.executemany("""
            INSERT OR IGNORE INTO Libros (ISBN, Titulo, Autor, Estado)
            VALUES (?, ?, ?, ?);
        """, nuevos_libros)

        conn.commit()

        # Resumen final de la base de datos
        total_libros = cursor.execute("SELECT COUNT(*) FROM Libros;").fetchone()[0]
        libros_disponibles = cursor.execute("SELECT COUNT(*) FROM Libros WHERE Estado = 'Disponible';").fetchone()[0]
        total_estudiantes = cursor.execute("SELECT COUNT(*) FROM Estudiantes;").fetchone()[0]
        total_prestamos = cursor.execute("SELECT COUNT(*) FROM Prestamos;").fetchone()[0]

        print("\n================ RESUMEN DE LA BASE DE DATOS ================")
        print(f" Total de libros en catalogo: {total_libros}")
        print(f" Libros disponibles:         {libros_disponibles}")
        print(f" Estudiantes validos (8 dig):{total_estudiantes}")
        print(f" Prestamos activos en BD:    {total_prestamos}")
        print("=============================================================")
        print("[OK] Mantenimiento completado exitosamente.")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error durante el mantenimiento: {str(e)}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    reset_and_expand_db()
