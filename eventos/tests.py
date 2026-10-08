from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ConfiguracionOrganizador, Evento, Subtarea

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
        for url in ['/api/eventos/', f'/api/eventos/{self.evento_ana.id}/', '/api/subtareas/', '/api/subtareas/hoy/']:
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


class VistaHoyTests(APITestCase):
    """GET /api/subtareas/hoy/: agrupación y orden (US-04) y filtros (US-05)."""

    def setUp(self):
        self.hoy = timezone.localdate()
        self.ana = User.objects.create_user(username='ana', password='clave-ana-123')
        self.boda = crear_evento(self.ana)
        self.feria = crear_evento(self.ana, titulo='Feria del libro')
        self.client.force_authenticate(self.ana)

    def gestion(self, nombre, dias, horas=1, evento=None):
        return Subtarea.objects.create(
            evento=evento or self.boda,
            nombre=nombre,
            plazo=self.hoy + timedelta(days=dias),
            horas_estimadas=horas
        )

    def consultar(self, **filtros):
        return self.client.get('/api/subtareas/hoy/', filtros)

    @staticmethod
    def nombres(res):
        return {grupo: [s['nombre'] for s in res.data[grupo]] for grupo in ['vencidas', 'hoy', 'proximas']}

    def test_agrupa_por_plazo_y_ordena_dentro_de_cada_grupo(self):
        self.gestion('Pagar DJ', -1)
        self.gestion('Reservar salón', -5)
        self.gestion('Confirmar catering', 0, horas=3)
        self.gestion('Llamar al cliente', 0, horas=1)
        self.gestion('Imprimir invitaciones', 10)
        self.gestion('Comprar flores', 2)

        res = self.consultar()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['fecha'], self.hoy.isoformat())
        self.assertEqual(self.nombres(res), {
            'vencidas': ['Reservar salón', 'Pagar DJ'],
            'hoy': ['Llamar al cliente', 'Confirmar catering'],
            'proximas': ['Comprar flores', 'Imprimir invitaciones'],
        })
        self.assertEqual(res.data['hoy'][0]['evento'], self.boda.id)
        self.assertEqual(res.data['hoy'][0]['evento_titulo'], 'Boda Ana y Luis')

    def test_solo_muestra_las_gestiones_del_organizador(self):
        beto = User.objects.create_user(username='beto', password='clave-beto-123')
        self.gestion('Gestión de Beto', 0, evento=crear_evento(beto, titulo='Evento de Beto'))
        self.gestion('Gestión de Ana', 0)

        self.assertEqual(self.nombres(self.consultar())['hoy'], ['Gestión de Ana'])

    def test_filtra_por_evento(self):
        self.gestion('De la boda', 0)
        self.gestion('De la feria', 0, evento=self.feria)

        self.assertEqual(self.nombres(self.consultar(evento=self.feria.id))['hoy'], ['De la feria'])

    def test_filtra_por_estado_sin_reordenar(self):
        self.gestion('Vencida', -1)
        self.gestion('Próxima lejana', 9, horas=1)
        self.gestion('Próxima cercana', 1, horas=4)

        self.assertEqual(self.nombres(self.consultar(estado='proximas')), {
            'vencidas': [],
            'hoy': [],
            'proximas': ['Próxima cercana', 'Próxima lejana'],
        })

    def test_rango_de_dias_solo_recorta_las_proximas(self):
        self.gestion('Vencida hace mucho', -30)
        self.gestion('De hoy', 0)
        self.gestion('En 3 días', 3)
        self.gestion('En 4 días', 4)

        self.assertEqual(self.nombres(self.consultar(dias=3)), {
            'vencidas': ['Vencida hace mucho'],
            'hoy': ['De hoy'],
            'proximas': ['En 3 días'],
        })

    def test_filtros_no_validos_responden_400(self):
        beto = User.objects.create_user(username='beto', password='clave-beto-123')
        evento_ajeno = crear_evento(beto, titulo='Evento de Beto')

        for filtros, campo in [
            ({'estado': 'completadas'}, 'estado'),
            ({'dias': 0}, 'dias'),
            ({'dias': 'muchos'}, 'dias'),
            ({'evento': 'boda'}, 'evento'),
            ({'evento': evento_ajeno.id}, 'evento'),
        ]:
            with self.subTest(filtros=filtros):
                res = self.consultar(**filtros)
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(campo, res.data)


