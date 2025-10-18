from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum
from main.forms import CustomUserCreationForm
from .models import DailyRecord
import json
from decimal import Decimal
from datetime import datetime
from django.db.models.functions import Coalesce
import uuid
import midtransclient
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
from .models import DailyRecord
from decimal import Decimal
import calendar
import json

def get_ai_advice(current_revenue, mom_change):
    if current_revenue == 0:
        return "No data recorded for this month yet. Start adding your daily records to unlock powerful AI insights and predictions!"
    
    advice = ""
    if mom_change > 20:
        advice += "Fantastic! Your revenue is up significantly (over 20%) from last month. Keep up the momentum! Whatever you did last month, it's working."
    elif mom_change > 0:
        advice += f"Good progress. Your revenue is up {mom_change:.0f}% from last month. Keep pushing to grow your sales channels."
    elif mom_change < -20:
        advice += "Warning: Your revenue has dropped significantly (over 20%) this month. It's time to review your expenses, marketing strategy, or product offerings."
    else:
        advice += "Your revenue is stable, which is good. Now, let's look for new opportunities to grow. Consider running a promotion or engaging with customers on social media."
    
    return advice

@login_required
def analytics_view(request):
    today = timezone.now().date()
    first_day_current_month = today.replace(day=1)
    
    # === HITUNG DATA BULAN INI (TETAP SAMA) ===
    current_month_data_qs = DailyRecord.objects.filter(date__gte=first_day_current_month)
    current_revenue = current_month_data_qs.aggregate(total=Sum('income'))['total'] or Decimal('0.00')
    # ... (Hitungan bulan lalu, MoM, prediksi, AI biarkan saja) ...
    last_day_last_month = first_day_current_month - timezone.timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    last_month_data = DailyRecord.objects.filter(date__range=[first_day_last_month, last_day_last_month])
    last_month_revenue = last_month_data.aggregate(total=Sum('income'))['total'] or Decimal('0.00')
    mom_change = 0
    if last_month_revenue > 0: mom_change = ((current_revenue - last_month_revenue) / last_month_revenue) * 100
    elif current_revenue > 0: mom_change = 100
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    current_day_of_month = today.day
    predicted_revenue = 0
    if current_day_of_month > 0:
        daily_avg = current_revenue / current_day_of_month
        predicted_revenue = daily_avg * days_in_month
    ai_advice = get_ai_advice(current_revenue, mom_change)

    # === SIAPIN DATA BUAT CHART (BARU!) ===
    # Ambil semua record bulan ini, diurutkan berdasarkan tanggal
    chart_data = current_month_data_qs.order_by('date')
    
    # Siapin list kosong buat nampung data chart
    chart_labels = [] # Buat tanggal (sumbu X)
    chart_revenue_data = [] # Buat pemasukan (sumbu Y)
    chart_expense_data = [] # Buat pengeluaran (sumbu Y)
    
    # Loop data harian dan masukin ke list
    for record in chart_data:
        chart_labels.append(record.date.strftime('%d %b')) # Format: "19 Oct"
        chart_revenue_data.append(float(record.income)) # Chart.js butuh angka float
        chart_expense_data.append(float(record.expense))

    context = {
        'current_revenue_formatted': f"Rp {current_revenue:,.2f}",
        'mom_change': f"{mom_change:+.2f}",
        'mom_change_value': mom_change,
        'predicted_revenue_formatted': f"Rp {predicted_revenue:,.2f}",
        'ai_advice': ai_advice,
        
        # Kirim data chart ke template (convert ke JSON biar aman dibaca JS)
        'chart_labels': json.dumps(chart_labels),
        'chart_revenue_data': json.dumps(chart_revenue_data),
        'chart_expense_data': json.dumps(chart_expense_data),
    }
    
    return render(request, 'main/analytics.html', context)

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

@login_required
def create_payment_view(request):
    if request.method == 'POST':
        try:
            # Buat instance Snap dengan Basic Auth
            server_key = settings.MIDTRANS_SERVER_KEY
            snap = midtransclient.Snap(
                is_production=False,
                server_key=server_key
            )

            # Buat ID Order yang unik
            order_id = f"QIOS-{request.user.id}-{uuid.uuid4().hex[:6]}"
            
            # Ambil data dari frontend (contoh aja, misal bayar 50rb)
            total_amount = 50000 

            # Siapin parameter transaksi buat Midtrans
            transaction_details = {
                'order_id': order_id,
                'gross_amount': total_amount
            }
            
            # Siapin info customer
            customer_details = {
                'first_name': request.user.username,
                'email': request.user.email
            }

            # Print untuk debugging
            print("Using Server Key:", server_key)
            print("Transaction Details:", transaction_details)
            print("Customer Details:", customer_details)
            
            # Panggil API Midtrans buat bikin transaksi
            transaction = snap.create_transaction({
                "transaction_details": transaction_details,
                "customer_details": customer_details
            })
            
            # Ambil token yang dikasih Midtrans
            payment_token = transaction['token']
            
            # Kirim token ini balik ke JavaScript
            return JsonResponse({'status': 'success', 'token': payment_token})
        
        except Exception as e:
            print("Midtrans Error:", str(e))  # Print error untuk debugging
            return JsonResponse({'status': 'error', 'message': f"Gagal membuat transaksi: {str(e)}"})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

