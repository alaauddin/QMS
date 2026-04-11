import asyncio
import hashlib
import os
import base64
import io
import edge_tts
from django.core.management.base import BaseCommand
from django.conf import settings
from qms_core.models import SystemConfig

class Command(BaseCommand):
    help = 'Pre-generates audio cache for common token numbers and counters to support offline mode.'

    def add_arguments(self, parser):
        parser.add_argument('--tokens', type=int, default=100, help='Number of tokens to pre-cache (1 to N)')
        parser.add_argument('--counters', type=int, default=10, help='Number of counters to pre-cache (1 to N)')

    def handle(self, *args, **options):
        max_tokens = options['tokens']
        max_counters = options['counters']
        
        config = SystemConfig.get_config()
        voice = config.voice_name or "ar-AE-FatimaNeural"
        
        cache_dir = os.path.join(settings.MEDIA_ROOT, 'audio_cache')
        os.makedirs(cache_dir, exist_ok=True)

        self.stdout.write(self.style.SUCCESS(f"Starting audio pre-cache for voice: {voice}"))
        self.stdout.write(f"Targets: 1-{max_tokens} tokens and 1-{max_counters} counters.")

        asyncio.run(self.warm_cache(max_tokens, max_counters, voice, cache_dir))

    async def warm_cache(self, max_tokens, max_counters, voice, cache_dir):
        # We need a small helper to convert numbers to Arabic words for the TTS
        # I'll reuse the logic from views or just a simple version here
        from qms_core.views import num_to_ar_words

        total_count = 0
        for t_num in range(1, max_tokens + 1):
            for c_num in range(1, max_counters + 1):
                text = f"تذكرة رقم {num_to_ar_words(t_num)} . يرجى التوجه إلى كونتر {num_to_ar_words(c_num)} ."
                
                file_hash = hashlib.md5(f"{text}_{voice}".encode()).hexdigest()
                cache_file = os.path.join(cache_dir, f"{file_hash}.mp3")

                if os.path.exists(cache_file):
                    continue

                try:
                    self.stdout.write(f"Caching: T{t_num} -> C{c_num}...")
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(cache_file)
                    total_count += 1
                    # Small delay to avoid hitting rate limits if the list is huge
                    await asyncio.sleep(0.1)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error caching T{t_num}C{c_num}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Finished! Cached {total_count} new audio files locally."))
