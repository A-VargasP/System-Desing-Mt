import React, { useState, useEffect, useMemo } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:5000/api';

// Componente para cargar portada desde Open Library con fallback elegante
function BookCover({ isbn, titulo }) {
  const [hasError, setHasError] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Limpiar ISBN para la URL de Open Library
  const cleanIsbn = isbn ? isbn.replace(/[^0-9X]/gi, '') : '';
  const coverUrl = cleanIsbn ? `https://covers.openlibrary.org/b/isbn/${cleanIsbn}-M.jpg` : '';

  if (!coverUrl || hasError) {
    return (
      <div className="book-cover-fallback">
        <span className="fallback-icon">📖</span>
        <span className="fallback-title">{titulo}</span>
      </div>
    );
  }

  return (
    <div className="book-cover-wrapper">
      {!loaded && (
        <div className="book-cover-loading">
          <span className="fallback-title">{titulo}</span>
        </div>
      )}
      <img
        src={coverUrl}
        alt={`Portada de ${titulo}`}
        className={`book-cover-img ${loaded ? 'visible' : 'hidden'}`}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        onError={() => setHasError(true)}
      />
    </div>
  );
}

// Formateador para input type="date" estándar HTML5 (YYYY-MM-DD)
function formatDateForInput(date) {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export default function App() {
  // -------------------------------------------------------------
  // ESTADOS GLOBALES Y DE SESIÓN
  // -------------------------------------------------------------
  const [currentUser, setCurrentUser] = useState(null); // { ID_Usuario, Rol }
  const [loginForm, setLoginForm] = useState({ ID_Usuario: '', Password: '' });
  const [loginError, setLoginError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);

  // Navegación por pestañas: 'catalogo' | 'estudiantes' | 'usuarios'
  const [activeTab, setActiveTab] = useState('catalogo');

  // Notificaciones flotantes / Banner
  const [bannerMessage, setBannerMessage] = useState(null);

  const showBanner = (type, text) => {
    setBannerMessage({ type, text });
    setTimeout(() => {
      setBannerMessage(null);
    }, 6000);
  };

  // Variable de rol
  const userRole = currentUser?.Rol;

  // -------------------------------------------------------------
  // LOGIN (POST /api/login)
  // -------------------------------------------------------------
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError('');
    if (!loginForm.ID_Usuario.trim() || !loginForm.Password.trim()) {
      setLoginError('Por favor complete todos los campos.');
      return;
    }

    try {
      setLoggingIn(true);
      const res = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm)
      });
      const data = await res.json();

      if (res.ok && data.success) {
        setCurrentUser(data.data);
        showBanner('success', `¡Bienvenido, ${data.data.ID_Usuario} (${data.data.Rol})!`);
      } else {
        setLoginError(data.error || 'Credenciales inválidas.');
      }
    } catch (err) {
      setLoginError(`Error al conectar con el servidor: ${err.message}`);
    } finally {
      setLoggingIn(false);
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setLoginForm({ ID_Usuario: '', Password: '' });
    setLoginError('');
    setActiveTab('catalogo');
    setStudentResult(null);
  };

  // -------------------------------------------------------------
  // PESTAÑA 1: CATÁLOGO DE LIBROS Y PRÉSTAMOS
  // -------------------------------------------------------------
  const [libros, setLibros] = useState([]);
  const [loadingLibros, setLoadingLibros] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('Todos');

  // Categorías fijas requeridas
  const CATEGORIAS = ['Todos', 'Programación', 'Literatura Clásica', 'Ciencia Ficción', 'Historia y Filosofía'];

  // Modal Alquiler / Carrito de Préstamos Múltiples (Batch Processing)
  const [librosSeleccionados, setLibrosSeleccionados] = useState([]); // Arreglo de libros seleccionados
  const [isLoanModalOpen, setIsLoanModalOpen] = useState(false);
  const [loanCarnet, setLoanCarnet] = useState('');
  const [loanDate, setLoanDate] = useState('');
  const [loanError, setLoanError] = useState('');
  const [submittingLoan, setSubmittingLoan] = useState(false);

  // Validación dinámica: min = hoy, max = hoy + 14 días
  const todayStr = useMemo(() => formatDateForInput(new Date()), []);
  const maxDateStr = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + 14);
    return formatDateForInput(d);
  }, []);

  const fetchLibros = async () => {
    try {
      setLoadingLibros(true);
      const res = await fetch(`${API_BASE_URL}/libros`);
      const data = await res.json();
      if (data.success) {
        setLibros(data.data || []);
        // Remover de la selección libros que ya no estén disponibles
        setLibrosSeleccionados((prev) =>
          prev.filter((item) => {
            const updated = (data.data || []).find((b) => b.ISBN === item.ISBN);
            return updated && updated.Estado === 'Disponible';
          })
        );
      }
    } catch (err) {
      showBanner('error', `Error al comunicar con la API: ${err.message}`);
    } finally {
      setLoadingLibros(false);
    }
  };

  useEffect(() => {
    if (currentUser) fetchLibros();
  }, [currentUser]);

  const filteredLibros = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    return libros.filter((b) => {
      const matchSearch =
        !q ||
        b.Titulo.toLowerCase().includes(q) ||
        b.Autor.toLowerCase().includes(q) ||
        (b.ISBN && b.ISBN.toLowerCase().includes(q));

      const matchCategory =
        selectedCategory === 'Todos' ||
        (b.Categoria && b.Categoria.trim().toLowerCase() === selectedCategory.trim().toLowerCase());

      return matchSearch && matchCategory;
    });
  }, [libros, searchQuery, selectedCategory]);

  // Manejo de Selección / Deselección en el Carrito (Máximo 5 libros)
  const handleToggleSelectBook = (libro) => {
    if (libro.Estado !== 'Disponible') return;

    const isSelected = librosSeleccionados.some((b) => b.ISBN === libro.ISBN);
    if (isSelected) {
      setLibrosSeleccionados((prev) => prev.filter((b) => b.ISBN !== libro.ISBN));
    } else {
      if (librosSeleccionados.length >= 5) {
        alert('Límite de selección alcanzado: no puedes seleccionar más de 5 libros para préstamo.');
        return;
      }
      setLibrosSeleccionados((prev) => [...prev, libro]);
    }
  };

  const handleClearCart = () => {
    setLibrosSeleccionados([]);
  };

  const handleOpenBatchLoanModal = () => {
    if (librosSeleccionados.length === 0) return;
    setLoanCarnet('');
    setLoanDate(maxDateStr); // Por defecto fecha máxima de 14 días
    setLoanError('');
    setIsLoanModalOpen(true);
  };

  const handleCloseBatchLoanModal = () => {
    setIsLoanModalOpen(false);
    setLoanCarnet('');
    setLoanDate('');
    setLoanError('');
  };

  const handleLoanCarnetChange = (e) => {
    const clean = e.target.value.replace(/\D/g, '').slice(0, 8);
    setLoanCarnet(clean);
    if (loanError) setLoanError('');
  };

  const handleSubmitBatchLoan = async (e) => {
    e.preventDefault();
    if (!/^\d{8}$/.test(loanCarnet.trim())) {
      setLoanError('El ID debe ser un número de exactamente 8 dígitos');
      return;
    }
    if (!loanDate) {
      setLoanError('Por favor seleccione una fecha de devolución.');
      return;
    }
    if (loanDate < todayStr || loanDate > maxDateStr) {
      setLoanError(`La fecha de devolución debe estar entre ${todayStr} y ${maxDateStr}.`);
      return;
    }
    if (librosSeleccionados.length === 0) {
      setLoanError('Debe seleccionar al menos un libro para procesar.');
      return;
    }
    setLoanError('');

    try {
      setSubmittingLoan(true);
      const isbnsPayload = librosSeleccionados.map((b) => b.ISBN);
      const res = await fetch(`${API_BASE_URL}/prestamos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ID_Carnet: loanCarnet.trim(),
          isbns: isbnsPayload,
          fecha_devolucion: loanDate
        })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showBanner(
          'success',
          `Préstamo múltiple exitoso: ${librosSeleccionados.length} libro(s) prestado(s). Devolver a más tardar el [${data.data.Fecha_Limite_Devolucion}]`
        );
        handleCloseBatchLoanModal();
        setLibrosSeleccionados([]); // Limpiar carrito
        await fetchLibros();
        if (selectedStudentCarnet === loanCarnet.trim()) {
          fetchStudentDetail(loanCarnet.trim());
        }
      } else {
        const errorMsg = data.error || 'No se pudo registrar el préstamo múltiple.';
        setLoanError(errorMsg);
        showBanner('error', errorMsg);
      }
    } catch (err) {
      const errorMsg = `Error al realizar el préstamo múltiple: ${err.message}`;
      setLoanError(errorMsg);
      showBanner('error', errorMsg);
    } finally {
      setSubmittingLoan(false);
    }
  };

  // -------------------------------------------------------------
  // PESTAÑA 2: GESTIÓN DE ESTUDIANTES (LISTADO, ELIMINACIÓN Y DETALLES)
  // -------------------------------------------------------------
  const [studentsList, setStudentsList] = useState([]);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [searchFilterId, setSearchFilterId] = useState('');
  const [selectedStudentCarnet, setSelectedStudentCarnet] = useState(null);
  const [studentResult, setStudentResult] = useState(null);
  const [loadingStudentDetail, setLoadingStudentDetail] = useState(false);
  const [returningIsbn, setReturningIsbn] = useState(null);
  const [deletingCarnet, setDeletingCarnet] = useState(null);

  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
  const [registerForm, setRegisterForm] = useState({ Nombre: '', ID_Carnet: '', Telefono: '' });
  const [registerError, setRegisterError] = useState('');
  const [submittingRegister, setSubmittingRegister] = useState(false);

  const fetchAllStudents = async () => {
    try {
      setLoadingStudents(true);
      const res = await fetch(`${API_BASE_URL}/estudiantes/todos`);
      const data = await res.json();
      if (data.success) setStudentsList(data.data || []);
    } catch (err) {
      showBanner('error', `Error al comunicar con la API: ${err.message}`);
    } finally {
      setLoadingStudents(false);
    }
  };

  useEffect(() => {
    if (currentUser && activeTab === 'estudiantes') {
      fetchAllStudents();
    }
  }, [currentUser, activeTab]);

  const filteredStudents = useMemo(() => {
    const q = searchFilterId.trim();
    if (!q) return studentsList;
    return studentsList.filter((s) => s.ID_Carnet.includes(q));
  }, [studentsList, searchFilterId]);

  const fetchStudentDetail = async (id_carnet) => {
    try {
      setSelectedStudentCarnet(id_carnet);
      setLoadingStudentDetail(true);
      const res = await fetch(`${API_BASE_URL}/estudiantes/${id_carnet}`);
      const data = await res.json();
      if (data.success) {
        setStudentResult(data);
      } else {
        setStudentResult(null);
      }
    } catch (err) {
      showBanner('error', `Error al obtener detalle: ${err.message}`);
    } finally {
      setLoadingStudentDetail(false);
    }
  };

  // Botón 'Eliminar Estudiante'
  const handleDeleteStudent = async (id_carnet, nombre) => {
    const confirmDelete = window.confirm(`¿Estás seguro de que deseas eliminar al estudiante "${nombre}" (Carnet: ${id_carnet})?`);
    if (!confirmDelete) return;

    try {
      setDeletingCarnet(id_carnet);
      const res = await fetch(`${API_BASE_URL}/estudiantes/${id_carnet}`, {
        method: 'DELETE'
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showBanner('success', data.message || `Estudiante "${nombre}" eliminado con éxito.`);
        // Si el panel de detalles abierto corresponde al estudiante eliminado, cerrarlo
        if (selectedStudentCarnet === id_carnet) {
          setStudentResult(null);
          setSelectedStudentCarnet(null);
        }
        // Actualizar lista de estudiantes
        await fetchAllStudents();
      } else {
        showBanner('error', data.error || 'No se pudo eliminar al estudiante.');
      }
    } catch (err) {
      showBanner('error', `Error al conectar con la API: ${err.message}`);
    } finally {
      setDeletingCarnet(null);
    }
  };

  // Devolución de libro
  const handleReturnBook = async (isbn) => {
    try {
      setReturningIsbn(isbn);
      const res = await fetch(`${API_BASE_URL}/devolucion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ISBN: isbn })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showBanner('success', 'Libro devuelto con éxito');
        if (selectedStudentCarnet) {
          await fetchStudentDetail(selectedStudentCarnet);
        }
        await fetchLibros();
      } else {
        showBanner('error', data.error || 'No se pudo procesar la devolución.');
      }
    } catch (err) {
      showBanner('error', `Error al procesar devolución: ${err.message}`);
    } finally {
      setReturningIsbn(null);
    }
  };

  const handleSubmitRegisterStudent = async (e) => {
    e.preventDefault();
    if (!/^\d{8}$/.test(registerForm.ID_Carnet.trim())) {
      setRegisterError('El ID debe ser un número de exactamente 8 dígitos');
      return;
    }
    setRegisterError('');

    try {
      setSubmittingRegister(true);
      const res = await fetch(`${API_BASE_URL}/estudiantes/registro`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          Nombre: registerForm.Nombre.trim(),
          ID_Carnet: registerForm.ID_Carnet.trim(),
          Telefono: registerForm.Telefono.trim()
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showBanner('success', `¡Estudiante ${data.data.Nombre} registrado con éxito!`);
        setIsRegisterModalOpen(false);
        await fetchAllStudents();
        fetchStudentDetail(data.data.ID_Carnet);
      } else {
        setRegisterError(data.error || 'Error al registrar al estudiante.');
      }
    } catch (err) {
      setRegisterError(`Error de conexión: ${err.message}`);
    } finally {
      setSubmittingRegister(false);
    }
  };

  // -------------------------------------------------------------
  // PESTAÑA 3: GESTIÓN DE PERSONAL (EXCLUSIVA ADMIN ABSOLUTO)
  // -------------------------------------------------------------
  const [gestorForm, setGestorForm] = useState({ ID_Usuario: '', Password: '' });
  const [gestorError, setGestorError] = useState('');
  const [submittingGestor, setSubmittingGestor] = useState(false);
  const [systemUsers, setSystemUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [deletingUser, setDeletingUser] = useState(null);

  const fetchUsers = async () => {
    try {
      setLoadingUsers(true);
      const res = await fetch(`${API_BASE_URL}/usuarios`);
      const data = await res.json();
      if (res.ok && data.success) {
        setSystemUsers(data.usuarios || []);
      }
    } catch (err) {
      showBanner('error', `Error al cargar la lista de usuarios: ${err.message}`);
    } finally {
      setLoadingUsers(false);
    }
  };

  useEffect(() => {
    if (currentUser && userRole === 'Admin_Absoluto' && activeTab === 'usuarios') {
      fetchUsers();
    }
  }, [currentUser, userRole, activeTab]);

  const handleSubmitGestor = async (e) => {
    e.preventDefault();
    setGestorError('');
    if (!gestorForm.ID_Usuario.trim() || !gestorForm.Password.trim()) {
      setGestorError('Todos los campos son obligatorios.');
      return;
    }

    try {
      setSubmittingGestor(true);
      const res = await fetch(`${API_BASE_URL}/usuarios/gestor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ID_Usuario: gestorForm.ID_Usuario.trim(),
          Password: gestorForm.Password.trim()
        })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showBanner('success', data.message || `Gestor "${gestorForm.ID_Usuario}" registrado con éxito.`);
        setGestorForm({ ID_Usuario: '', Password: '' });
        await fetchUsers();
      } else {
        setGestorError(data.error || 'Error al registrar el nuevo gestor.');
      }
    } catch (err) {
      setGestorError(`Error al conectar con el servidor: ${err.message}`);
    } finally {
      setSubmittingGestor(false);
    }
  };

  const handleDeleteUser = async (id_usuario, rol) => {
    const confirmDelete = window.confirm(`¿Estás seguro de que deseas eliminar al usuario "${id_usuario}" (${rol})?`);
    if (!confirmDelete) return;

    try {
      setDeletingUser(id_usuario);
      const res = await fetch(`${API_BASE_URL}/usuarios/${encodeURIComponent(id_usuario)}`, {
        method: 'DELETE'
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showBanner('success', data.message || `Usuario "${id_usuario}" eliminado exitosamente.`);
        await fetchUsers();
      } else {
        showBanner('error', data.error || 'No se pudo eliminar al usuario.');
      }
    } catch (err) {
      showBanner('error', `Error al eliminar usuario: ${err.message}`);
    } finally {
      setDeletingUser(null);
    }
  };

  // -------------------------------------------------------------
  // VISTA: LOGIN INICIAL
  // -------------------------------------------------------------
  if (!currentUser) {
    return (
      <div className="login-wrapper">
        <div className="login-card">
          <div className="login-header">
            <h1>📚 Sistema de Biblioteca</h1>
            <p>Inicie sesión con sus credenciales de usuario</p>
          </div>
          {loginError && <div className="login-error">⚠️ {loginError}</div>}
          <form onSubmit={handleLoginSubmit}>
            <div className="form-group">
              <label htmlFor="usuarioInput">Usuario:</label>
              <input
                id="usuarioInput"
                type="text"
                placeholder="Ej: admin"
                value={loginForm.ID_Usuario}
                onChange={(e) => setLoginForm({ ...loginForm, ID_Usuario: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="passwordInput">Contraseña:</label>
              <input
                id="passwordInput"
                type="password"
                placeholder="••••••••"
                value={loginForm.Password}
                onChange={(e) => setLoginForm({ ...loginForm, Password: e.target.value })}
                required
              />
            </div>
            <button type="submit" className="btn-primary btn-full" disabled={loggingIn}>
              {loggingIn ? 'Verificando...' : 'Iniciar Sesión'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Encabezado y Navegación por Pestañas */}
      <header className="app-header">
        <div className="brand-section">
          <span style={{ fontSize: '1.3rem' }}>📖</span>
          <span className="brand-title">Gestión de Biblioteca</span>
        </div>
        <nav className="nav-tabs">
          <button
            className={`tab-btn ${activeTab === 'catalogo' ? 'active' : ''}`}
            onClick={() => setActiveTab('catalogo')}
          >
            📚 Catálogo de Libros
          </button>
          <button
            className={`tab-btn ${activeTab === 'estudiantes' ? 'active' : ''}`}
            onClick={() => setActiveTab('estudiantes')}
          >
            🎓 Gestión de Estudiantes
          </button>

          {/* Pestaña exclusiva para Admin_Absoluto */}
          {userRole === 'Admin_Absoluto' && (
            <button
              className={`tab-btn ${activeTab === 'usuarios' ? 'active' : ''}`}
              onClick={() => setActiveTab('usuarios')}
            >
              👥 Gestión de Personal
            </button>
          )}
        </nav>
        <div className="user-profile">
          <span className="user-role-badge">👤 {currentUser.ID_Usuario} ({currentUser.Rol})</span>
          <button className="btn-logout" onClick={handleLogout}>Cerrar Sesión</button>
        </div>
      </header>

      {bannerMessage && (
        <div className={`status-banner ${bannerMessage.type}`}>
          <span>{bannerMessage.text}</span>
          <button onClick={() => setBannerMessage(null)} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      <div className="tab-content">
        {/* ======================================================== */}
        {/* PESTAÑA 1: CATÁLOGO DE LIBROS */}
        {/* ======================================================== */}
        {activeTab === 'catalogo' && (
          <div className="app-layout">
            <aside className="sidebar">
              <div className="sidebar-header">
                <h2>📚 Catálogo ({libros.length})</h2>
                <p>Libros registrados en sistema</p>
              </div>
              <ul className="sidebar-list">
                {libros.map((libro) => (
                  <li key={libro.ISBN} className={`sidebar-item ${libro.Estado === 'Prestado' ? 'borrowed' : 'available'}`}>
                    <span className="sidebar-item-title">{libro.Titulo}</span>
                    <span className={`badge sidebar-item-badge ${libro.Estado === 'Prestado' ? 'borrowed' : 'available'}`}>{libro.Estado}</span>
                  </li>
                ))}
              </ul>
            </aside>

            <main className="main-content">
              <div className="top-nav">
                <div className="search-input-wrapper">
                  <span className="search-icon">🔍</span>
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Buscar libros por título, autor o ISBN..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <button className="btn-secondary" onClick={fetchLibros}>🔄 Actualizar</button>
              </div>

              {/* Barra de Categorías (Pills) */}
              <div className="category-pills-bar">
                {CATEGORIAS.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    className={`category-pill ${selectedCategory === cat ? 'active' : ''}`}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              <div className="grid-container">
                {filteredLibros.length === 0 ? (
                  <div className="empty-state" style={{ padding: '60px 20px' }}>
                    <p style={{ fontSize: '1.2rem', marginBottom: '8px' }}>🔍 No se encontraron libros</p>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                      Prueba con otro término de búsqueda o selecciona la categoría "Todos".
                    </p>
                  </div>
                ) : (
                  <div className="books-grid">
                    {filteredLibros.map((libro) => {
                      const isSelected = librosSeleccionados.some((b) => b.ISBN === libro.ISBN);
                      const isAvailable = libro.Estado === 'Disponible';

                      return (
                        <div
                          key={libro.ISBN}
                          className={`book-card ${isAvailable ? 'available' : 'borrowed'} ${isSelected ? 'selected-cart' : ''}`}
                          onClick={() => isAvailable && handleToggleSelectBook(libro)}
                        >
                          <div className="book-card-cover-container">
                            <BookCover isbn={libro.ISBN} titulo={libro.Titulo} />
                            {isSelected && <span className="cart-badge-check">✓ En Carrito</span>}
                            {libro.Categoria && (
                              <span className="book-category-tag">{libro.Categoria}</span>
                            )}
                          </div>

                          <div className="book-info">
                            <h4 className="book-title" title={libro.Titulo}>{libro.Titulo}</h4>
                            <p className="book-author" title={libro.Autor}>{libro.Autor}</p>
                            <p className="book-isbn">ISBN: {libro.ISBN}</p>
                            
                            <div className="book-card-footer">
                              <span className={`badge ${isAvailable ? 'available' : 'borrowed'}`}>
                                {isAvailable ? '● Disponible' : '● Prestado'}
                              </span>
                              <button
                                type="button"
                                className={`card-action-btn ${isSelected ? 'btn-selected' : ''}`}
                                disabled={!isAvailable}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleToggleSelectBook(libro);
                                }}
                              >
                                {!isAvailable
                                  ? 'No disponible'
                                  : isSelected
                                  ? '✓ Deseleccionar'
                                  : 'Seleccionar'}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Barra inferior flotante tipo Carrito de Préstamos */}
              {librosSeleccionados.length > 0 && (
                <div className="loan-cart-floating-bar">
                  <div className="cart-info">
                    <span className="cart-icon">🛒</span>
                    <div>
                      <div className="cart-title">
                        Carrito de Préstamos: <strong>{librosSeleccionados.length} / 5 libro(s)</strong>
                      </div>
                      <div className="cart-subtitle">
                        {librosSeleccionados.map((b) => b.Titulo).join(', ')}
                      </div>
                    </div>
                  </div>
                  <div className="cart-actions">
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ padding: '8px 14px', fontSize: '0.85rem' }}
                      onClick={handleClearCart}
                    >
                      Vaciar Carrito
                    </button>
                    <button
                      type="button"
                      className="btn-primary"
                      style={{ padding: '8px 20px', fontSize: '0.88rem', fontWeight: 600 }}
                      onClick={handleOpenBatchLoanModal}
                    >
                      🚀 Procesar Préstamo Múltiple ({librosSeleccionados.length})
                    </button>
                  </div>
                </div>
              )}
            </main>
          </div>
        )}

        {/* ======================================================== */}
        {/* PESTAÑA 2: GESTIÓN DE ESTUDIANTES */}
        {/* ======================================================== */}
        {activeTab === 'estudiantes' && (
          <div className="students-view">
            <div className="students-header">
              <h2>🎓 Panel de Gestión de Estudiantes</h2>
              <button className="btn-primary" onClick={() => setIsRegisterModalOpen(true)}>
                ➕ Registrar Nuevo Estudiante
              </button>
            </div>

            <div className="student-search-box">
              <h3>🔍 Filtrar Estudiantes por ID de Carnet</h3>
              <div className="search-form-row">
                <input
                  type="text"
                  className="student-id-input"
                  inputMode="numeric"
                  maxLength={8}
                  placeholder="Escriba el ID para filtrar en tiempo real..."
                  value={searchFilterId}
                  onChange={(e) => setSearchFilterId(e.target.value.replace(/\D/g, '').slice(0, 8))}
                />
                {searchFilterId && (
                  <button className="btn-secondary" onClick={() => setSearchFilterId('')}>
                    Limpiar Filtro
                  </button>
                )}
              </div>
            </div>

            {/* Listado Completo de Estudiantes */}
            <div className="student-card" style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h3 style={{ fontSize: '1.05rem', color: 'var(--text-main)' }}>
                  📋 Lista de Estudiantes Registrados ({filteredStudents.length})
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  (Haz clic en una fila para ver sus préstamos)
                </span>
              </div>

              {loadingStudents ? (
                <div className="empty-state">Cargando lista de estudiantes...</div>
              ) : filteredStudents.length === 0 ? (
                <div className="empty-state">No hay estudiantes que coincidan con el filtro.</div>
              ) : (
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>ID Carnet</th>
                      <th>Nombre</th>
                      <th>Teléfono</th>
                      <th>Estado Cuenta</th>
                      <th style={{ textAlign: 'center' }}>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredStudents.map((est) => {
                      const isSelected = selectedStudentCarnet === est.ID_Carnet;
                      return (
                        <tr
                          key={est.ID_Carnet}
                          className={`table-row-clickable ${isSelected ? 'selected-row' : ''}`}
                          onClick={() => fetchStudentDetail(est.ID_Carnet)}
                        >
                          <td style={{ fontWeight: 600 }}>{est.ID_Carnet}</td>
                          <td>{est.Nombre}</td>
                          <td style={{ color: 'var(--text-muted)' }}>{est.Telefono}</td>
                          <td>
                            {est.Estado_Cuenta === 'Activo' ? (
                              <span className="status-indicator active">● Activo</span>
                            ) : (
                              <span className="status-indicator blocked">● {est.Estado_Cuenta} (Bloqueado/Penalizado)</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <div style={{ display: 'inline-flex', gap: '8px' }}>
                              <button
                                className="btn-secondary"
                                style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  fetchStudentDetail(est.ID_Carnet);
                                }}
                              >
                                {isSelected ? '✓ Seleccionado' : 'Ver Detalles'}
                              </button>
                              {/* Botón rojo de Eliminar Estudiante */}
                              <button
                                className="btn-danger"
                                style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                                disabled={deletingCarnet === est.ID_Carnet}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteStudent(est.ID_Carnet, est.Nombre);
                                }}
                                title="Eliminar estudiante"
                              >
                                {deletingCarnet === est.ID_Carnet ? 'Eliminando...' : 'Eliminar'}
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Panel de Detalles */}
            {loadingStudentDetail && (
              <div className="student-card empty-state">Cargando detalles del estudiante...</div>
            )}

            {studentResult && !loadingStudentDetail && (
              <div className="student-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>
                    📄 Detalles del Estudiante
                  </h3>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button
                      className="btn-danger"
                      style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                      disabled={deletingCarnet === studentResult.estudiante.ID_Carnet}
                      onClick={() => handleDeleteStudent(studentResult.estudiante.ID_Carnet, studentResult.estudiante.Nombre)}
                    >
                      🗑️ Eliminar Estudiante
                    </button>
                    <button className="btn-secondary" style={{ fontSize: '0.75rem', padding: '4px 10px' }} onClick={() => setStudentResult(null)}>
                      Cerrar Panel
                    </button>
                  </div>
                </div>

                <div className="student-info-grid">
                  <div className="info-item"><label>Nombre</label><span>{studentResult.estudiante.Nombre}</span></div>
                  <div className="info-item"><label>ID Carnet</label><span>{studentResult.estudiante.ID_Carnet}</span></div>
                  <div className="info-item"><label>Teléfono</label><span>{studentResult.estudiante.Telefono}</span></div>
                  <div className="info-item">
                    <label>Estado de Cuenta</label>
                    {studentResult.estudiante.Estado_Cuenta === 'Activo' ? (
                      <span className="status-indicator active">● Activo</span>
                    ) : (
                      <span className="status-indicator blocked">● {studentResult.estudiante.Estado_Cuenta} (Bloqueado/Penalizado)</span>
                    )}
                  </div>
                </div>

                <div className="loans-table-section">
                  <h4>📖 Libros Prestados Actualmente ({studentResult.total_prestamos_activos})</h4>
                  {studentResult.prestamos_activos.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
                      Este estudiante no tiene ningún libro prestado actualmente.
                    </p>
                  ) : (
                    <table className="custom-table">
                      <thead>
                        <tr>
                          <th>Título del Libro</th>
                          <th>ISBN</th>
                          <th>Fecha Préstamo</th>
                          <th>Fecha Límite Devolución</th>
                          <th>Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {studentResult.prestamos_activos.map((prestamo) => (
                          <tr key={prestamo.ID_Prestamo}>
                            <td style={{ fontWeight: 600 }}>{prestamo.Titulo}</td>
                            <td style={{ color: 'var(--text-muted)' }}>{prestamo.ISBN}</td>
                            <td>{prestamo.Fecha_Prestamo}</td>
                            <td style={{ color: '#f59e0b', fontWeight: 600 }}>{prestamo.Fecha_Limite_Devolucion}</td>
                            <td>
                              <button
                                className="btn-danger"
                                disabled={returningIsbn === prestamo.ISBN}
                                onClick={() => handleReturnBook(prestamo.ISBN)}
                                title="Registrar devolución de este libro"
                              >
                                {returningIsbn === prestamo.ISBN ? 'Procesando...' : 'Devolver'}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* PESTAÑA 3: GESTIÓN DE PERSONAL (EXCLUSIVA ADMIN ABSOLUTO) */}
        {/* ======================================================== */}
        {activeTab === 'usuarios' && userRole === 'Admin_Absoluto' && (
          <div className="users-view">
            {/* Formulario para registrar un nuevo gestor */}
            <div className="users-card" style={{ marginBottom: '24px' }}>
              <h2>👥 Gestión de Personal</h2>
              <p>Registre nuevos gestores para el sistema de biblioteca o gestione el personal activo.</p>

              {gestorError && (
                <p style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: '14px', fontWeight: '500' }}>
                  ⚠️ {gestorError}
                </p>
              )}

              <form onSubmit={handleSubmitGestor}>
                <div className="form-group">
                  <label htmlFor="gestorUsuarioInput">ID de Usuario:</label>
                  <input
                    id="gestorUsuarioInput"
                    type="text"
                    placeholder="Ej: gestor_biblioteca"
                    value={gestorForm.ID_Usuario}
                    onChange={(e) => setGestorForm({ ...gestorForm, ID_Usuario: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="gestorPasswordInput">Contraseña:</label>
                  <input
                    id="gestorPasswordInput"
                    type="password"
                    placeholder="••••••••"
                    value={gestorForm.Password}
                    onChange={(e) => setGestorForm({ ...gestorForm, Password: e.target.value })}
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="btn-primary btn-full"
                  disabled={submittingGestor}
                >
                  {submittingGestor ? 'Registrando...' : '➕ Registrar Nuevo Gestor'}
                </button>
              </form>
            </div>

            {/* Tabla que lista a los administradores y gestores actuales */}
            <div className="users-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h3 style={{ fontSize: '1.1rem', color: 'var(--text-main)', margin: 0 }}>
                  📋 Personal y Administradores Actuales ({systemUsers.length})
                </h3>
                <button
                  className="btn-secondary"
                  style={{ fontSize: '0.78rem', padding: '4px 10px' }}
                  onClick={fetchUsers}
                  disabled={loadingUsers}
                >
                  {loadingUsers ? 'Cargando...' : '🔄 Actualizar'}
                </button>
              </div>

              {loadingUsers && systemUsers.length === 0 ? (
                <div className="empty-state">Cargando personal del sistema...</div>
              ) : systemUsers.length === 0 ? (
                <div className="empty-state">No hay usuarios registrados.</div>
              ) : (
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>ID de Usuario</th>
                      <th>Rol</th>
                      <th style={{ textAlign: 'center' }}>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {systemUsers.map((u) => {
                      const isAdminAbsoluto = u.Rol === 'Admin_Absoluto' || u.ID_Usuario.toLowerCase() === 'admin';
                      const isSelf = currentUser?.ID_Usuario === u.ID_Usuario;

                      return (
                        <tr key={u.ID_Usuario}>
                          <td style={{ fontWeight: 600 }}>{u.ID_Usuario}</td>
                          <td>
                            <span
                              className={`status-indicator ${isAdminAbsoluto ? 'active' : 'borrowed'}`}
                              style={{
                                padding: '3px 8px',
                                borderRadius: '6px',
                                fontSize: '0.78rem',
                                background: isAdminAbsoluto ? 'rgba(59, 130, 246, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                                color: isAdminAbsoluto ? '#60a5fa' : '#34d399',
                                border: isAdminAbsoluto ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)'
                              }}
                            >
                              {isAdminAbsoluto ? '👑 Admin_Absoluto' : '🛡️ Gestor'}
                            </span>
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            {isAdminAbsoluto ? (
                              <span
                                style={{
                                  display: 'inline-block',
                                  padding: '3px 10px',
                                  borderRadius: '6px',
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                  color: '#94a3b8',
                                  backgroundColor: 'rgba(148, 163, 184, 0.12)',
                                  border: '1px solid rgba(148, 163, 184, 0.25)',
                                  userSelect: 'none'
                                }}
                                title="Cuenta protegida: Administrador principal del sistema"
                              >
                                🔒 Protegido / Principal
                              </span>
                            ) : u.Rol === 'Gestor' ? (
                              <button
                                className="btn-danger"
                                style={{ padding: '4px 12px', fontSize: '0.78rem' }}
                                disabled={isSelf || deletingUser === u.ID_Usuario}
                                onClick={() => handleDeleteUser(u.ID_Usuario, u.Rol)}
                                title={isSelf ? 'No puedes eliminarte a ti mismo' : 'Eliminar gestor'}
                              >
                                {deletingUser === u.ID_Usuario ? 'Eliminando...' : 'Eliminar'}
                              </button>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modal Préstamo Múltiple con Calendario Desplegable HTML5 */}
      {isLoanModalOpen && (
        <div className="modal-overlay" onClick={handleCloseBatchLoanModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Solicitar Préstamo Múltiple</h3>
              <button className="modal-close-btn" onClick={handleCloseBatchLoanModal}>&times;</button>
            </div>
            
            <div className="modal-book-summary">
              <p style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>
                Libros a prestar ({librosSeleccionados.length}):
              </p>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.86rem', color: 'var(--text-muted)' }}>
                {librosSeleccionados.map((b) => (
                  <li key={b.ISBN} style={{ marginBottom: '4px' }}>
                    <strong style={{ color: 'var(--text-main)' }}>{b.Titulo}</strong> (ISBN: {b.ISBN})
                  </li>
                ))}
              </ul>
            </div>

            <form onSubmit={handleSubmitBatchLoan}>
              <div className="form-group">
                <label htmlFor="loanCarnetInput">ID Carnet del Estudiante (8 dígitos):</label>
                <input
                  id="loanCarnetInput"
                  type="text"
                  maxLength={8}
                  placeholder="Ej: 20261001"
                  value={loanCarnet}
                  onChange={handleLoanCarnetChange}
                  autoFocus
                  required
                />
              </div>

              {/* Calendario desplegable nativo con min y max dinámico */}
              <div className="form-group">
                <label htmlFor="loanDateInput">Fecha de Devolución (Calendario desplegable):</label>
                <input
                  id="loanDateInput"
                  type="date"
                  min={todayStr}
                  max={maxDateStr}
                  value={loanDate}
                  onChange={(e) => setLoanDate(e.target.value)}
                  required
                />
                <small style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '4px', display: 'block' }}>
                  📅 Rango permitido: {todayStr} hasta {maxDateStr} (máx. 14 días)
                </small>
              </div>

              {loanError && <p style={{ color: '#ef4444', fontSize: '0.82rem', marginTop: '6px' }}>⚠️ {loanError}</p>}

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={handleCloseBatchLoanModal}>Cancelar</button>
                <button type="submit" className="btn-primary" disabled={submittingLoan}>
                  {submittingLoan ? 'Procesando Préstamos...' : `Confirmar Préstamo (${librosSeleccionados.length})`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Registrar Estudiante */}
      {isRegisterModalOpen && (
        <div className="modal-overlay" onClick={() => setIsRegisterModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Registrar Nuevo Estudiante</h3>
              <button className="modal-close-btn" onClick={() => setIsRegisterModalOpen(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmitRegisterStudent}>
              <div className="form-group">
                <label>Nombre Completo:</label>
                <input
                  type="text"
                  placeholder="Ej: Laura Gómez"
                  value={registerForm.Nombre}
                  onChange={(e) => setRegisterForm({ ...registerForm, Nombre: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>ID Carnet (8 dígitos numéricos exactos):</label>
                <input
                  type="text"
                  maxLength={8}
                  placeholder="Ej: 20268899"
                  value={registerForm.ID_Carnet}
                  onChange={(e) => setRegisterForm({ ...registerForm, ID_Carnet: e.target.value.replace(/\D/g, '').slice(0, 8) })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Teléfono:</label>
                <input
                  type="text"
                  placeholder="Ej: +502 5555-1234"
                  value={registerForm.Telefono}
                  onChange={(e) => setRegisterForm({ ...registerForm, Telefono: e.target.value })}
                  required
                />
              </div>
              {registerError && <p style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: '14px' }}>⚠️ {registerError}</p>}
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setIsRegisterModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn-primary" disabled={submittingRegister}>
                  {submittingRegister ? 'Registrando...' : 'Guardar Estudiante'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
