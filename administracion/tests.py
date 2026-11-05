import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from .models import Account, Administrador, Guardia, Lote, Socio


class AdministratorLoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='password-admin-123',
        )
        Account.objects.create(user=self.user, role='admin')

    def test_administrator_can_login_with_registered_email_and_password(self):
        response = self.client.post(
            reverse('api-login'),
            {
                'email': self.user.email,
                'password': 'password-admin-123',
                'rol': 'administrador',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['token'])
        self.assertEqual(response.data['user']['role_code'], 'admin')

    def test_administrator_login_rejects_unknown_email_and_wrong_password(self):
        attempts = (
            ('unknown@example.com', 'password-admin-123'),
            (self.user.email, 'incorrecta'),
        )

        for email, password in attempts:
            with self.subTest(email=email):
                response = self.client.post(
                    reverse('api-login'),
                    {
                        'email': email,
                        'password': password,
                        'rol': 'administrador',
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, 401)
                self.assertNotIn('token', response.data)
                self.assertEqual(
                    response.data['detail'],
                    'La información de inicio de sesión es incorrecta',
                )

    def test_setup_command_creates_configured_administrator_account(self):
        email = 'configured-admin@example.com'
        password = 'password-configured-123'
        with patch.dict(os.environ, {
            'ZENTRY_ADMIN_EMAIL': email,
            'ZENTRY_ADMIN_PASSWORD': password,
        }):
            call_command('configurar_administrador', stdout=StringIO())

        user = User.objects.get(email=email)
        self.assertTrue(authenticate(username=user.username, password=password))
        self.assertEqual(user.account.role, 'admin')


class AdministratorCreationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin-creacion',
            email='admin-creacion@example.com',
            password='password-admin-123',
        )
        Account.objects.create(user=self.admin, role='admin')
        self.url = reverse('administradores-list')
        self.payload = {
            'nombre': 'Pepita',
            'dni': '30101010',
            'email': 'pepita@example.com',
            'password': 'password-pepita-123',
        }

    def test_admin_can_create_another_administrator(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        self.assertEqual(response.data['nombre'], self.payload['nombre'])
        self.assertEqual(response.data['dni'], self.payload['dni'])
        self.assertEqual(response.data['email'], self.payload['email'])
        administrador = Administrador.objects.get(pk=response.data['id'])
        self.assertEqual(administrador.account.role, 'admin')
        self.assertTrue(administrador.account.user.check_password(self.payload['password']))

        login = self.client.post(
            reverse('api-login'),
            {
                'email': self.payload['email'],
                'password': self.payload['password'],
                'rol': 'administrador',
            },
            format='json',
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data['user']['role_code'], 'admin')

    def test_administrator_creation_requires_an_existing_admin(self):
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 401)

        residente = User.objects.create_user(
            username='residente-creacion',
            email='residente-creacion@example.com',
            password='password-residente-123',
        )
        Account.objects.create(user=residente, role='socio')
        self.client.force_authenticate(user=residente)
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 403)

        guardia = User.objects.create_user(
            username='guardia-creacion',
            email='guardia-creacion@example.com',
            password='password-guardia-123',
        )
        Account.objects.create(user=guardia, role='guardia')
        self.client.force_authenticate(user=guardia)
        response = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 403)

    def test_administrator_creation_rejects_duplicate_email(self):
        self.client.force_authenticate(user=self.admin)
        User.objects.create_user(
            username='cuenta-existente',
            email=self.payload['email'].upper(),
            password='password-existente-123',
        )

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)


class ResidentLoginTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='residente1',
            email='residente@example.com',
            password='password-segura-123',
        )
        self.account = Account.objects.create(user=self.user, role='socio')
        self.lote = Lote.objects.create(numero=10)
        self.socio = Socio.objects.create(
            nombre='Ana',
            apellido='Pérez',
            dni='12345678',
            email=self.user.email,
            account=self.account,
            lote=self.lote,
        )

    def test_resident_can_login_with_registered_email_and_password(self):
        response = self.client.post(
            reverse('api-login'),
            {
                'email': self.user.email,
                'password': 'password-segura-123',
                'rol': 'residente',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['token'])
        self.assertEqual(response.data['user']['socio_id'], self.socio.id)

    def test_unknown_email_and_incorrect_password_are_rejected(self):
        user_count = User.objects.count()
        attempts = (
            ('no-registrado@example.com', 'password-segura-123'),
            (self.user.email, 'incorrecta'),
        )

        for email, password in attempts:
            with self.subTest(email=email):
                response = self.client.post(
                    reverse('api-login'),
                    {
                        'identificador': email,
                        'password': password,
                        'rol': 'residente',
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, 401)
                self.assertNotIn('token', response.data)
                self.assertEqual(
                    response.data['detail'],
                    'La información de inicio de sesión es incorrecta',
                )

        self.assertEqual(User.objects.count(), user_count)

    def test_resident_login_does_not_accept_username_instead_of_email(self):
        response = self.client.post(
            reverse('api-login'),
            {
                'identificador': self.user.username,
                'password': 'password-segura-123',
                'rol': 'residente',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 401)

    def test_creating_resident_creates_login_account_and_password(self):
        email = 'nuevo.residente@example.com'
        password = 'password-nuevo-123'
        response = self.client.post(
            reverse('residentes-list'),
            {
                'nombre': 'Nuevo',
                'apellido': 'Residente',
                'dni': '87654321',
                'email': email,
                'password': password,
                'tipo': 'propietario',
                'lote_numero': 20,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        user = User.objects.get(email=email)
        self.assertEqual(user.account.role, 'socio')
        self.assertTrue(authenticate(username=user.username, password=password))

        all_residents = self.client.get(reverse('residentes-list'))
        owners = self.client.get(reverse('residentes-propietarios'))
        self.assertEqual(all_residents.status_code, 200)
        self.assertEqual(owners.status_code, 200)
        self.assertIn(response.data['id'], [item['id'] for item in all_residents.data])
        self.assertIn(response.data['id'], [item['id'] for item in owners.data])

        login_response = self.client.post(
            reverse('api-login'),
            {
                'email': email,
                'password': password,
                'rol': 'residente',
            },
            format='json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data['user']['socio_id'], response.data['id'])

    def test_creating_resident_rejects_duplicate_email(self):
        response = self.client.post(
            reverse('residentes-list'),
            {
                'nombre': 'Otro',
                'apellido': 'Residente',
                'dni': '87654322',
                'email': self.user.email,
                'password': 'password-nuevo-123',
                'tipo': 'propietario',
                'lote_numero': 21,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_setup_command_links_existing_resident_to_login_account(self):
        email = 'ana@example.com'
        password = 'password-ana-123'
        socio = Socio.objects.create(
            nombre='Ana',
            apellido='Residente',
            dni='99887766',
            email=email,
        )
        with patch.dict(os.environ, {
            'ZENTRY_RESIDENT_EMAIL': email,
            'ZENTRY_RESIDENT_PASSWORD': password,
        }):
            call_command('configurar_acceso_residente', stdout=StringIO())

        socio.refresh_from_db()
        user = User.objects.get(email=email)
        self.assertEqual(socio.account.user_id, user.id)
        self.assertEqual(user.account.role, 'socio')
        self.assertTrue(authenticate(username=user.username, password=password))

    def test_editing_existing_resident_can_create_login_access(self):
        email = 'legacy.residente@example.com'
        password = 'password-legacy-123'
        socio = Socio.objects.create(
            nombre='Residente',
            apellido='Anterior',
            dni='99887767',
            email=email,
        )
        response = self.client.patch(
            reverse('residentes-detail', args=[socio.id]),
            {'password': password},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['tiene_acceso'])
        self.assertNotIn('password', response.data)
        user = User.objects.get(email=email)
        self.assertTrue(authenticate(username=user.username, password=password))

        login_response = self.client.post(
            reverse('api-login'),
            {
                'email': email,
                'password': password,
                'rol': 'residente',
            },
            format='json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data['user']['socio_id'], socio.id)

    def test_login_without_email_or_password_is_rejected_even_without_role(self):
        response = self.client.post(
            reverse('api-login'),
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('token', response.data)


class GuardLoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='guardia@example.com',
            email='guardia@example.com',
            password='password-guardia-123',
        )
        Account.objects.create(user=self.user, role='guardia')

    def test_guard_can_login_with_registered_credentials(self):
        response = self.client.post(
            reverse('api-login'),
            {
                'email': self.user.email,
                'password': 'password-guardia-123',
                'rol': 'guardia',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['token'])
        self.assertEqual(response.data['user']['role_code'], 'guardia')

    def test_guard_login_rejects_wrong_password_and_unknown_email(self):
        user_count = User.objects.count()
        attempts = (
            (self.user.email, 'incorrecta'),
            ('no-existe@example.com', 'password-guardia-123'),
        )

        for email, password in attempts:
            with self.subTest(email=email):
                response = self.client.post(
                    reverse('api-login'),
                    {
                        'email': email,
                        'password': password,
                        'rol': 'guardia',
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, 401)
                self.assertNotIn('token', response.data)
                self.assertEqual(
                    response.data['detail'],
                    'La información de inicio de sesión es incorrecta',
                )

        self.assertEqual(User.objects.count(), user_count)


class GuardiaManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin-guardias',
            email='admin-guardias@example.com',
            password='password-admin-123',
        )
        Account.objects.create(user=self.admin, role='admin')
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_create_guardia_and_guardia_can_login(self):
        email = 'nuevo.guardia@example.com'
        password = 'password-guardia-123'
        response = self.client.post(
            reverse('guardias-list'),
            {
                'nombre': 'Nora',
                'email': email,
                'password': password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        self.assertEqual(response.data['nombre'], 'Nora')
        guardia = Guardia.objects.get(pk=response.data['id'])
        self.assertEqual(guardia.dni, '')
        self.assertEqual(guardia.account.role, 'guardia')
        self.assertTrue(guardia.account.user.check_password(password))

        login = self.client.post(
            reverse('api-login'),
            {'email': email, 'password': password, 'rol': 'guardia'},
            format='json',
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data['user']['role_code'], 'guardia')

    def test_frontend_singular_endpoint_accepts_request_without_trailing_slash(self):
        response = self.client.post(
            '/api/guardia',
            {
                'nombre': 'Nora',
                'email': 'nora.singular@example.com',
                'password': 'password-guardia-123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['email'], 'nora.singular@example.com')

    def test_guardia_can_be_updated_deactivated_and_reactivated(self):
        create_response = self.client.post(
            reverse('guardias-list'),
            {
                'nombre': 'Nora',
                'email': 'nora@example.com',
                'password': 'password-guardia-123',
            },
            format='json',
        )
        guardia_id = create_response.data['id']
        guardia = Guardia.objects.get(pk=guardia_id)
        user = guardia.account.user
        updated_email = 'nora.actualizada@example.com'
        updated_password = 'password-nuevo-123'

        update_response = self.client.patch(
            reverse('guardias-detail', args=[guardia_id]),
            {
                'nombre': 'Nora Actualizada',
                'email': updated_email,
                'password': updated_password,
            },
            format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Nora Actualizada')
        self.assertEqual(user.email, updated_email)
        self.assertTrue(user.check_password(updated_password))

        delete_response = self.client.delete(
            reverse('guardias-detail', args=[guardia_id])
        )
        self.assertEqual(delete_response.status_code, 204)
        guardia.refresh_from_db()
        user.refresh_from_db()
        self.assertFalse(guardia.is_active)
        self.assertFalse(guardia.account.is_active)
        self.assertFalse(user.is_active)

        reactivate_response = self.client.put(
            reverse('guardias-reactivate', args=[guardia_id])
        )
        self.assertEqual(reactivate_response.status_code, 204)
        guardia.refresh_from_db()
        user.refresh_from_db()
        self.assertTrue(guardia.is_active)
        self.assertTrue(guardia.account.is_active)
        self.assertTrue(user.is_active)

    def test_guardia_creation_requires_admin_and_unique_email(self):
        self.client.force_authenticate(user=None)
        payload = {
            'nombre': 'Nora',
            'email': 'guardia@example.com',
            'password': 'password-guardia-123',
        }
        response = self.client.post(
            reverse('guardias-list'), payload, format='json'
        )
        self.assertEqual(response.status_code, 401)

        self.client.force_authenticate(user=self.admin)
        User.objects.create_user(
            username='existing-guardia',
            email=payload['email'],
            password=payload['password'],
        )
        response = self.client.post(
            reverse('guardias-list'), payload, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)
