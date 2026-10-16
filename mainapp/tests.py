import csv
import io
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from smtplib import SMTPException
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import Client, TestCase
from django.test.utils import override_settings
from pypdf import PdfWriter

from .models import Request
from .views import MAX_CV_SIZE, lock_projects_csv, read_projects_csv, save_projects_csv


CSV_HEADER = 'S.No,Name,Category,Description,Detail,Github,Project\n'


def create_valid_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    pdf = io.BytesIO()
    writer.write(pdf)
    return pdf.getvalue()


VALID_PDF = create_valid_pdf()


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PortfolioAdminTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.csv_path = Path(self.temp_dir.name) / 'Data.csv'
        self.csv_path.write_text(
            CSV_HEADER + '1,Existing-Project,Python,Existing description,Existing detail,,\n',
            encoding='utf-8',
        )
        self.cv_path = Path(self.temp_dir.name) / 'Abhay_Singh_CV.pdf'
        self.original_cv = b'%PDF-1.4\nOriginal CV\n%%EOF\n'
        self.cv_path.write_bytes(self.original_cv)
        self.user = get_user_model().objects.create_user(
            username='portfolio-admin',
            password='safe-test-password',
            is_staff=True,
        )
        self.regular_user = get_user_model().objects.create_user(
            username='portfolio-visitor',
            password='safe-test-password',
            is_staff=False,
        )
        self.csv_patch = patch('mainapp.views.CSV_PATH', self.csv_path)
        self.cv_patch = patch('mainapp.views.CV_PATH', self.cv_path)
        self.csv_patch.start()
        self.cv_patch.start()
        self.addCleanup(self.csv_patch.stop)
        self.addCleanup(self.cv_patch.stop)
        self.client.force_login(self.user)

    def test_admin_dashboard_requires_staff_login(self):
        self.client.logout()
        response = self.client.get('/csv-projects/')
        self.assertRedirects(response, '/admins')

    def test_regular_user_is_forbidden_and_cannot_login_as_admin(self):
        self.client.force_login(self.regular_user)
        self.assertEqual(self.client.get('/csv-projects/').status_code, 403)
        self.client.logout()

        response = self.client.post('/admins', {
            'username': 'portfolio-visitor',
            'password': 'safe-test-password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, 'not an admin')

    def test_staff_login_and_post_logout(self):
        self.client.logout()
        response = self.client.post('/admins', {
            'username': 'portfolio-admin',
            'password': 'safe-test-password',
        })
        self.assertRedirects(response, '/csv-projects/')
        self.assertEqual(self.client.get('/csv-projects/').status_code, 200)

        self.assertEqual(self.client.get('/admins/logout/').status_code, 405)
        response = self.client.post('/admins/logout/')
        self.assertRedirects(response, '/')
        self.assertRedirects(self.client.get('/csv-projects/'), '/admins')

    def test_admin_mutations_require_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(
            '/csv-projects/delete/Existing-Project/',
        ).status_code, 403)
        self.assertEqual(self.csv_path.read_text(encoding='utf-8').count('Existing-Project'), 1)

    def test_add_project_preserves_existing_rows_and_assigns_serial_number(self):
        response = self.client.post('/csv-projects/add/', {
            'Name': 'New-Project',
            'Category': 'Django',
            'Description': 'A new project',
            'Detail': 'Project details',
            'Github': 'https://github.com/example/project',
            'Project': 'https://example.com/project',
        })

        self.assertRedirects(response, '/csv-projects/')
        with self.csv_path.open(encoding='utf-8', newline='') as csv_file:
            projects = list(csv.DictReader(csv_file))
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]['Name'], 'Existing-Project')
        self.assertEqual(projects[1]['S.No'], '2')
        self.assertEqual(projects[1]['Name'], 'New-Project')

    def test_add_project_rejects_missing_fields_duplicate_name_and_bad_url(self):
        for payload in (
            {'Name': '', 'Category': 'Python', 'Description': 'Description'},
            {'Name': 'existing-project', 'Category': 'Python', 'Description': 'Duplicate'},
            {
                'Name': 'New-Project',
                'Category': 'Python',
                'Description': 'Description',
                'Github': 'javascript:alert(1)',
            },
        ):
            before = self.csv_path.read_bytes()
            response = self.client.post('/csv-projects/add/', payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.csv_path.read_bytes(), before)

    def test_csv_write_failure_preserves_current_project_data(self):
        before = self.csv_path.read_bytes()
        with patch('mainapp.views.os.replace', side_effect=OSError('simulated storage failure')):
            with self.assertRaises(OSError):
                self.client.post('/csv-projects/add/', {
                    'Name': 'New-Project',
                    'Category': 'Python',
                    'Description': 'Description',
                })
        self.assertEqual(self.csv_path.read_bytes(), before)

    def test_concurrent_csv_additions_do_not_overwrite_each_other(self):
        def append_project(name):
            with lock_projects_csv():
                data = read_projects_csv()
                serial = str(len(data) + 1)
                data.loc[len(data)] = {
                    'S.No': serial,
                    'Name': name,
                    'Category': 'Python',
                    'Description': name,
                    'Detail': '',
                    'Github': '',
                    'Project': '',
                }
                save_projects_csv(data)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(append_project, 'Concurrent-A'),
                executor.submit(append_project, 'Concurrent-B'),
            ]
            for future in futures:
                future.result()

        self.assertEqual(
            set(read_projects_csv()['Name']),
            {'Existing-Project', 'Concurrent-A', 'Concurrent-B'},
        )

    def test_csv_lock_serializes_writers_in_separate_processes(self):
        environment = os.environ.copy()
        environment['PROJECTS_CSV_PATH'] = str(self.csv_path)
        child_code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Portfolio.settings')\n"
            "import django\n"
            "django.setup()\n"
            "from mainapp.views import lock_projects_csv\n"
            "print('ready', flush=True)\n"
            "with lock_projects_csv():\n"
            "    pass\n"
        )
        with lock_projects_csv():
            process = subprocess.Popen(
                [sys.executable, '-c', child_code],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(process.stdout.readline().strip(), 'ready')
            time.sleep(0.2)
            self.assertIsNone(process.poll(), 'Another process should block on the CSV lock.')

        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, stdout + stderr)

    def test_edit_project_updates_record_without_changing_others(self):
        response = self.client.post('/csv-projects/edit/Existing-Project/', {
            'Name': 'Updated-Project',
            'Category': 'Django',
            'Description': 'Updated description',
            'Detail': 'Updated detail',
            'Github': 'https://github.com/example/updated',
            'Project': '',
        })

        self.assertRedirects(response, '/csv-projects/')
        data = read_projects_csv()
        self.assertEqual(data.iloc[0]['Name'], 'Updated-Project')
        self.assertEqual(data.iloc[0]['Category'], 'Django')
        self.assertEqual(data.iloc[0]['S.No'], '1')

    def test_edit_rejects_duplicate_names_without_changing_csv(self):
        with self.csv_path.open('a', encoding='utf-8', newline='') as csv_file:
            csv_file.write('2,Another-Project,Python,Description,Detail,,\n')
        before = self.csv_path.read_bytes()

        response = self.client.post('/csv-projects/edit/Existing-Project/', {
            'Name': 'another-project',
            'Category': 'Python',
            'Description': 'Duplicate',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.csv_path.read_bytes(), before)

    def test_delete_is_post_only_and_preserves_remaining_rows(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/csv-projects/delete/Existing-Project/').status_code, 405)
        with self.csv_path.open('a', encoding='utf-8', newline='') as csv_file:
            csv_file.write('2,Another-Project,Python,Description,Detail,,\n')

        response = self.client.post('/csv-projects/delete/Existing-Project/')

        self.assertRedirects(response, '/csv-projects/')
        data = read_projects_csv()
        self.assertEqual(data['Name'].tolist(), ['Another-Project'])

    def test_missing_empty_malformed_and_wrong_header_csv_are_not_overwritten(self):
        for contents in (
            None,
            '',
            'wrong,columns\nvalue,here\n',
            CSV_HEADER + '1,Only,three\n',
            CSV_HEADER + '"unterminated\n',
        ):
            if contents is None:
                self.csv_path.unlink()
            else:
                self.csv_path.write_text(contents, encoding='utf-8')
            before = self.csv_path.read_bytes() if self.csv_path.exists() else None

            with self.assertLogs('mainapp.views', level='ERROR'):
                response = self.client.post('/csv-projects/add/', {
                    'Name': 'Must-Not-Write',
                    'Category': 'Python',
                    'Description': 'Should not alter a damaged CSV',
                })
            self.assertEqual(response.status_code, 503)

            if before is None:
                self.assertFalse(self.csv_path.exists())
            else:
                self.assertEqual(self.csv_path.read_bytes(), before)
            self.csv_path.write_text(
                CSV_HEADER + '1,Existing-Project,Python,Existing description,Existing detail,,\n',
                encoding='utf-8',
            )

    def test_public_project_page_reports_bad_csv_without_modifying_it(self):
        malformed_csv = 'invalid,header\nleave,this,file\n'
        self.csv_path.write_text(malformed_csv, encoding='utf-8')

        with self.assertLogs('mainapp.views', level='ERROR'):
            response = self.client.get('/Projects')

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'Project data is temporarily unavailable', status_code=503)
        self.assertEqual(self.csv_path.read_text(encoding='utf-8'), malformed_csv)

    def test_unsafe_existing_project_links_are_not_rendered_as_clickable_links(self):
        self.csv_path.write_text(
            CSV_HEADER + '1,Unsafe-Project,Python,Description,Detail,javascript:alert(1),\n',
            encoding='utf-8',
        )

        response = self.client.get('/Projects')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'javascript:alert(1)')

    def test_public_pages_and_cv_download_work(self):
        for url in ('/', '/About', '/Skills', '/Projects', '/Contact'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.get('/cv/download/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), self.original_cv)
        self.assertEqual(self.client.post('/cv/download/').status_code, 405)

    def test_missing_cv_download_returns_404(self):
        self.cv_path.unlink()
        self.assertEqual(self.client.get('/cv/download/').status_code, 404)

    def test_valid_cv_upload_replaces_existing_file(self):
        upload = SimpleUploadedFile('new-cv.pdf', VALID_PDF, content_type='application/pdf')

        response = self.client.post('/csv-projects/cv/', {'cv': upload})

        self.assertRedirects(response, '/csv-projects/')
        self.assertEqual(self.cv_path.read_bytes(), VALID_PDF)

    def test_invalid_incomplete_and_oversized_cv_uploads_keep_existing_cv(self):
        invalid_files = (
            SimpleUploadedFile('resume.pdf', b'not a PDF', content_type='application/pdf'),
            SimpleUploadedFile('incomplete.pdf', b'%PDF-1.4\nno EOF', content_type='application/pdf'),
            SimpleUploadedFile('malformed.pdf', b'%PDF-1.7\nNot a PDF structure\n%%EOF\n', content_type='application/pdf'),
            SimpleUploadedFile('resume.txt', VALID_PDF, content_type='application/pdf'),
            SimpleUploadedFile(
                'oversized.pdf',
                b'%PDF-1.7\n' + (b'x' * MAX_CV_SIZE) + b'\n%%EOF',
                content_type='application/pdf',
            ),
        )
        original = self.cv_path.read_bytes()
        for upload in invalid_files:
            with self.subTest(filename=upload.name):
                response = self.client.post('/csv-projects/cv/', {'cv': upload})
                self.assertRedirects(response, '/csv-projects/')
                self.assertEqual(self.cv_path.read_bytes(), original)

    def test_cv_storage_failure_keeps_existing_file_and_reports_failure(self):
        upload = SimpleUploadedFile('new-cv.pdf', VALID_PDF, content_type='application/pdf')
        with patch('mainapp.views.os.replace', side_effect=OSError('simulated storage failure')):
            with self.assertLogs('mainapp.views', level='ERROR'):
                response = self.client.post('/csv-projects/cv/', {'cv': upload}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.cv_path.read_bytes(), self.original_cv)
        self.assertContains(response, 'existing CV has not been changed')

    def test_contact_form_validates_input_and_persists_before_sending(self):
        response = self.client.post('/Contact', {
            'name': 'Visitor',
            'email': 'invalid-email',
            'subject': 'Question',
            'message': 'Hello',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Request.objects.count(), 0)

        with patch('mainapp.views.mail') as owner_email, patch('mainapp.views.confirmationmail') as confirmation:
            response = self.client.post('/Contact', {
                'name': 'Visitor',
                'email': 'visitor@example.com',
                'subject': 'Question',
                'message': 'Hello',
            })

        self.assertRedirects(response, '/Contact')
        self.assertEqual(Request.objects.count(), 1)
        owner_email.assert_called_once()
        confirmation.assert_called_once()

    def test_contact_email_failure_is_reported_without_losing_submission(self):
        with patch('mainapp.views.mail', side_effect=SMTPException('simulated mail failure')):
            with patch('mainapp.views.confirmationmail') as confirmation:
                with self.assertLogs('mainapp.views', level='ERROR'):
                    response = self.client.post('/Contact', {
                        'name': 'Visitor',
                        'email': 'visitor@example.com',
                        'subject': 'Question',
                        'message': 'Hello',
                    }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Request.objects.count(), 1)
        confirmation.assert_called_once()
        self.assertContains(response, 'message was saved, but an email notification could not be sent')

    def test_missing_email_credentials_are_reported_without_claiming_delivery(self):
        with patch('mainapp.views.settings.EMAIL_CONFIGS', {
            'personal': {'host_user': None, 'host_password': None},
            'portfolio': {'host_user': None, 'host_password': None},
        }):
            with patch('mainapp.views.get_connection') as get_mail_connection:
                with self.assertLogs('mainapp.views', level='ERROR'):
                    response = self.client.post('/Contact', {
                        'name': 'Visitor',
                        'email': 'visitor@example.com',
                        'subject': 'Question',
                        'message': 'Hello',
                    }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Request.objects.count(), 1)
        get_mail_connection.assert_not_called()
        self.assertContains(response, 'message was saved, but an email notification could not be sent')

    def test_contact_missing_required_fields_is_rejected(self):
        response = self.client.post('/Contact', {'name': 'Visitor'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Request.objects.count(), 0)
        self.assertContains(response, 'This field is required.')

    def test_request_migration_is_applied(self):
        loader = MigrationLoader(connection)
        self.assertIn(('mainapp', '0002_request'), loader.applied_migrations)
        self.assertEqual(Request.objects.count(), 0)
