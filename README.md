# Sistema de Gestión de Biblioteca Escolar (Full Stack)
**Curso:** SM4113 - Systems Design  
**Midterm Project**  
**Estudiante:** Adolfo N. Vargas  
**Docente:** Dr. Daniel Narváez  

## 📖 Descripción del Proyecto
Aplicación web Full Stack diseñada bajo una arquitectura de tres capas (React + Flask + SQLite) orientada a la integridad referencial, automatización de penalizaciones disciplinarias y control de inventario bibliotecario.

### ✨ Características y Reglas de Negocio Implementadas
- **Autenticación Basada en Roles:** Separación entre `Admin_Absoluto` (administración de cuentas con blindaje contra eliminación accidental) y `Gestores` (operaciones de mostrador y préstamos).
- **Integridad de Dominio:** Validación estricta del carnet estudiantil a exactamente 8 dígitos numéricos.
- **Préstamo por Lotes (Carrito de Libros):** Selección y préstamo concurrente de hasta 5 libros por estudiante en una sola transacción atómica.
- **Límite Temporal Estricto:** Control de fechas de devolución limitado por interfaz y backend a un máximo de 14 días calendario.
- **Penalizaciones y Desbloqueos Automáticos:** Evaluación dinámica en tiempo de consulta de libros vencidos; bloqueo automático de cuentas en mora y restablecimiento inmediato a estado 'Activo' al devolver los ejemplares adeudados.
- **Catálogo Optimizado:** Organización temática por categorías y consumo ligero de portadas vía Open Library Covers API con fallback estético offline.

---

## 📁 Estructura del Repositorio
```text
├── backend/
│   ├── app.py             # API REST en Flask y lógica de negocio
│   ├── database.py        # Esquema SQLite inicial
│   ├── reset_db.py        # Script para restaurar la BD con los 52 libros
│   ├── test_api.py        # Pruebas automatizadas de endpoints
│   ├── biblioteca.db      # Base de datos SQLite persistente
│   └── requirements.txt   # Dependencias de Python
├── frontend/
│   ├── src/               # Código fuente React (Vite)
│   ├── public/            # Recursos estáticos
│   └── package.json       # Dependencias de Node.js
└── docs/
    ├── Diagrama de Flujo de Datos.png  # DFD Nivel 0
    └── ER Diagram.png                  # Diagrama Entidad-Relación (Crow's Foot)
```

---

## 🚀 Instrucciones de Instalación y Ejecución

### 1. Backend (Flask)
```bash
cd backend
pip install -r requirements.txt
python app.py
```
> Servidor disponible en: `http://localhost:5000`

### 2. Frontend (React)
```bash
cd frontend
npm install
npm run dev
```
> Interfaz disponible en: `http://localhost:5173`

---

## 🛠️ Scripts de Utilidad y Pruebas (Backend)

### Restauración de Base de Datos (`reset_db.py`)
Permite restablecer la base de datos `biblioteca.db` a su estado original de evaluación (tablas en 3NF, 52 libros precargados con categorías y usuario administrador inicial):

```bash
cd backend
python reset_db.py
```

### Suite de Pruebas Automatizadas (`test_api.py`)
Ejecuta una serie de pruebas unitarias sobre los endpoints de la API Flask para verificar validaciones de negocio, respuestas HTTP esperadas y manejo de errores:

```bash
cd backend
python test_api.py
```

---

## 🔑 Credenciales de Acceso

- **Usuario:** `admin`
- **Rol:** `Admin_Absoluto`
- **Contraseña:** `admin` *(o `admin123` según la inicialización por defecto)*