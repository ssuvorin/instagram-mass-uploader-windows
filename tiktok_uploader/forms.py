"""
Forms for TikTok Uploader
==========================

Django формы для всех моделей TikTok Uploader.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
import re

from .models import (
    TikTokAccount, TikTokProxy, BulkUploadTask,
    WarmupTask, FollowTask, FollowCategory, FollowTarget,
    CookieRobotTask, BulkVideo, VideoCaption
)


# ============================================================================
# АККАУНТЫ
# ============================================================================

class TikTokAccountForm(forms.ModelForm):
    """
    Форма создания/редактирования TikTok аккаунта.
    """
    
    class Meta:
        model = TikTokAccount
        fields = [
            'username', 'password', 'email', 'email_password',
            'phone_number', 'proxy', 'locale', 'client', 'notes'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'email_password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
            'proxy': forms.Select(attrs={'class': 'form-select'}),
            'locale': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('en_US', 'English (US)'),
                ('en_GB', 'English (GB)'),
                ('es_ES', 'Español (España)'),
                ('es_MX', 'Español (México)'),
                ('pt_BR', 'Português (Brasil)'),
                ('ru_RU', 'Русский'),
                ('de_DE', 'Deutsch'),
                ('fr_FR', 'Français'),
            ]),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_username(self):
        """Валидация username: только буквы, цифры, точки, подчеркивания."""
        username = self.cleaned_data.get('username')
        if not re.match(r'^[\w.]+$', username):
            raise ValidationError('Username can only contain letters, numbers, dots, and underscores.')
        return username
    
    def clean_phone_number(self):
        """Валидация номера телефона."""
        phone = self.cleaned_data.get('phone_number')
        if phone and not re.match(r'^\+?[\d\s\-\(\)]+$', phone):
            raise ValidationError('Invalid phone number format.')
        return phone


class BulkAccountImportForm(forms.Form):
    """
    Форма массового импорта аккаунтов.
    """
    
    file = forms.FileField(
        label='Accounts File',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.txt,.csv,.json'}),
        help_text='Supported formats: TXT, CSV, JSON'
    )
    
    format = forms.ChoiceField(
        label='File Format',
        choices=[
            ('auto', 'Auto-detect'),
            ('txt', 'TXT (username:password:email:...)'),
            ('csv', 'CSV (username,password,email,...)'),
            ('json', 'JSON'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='auto'
    )
    
    assign_proxies = forms.BooleanField(
        label='Auto-assign proxies',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    create_dolphin_profiles = forms.BooleanField(
        label='Create Dolphin profiles',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Create Dolphin Anty profiles for each account (slower)'
    )
    
    client = forms.ModelChoiceField(
        queryset=None,  # Set in __init__ based on user
        label='Assign to Client',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ============================================================================
# ПРОКСИ
# ============================================================================

class TikTokProxyForm(forms.ModelForm):
    """
    Форма создания/редактирования прокси.
    """
    
    test_on_save = forms.BooleanField(
        label='Test proxy after saving',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = TikTokProxy
        fields = [
            'host', 'port', 'username', 'password',
            'proxy_type', 'ip_change_url', 'notes'
        ]
        widgets = {
            'host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1.2.3.4 or proxy.example.com'}),
            'port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '8080'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'proxy_type': forms.Select(attrs={'class': 'form-select'}),
            'ip_change_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean_port(self):
        """Валидация порта."""
        port = self.cleaned_data.get('port')
        if port < 1 or port > 65535:
            raise ValidationError('Port must be between 1 and 65535.')
        return port
    
    def clean_ip_change_url(self):
        """Валидация URL для смены IP."""
        url = self.cleaned_data.get('ip_change_url')
        if url:
            validator = URLValidator()
            try:
                validator(url)
            except ValidationError:
                raise ValidationError('Invalid URL format.')
        return url


class BulkProxyImportForm(forms.Form):
    """
    Форма массового импорта прокси.
    """
    
    file = forms.FileField(
        label='Proxy List File',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.txt'}),
        help_text='One proxy per line'
    )
    
    format = forms.ChoiceField(
        label='Proxy Format',
        choices=[
            ('auto', 'Auto-detect'),
            ('host_port', 'host:port'),
            ('host_port_user_pass', 'host:port:username:password'),
            ('url', 'protocol://username:password@host:port'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='auto'
    )
    
    default_type = forms.ChoiceField(
        label='Default Proxy Type',
        choices=TikTokProxy.PROXY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='HTTP'
    )
    
    test_on_import = forms.BooleanField(
        label='Test proxies after import',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Test each proxy (slower but ensures quality)'
    )


# ============================================================================
# МАССОВАЯ ЗАГРУЗКА
# ============================================================================

class BulkUploadTaskForm(forms.ModelForm):
    """
    Форма создания задачи массовой загрузки.
    """
    
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=TikTokAccount.objects.filter(status='ACTIVE').order_by('-created_at'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label='Select Accounts'
    )
    
    class Meta:
        model = BulkUploadTask
        fields = [
            'name', 'delay_min_sec', 'delay_max_sec', 'concurrency',
            'default_caption', 'default_hashtags', 'default_privacy',
            'allow_comments', 'allow_duet', 'allow_stitch'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bulk Upload Task Name'}),
            'delay_min_sec': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'value': 30}),
            'delay_max_sec': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'value': 60}),
            'concurrency': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 4, 'value': 1}),
            'default_caption': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Default caption for all videos...'}),
            'default_hashtags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '#tag1, #tag2, #tag3'}),
            'default_privacy': forms.Select(attrs={'class': 'form-select'}),
            'allow_comments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_duet': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_stitch': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        """Валидация диапазонов задержек."""
        cleaned_data = super().clean()
        delay_min = cleaned_data.get('delay_min_sec')
        delay_max = cleaned_data.get('delay_max_sec')
        
        if delay_min and delay_max and delay_min > delay_max:
            raise ValidationError('Minimum delay cannot be greater than maximum delay.')
        
        return cleaned_data


class BulkVideoUploadForm(forms.Form):
    """
    Форма загрузки видео для bulk upload.
    
    Note: Для множественной загрузки файлов используйте request.FILES.getlist('video_files') в view.
    """
    
    video_files = forms.FileField(
        label='Video Files',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/mp4,video/quicktime,video/x-msvideo',
        }),
        required=False,  # Required=False, так как валидация будет в view
        help_text='Select one or more video files (MP4, MOV, AVI). Max 2GB each.'
    )


class BulkCaptionsUploadForm(forms.Form):
    """
    Форма загрузки описаний для видео.
    """
    
    captions_file = forms.FileField(
        label='Captions File',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.txt,.json'}),
        help_text='Text file with captions (one per line or JSON array)'
    )
    
    format = forms.ChoiceField(
        label='Caption Format',
        choices=[
            ('line', 'One caption per line'),
            ('double_newline', 'Captions separated by double newline'),
            ('json', 'JSON array'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='line'
    )
    
    assignment_mode = forms.ChoiceField(
        label='Assignment Mode',
        choices=[
            ('sequential', 'Sequential (1st caption → 1st video)'),
            ('random', 'Random distribution'),
            ('round_robin', 'Round-robin by accounts'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='sequential'
    )


# ============================================================================
# ПРОГРЕВ
# ============================================================================

class WarmupTaskForm(forms.ModelForm):
    """
    Форма создания задачи прогрева.
    """
    
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=TikTokAccount.objects.filter(status='ACTIVE').order_by('-created_at'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label='Select Accounts to Warm Up'
    )
    
    class Meta:
        model = WarmupTask
        fields = [
            'name', 'delay_min_sec', 'delay_max_sec', 'concurrency',
            'feed_scroll_min_count', 'feed_scroll_max_count',
            'like_min_count', 'like_max_count',
            'watch_video_min_count', 'watch_video_max_count',
            'follow_min_count', 'follow_max_count',
            'comment_min_count', 'comment_max_count',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'delay_min_sec': forms.NumberInput(attrs={'class': 'form-control', 'value': 15}),
            'delay_max_sec': forms.NumberInput(attrs={'class': 'form-control', 'value': 45}),
            'concurrency': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 4, 'value': 1}),
            'feed_scroll_min_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 5}),
            'feed_scroll_max_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 15}),
            'like_min_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 3}),
            'like_max_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 10}),
            'watch_video_min_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 5}),
            'watch_video_max_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 20}),
            'follow_min_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 0}),
            'follow_max_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 5}),
            'comment_min_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 0}),
            'comment_max_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 3}),
        }
    
    def clean(self):
        """Валидация всех min/max диапазонов."""
        cleaned_data = super().clean()
        
        ranges = [
            ('delay_min_sec', 'delay_max_sec', 'delay'),
            ('feed_scroll_min_count', 'feed_scroll_max_count', 'feed scroll'),
            ('like_min_count', 'like_max_count', 'like'),
            ('watch_video_min_count', 'watch_video_max_count', 'watch video'),
            ('follow_min_count', 'follow_max_count', 'follow'),
            ('comment_min_count', 'comment_max_count', 'comment'),
        ]
        
        for min_field, max_field, name in ranges:
            min_val = cleaned_data.get(min_field)
            max_val = cleaned_data.get(max_field)
            if min_val is not None and max_val is not None and min_val > max_val:
                raise ValidationError(f'{name.title()} min cannot be greater than max.')
        
        return cleaned_data


# ============================================================================
# ПОДПИСКИ
# ============================================================================

class FollowCategoryForm(forms.ModelForm):
    """
    Форма создания категории целевых аккаунтов.
    """
    
    class Meta:
        model = FollowCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FollowTargetForm(forms.ModelForm):
    """
    Форма добавления целевого аккаунта.
    """
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'username (without @)'}),
        help_text='TikTok username without @'
    )
    
    class Meta:
        model = FollowTarget
        fields = ['username']
    
    def clean_username(self):
        """Валидация TikTok username."""
        username = self.cleaned_data.get('username')
        # Remove @ if user included it
        username = username.lstrip('@')
        
        if not re.match(r'^[\w.]+$', username):
            raise ValidationError('Invalid TikTok username format.')
        
        return username


class BulkFollowTargetForm(forms.Form):
    """
    Форма массового добавления целевых аккаунтов.
    """
    
    usernames = forms.CharField(
        label='Target Usernames',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Enter usernames, one per line or comma-separated'
        }),
        help_text='One username per line, or comma-separated'
    )


class FollowTaskForm(forms.ModelForm):
    """
    Форма создания задачи подписок/отписок.
    """
    
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=TikTokAccount.objects.filter(status='ACTIVE').order_by('-created_at'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label='Select Accounts'
    )
    
    class Meta:
        model = FollowTask
        fields = [
            'name', 'action', 'category',
            'delay_min_sec', 'delay_max_sec', 'concurrency',
            'follow_min_count', 'follow_max_count'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'action': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'delay_min_sec': forms.NumberInput(attrs={'class': 'form-control', 'value': 30}),
            'delay_max_sec': forms.NumberInput(attrs={'class': 'form-control', 'value': 60}),
            'concurrency': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 4, 'value': 1}),
            'follow_min_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 10}),
            'follow_max_count': forms.NumberInput(attrs={'class': 'form-control', 'value': 50}),
        }
    
    def clean(self):
        """Валидация."""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        category = cleaned_data.get('category')
        
        # Для FOLLOW обязательно нужна категория
        if action == 'FOLLOW' and not category:
            raise ValidationError('Category is required for FOLLOW action.')
        
        # Проверка диапазона
        follow_min = cleaned_data.get('follow_min_count')
        follow_max = cleaned_data.get('follow_max_count')
        if follow_min and follow_max and follow_min > follow_max:
            raise ValidationError('Follow min cannot be greater than follow max.')
        
        return cleaned_data


# ============================================================================
# COOKIES
# ============================================================================

class CookieRobotTaskForm(forms.ModelForm):
    """
    Форма создания задачи обновления cookies.
    """
    
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=TikTokAccount.objects.filter(status='ACTIVE').order_by('-created_at'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label='Select Accounts'
    )
    
    class Meta:
        model = CookieRobotTask
        fields = ['name', 'delay_min_sec', 'delay_max_sec', 'concurrency']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'delay_min_sec': forms.NumberInput(attrs={'class': 'form-control', 'value': 10}),
            'delay_max_sec': forms.NumberInput(attrs={'class': 'form-control', 'value': 30}),
            'concurrency': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 4, 'value': 2}),
        }


