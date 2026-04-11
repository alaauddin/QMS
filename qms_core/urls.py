from django.urls import path
from . import views
from .api import views as api_views

app_name = 'qms_core'

from django.contrib.auth import views as auth_views

urlpatterns = [
    # Counter User Auth
    path('login/', auth_views.LoginView.as_view(template_name='qms_core/login.html'), name='login'),
    path('logout/', views.logout_counter_user, name='logout'),

    # Select service & counter
    path('select-counter/', views.select_counter, name='select_counter'),
    path('stop-session/', views.stop_session, name='stop_session'),

    # Counter dashboard
    path('dashboard/', views.counter_dashboard, name='counter_dashboard'),
    path('call-next/', views.call_next, name='call_next'),
    path('recall/', views.recall_token, name='recall_token'),
    path('mark-done/', views.mark_token_done, name='mark_token_done'),
    path('mark-no-show/', views.mark_token_no_show, name='mark_token_no_show'),
    path('hold/', views.hold_token, name='hold_token'),
    path('resume/<int:token_id>/', views.resume_token, name='resume_token'),
    path('transfer/', views.transfer_token, name='transfer_token'),
    path('dashboard-data/', views.get_dashboard_data, name='get_dashboard_data'),
    # Public Screen
    path('screen/<str:device_token>/', views.public_screen, name='public_screen'),
    
    # Kiosk
    path('kiosk/', views.kiosk, name='kiosk'),
    path('kiosk/take-token/<int:service_id>/', views.take_token, name='take_token'),
    
    # API for Mobile App
    path('api/kiosk/', api_views.api_kiosk_data, name='api_kiosk_data'),
    path('api/kiosk/take-token/<int:service_id>/', api_views.api_take_token, name='api_take_token'),
    path('api/counters/', api_views.api_get_counters, name='api_get_counters'),
    path('api/counters/current-token/<int:counter_id>/', api_views.api_get_current_token, name='api_get_current_token'),
    path('api/config/', api_views.api_system_config, name='api_system_config'),
    path('api/screens/', api_views.api_get_screens, name='api_get_screens'),
    path('api/screens/data/<str:device_token>/', api_views.api_get_screen_data, name='api_get_screen_data'),

    # Management
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('test-voice-sound/', views.test_voice_sound, name='test_voice_sound'),
]
