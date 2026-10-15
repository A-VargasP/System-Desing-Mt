import React, { useState, useEffect, useMemo } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:5000/api';

// Paleta de gradientes para los placeholders de portadas
const COVER_GRADIENTS = [
  'linear-gradient(135deg, #1e3a8a, #3b82f6)',
  'linear-gradient(135deg, #065f46, #10b981)',
  'linear-gradient(135deg, #7c2d12, #f97316)',
  'linear-gradient(135deg, #581c87, #a855f7)',
  'linear-gradient(135deg, #831843, #ec4899)',
  'linear-gradient(135deg, #134e4a, #14b8a6)',
  'linear-gradient(135deg, #374151, #6b7280)',
  'linear-gradient(135deg, #14532d, #22c55e)'
];

function getCoverStyle(isbn) {
  let hash = 0;
  for (let i = 0; i < isbn.length; i++) {
    hash = isbn.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % COVER_GRADIENTS.length;
  return { background: COVER_GRADIENTS[index] };
}

// Formateador para input type="date" (YYYY-MM-DD)
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

  // Navegación por pestañas: 'catalogo' | 'estudiantes'
  const [activeTab, setActiveTab] = useState('catalogo');

  // Notificaciones flotantes / Banner
  const [bannerMessage, setBannerMessage] = useState(null);

  const showBanner = (type, text) => {
    setBannerMessage({ type, text });
    setTimeout(() => {
      setBannerMessage(null);
    }, 6000);
  };

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
    setStudentResult(null);
  };

  // -------------------------------------------------------------
  // PESTAÑA 1: CATÁLOGO DE LIBROS Y PRÉSTAMOS
  // -------------------------------------------------------------
  const [libros, setLibros] = useState([]);
  const [loadingLibros, setLoadingLibros] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Modal Alquiler de Libros
  const [selectedBook, setSelectedBook] = useState(null);
  const [loanCarnet, setLoanCarnet] = useState('');
  const [loanDate, setLoanDate] = useState(''); // Fecha de devolución requerida
  const [loanError, setLoanError] = useState('');
  const [submittingLoan, setSubmittingLoan] = useState(false);

  // Fechas límites para el calendario (Hoy y +14 días)
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
      } else {
        showBanner('error', data.error || 'Error al obtener catálogo de libros.');
      }
    } catch (err) {
      showBanner('error', `Error al comunicar con la API: ${err.message}`);
    } finally {
      setLoadingLibros(false);
    }
  };

  useEffect(() => {
    if (currentUser) {
      fetchLibros();
    }
  }, [currentUser]);

  const filteredLibros = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return libros;
    return libros.filter(
      (b) =>
        b.Titulo.toLowerCase().includes(q) ||
        b.Autor.toLowerCase().includes(q)
    );
  }, [libros, searchQuery]);

  const handleOpenLoanModal = (libro) => {
    if (libro.Estado !== 'Disponible') return;
    setSelectedBook(libro);
    setLoanCarnet('');
    setLoanDate(maxDateStr); // Por defecto sugiere 14 días
    setLoanError('');
  };

  const handleCloseLoanModal = () => {
    setSelectedBook(null);
    setLoanCarnet('');
    setLoanDate('');
    setLoanError('');
  };

  const handleLoanCarnetChange = (e) => {
    const clean = e.target.value.replace(/\D/g, '').slice(0, 8);
    setLoanCarnet(clean);
    if (loanError) setLoanError('');
  };

  const handleSubmitLoan = async (e) => {
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

    setLoanError('');

    try {
      setSubmittingLoan(true);
      const res = await fetch(`${API_BASE_URL}/prestamos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ID_Carnet: loanCarnet.trim(),
          ISBN: selectedBook.ISBN,
          Fecha_Devolucion: loanDate
        })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        showBanner(
          'success',
          `Préstamo exitoso. El libro debe ser devuelto a más tardar el [${data.data.Fecha_Limite_Devolucion}]`
        );
        handleCloseLoanModal();
        await fetchLibros();

        // Si el estudiante cuyo detalle está abierto es el mismo, refrescar su panel
        if (studentResult && studentResult.estudiante.ID_Carnet === loanCarnet.trim()) {
          fetchStudentDetail(loanCarnet.trim());
        }
      } else {
        showBanner('error', data.error || 'No se pudo registrar el préstamo.');
      }
    } catch (err) {
      showBanner('error', `Error al realizar el préstamo: ${err.message}`);
    } finally {
      setSubmittingLoan(false);
    }
  };

  // -------------------------------------------------------------
  // PESTAÑA 2: GESTIÓN DE ESTUDIANTES (LISTADO COMPLETO Y DEVOLUCIÓN)
  // -------------------------------------------------------------
  const [studentsList, setStudentsList] = useState([]);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [searchFilterId, setSearchFilterId] = useState(''); // Filtro dinámico en tiempo real
  const [selectedStudentCarnet, setSelectedStudentCarnet] = useState(null);
  const [studentResult, setStudentResult] = useState(null); // { estudiante, prestamos_activos }
  const [loadingStudentDetail, setLoadingStudentDetail] = useState(false);
  const [returningIsbn, setReturningIsbn] = useState(null); // ISBN procesándose para devolución

  // Modal Registro Nuevo Estudiante
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
  const [registerForm, setRegisterForm] = useState({ Nombre: '', ID_Carnet: '', Telefono: '' });
  const [registerError, setRegisterError] = useState('');
  const [submittingRegister, setSubmittingRegister] = useState(false);

  // Cargar TODOS los estudiantes desde GET /api/estudiantes/todos
  const fetchAllStudents = async () => {
    try {
      setLoadingStudents(true);
      const res = await fetch(`${API_BASE_URL}/estudiantes/todos`);
      const data = await res.json();
      if (data.success) {
        setStudentsList(data.data || []);
      } else {
        showBanner('error', data.error || 'Error al obtener la lista de estudiantes.');
      }
    } catch (err) {
      showBanner('error', `Error al comunicar con la API: ${err.message}`);
    } finally {
      setLoadingStudents(false);
    }
  };

  // Cargar lista de estudiantes al activar la pestaña
  useEffect(() => {
    if (currentUser && activeTab === 'estudiantes') {
      fetchAllStudents();
    }
  }, [currentUser, activeTab]);

  // Filtro dinámico por ID en tiempo real
  const filteredStudents = useMemo(() => {
    const q = searchFilterId.trim();
    if (!q) return studentsList;
    return studentsList.filter((s) => s.ID_Carnet.includes(q));
  }, [studentsList, searchFilterId]);

  // Cargar detalle de un estudiante al hacer clic en la tabla
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
        showBanner('error', data.error || 'No se pudo obtener el detalle del estudiante.');
      }
    } catch (err) {
      showBanner('error', `Error al obtener detalle: ${err.message}`);
    } finally {
      setLoadingStudentDetail(false);
    }
  };

  // Botón de Devolución (POST /api/devolucion)
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
        // Actualizar el panel del estudiante
        if (selectedStudentCarnet) {
          await fetchStudentDetail(selectedStudentCarnet);
        }
        // Actualizar el catálogo de libros para que vuelvan a estar disponibles
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

  // Registro de estudiante
  const handleSubmitRegisterStudent = async (e) => {
    e.preventDefault();
    if (!registerForm.Nombre.trim() || !registerForm.Telefono.trim()) {
      setRegisterError('Todos los campos son obligatorios.');
      return;
    }

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
        // Recargar la lista completa de estudiantes
        await fetchAllStudents();
        // Abrir inmediatamente sus detalles
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
                autoFocus
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

  // -------------------------------------------------------------
  // VISTA PRINCIPAL CON SESIÓN ACTIVA
  // -------------------------------------------------------------
  return (
    <div className="app-container">
      {/* Encabezado y Pestañas */}
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
        </nav>

        <div className="user-profile">
          <span className="user-role-badge">
            👤 {currentUser.ID_Usuario} ({currentUser.Rol})
          </span>
          <button className="btn-logout" onClick={handleLogout} title="Cerrar Sesión">
            Cerrar Sesión
          </button>
        </div>
      </header>

      {/* Banner de Notificaciones */}
      {bannerMessage && (
        <div className={`status-banner ${bannerMessage.type}`}>
          <span>{bannerMessage.text}</span>
          <button
            onClick={() => setBannerMessage(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontWeight: 'bold' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Contenido de Pestañas */}
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
                {libros.map((libro) => {
                  const isBorrowed = libro.Estado === 'Prestado';
                  return (
                    <li
                      key={libro.ISBN}
                      className={`sidebar-item ${isBorrowed ? 'borrowed' : 'available'}`}
                      title={`${libro.Titulo} - Estado: ${libro.Estado}`}
                    >
                      <span className="sidebar-item-title">{libro.Titulo}</span>
                      <span className={`badge sidebar-item-badge ${isBorrowed ? 'borrowed' : 'available'}`}>
                        {libro.Estado}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </aside>

            <main className="main-content">
              <div className="top-nav">
                <div className="search-input-wrapper">
                  <span className="search-icon">🔍</span>
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Buscar libros por título o autor en tiempo real..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <button className="btn-secondary" onClick={fetchLibros} title="Actualizar catálogo">
                  🔄 Actualizar
                </button>
              </div>

              <div className="grid-container">
                {loadingLibros && libros.length === 0 ? (
                  <div className="empty-state">Cargando libros del catálogo...</div>
                ) : filteredLibros.length === 0 ? (
                  <div className="empty-state">No se encontraron libros que coincidan con la búsqueda.</div>
                ) : (
                  <div className="books-grid">
                    {filteredLibros.map((libro) => {
                      const isAvailable = libro.Estado === 'Disponible';
                      return (
                        <div
                          key={libro.ISBN}
                          className={`book-card ${isAvailable ? 'available' : 'borrowed'}`}
                          onClick={() => isAvailable && handleOpenLoanModal(libro)}
                        >
                          <div className="cover-placeholder" style={getCoverStyle(libro.ISBN)}>
                            <span className="cover-placeholder-title">{libro.Titulo}</span>
                          </div>

                          <div className="book-info">
                            <h4 className="book-title" title={libro.Titulo}>{libro.Titulo}</h4>
                            <p className="book-author">Por: {libro.Autor}</p>
                            <p className="book-isbn">ISBN: {libro.ISBN}</p>
                            <span className={`badge ${isAvailable ? 'available' : 'borrowed'}`}>
                              {libro.Estado}
                            </span>
                            <button
                              className="card-action-btn"
                              disabled={!isAvailable}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenLoanModal(libro);
                              }}
                            >
                              {isAvailable ? 'Prestar Libro' : 'No disponible'}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
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

            {/* Barra de Búsqueda / Filtro Dinámico */}
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
                  (Haz clic en un estudiante para ver sus préstamos)
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
                      <th>Acción</th>
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
                              <span className="status-indicator blocked">
                                ● {est.Estado_Cuenta} (Bloqueado/Penalizado)
                              </span>
                            )}
                          </td>
                          <td>
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
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>

            {/* Panel de Detalles del Estudiante Seleccionado */}
            {loadingStudentDetail && (
              <div className="student-card empty-state">Cargando detalles del estudiante...</div>
            )}

            {studentResult && !loadingStudentDetail && (
              <div className="student-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>
                    📄 Detalles del Estudiante
                  </h3>
                  <button
                    className="btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '3px 8px' }}
                    onClick={() => setStudentResult(null)}
                  >
                    Cerrar Panel
                  </button>
                </div>

                <div className="student-info-grid">
                  <div className="info-item">
                    <label>Nombre del Estudiante</label>
                    <span>{studentResult.estudiante.Nombre}</span>
                  </div>
                  <div className="info-item">
                    <label>ID Carnet</label>
                    <span>{studentResult.estudiante.ID_Carnet}</span>
                  </div>
                  <div className="info-item">
                    <label>Teléfono</label>
                    <span>{studentResult.estudiante.Telefono}</span>
                  </div>
                  <div className="info-item">
                    <label>Estado de Cuenta</label>
                    <div>
                      {studentResult.estudiante.Estado_Cuenta === 'Activo' ? (
                        <span className="status-indicator active">● Activo</span>
                      ) : (
                        <span className="status-indicator blocked">
                          ● {studentResult.estudiante.Estado_Cuenta} (Bloqueado/Penalizado)
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Tabla de Libros Prestados con Botón de Devolución */}
                <div className="loans-table-section">
                  <h4>
                    📖 Libros Prestados Actualmente ({studentResult.total_prestamos_activos})
                  </h4>

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
                            <td style={{ color: '#f59e0b', fontWeight: 600 }}>
                              {prestamo.Fecha_Limite_Devolucion}
                            </td>
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
      </div>

      {/* ======================================================== */}
      {/* MODAL: ALQUILER DE LIBROS (CON FECHA DE DEVOLUCIÓN) */}
      {/* ======================================================== */}
      {selectedBook && (
        <div className="modal-overlay" onClick={handleCloseLoanModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Solicitar Préstamo</h3>
              <button className="modal-close-btn" onClick={handleCloseLoanModal}>&times;</button>
            </div>

            <div className="modal-book-summary">
              <p><strong>Libro:</strong> {selectedBook.Titulo}</p>
              <p><strong>Autor:</strong> {selectedBook.Autor}</p>
              <p><strong>ISBN:</strong> {selectedBook.ISBN}</p>
            </div>

            <form onSubmit={handleSubmitLoan}>
              <div className="form-group">
                <label htmlFor="loanCarnetInput">ID Carnet del Estudiante (8 dígitos):</label>
                <input
                  id="loanCarnetInput"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={8}
                  placeholder="Ej: 20261001"
                  value={loanCarnet}
                  onChange={handleLoanCarnetChange}
                  autoFocus
                  required
                />
              </div>

              {/* Nuevo campo de tipo date: Fecha de Devolución */}
              <div className="form-group">
                <label htmlFor="loanDateInput">
                  Fecha de Devolución (Máximo 14 días):
                </label>
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
                  Permitido entre {todayStr} y {maxDateStr}
                </small>
              </div>

              {loanError && (
                <p style={{ color: '#ef4444', fontSize: '0.82rem', marginTop: '6px', fontWeight: '500' }}>
                  ⚠️ {loanError}
                </p>
              )}

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleCloseLoanModal}
                  disabled={submittingLoan}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={submittingLoan}
                >
                  {submittingLoan ? 'Procesando...' : 'Confirmar Préstamo'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL: REGISTRAR NUEVO ESTUDIANTE */}
      {/* ======================================================== */}
      {isRegisterModalOpen && (
        <div className="modal-overlay" onClick={() => setIsRegisterModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Registrar Nuevo Estudiante</h3>
              <button className="modal-close-btn" onClick={() => setIsRegisterModalOpen(false)}>&times;</button>
            </div>

            <form onSubmit={handleSubmitRegisterStudent}>
              <div className="form-group">
                <label htmlFor="regNombre">Nombre Completo:</label>
                <input
                  id="regNombre"
                  type="text"
                  placeholder="Ej: Laura Gómez"
                  value={registerForm.Nombre}
                  onChange={(e) => setRegisterForm({ ...registerForm, Nombre: e.target.value })}
                  autoFocus
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="regCarnet">ID Carnet (8 dígitos numéricos exactos):</label>
                <input
                  id="regCarnet"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={8}
                  placeholder="Ej: 20268899"
                  value={registerForm.ID_Carnet}
                  onChange={(e) => setRegisterForm({ ...registerForm, ID_Carnet: e.target.value.replace(/\D/g, '').slice(0, 8) })}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="regTelefono">Teléfono:</label>
                <input
                  id="regTelefono"
                  type="text"
                  placeholder="Ej: +502 5555-1234"
                  value={registerForm.Telefono}
                  onChange={(e) => setRegisterForm({ ...registerForm, Telefono: e.target.value })}
                  required
                />
              </div>

              {registerError && (
                <p style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: '14px', fontWeight: '500' }}>
                  ⚠️ {registerError}
                </p>
              )}

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsRegisterModalOpen(false)}
                  disabled={submittingRegister}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={submittingRegister}
                >
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
