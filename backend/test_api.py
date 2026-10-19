import unittest
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import get_db_connection, init_db

class BibliotecaAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_01_get_libros(self):
        response = self.client.get('/api/libros')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['total'], 10)
        # Verificar orden alfabetico por titulo
        titulos = [l['Titulo'] for l in data['data']]
        self.assertEqual(titulos, sorted(titulos))

    def test_02_post_estudiante_success_and_duplicate(self):
        payload_invalido = {
            "ID_Carnet": "EST-1001",
            "Nombre": "Invalido Formato",
            "Telefono": "+502 5555-0000"
        }
        res_inv = self.client.post('/api/estudiantes', json=payload_invalido)
        self.assertEqual(res_inv.status_code, 400)
        self.assertEqual(res_inv.get_json()['error'], 'El ID debe ser un número de exactamente 8 dígitos.')

        payload = {
            "ID_Carnet": "20261001",
            "Nombre": "Carlos Mendoza",
            "Telefono": "+502 5555-1234"
        }
        # Registro inicial o duplicado
        res1 = self.client.post('/api/estudiantes/registro', json=payload)
        self.assertIn(res1.status_code, [201, 400])
        
        # Intento de duplicado debe retornar 400
        res2 = self.client.post('/api/estudiantes/registro', json=payload)
        self.assertEqual(res2.status_code, 400)
        self.assertFalse(res2.get_json()['success'])

    def test_03_prestamos_logica(self):
        # 1. Registrar estudiante de prueba con ID numerico de 8 digitos
        carnet = "20261002"
        self.client.post('/api/estudiantes/registro', json={
            "ID_Carnet": carnet,
            "Nombre": "Lucia Morales",
            "Telefono": "+502 4444-5678"
        })
        # Asegurar estado Activo
        conn = get_db_connection()
        conn.execute("UPDATE Estudiantes SET Estado_Cuenta = 'Activo' WHERE ID_Carnet = ?;", (carnet,))
        conn.commit()
        conn.close()

        # Test validacion rechazo prestamo por carnet no numerico o longitud != 8
        res_inv = self.client.post('/api/prestamos', json={
            "ID_Carnet": "123",
            "ISBN": "978-0132350884"
        })
        self.assertEqual(res_inv.status_code, 400)
        self.assertEqual(res_inv.get_json()['error'], 'El ID debe ser un número de exactamente 8 dígitos.')

        # Obtener o resetear un libro a 'Disponible'
        conn = get_db_connection()
        conn.execute("UPDATE Libros SET Estado = 'Disponible' WHERE ISBN = '978-0141439518';")
        conn.commit()
        conn.close()

        isbn_test = '978-0141439518'

        # Realizar prestamo con exito
        res_prestamo = self.client.post('/api/prestamos', json={
            "ID_Carnet": carnet,
            "ISBN": isbn_test
        })
        self.assertEqual(res_prestamo.status_code, 201)
        data_p = res_prestamo.get_json()
        self.assertTrue(data_p['success'])

        # Intentar prestar el mismo libro nuevamente (debe fallar por estado 'Prestado')
        res_prestamo_repetido = self.client.post('/api/prestamos', json={
            "ID_Carnet": carnet,
            "ISBN": isbn_test
        })
        self.assertEqual(res_prestamo_repetido.status_code, 409)

        # Verificar validacion de estudiante bloqueado
        conn = get_db_connection()
        conn.execute("UPDATE Estudiantes SET Estado_Cuenta = 'Bloqueado' WHERE ID_Carnet = ?;", (carnet,))
        conn.commit()
        conn.close()

        res_libros = self.client.get('/api/libros')
        libros = res_libros.get_json()['data']
        otro_libro = next((l for l in libros if l['ISBN'] != isbn_test and l['Estado'] == 'Disponible'), None)
        res_bloqueado = self.client.post('/api/prestamos', json={
            "ID_Carnet": carnet,
            "ISBN": otro_libro['ISBN']
        })
        self.assertIn(res_bloqueado.status_code, [400, 403])

    def test_04_get_prestamos_activos(self):
        res = self.client.get('/api/prestamos/activos')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIsInstance(data['data'], list)
        if len(data['data']) > 0:
            prestamo = data['data'][0]
            for key in ["ID", "Nombre_Estudiante", "ID_Carnet", "Titulo_Libro", "ISBN", "Telefono", "Fecha_Limite_Devolucion"]:
                self.assertIn(key, prestamo)

if __name__ == "__main__":
    unittest.main()
