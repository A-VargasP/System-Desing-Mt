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

    # Inserción de 52 libros con sus categorías correspondientes
    libros_iniciales = [
        # Literatura Clásica e Hispanoamericana
        ('978-0156012195', 'El Principito', 'Antoine de Saint-Exupery', 'Literatura Clásica', 'Disponible'),
        ('978-8420674217', 'Azul...', 'Ruben Dario', 'Literatura Clásica', 'Disponible'),
        ('978-8437604329', 'Cantos de vida y esperanza', 'Ruben Dario', 'Literatura Clásica', 'Disponible'),
        ('978-8420685626', 'Cien anos de soledad', 'Gabriel Garcia Marquez', 'Literatura Clásica', 'Disponible'),
        ('978-8424116286', 'Don Quijote de la Mancha', 'Miguel de Cervantes', 'Literatura Clásica', 'Disponible'),
        ('978-8437604947', 'Pedro Paramo', 'Juan Rulfo', 'Literatura Clásica', 'Disponible'),
        ('978-8437606606', 'La ciudad y los perros', 'Mario Vargas Llosa', 'Literatura Clásica', 'Disponible'),
        ('978-8466332521', 'Rayuela', 'Julio Cortazar', 'Literatura Clásica', 'Disponible'),
        ('978-8437601199', 'Ficciones', 'Jorge Luis Borges', 'Literatura Clásica', 'Disponible'),
        ('978-8437601663', 'El Aleph', 'Jorge Luis Borges', 'Literatura Clásica', 'Disponible'),
        ('978-0141439518', 'Pride and Prejudice', 'Jane Austen', 'Literatura Clásica', 'Disponible'),
        ('978-0141439556', 'Wuthering Heights', 'Emily Bronte', 'Literatura Clásica', 'Disponible'),
        ('978-0141439600', 'Great Expectations', 'Charles Dickens', 'Literatura Clásica', 'Disponible'),
        ('978-0140449136', 'Crime and Punishment', 'Fyodor Dostoevsky', 'Literatura Clásica', 'Disponible'),
        ('978-0140449174', 'The Brothers Karamazov', 'Fyodor Dostoevsky', 'Literatura Clásica', 'Disponible'),
        ('978-0140449242', 'War and Peace', 'Leo Tolstoy', 'Literatura Clásica', 'Disponible'),
        ('978-0140449181', 'Anna Karenina', 'Leo Tolstoy', 'Literatura Clásica', 'Disponible'),
        ('978-0140447934', 'The Odyssey', 'Homer', 'Literatura Clásica', 'Disponible'),
        ('978-0140447941', 'The Iliad', 'Homer', 'Literatura Clásica', 'Disponible'),
        ('978-0140449266', 'The Divine Comedy', 'Dante Alighieri', 'Literatura Clásica', 'Disponible'),
        ('978-0140440393', 'Hamlet', 'William Shakespeare', 'Literatura Clásica', 'Disponible'),

        # Ciencia Ficción
        ('978-0451524935', '1984', 'George Orwell', 'Ciencia Ficción', 'Disponible'),
        ('978-0451526342', 'Animal Farm', 'George Orwell', 'Ciencia Ficción', 'Disponible'),
        ('978-0060883287', 'Fahrenheit 451', 'Ray Bradbury', 'Ciencia Ficción', 'Disponible'),
        ('978-0060850524', 'Brave New World', 'Aldous Huxley', 'Ciencia Ficción', 'Disponible'),
        ('978-0441172719', 'Dune', 'Frank Herbert', 'Ciencia Ficción', 'Disponible'),
        ('978-0553293357', 'Foundation', 'Isaac Asimov', 'Ciencia Ficción', 'Disponible'),
        ('978-0553294385', 'I, Robot', 'Isaac Asimov', 'Ciencia Ficción', 'Disponible'),
        ('978-0345391803', 'The Hitchhiker\'s Guide to the Galaxy', 'Douglas Adams', 'Ciencia Ficción', 'Disponible'),
        ('978-0441569595', 'Neuromancer', 'William Gibson', 'Ciencia Ficción', 'Disponible'),
        ('978-0765382030', 'The Three-Body Problem', 'Cixin Liu', 'Ciencia Ficción', 'Disponible'),
        ('978-0345339683', 'The Hobbit', 'J.R.R. Tolkien', 'Ciencia Ficción', 'Disponible'),

        # Programación
        ('978-0132350884', 'Clean Code: A Handbook of Agile Software Craftsmanship', 'Robert C. Martin', 'Programación', 'Disponible'),
        ('978-0137081073', 'The Clean Coder: A Code of Conduct for Professional Programmers', 'Robert C. Martin', 'Programación', 'Disponible'),
        ('978-0134494166', 'Clean Architecture: A Craftsman\'s Guide to Software Structure', 'Robert C. Martin', 'Programación', 'Disponible'),
        ('978-0201616224', 'The Pragmatic Programmer: From Journeyman to Master', 'Andrew Hunt, David Thomas', 'Programación', 'Disponible'),
        ('978-0262033848', 'Introduction to Algorithms (CLRS)', 'Thomas H. Cormen et al.', 'Programación', 'Disponible'),
        ('978-0131103627', 'The C Programming Language', 'Brian W. Kernighan, Dennis M. Ritchie', 'Programación', 'Disponible'),
        ('978-0596007126', 'Head First Design Patterns', 'Eric Freeman, Elisabeth Robson', 'Programación', 'Disponible'),
        ('978-0201633610', 'Design Patterns: Elements of Reusable Object-Oriented Software', 'Erich Gamma et al.', 'Programación', 'Disponible'),
        ('978-0134685991', 'Effective Java', 'Joshua Bloch', 'Programación', 'Disponible'),
        ('978-1491957660', 'Designing Data-Intensive Applications', 'Martin Kleppmann', 'Programación', 'Disponible'),
        ('978-0134757599', 'Refactoring: Improving the Design of Existing Code', 'Martin Fowler', 'Programación', 'Disponible'),
        ('978-0321125217', 'Domain-Driven Design: Tackling Complexity in the Heart of Software', 'Eric Evans', 'Programación', 'Disponible'),
        ('978-1593279288', 'Python Crash Course', 'Eric Matthes', 'Programación', 'Disponible'),
        ('978-1492051367', 'Fluent Python', 'Luciano Ramalho', 'Programación', 'Disponible'),
        ('978-0135957059', 'The Pragmatic Programmer (20th Anniversary Edition)', 'David Thomas, Andrew Hunt', 'Programación', 'Disponible'),
        ('978-0596517748', 'JavaScript: The Good Parts', 'Douglas Crockford', 'Programación', 'Disponible'),

        # Historia y Filosofía
        ('978-0062316097', 'Sapiens: De animales a dioses', 'Yuval Noah Harari', 'Historia y Filosofía', 'Disponible'),
        ('978-0062464316', 'Homo Deus: Breve historia del manana', 'Yuval Noah Harari', 'Historia y Filosofía', 'Disponible'),
        ('978-0345539434', 'Cosmos', 'Carl Sagan', 'Historia y Filosofía', 'Disponible'),
        ('978-0553380163', 'A Brief History of Time', 'Stephen Hawking', 'Historia y Filosofía', 'Disponible')
    ]

    cursor.executemany("""
        INSERT INTO Libros (ISBN, Titulo, Autor, Categoria, Estado)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(ISBN) DO UPDATE SET 
            Categoria = excluded.Categoria,
            Titulo = excluded.Titulo,
            Autor = excluded.Autor;
    """, libros_iniciales)

    conn.commit()
    conn.close()
    print("Base de datos inicializada exitosamente en:", DB_PATH)

if __name__ == "__main__":
    init_db()
