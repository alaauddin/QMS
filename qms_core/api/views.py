from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from ..models import Token, Service, Ads, Counter, SystemConfig, Screen
from ..views import get_service_wait_info, get_waiting_queue_tokens

@csrf_exempt
def api_kiosk_data(request):
    """
    JSON API for the Kiosk mobile app. Returns services and ads.
    """
    all_services = Service.objects.all()
    services_data = []
    for s in all_services:
        waiting_count, ewt = get_service_wait_info(s)
        services_data.append({
            'id': s.id,
            'name': s.name,
            'prefix': s.prefix,
            'description': s.description or "",
            'icon': s.icon_class or "fas fa-concierge-bell",
            'waiting_count': waiting_count,
            'ewt': ewt
        })
    
    ads = Ads.objects.filter(is_active=True, show_in_kiosk=True)
    ads_data = [{'id': ad.id, 'image_url': request.build_absolute_uri(ad.image.url)} for ad in ads if ad.image]
    
    return JsonResponse({
        'services': services_data,
        'ads': ads_data
    })

@csrf_exempt
@require_POST
def api_take_token(request, service_id):
    """
    JSON API to generate a token and return data for the mobile app (including print fragment).
    """
    service = get_object_or_404(Service, id=service_id)
    
    now = timezone.localtime()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    last_token = Token.objects.filter(created_at__gte=start_of_day).order_by('-number').first()
    next_number = 1 if not last_token else last_token.number + 1
    
    token = Token.objects.create(
        number=next_number,
        service=service,
        status='waiting',
        created_at=timezone.now()
    )
    
    # Broadcast to dashboards
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("queue_updates", {'type': 'queue_changed'})

    # Render the print fragment to a string for expo-print
    print_html = render_to_string('qms_core/token_ticket_fragment.html', {'token': token})

    return JsonResponse({
        'success': True,
        'token': {
            'number': token.number,
            'full_token': str(token),
            'service_name': service.name,
            'prefix': service.prefix,
        },
        'print_html': print_html
    })

@csrf_exempt
def api_get_counters(request):
    """
    Returns a list of all available counters.
    """
    counters = Counter.objects.all().order_by('number')
    data = [{'id': c.id, 'number': c.number} for c in counters]
    return JsonResponse({'counters': data})

@csrf_exempt
def api_get_current_token(request, counter_id):
    """
    Returns the current serving token for a specific counter.
    """
    counter = get_object_or_404(Counter, id=counter_id)
    token = Token.objects.filter(counter=counter, status='called').order_by('-called_at').first()
    
    if token:
        return JsonResponse({
            'success': True,
            'has_token': True,
            'token': {
                'number': token.number,
                'prefix': token.service.prefix,
                'full_token': str(token),
                'service_name': token.service.name,
            }
        })
    else:
        return JsonResponse({
            'success': True,
            'has_token': False
        })
@csrf_exempt
def api_system_config(request):
    """
    Returns the system branding configuration.
    """
    config = SystemConfig.get_config()
    return JsonResponse({
        'system_name': config.system_name,
        'logo_url': request.build_absolute_uri(config.logo.url) if config.logo else None,
        'primary_color': config.primary_color,
        'secondary_color': config.secondary_color,
        'accent_color': config.accent_color,
    })
@csrf_exempt
def api_get_screens(request):
    """
    Returns a list of all active public screens.
    """
    screens = Screen.objects.filter(is_active=True)
    data = [{'id': s.id, 'name': s.name, 'token': s.device_token} for s in screens]
    return JsonResponse({'screens': data})

@csrf_exempt
def api_get_screen_data(request, device_token):
    """
    Returns the current serving status for all counters associated with this screen.
    """
    screen = get_object_or_404(Screen, device_token=device_token, is_active=True)
    counters = screen.counters.all()
    
    serving_data = []
    for c in counters:
        token = Token.objects.filter(counter=c, status='called').order_by('-called_at').first()
        if token:
            serving_data.append({
                'counter_number': c.number,
                'token': {
                    'number': token.number,
                    'prefix': token.service.prefix,
                    'full_token': str(token),
                    'service_name': token.service.name
                }
            })
        else:
            serving_data.append({
                'counter_number': c.number,
                'token': None
            })
    
    # Get last 5 called tokens for this screen's counters
    recent_tokens = Token.objects.filter(
        counter__in=counters, 
        status__in=['called', 'done']
    ).order_by('-called_at')[:5]
    
    recent_data = [{
        'number': t.number,
        'prefix': t.service.prefix,
        'full_token': str(t),
        'counter_number': t.counter.number if t.counter else '?'
    } for t in recent_tokens]

    # Ads for this screen
    ads = Ads.objects.filter(is_active=True, public_screens=screen)
    ads_data = [{'image_url': request.build_absolute_uri(ad.image.url)} for ad in ads if ad.image]

    return JsonResponse({
        'success': True,
        'screen_name': screen.name,
        'serving': serving_data,
        'recent': recent_data,
        'queue': [str(token) for token in get_waiting_queue_tokens()],
        'ads': ads_data
    })
