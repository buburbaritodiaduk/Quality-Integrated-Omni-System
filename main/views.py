from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum
from .models import DailyRecord
import json
from decimal import Decimal
from datetime import datetime
from django.db.models.functions import Coalesce

@login_required
def dashboard_view(request):
    # Ambil data awal untuk ditampilkan saat halaman pertama kali dibuka
    total_orders = DailyRecord.objects.aggregate(total=Sum('orders_count'))['total'] or 0
    total_income = DailyRecord.objects.aggregate(total=Sum('income'))['total'] or 0
    total_expense = DailyRecord.objects.aggregate(total=Sum('expense'))['total'] or 0
    total_revenue = total_income - total_expense
    
    latest_records = DailyRecord.objects.all()

    context = {
        'total_orders': total_orders,
        # Format angka menjadi string yang cantik sebelum dikirim
        'total_revenue': f"Rp {total_revenue:,.2f}",
        'total_income': f"Rp {total_income:,.2f}",
        'latest_records': latest_records,
    }
    return render(request, 'main/dashboard.html', context)

@login_required
def add_record_view(request):
    if request.method == 'POST':
        try:
            # Parse JSON data dari request body
            data = json.loads(request.body)
            
            # Ambil data dari JSON dan convert date string ke datetime object
            date_str = data.get('date')
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            income = Decimal(data.get('income', 0))
            expense = Decimal(data.get('expense', 0))
            orders_count = int(data.get('orders_count', 0))

            # Simpan record baru ke database
            new_record = DailyRecord.objects.create(
                date=date,
                income=income,
                expense=expense,
                orders_count=orders_count
            )

            # Hitung ulang total untuk response
            total_orders = DailyRecord.objects.aggregate(total=Sum('orders_count'))['total'] or 0
            total_income = DailyRecord.objects.aggregate(total=Sum('income'))['total'] or 0
            total_expense = DailyRecord.objects.aggregate(total=Sum('expense'))['total'] or 0
            total_revenue = total_income - total_expense

            # Return response JSON dengan data yang diperbarui
            return JsonResponse({
                'status': 'success',
                'new_record': {
                    'date': new_record.date.strftime("%d/%m/%Y"),
                    'income': f"Rp {new_record.income}",
                },
                'total_orders': total_orders,
                'total_income': f"Rp {total_income}",
                'total_revenue': f"Rp {total_revenue}"
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return redirect('dashboard')

# Halaman Register
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'main/register.html', {'form': form})

# Halaman Login
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'main/login.html', {'form': form})

@login_required
def filter_dashboard_view(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        # Filter queryset berdasarkan rentang tanggal
        queryset = DailyRecord.objects.filter(date__range=[start_date_str, end_date_str])
    else:
        # Jika tidak ada tanggal, kembalikan semua data
        queryset = DailyRecord.objects.all()

    # Hitung ulang agregat dari data yang sudah difilter
    aggregates = queryset.aggregate(
        total_orders=Coalesce(Sum('orders_count'), 0),
        total_income=Coalesce(Sum('income'), Decimal('0.00')),
        total_expense=Coalesce(Sum('expense'), Decimal('0.00'))
    )
    
    total_revenue = aggregates['total_income'] - aggregates['total_expense']
    
    # Ambil semua record dalam rentang itu untuk di-render di tabel
    records = list(queryset.values('date', 'income'))
    
    # Format data untuk dikirim sebagai JSON
    for record in records:
        record['date'] = record['date'].strftime('%d/%m/%Y')
        record['income'] = f"Rp {record['income']:,.2f}"

    response_data = {
        'total_orders': aggregates['total_orders'],
        'total_income': f"Rp {aggregates['total_income']:,.2f}",
        'total_revenue': f"Rp {total_revenue:,.2f}",
        'records': records
    }
    
    return JsonResponse(response_data)