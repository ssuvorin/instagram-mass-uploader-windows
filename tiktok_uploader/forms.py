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
    WarmupTask, WarmupTaskAccount, FollowTask, FollowCategory, FollowTarget,
    CookieRobotTask, BulkVideo, VideoCaption, AccountTag
)


# ============================================================================
# АККАУНТЫ
# ============================================================================

class TikTokAccountForm(forms.ModelForm):
    """
    Форма создания/редактирования TikTok аккаунта.
    """
    
    # Дополнительные поля для cookies
    cookies_json = forms.CharField(
        label='Cookies (JSON format)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '[{"name": "sessionid", "value": "...", "domain": ".tiktok.com"}, ...]'
        }),
        help_text='Paste cookies in JSON format (array of cookie objects)'
    )
    
    cookies_file = forms.FileField(
        label='Or upload cookies file',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.json,.txt'
        }),
        help_text='Upload cookies as JSON file'
    )
    
    # Дополнительное поле для тега (выбор из dropdown)
    tag = forms.ChoiceField(
        label='Tag / Category',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Select an account tag or leave empty'
    )
    
    class Meta:
        model = TikTokAccount
        fields = [
            'username', 'password', 'email', 'email_password',
            'proxy', 'locale', 'client', 'tag', 'notes'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}, render_value=True),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'email_password': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем queryset для прокси (все прокси, сортировка по ID)
        self.fields['proxy'].queryset = TikTokProxy.objects.all().order_by('-id')
        self.fields['proxy'].required = False
        self.fields['proxy'].empty_label = "-- No Proxy --"
        
        # Устанавливаем queryset для клиента, если cabinet доступен
        try:
            from cabinet.models import Client
            self.fields['client'].queryset = Client.objects.all().order_by('name')
            self.fields['client'].required = False
            self.fields['client'].empty_label = "-- No Client --"
        except ImportError:
            # Если cabinet не доступен, оставляем пустой queryset
            pass
        
        # Заполняем choices для тегов
        tag_choices = [('', '-- No Tag --')]
        tags = AccountTag.objects.all().order_by('name')
        for tag in tags:
            tag_choices.append((tag.name, tag.name))
        self.fields['tag'].choices = tag_choices
        
        # Устанавливаем начальное значение тега, если редактируем существующий аккаунт
        if self.instance and self.instance.pk and self.instance.tag:
            self.fields['tag'].initial = self.instance.tag
    
    def clean_username(self):
        """Валидация username: только буквы, цифры, точки, подчеркивания."""
        username = self.cleaned_data.get('username')
        if not re.match(r'^[\w.]+$', username):
            raise ValidationError('Username can only contain letters, numbers, dots, and underscores.')
        return username
    
    def clean(self):
        """Валидация и обработка cookies."""
        cleaned_data = super().clean()
        cookies_json = cleaned_data.get('cookies_json')
        cookies_file = cleaned_data.get('cookies_file')
        
        # Обработка cookies из текстового поля или файла
        cookies_data = None
        
        if cookies_file:
            # Читаем cookies из файла
            try:
                import json
                file_content = cookies_file.read().decode('utf-8')
                cookies_data = json.loads(file_content)
                cleaned_data['_cookies_data'] = cookies_data
            except json.JSONDecodeError:
                raise ValidationError({'cookies_file': 'Invalid JSON format in cookies file.'})
            except Exception as e:
                raise ValidationError({'cookies_file': f'Error reading cookies file: {str(e)}'})
        elif cookies_json:
            # Парсим cookies из текстового поля
            try:
                import json
                cookies_data = json.loads(cookies_json)
                cleaned_data['_cookies_data'] = cookies_data
            except json.JSONDecodeError:
                raise ValidationError({'cookies_json': 'Invalid JSON format. Please provide valid JSON array.'})
        
        return cleaned_data


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


# ============================================================================
# WARMUP TASKS (ПРОГРЕВ АККАУНТОВ)
# ============================================================================

