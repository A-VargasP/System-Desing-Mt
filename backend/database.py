import sqlite3
import os

DB_NAME = "biblioteca.db"
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

def get_db_connection():
    """Establece una conexión a la base de datos SQLite con soporte para llaves foráneas."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Crea las tablas en 3FN e inserta datos iniciales de prueba si no existen."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabla Usuarios_Sistema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Usuarios_Sistema (
            ID_Usuario TEXT PRIMARY KEY,
            Password TEXT NOT NULL,
            Rol TEXT NOT NULL CHECK (Rol IN ('Admin_Absoluto', 'Gestor'))
        );
    """)

    # Tabla Estudiantes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Estudiantes (
            ID_Carnet TEXT PRIMARY KEY,
            Nombre TEXT NOT NULL,
            Telefono TEXT NOT NULL,
            Estado_Cuenta TEXT NOT NULL DEFAULT 'Activo' CHECK (Estado_Cuenta IN ('Activo', 'Inactivo', 'Suspendido', 'Bloqueado'))
        );
    """)

    # Tabla Libros (con campo Categoria)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Libros (
            ISBN TEXT PRIMARY KEY,
            Titulo TEXT NOT NULL,
            Autor TEXT NOT NULL,
            Categoria TEXT NOT NULL DEFAULT 'Literatura Clásica',
            Estado TEXT NOT NULL DEFAULT 'Disponible' CHECK (Estado IN ('Disponible', 'Prestado', 'En Reparacion', 'Baja'))
        );
    """)

    # Migración de esquema: Si la tabla ya existía sin Categoria, agregar la columna
    cursor.execute("PRAGMA table_info(Libros);")
    columnas_libros = [col["name"] for col in cursor.fetchall()]
    if "Categoria" not in columnas_libros:
        cursor.execute("ALTER TABLE Libros ADD COLUMN Categoria TEXT NOT NULL DEFAULT 'Literatura Clásica';")

    # Tabla Prestamos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Prestamos (
            ID_Prestamo INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_Carnet TEXT NOT NULL,
            ISBN TEXT NOT NULL,
            Fecha_Prestamo TEXT NOT NULL,
            Fecha_Limite_Devolucion TEXT NOT NULL,
            Estado_Prestamo TEXT NOT NULL DEFAULT 'Activo' CHECK (Estado_Prestamo IN ('Activo', 'Devuelto', 'Vencido')),
            FOREIGN KEY (ID_Carnet) REFERENCES Estudiantes (ID_Carnet) ON UPDATE CASCADE ON DELETE RESTRICT,
            FOREIGN KEY (ISBN) REFERENCES Libros (ISBN) ON UPDATE CASCADE ON DELETE RESTRICT
        );
    """)

    # Inserción de 1 usuario 'Admin_Absoluto' de prueba
    cursor.execute("""
        INSERT OR IGNORE INTO Usuarios_Sistema (ID_Usuario, Password, Rol)
        VALUES (?, ?, ?);
    """, ('admin', 'admin123', 'Admin_Absoluto'))

    # Inserción de 10 libros clásicos de programación y literatura con su Categoria
    libros_iniciales = [
        ('978-0132350884', 'Clean Code: A Handbook of Agile Software Craftsmanship', 'Robert C. Martin', 'Programación', 'Disponible'),
        ('978-0201616224', 'The Pragmatic Programmer: From Journeyman to Master', 'Andrew Hunt, David Thomas', 'Programación', 'Disponible'),
        ('978-0262033848', 'Introduction to Algorithms (CLRS)', 'Thomas H. Cormen et al.', 'Programación', 'Disponible'),
        ('978-0131103627', 'The C Programming Language', 'Brian W. Kernighan, Dennis M. Ritchie', 'Programación', 'Disponible'),
        ('978-0596007126', 'Head First Design Patterns', 'Eric Freeman, Elisabeth Robson', 'Programación', 'Disponible'),
        ('978-8420685626', 'Cien años de soledad', 'Gabriel García Márquez', 'Literatura Clásica', 'Disponible'),
        ('978-8424116286', 'Don Quijote de la Mancha', 'Miguel de Cervantes', 'Literatura Clásica', 'Disponible'),
        ('978-0451524935', '1984', 'George Orwell', 'Ciencia Ficción', 'Disponible'),
        ('978-0141439518', 'Pride and Prejudice', 'Jane Austen', 'Literatura Clásica', 'Disponible'),
        ('978-0060883287', 'Fahrenheit 451', 'Ray Bradbury', 'Ciencia Ficción', 'Disponible')
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO Libros (ISBN, Titulo, Autor, Categoria, Estado)
        VALUES (?, ?, ?, ?, ?);
    """, libros_iniciales)

    conn.commit()
    conn.close()
    print("Base de datos inicializada exitosamente en:", DB_PATH)

if __name__ == "__main__":
    init_db()
