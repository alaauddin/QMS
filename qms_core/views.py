from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Token, CounterAssignment, Counter, Screen, Service, SystemConfig
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from django.utils.translation import gettext as _

from django.contrib.auth import logout
from django.urls import reverse
import base64
import io
import asyncio
import edge_tts
from .models import Ads
from django.db.models import Count, Avg, F, Q
import threading
import uuid
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

def num_to_ar_words(n):
    # Neural voices handle Ta Marbouta correctly.
    ones = ['', 'واحد', 'اثنان', 'ثلاثة', 'أربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة']
    teens = ['عشرة', 'أحد عشر', 'اثنا عشر', 'ثلاثة عشر', 'أربعة عشر', 'خمسة عشر', 'ستة عشر', 'سبعة عشر', 'ثمانية عشر', 'تسعة عشر']
    tens = ['', '', 'عشرون', 'ثلاثون', 'أربعون', 'خمسون', 'ستون', 'سبعون', 'ثمانون', 'تسعون']
    hundreds = ['', 'مائة', 'مائتان', 'ثلاثمائة', 'أربعمائة', 'خمسمائة', 'ستمائة', 'سبعمائة', 'ثمانمائة', 'تسعمائة']
    
    n = int(n)
    if n == 0: return 'صفر'
    res = ""
    if n >= 100:
        res += hundreds[n // 100] + " "
        n %= 100
        if n > 0: res += "و "
    if n >= 20:
        if n % 10 > 0:
            res += ones[n % 10] + " و " + tens[n // 10]
        else: res += tens[n // 10]
    elif n >= 10: res += teens[n - 10]
    elif n > 0: res += ones[n]
    return res.strip()

def call_voice_text(token_number, counter_number):
    return (
        f"تذكرة رقم {num_to_ar_words(token_number)} . "
        f"يرجى التوجه إلى كونتر {num_to_ar_words(counter_number)} ."
    )


def cached_call_audio_url(token):
    """Return a browser-friendly MP3 URL once this call's audio is cached."""
    if not token.counter_id:
        return None
    import hashlib
    import os
    voice_name = SystemConfig.get_config().voice_name or "ar-AE-FatimaNeural"
    voice_text = call_voice_text(token.number, token.counter.number)
    file_hash = hashlib.md5(f"{voice_text}_{voice_name}".encode()).hexdigest()
    audio_path = os.path.join(settings.MEDIA_ROOT, 'audio_cache', f'{file_hash}.mp3')
    if not os.path.isfile(audio_path):
        return None
    return f"{settings.MEDIA_URL.rstrip('/')}/audio_cache/{file_hash}.mp3"


def _async_tts_broadcast(token_id, counter_id, text):
    """
    Background worker to generate Neural Edge-TTS and broadcast only the audio.
    """
    from .models import Token, Counter, SystemConfig
    try:
        # Fetch data synchronously in the thread before starting async loop
        token = Token.objects.get(id=token_id)
        counter = Counter.objects.get(id=counter_id)
        counter_id_val = counter.id 
        
        # Get voice choice here (synchronously)
        config = SystemConfig.get_config()
        voice_name = config.voice_name or "ar-AE-FatimaNeural"
    except Exception as e:
        print(f"TTS Pre-fetch Error: {e}")
        return

    import hashlib
    import os
    
    # 1. Generate Cache Path
    cache_dir = os.path.join(settings.MEDIA_ROOT, 'audio_cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    
    # Unique filename based on text and voice
    file_hash = hashlib.md5(f"{text}_{voice_name}".encode()).hexdigest()
    cache_file = os.path.join(cache_dir, f"{file_hash}.mp3")

    async def generate_and_send():
        try:
            audio_data = None
            
            # 2. Check Cache First
            if os.path.exists(cache_file):
                print(f"Serving TTS for Token {token.number} from LOCAL CACHE.")
                with open(cache_file, 'rb') as f:
                    audio_data = f.read()
            else:
                # 3. Fetch from Cloud and Save to Cache
                print(f"Generating NEW TTS via Edge-TTS for Token {token.number}.")
                communicate = edge_tts.Communicate(text, voice_name)
                audio_fp = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_fp.write(chunk["data"])
                
                audio_data = audio_fp.getvalue()
                
                # Check if generated audio is valid (at least 1KB)
                if audio_data and len(audio_data) > 1000:
                    # Save to cache asynchronously 
                    with open(cache_file, 'wb') as f:
                        f.write(audio_data)
                    print(f"Successfully generated and CACHED TTS for Token {token.number}")
                else:
                    print(f"WARNING: Generated audio for Token {token.number} is too small/invalid. Not caching.")
                    if not audio_data:
                         return # Don't send empty audio
            
            if len(audio_data) <= 1000:
                return
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            audio_url = f"{settings.MEDIA_URL.rstrip('/')}/audio_cache/{file_hash}.mp3"

            channel_layer = get_channel_layer()
            await channel_layer.group_send(
                "queue_updates",
                {
                    'type': 'token_audio',
                    'audio': audio_base64,
                    'audio_url': audio_url,
                    'token_id': token_id,
                    'counter_id': counter_id_val,
                    'announcement_id': uuid.uuid4().hex,
                }
            )
        except Exception as e:
            print(f"Background Audio Dispatch Error: {e}")

    # Run the async generator inside the background thread
    asyncio.run(generate_and_send())



def broadcast_token_call(token, serving_counter):
    """
    Broadcasts token update immediately, then generates audio in background.
    """
    channel_layer = get_channel_layer()
    
    # 1. Global Call Update (Visual)
    # Sending to 'queue_updates' ensures all screens and dashboards update their display
    async_to_sync(channel_layer.group_send)(
        "queue_updates",
        {
            'type': 'token_called',
            'token': str(token.number),
            'token_id': token.id,
            'service': token.service.prefix,
            'service_name': token.service.name,
            'counter': serving_counter.number,
            'audio': None 
        }
    )
    
    # Also send a small refresh trigger
    async_to_sync(channel_layer.group_send)( "queue_updates", {'type': 'queue_changed'} )

    # 3. Asynchronous Voice Generation
    # Modern & Smooth: Concisely stating the instructions.
    voice_text = call_voice_text(token.number, serving_counter.number)
    threading.Thread(
        target=_async_tts_broadcast, 
        args=(token.id, serving_counter.id, voice_text),
        daemon=True
    ).start()

def get_service_wait_info(service):
    """
    Calculates waiting count and estimated wait time (EWT) for a service.
    EWT = (Waiting Count / Active Counters for this service) * Avg Service Time.
    """
    waiting_count = Token.objects.filter(service=service, status='waiting').count()
    
    # Active counters serving this service
    active_counters_count = CounterAssignment.objects.filter(
        services=service, 
        is_active=True
    ).count()
    
    if active_counters_count == 0:
        return waiting_count, None # No one serving
        
    # Get Avg Service Time today (last 24h)
    from datetime import timedelta
    last_24h = timezone.now() - timedelta(hours=24)
    avg_service_time = Token.objects.filter(
        service=service,
        status='done',
        completed_at__gte=last_24h,
        called_at__isnull=False
    ).annotate(
        duration=F('completed_at') - F('called_at')
    ).aggregate(avg_dur=Avg('duration'))['avg_dur']
    
    # Default to 10 mins if no data
    avg_minutes = (avg_service_time.total_seconds() / 60) if avg_service_time else 10
    
    # EWT Calculation
    ewt_minutes = round((waiting_count / active_counters_count) * avg_minutes)
    if ewt_minutes < 1: ewt_minutes = 1 # Min 1 min
    
    return waiting_count, ewt_minutes




@login_required
def counter_dashboard(request):
    """
    View for the operator dashboard. Shows current token and controls to call next.
    """
    # Ensure the user has at least one active assignment
    assignments = CounterAssignment.objects.filter(user=request.user, is_active=True).select_related('counter').prefetch_related('services')
    if not assignments.exists():
        return redirect('qms_core:select_counter')

    return render(request, "qms_core/counter_dashboard.html", {
        'assignments': assignments,
    })

@login_required
def select_counter(request):
    if request.method == 'POST':
        new_counter_ids = set(request.POST.getlist('counter_ids'))
        new_service_ids = set(request.POST.getlist('service_ids'))
        
        if not new_counter_ids or not new_service_ids:
            # Re-render with error if either is missing
            services = Service.objects.all()
            all_counters = Counter.objects.all()
            return render(request, 'qms_core/select_counter.html', {
                'services': services,
                'all_counters': all_counters,
                'error': _('Please select at least one counter and one service.'),
                'active_counters': CounterAssignment.objects.filter(is_active=True).exclude(user=request.user).values_list('counter_id', flat=True),
                'my_active_counters': CounterAssignment.objects.filter(user=request.user, is_active=True).values_list('counter_id', flat=True),
                'my_active_services': CounterAssignment.objects.filter(user=request.user, is_active=True).values_list('services__id', flat=True)
            })
        
        # 1. Deactivate current user's active assignments
        CounterAssignment.objects.filter(user=request.user, is_active=True).update(
            is_active=False, 
            end_time=timezone.now()
        )
        
        # 2. Activate/Create and set services
        # Even though the frontend sends one, we handle the list for robustness
        for cid in new_counter_ids:
            counter = get_object_or_404(Counter, id=cid)
            assignment, created = CounterAssignment.objects.get_or_create(
                user=request.user,
                counter=counter,
                defaults={'is_active': True, 'start_time': timezone.now()}
            )
            if not created and not assignment.is_active:
                assignment.is_active = True
                assignment.start_time = timezone.now()
                assignment.end_time = None
                assignment.save()
            
            assignment.services.set(new_service_ids)
        
        return redirect('qms_core:counter_dashboard')

    services = Service.objects.all()
    all_counters = Counter.objects.all()
    # Find all counters currently taken by others
    active_counters_other = CounterAssignment.objects.filter(is_active=True).exclude(user=request.user).values_list('counter_id', flat=True)
    my_active_counters = CounterAssignment.objects.filter(user=request.user, is_active=True).values_list('counter_id', flat=True)
    my_active_services = CounterAssignment.objects.filter(user=request.user, is_active=True).values_list('services__id', flat=True).distinct()
    
    return render(request, 'qms_core/select_counter.html', {
        'services': services,
        'all_counters': all_counters,
        'active_counters': active_counters_other,
        'my_active_counters': my_active_counters,
        'my_active_services': my_active_services
    })

@login_required
def stop_session(request):
    """
    Deactivates all active counter assignments for the user without logging out.
    """
    CounterAssignment.objects.filter(user=request.user, is_active=True).update(
        is_active=False,
        end_time=timezone.now()
    )
    return redirect('qms_core:select_counter')

@login_required
def logout_counter_user(request):
    """
    Custom logout to deactivate current assignment before logging out.
    """
    # Deactivate all active assignments for this user
    CounterAssignment.objects.filter(user=request.user, is_active=True).update(
        is_active=False,
        end_time=timezone.now()
    )
    
    logout(request)
    return redirect('qms_core:login')


@login_required
def call_next(request):
    """
    API endpoint to call the next waiting token for the operator's assigned service.
    """
    # Find all counters assigned to this user
    active_assignments = CounterAssignment.objects.filter(user=request.user, is_active=True).prefetch_related('services')
    if not active_assignments.exists():
        return JsonResponse({'error': _('No active counter assignment found.')}, status=400)
    
    # Get all service IDs handleable by these assignments
    service_ids = set()
    for assignment in active_assignments:
        for s in assignment.services.all():
            service_ids.add(s.id)
    
    # NEW LOGIC: Prioritize tokens specifically assigned to this operator's counter(s)
    # 1. Look for tokens where status='waiting' AND counter is one of the user's assigned counters
    counter_ids = active_assignments.values_list('counter_id', flat=True)
    token = Token.objects.filter(
        counter_id__in=counter_ids,
        status='waiting'
    ).order_by('-is_priority', 'created_at').first()

    # 2. Fallback to general queue (counter is None) for the services handled by this operator
    if not token:
        token = Token.objects.filter(
            service_id__in=list(service_ids),
            status='waiting',
            counter__isnull=True
        ).order_by('-is_priority', 'created_at').first()

    if token:
        # Pick the counter that handles this token's service (or just the first assigned counter)
        target_assignment = active_assignments.filter(services=token.service).first()
        serving_counter = target_assignment.counter
        
        token.status = 'called'
        token.counter = serving_counter
        token.called_at = timezone.now()
        token.save()

        broadcast_token_call(token, serving_counter)
        
        return JsonResponse({
            'token': str(token.number), 
            'service': token.service.prefix,
            'full_token': str(token)
        })

    return JsonResponse({'error': _('No tokens waiting for this service.')})

@login_required
def recall_token(request):
    """
    Re-calls the current token assigned to the operator's counter.
    """
    active_assignments = CounterAssignment.objects.filter(user=request.user, is_active=True)
    counter_ids = active_assignments.values_list('counter_id', flat=True)
    
    token = Token.objects.filter(counter_id__in=counter_ids, status='called').order_by('-called_at').first()
    
    if token:
        broadcast_token_call(token, token.counter)
        return JsonResponse({'success': True, 'token': str(token)})
    
    return JsonResponse({'error': _('No active token to recall.')}, status=400)

@login_required
def mark_token_done(request):
    """
    Marks the current token as done.
    """
    active_assignments = CounterAssignment.objects.filter(user=request.user, is_active=True)
    counter_ids = active_assignments.values_list('counter_id', flat=True)
    
    token = Token.objects.filter(counter_id__in=counter_ids, status='called').order_by('-called_at').first()
    
    if token:
        token.status = 'done'
        token.completed_at = timezone.now()
        token.save()
        
        # Broadcast queue update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)("queue_updates", {'type': 'queue_changed'})
        
        # Broadcast clear to counter group
        async_to_sync(channel_layer.group_send)(f"counter_{token.counter.id}", {'type': 'token_cleared'})
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': _('No active token to complete.')}, status=400)

@login_required
def mark_token_no_show(request):
    """
    Marks the current token as skipped/no-show.
    """
    active_assignments = CounterAssignment.objects.filter(user=request.user, is_active=True)
    counter_ids = active_assignments.values_list('counter_id', flat=True)
    
    token = Token.objects.filter(counter_id__in=counter_ids, status='called').order_by('-called_at').first()
    
    if token:
        token.status = 'skipped'
        token.save()
        
        # Broadcast queue update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)("queue_updates", {'type': 'queue_changed'})
        
        # Broadcast clear to counter group
        if token.counter:
            async_to_sync(channel_layer.group_send)(f"counter_{token.counter.id}", {'type': 'token_cleared'})
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': _('No active token to mark as no-show.')}, status=400)

@login_required
def hold_token(request):
    """
    Puts the current called token on hold at the operator's counter.
    """
    active_assignments = CounterAssignment.objects.filter(user=request.user, is_active=True)
    counter_ids = active_assignments.values_list('counter_id', flat=True)
    token = Token.objects.filter(counter_id__in=counter_ids, status='called').order_by('-called_at').first()
    
    if token:
        token.status = 'hold'
        token.save()
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)("queue_updates", {'type': 'queue_changed'})
        
        # Broadcast clear to counter group
        async_to_sync(channel_layer.group_send)(f"counter_{token.counter.id}", {'type': 'token_cleared'})
        
        return JsonResponse({'success': True})
    return JsonResponse({'error': _('No active token to hold.')}, status=400)

@login_required
def resume_token(request, token_id):
    """
    Re-calls a held token.
    """
    token = get_object_or_404(Token, id=token_id, status='hold')
    
    # Ensure this token was held at one of the user's active counters
    active_assignments = CounterAssignment.objects.filter(user=request.user, is_active=True)
    if not active_assignments.filter(counter=token.counter).exists():
        return JsonResponse({'error': _('This token is held at a different counter.')}, status=403)

    token.status = 'called'
    token.called_at = timezone.now()
    token.save()
    
    broadcast_token_call(token, token.counter)
    return JsonResponse({'success': True})

@login_required
def transfer_token(request):
    """
    Transfers current token to another service or counter.
    """
    if request.method != 'POST':
        return JsonResponse({'error': _('Invalid request method.')}, status=405)
        
    import json
    data = json.loads(request.body)
    target_service_id = data.get('service_id')
    target_counter_id = data.get('counter_id')
    is_priority = data.get('is_priority', True)
    
    active_assignments = CounterAssignment.objects.filter(user=request.user, is_active=True)
    counter_ids = active_assignments.values_list('counter_id', flat=True)
    token = Token.objects.filter(counter_id__in=counter_ids, status='called').order_by('-called_at').first()
    
    old_counter_id = token.counter_id
    if target_service_id:
        token.service_id = target_service_id
    
    if target_counter_id:
        token.counter_id = target_counter_id # Direct assignment
    else:
        token.counter = None # Release counter so anyone in the target service can call it
        
    token.status = 'waiting' # Back to queue
    token.is_priority = is_priority
    token.save()
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("queue_updates", {'type': 'queue_changed'})
    
    # Broadcast clear to the OLD counter group
    if old_counter_id:
        async_to_sync(channel_layer.group_send)(f"counter_{old_counter_id}", {'type': 'token_cleared'})
        
    return JsonResponse({'success': True})

@login_required
def get_dashboard_data(request):
    """
    API to fetch real-time dashboard data (stats and queue list).
    """
    active_assignments = CounterAssignment.objects.filter(user=request.user, is_active=True).prefetch_related('services')
    if not active_assignments.exists():
        return JsonResponse({'error': _('No active assignment.')}, status=403)
    
    service_ids = []
    for a in active_assignments:
        service_ids.extend(a.services.values_list('id', flat=True))
    
    now = timezone.localtime()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Stats: Waiting count includes general queue + my specific assignments
    my_counter_ids = active_assignments.values_list('counter_id', flat=True)
    waiting_query = Q(status='waiting') & (
        Q(counter_id__in=my_counter_ids) | 
        (Q(counter__isnull=True) & Q(service_id__in=service_ids))
    )
    
    waiting_count = Token.objects.filter(waiting_query).count()
    served_today = Token.objects.filter(counter__in=active_assignments.values_list('counter_id', flat=True), status='done', completed_at__gte=start_of_day).count()
    
    # Avg service time (for tokens done today by this operator/counter)
    avg_service_time_seconds = Token.objects.filter(
        counter__in=active_assignments.values_list('counter_id', flat=True),
        status='done',
        completed_at__gte=start_of_day,
        called_at__isnull=False
    ).annotate(
        duration=F('completed_at') - F('called_at')
    ).aggregate(avg_dur=Avg('duration'))['avg_dur']
    
    avg_minutes = 0
    if avg_service_time_seconds:
        avg_minutes = round(avg_service_time_seconds.total_seconds() / 60, 1)

    # Queue List: Prioritize direct transfers to me, then general queue
    queue_list = Token.objects.filter(waiting_query).order_by(F('counter_id').asc(nulls_last=True), 'created_at')[:10]
    queue_data = [{
        'number': t.number,
        'prefix': t.service.prefix,
        'service_name': t.service.name,
        'wait_time': round((timezone.now() - t.created_at).total_seconds() / 60)
    } for t in queue_list]
    
    # Currently serving
    current_token = Token.objects.filter(counter_id__in=active_assignments.values_list('counter_id', flat=True), status='called').order_by('-called_at').first()
    current_data = None
    if current_token:
        current_data = {
            'full_token': str(current_token),
            'service_name': current_token.service.name,
            'called_at': current_token.called_at.isoformat() if current_token.called_at else None
        }

    # Held units at this counter
    held_tokens = Token.objects.filter(counter_id__in=active_assignments.values_list('counter_id', flat=True), status='hold').order_by('-called_at')
    held_data = [{
        'id': t.id,
        'number': t.number,
        'prefix': t.service.prefix,
        'service_name': t.service.name,
        'held_at': t.called_at.isoformat() if t.called_at else None
    } for t in held_tokens]

    # Available services & counters for transfer
    all_services = Service.objects.all().values('id', 'name')
    all_counters = Counter.objects.exclude(id__in=active_assignments.values_list('counter_id', flat=True)).values('id', 'number')

    return JsonResponse({
        'stats': {
            'waiting': waiting_count,
            'served': served_today,
            'avg_time': avg_minutes
        },
        'queue': queue_data,
        'current': current_data,
        'held': held_data,
        'transfer_options': {
            'services': list(all_services),
            'counters': list(all_counters)
        }
    })

def broadcast_token_issued(token):
    """Tell public screens about a newly issued ticket and refresh queue clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("queue_updates", {
        'type': 'token_issued',
        'token_id': token.id,
        'full_token': str(token),
        'service_name': token.service.name,
    })
    async_to_sync(channel_layer.group_send)("queue_updates", {'type': 'queue_changed'})


def get_waiting_queue_tokens():
    """Return the first 16 waiting tickets in call order."""
    return list(
        Token.objects.filter(status='waiting')
        .select_related('service')
        .order_by('-is_priority', 'created_at', 'pk')[:16]
    )


def public_screen(request, device_token):
    """
    Public display screen.
    """
    screen = get_object_or_404(Screen, device_token=device_token, is_active=True)
    counters = screen.counters.all()
    queue_tokens = get_waiting_queue_tokens()
    latest_issued = Token.objects.order_by('-created_at', '-pk').first()
    current_token = (
        Token.objects.filter(counter__in=counters, status='called')
        .select_related('service', 'counter')
        .order_by('-called_at', '-pk')
        .first()
    )

    return render(request, 'qms_core/screen.html', {
        'screen': screen,
        'counters': counters,
        'current_token': current_token,
        'latest_issued': latest_issued,
        'queue_columns': [queue_tokens[:8], queue_tokens[8:]],
    })

def kiosk(request):
    """
    Kiosk interface for token generation.
    """
    all_services = Service.objects.all()
    services_data = []
    
    for s in all_services:
        waiting_count, ewt = get_service_wait_info(s)
        services_data.append({
            'obj': s,
            'waiting_count': waiting_count,
            'ewt': ewt
        })
        
    return render(request, 'qms_core/kiosk.html', {
        'services_data': services_data,
    })

@xframe_options_exempt
@require_POST
def take_token(request, service_id):
    """
    Logic for generating a new token for a customer.
    Numbers are unique globally for the day across all services.
    """
    service = get_object_or_404(Service, id=service_id)
    
    # Get the last token number created today (local time) across ALL services
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.localtime()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    last_token = Token.objects.filter(
        created_at__gte=start_of_day
    ).order_by('-number').first()
    
    next_number = 1 if not last_token else last_token.number + 1
    
    token = Token.objects.create(
        number=next_number,
        service=service,
        status='waiting',
        created_at=timezone.now()
    )
    
    broadcast_token_issued(token)

    # Check if a print fragment is requested
    if request.GET.get('format') == 'print':
        return render(request, 'qms_core/token_ticket_fragment.html', {'token': token})

    return render(request, 'qms_core/token_print.html', {'token': token})

@login_required
def admin_dashboard(request):
    """
    Administrative overview of the queue system.
    """
    # Restrict to superusers or specific staff if needed
    if not request.user.is_staff:
        return render(request, 'qms_core/no_permission.html')
        
    counters = Counter.objects.all()
    # Last 50 tokens
    tokens = Token.objects.all().order_by('-created_at')[:50]
    # Current assignments
    assignments = CounterAssignment.objects.all().select_related('user', 'counter')
    
    return render(request, 'qms_core/admin_dashboard.html', {
        'counters': counters,
        'tokens': tokens,
        'assignments': assignments
    })

@login_required
def test_voice_sound(request):
    """
    Diagnostic view to test the selected neural voice.
    """
    voice_name = request.GET.get('voice', SystemConfig.get_config().voice_name)
    test_text = request.GET.get('text', _("تم تفعيل نظام المناداة بنجاح."))
    
    async def generate():
        try:
            communicate = edge_tts.Communicate(test_text, voice_name)
            audio_fp = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_fp.write(chunk["data"])
            return base64.b64encode(audio_fp.getvalue()).decode('utf-8')
        except Exception as e:
            return str(e)

    audio_data = asyncio.run(generate())
    
    if len(audio_data) > 1000: # Simple check for base64 vs error string
        return JsonResponse({'success': True, 'audio': audio_data})
    return JsonResponse({'success': False, 'error': audio_data})