class WarmupTaskForm(forms.ModelForm):
    """
    Форма создания задачи прогрева TikTok аккаунтов.
    Позволяет выбрать аккаунты и настроить параметры прогрева.
    """
    
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=TikTokAccount.objects.all().order_by('-created_at'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label="Select Accounts to Warmup",
        help_text="Select one or more accounts for warmup"
    )
    
    class Meta:
        model = WarmupTask
        fields = [
            'name',
            'delay_min_sec', 'delay_max_sec',
            'concurrency',
            'feed_scroll_min_count', 'feed_scroll_max_count',
            'like_min_count', 'like_max_count',
            'watch_video_min_count', 'watch_video_max_count',
            'follow_min_count', 'follow_max_count',
            'comment_min_count', 'comment_max_count',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Daily Warmup Task'
            }),
            'delay_min_sec': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 5,
                'max': 300,
            }),
            'delay_max_sec': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 5,
                'max': 300,
            }),
            'concurrency': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 4,
            }),
            'feed_scroll_min_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'feed_scroll_max_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'like_min_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'like_max_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'watch_video_min_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'watch_video_max_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'follow_min_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'follow_max_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'comment_min_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'comment_max_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
        }
        labels = {
            'name': 'Task Name',
            'delay_min_sec': 'Min Delay (seconds)',
            'delay_max_sec': 'Max Delay (seconds)',
            'concurrency': 'Parallel Accounts (1-4)',
            'feed_scroll_min_count': 'Min Feed Scrolls',
            'feed_scroll_max_count': 'Max Feed Scrolls',
            'like_min_count': 'Min Likes',
            'like_max_count': 'Max Likes',
            'watch_video_min_count': 'Min Video Watches',
            'watch_video_max_count': 'Max Video Watches',
            'follow_min_count': 'Min Follows',
            'follow_max_count': 'Max Follows',
            'comment_min_count': 'Min Comments',
            'comment_max_count': 'Max Comments',
        }
    
    def clean(self):
        """
        Валидация диапазонов: min <= max для всех параметров.
        """
        cleaned_data = super().clean()
        
        # Проверка задержек
        delay_min = cleaned_data.get('delay_min_sec')
        delay_max = cleaned_data.get('delay_max_sec')
        if delay_min and delay_max and delay_min > delay_max:
            raise ValidationError({
                'delay_max_sec': 'Max delay must be >= Min delay'
            })
        
        # Проверка прокруток ленты
        feed_min = cleaned_data.get('feed_scroll_min_count')
        feed_max = cleaned_data.get('feed_scroll_max_count')
        if feed_min and feed_max and feed_min > feed_max:
            raise ValidationError({
                'feed_scroll_max_count': 'Max scrolls must be >= Min scrolls'
            })
        
        # Проверка лайков
        like_min = cleaned_data.get('like_min_count')
        like_max = cleaned_data.get('like_max_count')
        if like_min and like_max and like_min > like_max:
            raise ValidationError({
                'like_max_count': 'Max likes must be >= Min likes'
            })
        
        # Проверка просмотров
        watch_min = cleaned_data.get('watch_video_min_count')
        watch_max = cleaned_data.get('watch_video_max_count')
        if watch_min and watch_max and watch_min > watch_max:
            raise ValidationError({
                'watch_video_max_count': 'Max watches must be >= Min watches'
            })
        
        # Проверка подписок
        follow_min = cleaned_data.get('follow_min_count')
        follow_max = cleaned_data.get('follow_max_count')
        if follow_min and follow_max and follow_min > follow_max:
            raise ValidationError({
                'follow_max_count': 'Max follows must be >= Min follows'
            })
        
        # Проверка комментариев
        comment_min = cleaned_data.get('comment_min_count')
        comment_max = cleaned_data.get('comment_max_count')
        if comment_min and comment_max and comment_min > comment_max:
            raise ValidationError({
                'comment_max_count': 'Max comments must be >= Min comments'
            })
        
        # Проверка параллельности
        concurrency = cleaned_data.get('concurrency')
        if concurrency and (concurrency < 1 or concurrency > 4):
            raise ValidationError({
                'concurrency': 'Concurrency must be between 1 and 4'
            })
        
        # Проверка что хотя бы одно действие включено
        has_actions = any([
            feed_max and feed_max > 0,
            like_max and like_max > 0,
            watch_max and watch_max > 0,
            follow_max and follow_max > 0,
            comment_max and comment_max > 0,
        ])
        
        if not has_actions:
            raise ValidationError(
                'At least one action type must be enabled (set max count > 0)'
            )
        
        return cleaned_data


