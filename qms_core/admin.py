from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.forms import widgets
from .models import Service, Counter, CounterAssignment, Token, Screen, Ads, SystemConfig

from django.utils.safestring import mark_safe
from django.urls import reverse

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('system_name', 'voice_name', 'primary_color')
    readonly_fields = ('test_sound_button',)
    
    fieldsets = (
        (_('Identity'), {'fields': ('system_name', 'logo')}),
        (_('Visual Style'), {'fields': ('primary_color', 'secondary_color', 'accent_color')}),
        (_('Voice & Sound'), {'fields': ('voice_name', 'test_sound_button')}),
    )

    def test_sound_button(self, obj):
        test_url = reverse('qms_core:test_voice_sound')
        return mark_safe(
            f'''
            <div style="display: flex; align-items: center; gap: 15px; margin-top: 5px;">
                <button type="button" id="btn-test-voice" class="button" style="background: #2563eb; color: white; padding: 10px 20px; border-radius: 6px; font-weight: bold; border: none; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                    <span id="test-btn-icon">🔊</span> <span id="test-btn-text">Test Selected Voice</span>
                </button>
                <div id="test-loader" style="display: none;" class="spinner-border spinner-border-sm text-primary"></div>
                <small id="test-msg" style="color: #666;"></small>
            </div>
            
            <script>
            (function() {{
                const btn = document.getElementById('btn-test-voice');
                const voiceSelect = document.getElementById('id_voice_name');
                const msg = document.getElementById('test-msg');
                const btnText = document.getElementById('test-btn-text');

                btn.onclick = async function() {{
                    const voice = voiceSelect.value;
                    btn.disabled = true;
                    btn.style.opacity = '0.7';
                    btnText.innerText = 'Generating...';
                    msg.innerText = '';
                    
                    try {{
                        const res = await fetch(`{test_url}?voice=${{voice}}`);
                        const data = await res.json();
                        if (data.success) {{
                            const audio = new Audio("data:audio/mp3;base64," + data.audio);
                            audio.play();
                            msg.innerText = 'Playing...';
                        }} else {{
                            msg.innerText = 'Error: ' + data.error;
                            alert("TTS Error: " + data.error);
                        }}
                    }} catch (e) {{
                        msg.innerText = 'Connection error';
                        console.error(e);
                    }} finally {{
                        btn.disabled = false;
                        btn.style.opacity = '1';
                        btnText.innerText = 'Test Selected Voice';
                    }}
                }};
            }})();
            </script>
            '''
        )
    test_sound_button.short_description = _("Audio Preview")

    def has_add_permission(self, request):
        if SystemConfig.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in ['primary_color', 'secondary_color', 'accent_color']:
            kwargs['widget'] = widgets.TextInput(attrs={
                'type': 'color',
                'style': 'width: 100px; height: 40px; padding: 0; border: none; cursor: pointer; border-radius: 8px;'
            })
        return super().formfield_for_dbfield(db_field, **kwargs)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix')
    search_fields = ('name', 'prefix')

@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display = ('number',)

@admin.register(CounterAssignment)
class CounterAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'counter', 'is_active', 'start_time')
    list_filter = ('is_active', 'user')
    search_fields = ('user__username',)

@admin.register(Ads)
class AdsAdmin(admin.ModelAdmin):
    list_display = ('title', 'show_in_kiosk', 'is_active')
    list_filter = ('show_in_kiosk', 'is_active')
    filter_horizontal = ('public_screens',)
    search_fields = ('user__username',)

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'counter', 'created_at', 'called_at')
    list_filter = ('status', 'service', 'counter')
    readonly_fields = ('created_at',)

@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_counters', 'device_token', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'device_token')
    filter_horizontal = ('counters',)

    def display_counters(self, obj):
        return ", ".join([str(c.number) for c in obj.counters.all()])
    display_counters.short_description = 'Counters'
