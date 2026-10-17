# 📚 Sistema de Biblioteca Escolar Full Stack

Sistema de Biblioteca Escolar Full Stack desarrollado con **React**, **Flask** y **SQLite**, enfocado en la implementación estricta de reglas de negocio, persistencia relacional en Tercera Forma Normal (3FN), integridad transaccional y una experiencia de usuario moderna y reactiva.

---

## 🛠️ Tecnologías y Arquitectura

El sistema implementa una arquitectura desacoplada de tres capas:

```
┌────────────────────────────────────────┐
│         Frontend (SPA - React)         │  • React 18 + Vite
│    UI Reactiva, CSS Modular, Estado    │  • Open Library Covers API
└───────────────────▲────────────────────┘
                    │ RESTful API (JSON / HTTP)
┌───────────────────▼────────────────────┐
│      Backend (Flask REST API)          │  • Python 3 + Flask + Flask-CORS
│   Capa de Controladores y Negocio      │  • Manejo atómico de transacciones
└───────────────────▲────────────────────┘
                    │ SQL Queries (PRAGMA foreign_keys = ON)
┌───────────────────▼────────────────────┐
│      Base de Datos Relacional          │  • SQLite3 (3FN)
│    Tablas Normalizadas e Índices       │  • Integridad referencial en cascada
└────────────────────────────────────────┘
```

- **Frontend (React + Vite):** Interfaz moderna de usuario en Vanilla CSS, con gestión de estados para carrito de préstamos, búsqueda y filtrado en tiempo real por categorías, y consumo de la API REST.
- **Backend (API REST en Flask):** Capa de lógica y orquestación con endpoints REST que validan parámetros, aplican penalizaciones dinámicas y aseguran atomicidad en operaciones de préstamos y devoluciones.
- **Base de Datos Relacional (SQLite3):** Modelo relacional normalizado en 3FN con tablas para `Usuarios_Sistema`, `Estudiantes`, `Libros` y `Prestamos`, con claves foráneas activas (`PRAGMA foreign_keys = ON;`).

---

## 📋 Reglas de Negocio Implementadas

1. **Roles de Usuario y Seguridad Jerárquica:**
   - **`Admin_Absoluto` (Protegido):** Acceso total al sistema y vista exclusiva de **Gestión de Personal** para crear nuevos gestores (`POST /api/usuarios/gestor`) y gestionar el equipo. La cuenta `admin` y los usuarios con este rol no pueden ser eliminados ni modificados desde la API ni desde la interfaz (se muestra el distintivo `🔒 Protegido / Principal`).
   - **`Gestor`:** Rol operativo encargado de la atención a estudiantes, registro de préstamos y recepción de devoluciones.
2. **Control de Préstamos por Lotes (Carrito de Préstamos):**
   - Sistema de carrito que permite seleccionar hasta 5 libros simultáneos.
   - Procesamiento en lote mediante `POST /api/prestamos` recibiendo el arreglo `isbns`.
   - **Límite Estricto:** Si el número de préstamos activos actuales del estudiante más los libros seleccionados supera 5, la operación se cancela automáticamente con código HTTP 400.
3. **Límite Estricto de Devolución (Máximo 14 Días):**
   - Selector de fecha nativo HTML5 (`<input type="date">`) en el modal de confirmación.
   - Validación dinámica: la fecha mínima permitida es hoy (`today`) y la fecha máxima es exactamente 14 días después.
4. **Penalizaciones y Desbloqueos Automáticos por Fecha (`datetime.now()`):**
   - **Detección Dinámica:** Cada vez que se consulta la lista o detalle de estudiantes (`GET /api/estudiantes`), el backend evalúa dinámicamente si existen préstamos activos con `Fecha_Limite_Devolucion < datetime.now().date()`, actualizando su estado a `'Bloqueado'`. Aquellos sin libros vencidos se mantienen o reactivan como `'Activo'`.
   - **Bloqueo al Prestar:** En `POST /api/prestamos`, se recalcula la condición y si el estudiante tiene libros vencidos, se actualiza a `'Bloqueado'` y se rechaza la solicitud con error 400 (`"El estudiante se encuentra penalizado por libros vencidos"`).
   - **Desbloqueo en Devolución:** En `POST /api/devolucion`, tras registrar la entrega, se verifica si el estudiante aún tiene otros préstamos vencidos. Si el conteo es 0, su cuenta se desbloquea automáticamente a `'Activo'`.
5. **Protección contra Borrado de Estudiantes:**
   - Al intentar eliminar un estudiante (`DELETE /api/estudiantes/<id_carnet>`), el backend verifica si tiene préstamos activos. Si tiene libros pendientes, cancela la operación y devuelve un error HTTP 400.
6. **Manejo Eficiente de Portadas por URL y Filtrado por Categorías:**
   - Carga dinámica de portadas desde **Open Library Covers API** (`https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`).
   - Manejador `onError` con fallback visual elegante en fondo neutro oscuro y tipografía legible para evitar enlaces rotos o caídas de conexión.
   - Barra horizontal de filtros (Pills): `[ Todos ]`, `[ Programación ]`, `[ Literatura Clásica ]`, `[ Ciencia Ficción ]` e `[ Historia y Filosofía ]`.

---

## 📂 Estructura del Proyecto

```text
Midterm/
├── backend/
│   ├── app.py                # Servidor Flask, configuración CORS y endpoints REST
│   ├── database.py           # Esquema DDL en 3FN y conexión SQLite
│   ├── reset_db.py           # Script de inicialización y catálogo de 52 libros
│   ├── requirements.txt      # Dependencias backend (Flask, Flask-Cors)
│   └── biblioteca.db         # Base de datos SQLite
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Componente principal, carrito y vistas
│   │   ├── App.css           # Estilos y tokens de diseño
│   │   ├── main.jsx          # Punto de entrada de React
│   │   └── index.css         # Estilos globales
│   ├── index.html            # HTML base
│   ├── package.json          # Dependencias y scripts de Vite
│   └── vite.config.js        # Configuración de Vite
├── docs/                     # Documentación técnica adicional y diagramas
└── README.md                 # Documentación técnica general
```

---

## 🚀 Instrucciones Claras de Ejecución

### 1. Levantar el Backend (Flask)
Desde la raíz del proyecto, abre una terminal:
```bash
cd backend
pip install -r requirements.txt
python app.py
```
> El servidor iniciará en el puerto **5000** (`http://localhost:5000`).

### 2. Levantar el Frontend (React)
En una segunda terminal desde la raíz del proyecto:
```bash
cd frontend
npm install
npm run dev
```
> La interfaz estará disponible en `http://localhost:5173`.

---

## 🔑 Credenciales de Prueba

Para ingresar inmediatamente al sistema con acceso completo:

- **Usuario:** `admin`
- **Contraseña:** `admin123`
- **Rol:** `Admin_Absoluto`