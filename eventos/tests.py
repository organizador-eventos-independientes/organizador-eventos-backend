from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Evento, Subtarea

User = get_user_model()


def crear_evento(organizador, titulo='Boda Ana y Luis'):
    return Evento.objects.create(
        organizador=organizador,
        titulo=titulo,
        tipo='boda',
        cliente='Ana Pérez',
        fecha=date.today() + timedelta(days=30),
        hora=time(18, 0),
        lugar='Salón Los Robles'
    )


class LoginTests(APITestCase):
    """US-11, escenarios 1 y 2."""

    def setUp(self):
        User.objects.create_user(username='ana', password='clave-segura-123', first_name='Ana')

    def login(self, username, password):
        return self.client.post('/api/auth/login/', {'username': username, 'password': password})

    def test_login_correcto_devuelve_token_y_usuario(self):
        res = self.login('ana', 'clave-segura-123')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['token'])
        self.assertEqual(res.data['usuario']['username'], 'ana')
        self.assertEqual(res.data['usuario']['nombre'], 'Ana')

    def test_credenciales_invalidas_no_revelan_si_el_usuario_existe(self):
        clave_incorrecta = self.login('ana', 'otra-clave')
        usuario_inexistente = self.login('nadie', 'otra-clave')

        self.assertEqual(clave_incorrecta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(clave_incorrecta.data, {'detail': 'Credenciales inválidas.'})
        self.assertEqual(usuario_inexistente.status_code, clave_incorrecta.status_code)
        self.assertEqual(usuario_inexistente.data, clave_incorrecta.data)

    def test_campos_vacios_responden_como_credenciales_invalidas(self):
        res = self.client.post('/api/auth/login/', {})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data, {'detail': 'Credenciales inválidas.'})

    def test_logout_invalida_el_token(self):
        token = self.login('ana', 'clave-segura-123').data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        self.assertEqual(self.client.post('/api/auth/logout/').status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get('/api/eventos/').status_code, status.HTTP_401_UNAUTHORIZED)


class RegistroTests(APITestCase):
    def registrar(self, **datos):
        datos = {'nombre': 'Carla Gómez', 'username': 'carla', 'password': 'Fiesta-2026-cali', **datos}
        return self.client.post('/api/auth/registro/', datos)

    def test_registro_crea_la_cuenta_y_deja_la_sesion_iniciada(self):
        res = self.registrar()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['usuario']['username'], 'carla')
        self.assertEqual(res.data['usuario']['nombre'], 'Carla Gómez')
        usuario = User.objects.get(username='carla')
        self.assertEqual((usuario.first_name, usuario.last_name), ('Carla', 'Gómez'))
        self.assertNotEqual(usuario.password, 'Fiesta-2026-cali')  # se guarda cifrada

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {res.data['token']}")
        self.assertEqual(self.client.get('/api/eventos/').data, [])

    def test_la_cuenta_nueva_puede_iniciar_sesion(self):
        self.registrar()

        res = self.client.post('/api/auth/login/', {'username': 'carla', 'password': 'Fiesta-2026-cali'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_usuario_repetido_sin_importar_mayusculas(self):
        self.registrar()

        res = self.registrar(username='Carla')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['username'], ['Ese nombre de usuario ya está en uso. Elige otro.'])
        self.assertEqual(User.objects.filter(username__iexact='carla').count(), 1)

    def test_contrasena_debil_se_rechaza_con_mensajes_en_espanol(self):
        res = self.registrar(password='123')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('La contraseña es demasiado corta. Debe contener por lo menos 8 caracteres.', res.data['password'])
        self.assertIn('Esta contraseña es completamente numérica.', res.data['password'])
        self.assertFalse(User.objects.filter(username='carla').exists())

    def test_campos_obligatorios_y_usuario_con_espacios(self):
        vacio = self.client.post('/api/auth/registro/', {})
        con_espacios = self.registrar(username='carla gomez')

        self.assertEqual(set(vacio.data), {'nombre', 'username', 'password'})
        self.assertEqual(con_espacios.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', con_espacios.data)


class AislamientoPorOrganizadorTests(APITestCase):
    """US-11, escenarios 3 y 4."""

    def setUp(self):
        self.ana = User.objects.create_user(username='ana', password='clave-ana-123')
        self.beto = User.objects.create_user(username='beto', password='clave-beto-123')
        self.evento_ana = crear_evento(self.ana)
        self.gestion_ana = Subtarea.objects.create(
            evento=self.evento_ana,
            nombre='Reservar salón',
            plazo=date.today(),
            horas_estimadas=2
        )

    def test_sin_sesion_no_hay_acceso_a_los_datos(self):
        for url in ['/api/eventos/', f'/api/eventos/{self.evento_ana.id}/', '/api/subtareas/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_el_organizador_ve_sus_eventos_y_gestiones(self):
        self.client.force_authenticate(self.ana)

        self.assertEqual([e['id'] for e in self.client.get('/api/eventos/').data], [self.evento_ana.id])
        self.assertEqual([s['id'] for s in self.client.get('/api/subtareas/').data], [self.gestion_ana.id])

    def test_otro_organizador_no_ve_ni_modifica_eventos_ajenos(self):
        self.client.force_authenticate(self.beto)

        self.assertEqual(self.client.get('/api/eventos/').data, [])
        self.assertEqual(self.client.get('/api/subtareas/').data, [])
        for res in [
            self.client.get(f'/api/eventos/{self.evento_ana.id}/'),
            self.client.get(f'/api/eventos/{self.evento_ana.id}/subtareas/'),
            self.client.patch(f'/api/eventos/{self.evento_ana.id}/', {'titulo': 'Hackeado'}),
            self.client.delete(f'/api/eventos/{self.evento_ana.id}/'),
            self.client.patch(f'/api/subtareas/{self.gestion_ana.id}/', {'nombre': 'Hackeada'}),
            self.client.delete(f'/api/subtareas/{self.gestion_ana.id}/'),
        ]:
            self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        self.evento_ana.refresh_from_db()
        self.assertEqual(self.evento_ana.titulo, 'Boda Ana y Luis')
        self.assertTrue(Subtarea.objects.filter(id=self.gestion_ana.id, nombre='Reservar salón').exists())

    def test_no_se_pueden_crear_gestiones_en_eventos_ajenos(self):
        self.client.force_authenticate(self.beto)
        datos = {'nombre': 'Intrusa', 'plazo': date.today().isoformat(), 'horas_estimadas': '1'}

        anidada = self.client.post(f'/api/eventos/{self.evento_ana.id}/subtareas/', datos)
        directa = self.client.post('/api/subtareas/', {**datos, 'evento': self.evento_ana.id})

        self.assertEqual(anidada.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(directa.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Subtarea.objects.filter(nombre='Intrusa').exists())

    def test_el_evento_creado_queda_a_nombre_de_quien_lo_crea(self):
        self.client.force_authenticate(self.beto)
        datos = {
            'titulo': 'Cumpleaños de Beto',
            'tipo': 'cumpleanos',
            'cliente': 'Beto',
            'fecha': (date.today() + timedelta(days=10)).isoformat(),
            'hora': '19:00',
            'lugar': 'Casa de Beto',
            'organizador': self.ana.id,  # se ignora: es de solo lectura
        }

        res = self.client.post('/api/eventos/', datos)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Evento.objects.get(id=res.data['id']).organizador, self.beto)
