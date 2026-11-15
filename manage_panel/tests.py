import smtplib
from urllib.parse import urlsplit
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='clinic@example.com',
)
class AdminAccountInviteTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='clinic-admin',
            password='admin-pass-928!',
            role='admin',
        )
        self.client.force_login(self.admin)

    def account_payload(self, username='new-patient'):
        return {
            'username': username,
            'first_name': 'New',
            'last_name': 'Patient',
            'email': f'{username}@example.com',
            'role': 'patient',
            'is_active': 'on',
        }

    def test_creation_emails_one_time_password_setup_link(self):
        response = self.client.post(
            reverse('manage_panel:user_create'),
            self.account_payload(),
        )

        self.assertRedirects(response, reverse('manage_panel:user_list'))
        user = User.objects.get(username='new-patient')
        self.assertFalse(user.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.username, mail.outbox[0].body)

        setup_url = next(
            line for line in mail.outbox[0].body.splitlines()
            if '/accounts/password-setup/' in line
        )
        setup_path = urlsplit(setup_url).path
        response = self.client.post(setup_path, {
            'new_password1': 'Secure-Setup-Password-928!',
            'new_password2': 'Secure-Setup-Password-928!',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('accounts:login'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('Secure-Setup-Password-928!'))
        self.assertEqual(self.client.get(setup_path).status_code, 400)

    def test_account_creation_requires_an_email_address(self):
        payload = self.account_payload(username='no-email-user')
        payload['email'] = ''

        response = self.client.post(reverse('manage_panel:user_create'), payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertFalse(User.objects.filter(username='no-email-user').exists())
        self.assertEqual(mail.outbox, [])

    @patch('manage_panel.views.send_mail', side_effect=smtplib.SMTPException)
    def test_account_creation_rolls_back_if_email_cannot_be_sent(self, _send_mail):
        response = self.client.post(
            reverse('manage_panel:user_create'),
            self.account_payload(username='unsent-user'),
        )

        _send_mail.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'password setup email could not be sent')
        self.assertFalse(User.objects.filter(username='unsent-user').exists())
