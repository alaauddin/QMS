from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Service(models.Model):
    name = models.CharField(_("Service Name"), max_length=100)
    prefix = models.CharField(_("Token Prefix"), max_length=5)
    description = models.TextField(_("Service Description"), null=True, blank=True)
    icon_class = models.CharField(_("Icon Class"), max_length=50, default="fas fa-concierge-bell")
    is_visible_on_kiosk = models.BooleanField(_("Show on Kiosk"), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")


class Counter(models.Model):
    number = models.IntegerField(_("Counter Number"))

    def __str__(self):
        return f"{_('Counter')} {self.number}"

    class Meta:
        verbose_name = _("Counter")
        verbose_name_plural = _("Counters")


class CounterAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Operator"))
    counter = models.ForeignKey(Counter, on_delete=models.CASCADE, verbose_name=_("Counter"))
    services = models.ManyToManyField(Service, verbose_name=_("Providing Services"), blank=True)
    start_time = models.DateTimeField(_("Shift Start"), null=True, blank=True)
    end_time = models.DateTimeField(_("Shift End"), null=True, blank=True)
    is_active = models.BooleanField(_("Is Active"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Counter Assignment")
        verbose_name_plural = _("Counter Assignments")
        ordering = ['-created_at']

    def __str__(self):
        status = _("Active") if self.is_active else _("Inactive")
        return f"{self.user} → {self.counter} ({status})"

    def __str__(self):
        status = _("Active") if self.is_active else _("Inactive")
        return f"{self.user} → {self.counter} ({status})"


class Token(models.Model):
    number = models.IntegerField(_("Token Number"))
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))

    STATUS_CHOICES = [
        ('waiting', _('Waiting')),
        ('called', _('Called')),
        ('hold', _('On Hold')),
        ('done', _('Done')),
        ('skipped', _('Skipped')),
        ('no_show', _('Did Not Show Up')),
    ]
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='waiting')
    is_priority = models.BooleanField(_("Is Priority"), default=False)
    counter = models.ForeignKey(Counter, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Counter"))
    created_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(_("Called At"), null=True, blank=True)
    announcement_id = models.CharField(max_length=32, blank=True, default="")
    announced_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(_("Completed At"), null=True, blank=True)

    def __str__(self):
        return f"{self.service.prefix}{self.number}"

    class Meta:
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")


class Screen(models.Model):
    name = models.CharField(_("Screen Name"), max_length=100)
    device_token = models.CharField(_("Device Token"), max_length=100, unique=True)
    counters = models.ManyToManyField(Counter, verbose_name=_("Counters"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Screen")
        verbose_name_plural = _("Screens")

class Ads(models.Model):
    title = models.CharField(_("Title"), max_length=200)
    image = models.ImageField(_("Image"), upload_to='ads/')
    show_in_kiosk = models.BooleanField(_("Show in Kiosk"), default=True)
    public_screens = models.ManyToManyField(Screen, verbose_name=_("Public Screens"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Advertisement")
        verbose_name_plural = _("Advertisements")

class SystemConfig(models.Model):
    VOICE_CHOICES = [
        ('ar-AE-FatimaNeural', _('Fatima (Female - UAE)')),
        ('ar-SA-HamedNeural', _('Hamed (Male - Saudi)')),
        ('ar-SA-ZariyahNeural', _('Zariyah (Female - Saudi)')),
        ('ar-EG-SalmaNeural', _('Salma (Female - Egypt)')),
        ('ar-KW-FahedNeural', _('Fahed (Male - Kuwait)')),
    ]

    system_name = models.CharField(_("System Name"), max_length=100, default="QMS System")
    logo = models.ImageField(_("Logo"), upload_to='system/', null=True, blank=True)
    primary_color = models.CharField(_("Primary Color"), max_length=7, default="#1e40af")
    secondary_color = models.CharField(_("Secondary Color"), max_length=7, default="#0f172a")
    accent_color = models.CharField(_("Accent Color"), max_length=7, default="#f8fafc")
    voice_name = models.CharField(_("Announcement Voice"), max_length=50, choices=VOICE_CHOICES, default='ar-AE-FatimaNeural')


    def save(self, *args, **kwargs):
        if not self.pk and SystemConfig.objects.exists():
            # Ensure only one instance exists
            return
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        config = cls.objects.first()
        if not config:
            config = cls.objects.create()
        return config

    def __str__(self):
        return self.system_name

    class Meta:
        verbose_name = _("System Configuration")
        verbose_name_plural = _("System Configuration")