class ReprogramarSubtareaTests(APITestCase):
    """US-06: reprogramar una gestión logística."""

    def setUp(self):
        self.ana = User.objects.create_user(username='ana', password='clave-ana-123')
        self.beto = User.objects.create_user(username='beto', password='clave-beto-123')
        self.hoy = timezone.localdate()
        self.gestion = Subtarea.objects.create(
            evento=crear_evento(self.ana),
            nombre='Confirmar catering',
            plazo=self.hoy - timedelta(days=2),
            horas_estimadas=3
        )
        self.url = f'/api/subtareas/{self.gestion.id}/reprogramar/'

    def test_reprogramacion_exitosa_guarda_solo_la_nueva_fecha(self):
        self.client.force_authenticate(self.ana)
        nueva = self.hoy + timedelta(days=5)

        res = self.client.patch(self.url, {'plazo': nueva.isoformat(), 'nombre': 'Otro nombre'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['id'], self.gestion.id)
        self.assertEqual(res.data['plazo'], nueva.isoformat())
        self.assertEqual(res.data['evento_titulo'], 'Boda Ana y Luis')
        self.gestion.refresh_from_db()
        self.assertEqual(self.gestion.plazo, nueva)
        self.assertEqual(self.gestion.nombre, 'Confirmar catering')

    def test_la_gestion_reprogramada_aparece_en_su_nuevo_grupo_de_hoy(self):
        self.client.force_authenticate(self.ana)
        antes = self.client.get('/api/subtareas/hoy/').data
        self.assertEqual([s['id'] for s in antes['vencidas']], [self.gestion.id])

        for dias, grupo in [(0, 'hoy'), (3, 'proximas')]:
            with self.subTest(grupo=grupo):
                self.client.patch(self.url, {'plazo': (self.hoy + timedelta(days=dias)).isoformat()})
                despues = self.client.get('/api/subtareas/hoy/').data

                for nombre in ['vencidas', 'hoy', 'proximas']:
                    ids = [s['id'] for s in despues[nombre]]
                    self.assertEqual(ids, [self.gestion.id] if nombre == grupo else [])

    def test_fecha_no_valida_no_reprograma(self):
        self.client.force_authenticate(self.ana)
        ayer = (self.hoy - timedelta(days=1)).isoformat()

        for datos in [{}, {'plazo': ''}, {'plazo': '31/12/2030'}, {'plazo': '2030-02-30'}, {'plazo': ayer}]:
            with self.subTest(datos=datos):
                res = self.client.patch(self.url, datos)

                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(res.data['detail'], 'No se pudo reprogramar.')
                self.assertIn('plazo', res.data)

        self.gestion.refresh_from_db()
        self.assertEqual(self.gestion.plazo, self.hoy - timedelta(days=2))

    def test_no_se_reprograman_gestiones_ajenas_ni_sin_sesion(self):
        datos = {'plazo': (self.hoy + timedelta(days=1)).isoformat()}

        self.assertEqual(self.client.patch(self.url, datos).status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.force_authenticate(self.beto)
        self.assertEqual(self.client.patch(self.url, datos).status_code, status.HTTP_404_NOT_FOUND)

        self.gestion.refresh_from_db()
        self.assertEqual(self.gestion.plazo, self.hoy - timedelta(days=2))


class SobrecargaDiariaTests(APITestCase):
    """US-07: conflicto por sobrecarga diaria al reprogramar (límite de US-12)."""

    def setUp(self):
        self.ana = User.objects.create_user(username='ana', password='clave-ana-123')
        self.client.force_authenticate(self.ana)
        self.boda = crear_evento(self.ana)
        self.feria = crear_evento(self.ana, titulo='Feria del libro')
        self.dia_x = timezone.localdate() + timedelta(days=5)
        # La gestión que se retrasa: "buscar proveedores", 2 h, hoy.
        self.proveedores = self.gestion('Buscar proveedores', timezone.localdate(), 2)

    def gestion(self, nombre, plazo, horas, evento=None):
        return Subtarea.objects.create(
            evento=evento or self.boda, nombre=nombre, plazo=plazo, horas_estimadas=horas
        )

    def reprogramar(self, plazo, **extra):
        return self.client.patch(
            f'/api/subtareas/{self.proveedores.id}/reprogramar/',
            {'plazo': plazo.isoformat(), **extra}
        )

    def test_escenario_1_conflicto_por_retraso_de_proveedores(self):
        # Límite 6 h (por defecto); el día X ya tiene 5 h, en dos eventos.
        reservar = self.gestion('Reservar salón', self.dia_x, 3)
        stands = self.gestion('Montar stands', self.dia_x, 2, evento=self.feria)

        res = self.reprogramar(self.dia_x)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res.data['detail'], 'Quedarías con 7h de gestión planificadas (límite 6h)')
        conflicto = res.data['conflicto']
        self.assertEqual(conflicto['fecha'], self.dia_x.isoformat())
        self.assertEqual(Decimal(conflicto['limite']), 6)
        self.assertEqual(Decimal(conflicto['planificadas']), 5)
        self.assertEqual(Decimal(conflicto['horas_gestion']), 2)
        self.assertEqual(Decimal(conflicto['total']), 7)
        self.assertEqual(
            [(s['id'], s['evento_titulo']) for s in conflicto['gestiones_del_dia']],
            [(stands.id, 'Feria del libro'), (reservar.id, 'Boda Ana y Luis')]
        )
        self.proveedores.refresh_from_db()
        self.assertEqual(self.proveedores.plazo, timezone.localdate())

    def test_escenario_2_sin_conflicto_guarda_directo(self):
        # 4 h + 2 h = 6 h: llega justo al límite, no lo supera.
        self.gestion('Reservar salón', self.dia_x, 4)

        res = self.reprogramar(self.dia_x)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.proveedores.refresh_from_db()
        self.assertEqual(self.proveedores.plazo, self.dia_x)

    def test_escenario_3_datos_para_resolver_el_conflicto(self):
        self.gestion('Reservar salón', self.dia_x, 5)
        self.gestion('Ensayo', self.dia_x + timedelta(days=1), 5)  # X+1 tampoco tiene espacio

        conflicto = self.reprogramar(self.dia_x).data['conflicto']

        # Reducir horas: caben 1 h. Posponer: el primer día con espacio es X+2.
        self.assertEqual(Decimal(conflicto['horas_disponibles']), 1)
        self.assertEqual(conflicto['siguiente_dia_disponible'], (self.dia_x + timedelta(days=2)).isoformat())

    def test_reducir_horas_resuelve_el_conflicto(self):
        self.gestion('Reservar salón', self.dia_x, 5)

        res = self.reprogramar(self.dia_x, horas_estimadas='1')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(res.data['horas_estimadas']), 1)
        self.proveedores.refresh_from_db()
        self.assertEqual((self.proveedores.plazo, self.proveedores.horas_estimadas), (self.dia_x, 1))

    def test_dia_vacio_empieza_en_0_horas(self):
        self.proveedores.horas_estimadas = 7
        self.proveedores.save()

        res = self.reprogramar(self.dia_x)

        # Sola ya supera el límite: no hay día al que posponerla.
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(res.data['detail'], 'Quedarías con 7h de gestión planificadas (límite 6h)')
        self.assertEqual(Decimal(res.data['conflicto']['planificadas']), 0)
        self.assertEqual(res.data['conflicto']['gestiones_del_dia'], [])
        self.assertEqual(Decimal(res.data['conflicto']['horas_disponibles']), 6)
        self.assertIsNone(res.data['conflicto']['siguiente_dia_disponible'])

    def test_horas_con_decimales_en_el_mensaje(self):
        self.gestion('Reservar salón', self.dia_x, '5.5')

        res = self.reprogramar(self.dia_x)

        self.assertEqual(res.data['detail'], 'Quedarías con 7,5h de gestión planificadas (límite 6h)')

    def test_usa_el_limite_definido_por_el_organizador(self):
        ConfiguracionOrganizador.objects.create(organizador=self.ana, limite_horas_diarias=8)
        self.gestion('Reservar salón', self.dia_x, 5)

        self.assertEqual(self.reprogramar(self.dia_x).status_code, status.HTTP_200_OK)

    def test_no_cuenta_gestiones_de_otros_ni_la_misma_dos_veces(self):
        beto = User.objects.create_user(username='beto', password='clave-beto-123')
        self.gestion('De Beto', self.dia_x, 5, evento=crear_evento(beto, titulo='Evento de Beto'))
        self.gestion('Reservar salón', self.dia_x, 4)
        self.proveedores.plazo = self.dia_x
        self.proveedores.save()

        # Ya estaba en X: 4 h + sus 2 h = 6 h, sin contarla dos veces.
        self.assertEqual(self.reprogramar(self.dia_x).status_code, status.HTTP_200_OK)

    def test_error_de_validacion_no_guarda(self):
        for extra in [{'horas_estimadas': '0'}, {'horas_estimadas': 'muchas'}]:
            with self.subTest(extra=extra):
                res = self.reprogramar(self.dia_x, **extra)

                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(res.data['detail'], 'No se pudo reprogramar.')
                self.assertIn('horas_estimadas', res.data)

        self.proveedores.refresh_from_db()
        self.assertEqual(self.proveedores.plazo, timezone.localdate())


class ConfiguracionTests(APITestCase):
    """US-12: límite diario de horas de gestión del organizador."""

    def setUp(self):
        self.ana = User.objects.create_user(username='ana', password='clave-ana-123')

    def test_por_defecto_es_6_horas(self):
        self.client.force_authenticate(self.ana)

        res = self.client.get('/api/configuracion/')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(res.data['limite_horas_diarias']), 6)

    def test_cambiar_el_limite(self):
        self.client.force_authenticate(self.ana)

        res = self.client.patch('/api/configuracion/', {'limite_horas_diarias': '7.5'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.ana.configuracion.limite_horas_diarias, Decimal('7.5'))

    def test_limite_no_valido(self):
        self.client.force_authenticate(self.ana)

        for valor in ['', '0', '-1', '25', '100', 'seis', '6.555']:
            with self.subTest(valor=valor):
                res = self.client.patch('/api/configuracion/', {'limite_horas_diarias': valor})
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('limite_horas_diarias', res.data)

    def test_exige_sesion(self):
        self.assertEqual(self.client.get('/api/configuracion/').status_code, status.HTTP_401_UNAUTHORIZED)
