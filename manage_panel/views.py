import json
import logging
import smtplib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.core.mail.message import BadHeaderError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.decorators import admin_required
from accounts.forms import StaffUserForm
from clinic import analytics
from clinic.models import (Appointment, Invoice, Prescription, Service,
                           TreatmentRecord)

from .registry import RESOURCES, get_resource

User = get_user_model()
logger = logging.getLogger(__name__)


def _j(obj):
    return json.dumps(obj)


@admin_required
def dashboard(request):
    kpis = analytics.admin_kpis()
    context = {
        'kpis': kpis,
        'revenue_json': _j(analytics.revenue_by_month()),
        'status_json': _j(analytics.appointments_by_status()),
        'treatment_json': _j(analytics.treatment_distribution()),
        'growth_json': _j(analytics.patient_growth()),
        'appts_month_json': _j(analytics.appointments_per_month()),
        'recent_appointments': Appointment.objects.select_related(
            'patient', 'dentist')[:6],
        'recent_invoices': Invoice.objects.select_related('patient')[:6],
        'resources': RESOURCES.values(),
    }
    return render(request, 'manage_panel/dashboard.html', context)


# --------------------------------------------------------------------------
# Generic CRUD
# --------------------------------------------------------------------------
@admin_required
def resource_list(request, slug):
    resource = get_resource(slug)
    if not resource:
        raise Http404
    objects = resource.model.objects.all()
    search = request.GET.get('q', '')
    if search and resource.search_fields:
        q = Q()
        for f in resource.search_fields:
            q |= Q(**{f'{f}__icontains': search})
        objects = objects.filter(q)
    rows = []
    for obj in objects:
        rows.append({
            'obj': obj,
            'cells': [resource.value(obj, attr) for _, attr in resource.list_display],
        })
    return render(request, 'manage_panel/resource_list.html', {
        'resource': resource, 'rows': rows, 'search': search,
    })


@admin_required
def resource_create(request, slug):
    resource = get_resource(slug)
    if not resource:
        raise Http404
    FormClass = resource.form_class()
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f'{resource.label} created.')
            return redirect('manage_panel:resource_list', slug=slug)
    else:
        form = FormClass()
    return render(request, 'manage_panel/resource_form.html',
                  {'resource': resource, 'form': form,
                   'title': f'New {resource.label}'})


@admin_required
def resource_update(request, slug, pk):
    resource = get_resource(slug)
    if not resource:
        raise Http404
    obj = get_object_or_404(resource.model, pk=pk)
    FormClass = resource.form_class()
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'{resource.label} updated.')
            return redirect('manage_panel:resource_list', slug=slug)
    else:
        form = FormClass(instance=obj)
    return render(request, 'manage_panel/resource_form.html',
                  {'resource': resource, 'form': form,
                   'title': f'Edit {resource.label}'})


@admin_required
def resource_delete(request, slug, pk):
    resource = get_resource(slug)
    if not resource:
        raise Http404
    obj = get_object_or_404(resource.model, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, f'{resource.label} deleted.')
        return redirect('manage_panel:resource_list', slug=slug)
    return render(request, 'manage_panel/confirm_delete.html',
                  {'resource': resource, 'object': obj})


# --------------------------------------------------------------------------
# User management (dedicated, supports roles + password)
# --------------------------------------------------------------------------
@admin_required
def user_list(request):
    role = request.GET.get('role', '')
    search = request.GET.get('q', '')
    users = User.objects.all().order_by('-date_joined')
    if role:
        users = users.filter(role=role)
    if search:
        users = users.filter(Q(username__icontains=search) |
                             Q(first_name__icontains=search) |
                             Q(last_name__icontains=search) |
                             Q(email__icontains=search))
    return render(request, 'manage_panel/user_list.html', {
        'users': users, 'current_role': role, 'search': search,
    })


@admin_required
def user_create(request):
    if request.method == 'POST':
        form = StaffUserForm(
            request.POST, request.FILES, require_email=True, include_password=False)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.set_unusable_password()
                    user.save()

                    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                    token = default_token_generator.make_token(user)
                    setup_url = (
                        f'{settings.SITE_URL}'
                        f'{reverse("accounts:password_setup", args=(uidb64, token))}'
                    )
                    email_body = render_to_string(
                        'accounts/emails/account_created.txt',
                        {
                            'name': user.display_name,
                            'username': user.username,
                            'setup_url': setup_url,
                            'login_url': f'{settings.SITE_URL}{reverse("accounts:login")}',
                        },
                    )
                    sent_count = send_mail(
                        subject='Your AimSmile account is ready',
                        message=email_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    if sent_count != 1:
                        raise smtplib.SMTPException('Account setup email was not sent.')
            except (BadHeaderError, ImproperlyConfigured, OSError,
                    smtplib.SMTPException):
                logger.exception(
                    'Could not send account setup email for %s',
                    form.cleaned_data['username'],
                )
                messages.error(
                    request,
                    'The account was not created because its password setup email could not be sent. '
                    'Set valid SMTP values in .env (see README.md), restart the server, and try again.',
                )
            else:
                messages.success(
                    request,
                    f'Account created. Password setup instructions were emailed to {user.email}.',
                )
                return redirect('manage_panel:user_list')
    else:
        form = StaffUserForm(require_email=True, include_password=False)
    return render(request, 'manage_panel/user_form.html',
                  {'form': form, 'title': 'Add User'})


@admin_required
def user_update(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = StaffUserForm(request.POST, request.FILES, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user_obj.username} updated.')
            return redirect('manage_panel:user_list')
    else:
        form = StaffUserForm(instance=user_obj)
    return render(request, 'manage_panel/user_form.html',
                  {'form': form, 'title': f'Edit {user_obj.username}'})


@admin_required
def user_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "You can't delete your own account.")
        return redirect('manage_panel:user_list')
    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, 'User deleted.')
        return redirect('manage_panel:user_list')
    return render(request, 'manage_panel/confirm_delete_user.html', {'object': user_obj})


@admin_required
def reports(request):
    """Extra admin analytics page."""
    from django.db.models import Count
    top_services = (TreatmentRecord.objects.values('service__name')
                    .annotate(count=Count('id')).order_by('-count')[:8])
    context = {
        'revenue_json': _j(analytics.revenue_by_month()),
        'growth_json': _j(analytics.patient_growth()),
        'status_json': _j(analytics.appointments_by_status()),
        'treatment_json': _j(analytics.treatment_distribution()),
        'appts_month_json': _j(analytics.appointments_per_month()),
        'kpis': analytics.admin_kpis(),
        'top_services': top_services,
        'services': Service.objects.all(),
        'total_prescriptions': Prescription.objects.count(),
    }
    return render(request, 'manage_panel/reports.html', context)
