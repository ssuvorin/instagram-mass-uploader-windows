"""
Forms for YouTube Shorts bulk upload functionality
Following SOLID, DRY, CLEAN, KISS principles
"""
from django import forms
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
import logging

logger = logging.getLogger(__name__)
from .models import (
    YouTubeAccount,
    YouTubeShortsBulkUploadTask,
    YouTubeShortsVideo,
    YouTubeShortsVideoTitle,
    DolphinCookieRobotTask
)


class YouTubeShortsBulkUploadTaskForm(forms.ModelForm):
    """Form for creating YouTube Shorts bulk upload task"""
    
    client_filter = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'client-filter'}),
        label="Filter by client"
    )
    
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select YouTube accounts to use"
    )
    
    default_tags = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '#shorts\n#youtube\n#viral'
        }),
        label="Default Tags",
        help_text="Tags template to copy to videos (not applied automatically)"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set client filter choices
        try:
            from cabinet.models import Client
            clients = Client.objects.all().order_by('name')
            choices = [('', 'All clients'), ('no_client', 'Without client')]
            choices.extend([(str(client.id), client.name) for client in clients])
            self.fields['client_filter'].choices = choices
        except ImportError:
            self.fields['client_filter'].choices = [('', 'All clients (cabinet app not available)')]
        
        # Set queryset dynamically for fresh data
        self.fields['selected_accounts'].queryset = (
            YouTubeAccount.objects.all()
            .order_by('-created_at')
            .annotate(
                uploaded_success_total=Coalesce(Sum('bulk_uploads__uploaded_success_count'), Value(0)),
                uploaded_failed_total=Coalesce(Sum('bulk_uploads__uploaded_failed_count'), Value(0)),
            )
        )
    
    class Meta:
        model = YouTubeShortsBulkUploadTask
        fields = ['default_visibility', 'default_category', 'default_tags']
        widgets = {
            'default_visibility': forms.Select(attrs={'class': 'form-select'}),
            'default_category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Entertainment, Gaming, Music'
            }),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-generate name if not set
        if not instance.name:
            from django.utils import timezone
            selected_accounts = self.cleaned_data.get('selected_accounts', [])
            account_count = len(selected_accounts)
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            instance.name = f"YT Shorts Bulk Upload - {account_count} accounts - {timestamp}"
        
        if commit:
            instance.save()
        
        return instance


class YouTubeShortsVideoUploadForm(forms.Form):
    """Form for uploading YouTube Shorts videos"""
    
    # Note: Multiple file handling is done in the view by using request.FILES.getlist()
    videos = forms.FileField(
        required=True,
        label="Upload Videos",
        help_text="Select multiple video files (MP4, MOV, AVI)",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'video/mp4,video/quicktime,video/x-msvideo'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add multiple attribute via widget attrs
        self.fields['videos'].widget.attrs['multiple'] = 'multiple'


class YouTubeShortsVideoTitleForm(forms.Form):
    """Form for uploading titles/descriptions for YouTube Shorts"""
    
    titles_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.txt'}),
        required=True,
        label="Titles File",
        help_text="Text file with titles and descriptions. Format: Title on first line, description on following lines, separated by blank line"
    )


class YouTubeShortsVideoEditForm(forms.ModelForm):
    """Form for editing individual video settings"""
    
    class Meta:
        model = YouTubeShortsVideo
        fields = ['visibility', 'category', 'tags']
        widgets = {
            'visibility': forms.Select(
                choices=[
                    ('', 'Use default'),
                    ('PUBLIC', 'Public'),
                    ('UNLISTED', 'Unlisted'),
                    ('PRIVATE', 'Private'),
                ],
                attrs={'class': 'form-select'}
            ),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank to use default'
            }),
            'tags': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'One tag per line. Leave blank to use default.'
            }),
        }


class YouTubeShortsVideoBulkEditForm(forms.Form):
    """Form for bulk editing video settings"""
    
    visibility = forms.ChoiceField(
        choices=[
            ('', 'Keep existing'),
            ('PUBLIC', 'Public'),
            ('UNLISTED', 'Unlisted'),
            ('PRIVATE', 'Private'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Visibility"
    )
    
    category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep existing'
        }),
        label="Category"
    )
    
    tags = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'One tag per line. Leave blank to keep existing.'
        }),
        label="Tags"
    )
    
    apply_to_all = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Apply to all videos in this task"
    )


# ===== YouTube Account Management Forms =====

class YouTubeAccountImportForm(forms.Form):
    """Form for importing YouTube accounts from text file"""
    
    accounts_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.txt'}),
        required=True,
        label="Accounts File",
        help_text="Text file with YouTube accounts. Each account on a new line."
    )
    
    client = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="— Without client —",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assign to Client (optional)",
        help_text="Выберите клиента, к которому будут привязаны импортируемые аккаунты."
    )
    
    tags = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label="— Without tag —",
        label="Assign Tag (optional)",
        help_text="Выберите тег, который будет присвоен всем импортируемым аккаунтам."
    )
    
    locale = forms.ChoiceField(
        choices=[
            ('ru_BY', 'ru_BY (Русский интерфейс, регион BY)'),
            ('en_IN', 'en_IN (English interface, India)'),
            ('es_CL', 'es_CL (Español, Chile)'),
            ('es_MX', 'es_MX (Español, México)'),
            ('pt_BR', 'pt_BR (Português, Brasil)'),
            ('el_GR', 'el_GR (Ελληνικά, Ελλάδα)'),
            ('de_DE', 'de_DE (Deutsch, Deutschland)'),
        ],
        initial='ru_BY',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Dolphin Profile Locale",
        help_text="Локаль профиля Dolphin. Используется для Accept-Language/TZ/Гео."
    )
    
    proxy_selection = forms.ChoiceField(
        choices=[
            ('locale_only', 'Only proxies matching selected locale'),
            ('any_available', 'Any available proxies'),
        ],
        initial='locale_only',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Proxy Selection",
        help_text="Choose how to select proxies for accounts."
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set client queryset
        from cabinet.models import Client
        self.fields['client'].queryset = Client.objects.all().order_by('name')
        
        # Set tag queryset
        from uploader.models import Tag
        self.fields['tags'].queryset = Tag.objects.all().order_by('name')
    
    def clean_accounts_file(self):
        """Validate and parse the accounts file"""
        file = self.cleaned_data.get('accounts_file')
        if not file:
            raise forms.ValidationError("Please select a file to upload.")
        
        try:
            content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            raise forms.ValidationError("File must be UTF-8 encoded.")
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if not lines:
            raise forms.ValidationError("File is empty or contains no valid lines.")
        
        parsed_accounts = []
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            # Support both formats:
            # 1. email:password:recovery_email
            # 2. email:password:recovery_email|user_agent|cookies
            parts = line.split('|')
            
            if len(parts) == 1:
                # Simple format: email:password:recovery_email
                cred_parts = parts[0].split(':')
                if len(cred_parts) == 2:
                    # Format: email:password
                    email, password = cred_parts
                    parsed_accounts.append({
                        'email': email.strip(),
                        'password': password.strip(),
                        'recovery_email': '',
                        'user_agent': '',
                        'cookies': [],
                        'line': line_num
                    })
                elif len(cred_parts) == 3:
                    # Format: email:password:recovery_email
                    email, password, recovery_email = cred_parts
                    parsed_accounts.append({
                        'email': email.strip(),
                        'password': password.strip(),
                        'recovery_email': recovery_email.strip(),
                        'user_agent': '',
                        'cookies': [],
                        'line': line_num
                    })
                else:
                    errors.append(f"Line {line_num}: Invalid format. Expected 'email:password' or 'email:password:recovery_email'")
            elif len(parts) == 3:
                # Extended format: email:password:recovery_email|user_agent|cookies
                cred_parts = parts[0].split(':')
                if len(cred_parts) >= 2:
                    email = cred_parts[0].strip()
                    password = cred_parts[1].strip()
                    recovery_email = cred_parts[2].strip() if len(cred_parts) >= 3 else ''
                    user_agent = parts[1].strip()
                    cookies_raw = parts[2].strip()
                    
                    # Parse cookies
                    cookies = []
                    if cookies_raw:
                        try:
                            # Parse cookies in format: name1=value1; name2=value2
                            cookie_pairs = cookies_raw.split(';')
                            for pair in cookie_pairs:
                                if '=' in pair:
                                    name, value = pair.split('=', 1)
                                    cookies.append({
                                        'name': name.strip(),
                                        'value': value.strip(),
                                        'domain': '.youtube.com',
                                        'path': '/',
                                        'httpOnly': False,
                                        'secure': True
                                    })
                        except Exception as e:
                            logger.warning(f"Failed to parse cookies for line {line_num}: {e}")
                    
                    parsed_accounts.append({
                        'email': email,
                        'password': password,
                        'recovery_email': recovery_email,
                        'user_agent': user_agent,
                        'cookies': cookies,
                        'line': line_num
                    })
                else:
                    errors.append(f"Line {line_num}: Invalid credentials format. Expected 'email:password[:recovery_email]'")
            else:
                errors.append(f"Line {line_num}: Invalid format. Expected 'email:password:recovery_email' or 'email:password:recovery_email|user_agent|cookies'")
        
        if errors:
            raise forms.ValidationError(errors)
        
        # Store parsed accounts for later use
        self.parsed_accounts = parsed_accounts
        return file


class YouTubeAccountForm(forms.ModelForm):
    """Form for creating/editing individual YouTube account"""
    
    class Meta:
        model = YouTubeAccount
        fields = [
            'email', 'password', 'channel_name', 'channel_id', 
            'recovery_email', 'phone_number', 'tfa_secret', 
            'proxy', 'dolphin_profile_id', 'status', 'notes', 'locale'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'channel_name': forms.TextInput(attrs={'class': 'form-control'}),
            'channel_id': forms.TextInput(attrs={'class': 'form-control'}),
            'recovery_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tfa_secret': forms.TextInput(attrs={'class': 'form-control'}),
            'proxy': forms.Select(attrs={'class': 'form-select'}),
            'dolphin_profile_id': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'locale': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set locale choices
        self.fields['locale'].choices = [
            ('en_US', 'English (US)'),
            ('en_GB', 'English (UK)'),
            ('ru_RU', 'Русский'),
            ('es_ES', 'Español'),
            ('fr_FR', 'Français'),
            ('de_DE', 'Deutsch'),
            ('pt_BR', 'Português (Brasil)'),
            ('ja_JP', '日本語'),
            ('ko_KR', '한국어'),
            ('zh_CN', '中文 (简体)'),
        ]


class YouTubeAccountBulkActionForm(forms.Form):
    """Form for bulk actions on YouTube accounts"""
    
    ACTION_CHOICES = [
        ('change_status', 'Change Status'),
        ('assign_proxy', 'Assign Proxy'),
        ('change_locale', 'Change Locale'),
        ('delete', 'Delete Accounts'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Action"
    )
    
    new_status = forms.ChoiceField(
        choices=YouTubeAccount.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="New Status"
    )
    
    new_proxy = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="New Proxy"
    )
    
    new_locale = forms.ChoiceField(
        choices=[
            ('en_US', 'English (US)'),
            ('en_GB', 'English (UK)'),
            ('ru_RU', 'Русский'),
            ('es_ES', 'Español'),
            ('fr_FR', 'Français'),
            ('de_DE', 'Deutsch'),
            ('pt_BR', 'Português (Brasil)'),
            ('ja_JP', '日本語'),
            ('ko_KR', '한국어'),
            ('zh_CN', '中文 (简体)'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="New Locale"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set proxy queryset
        from uploader.models import Proxy
        self.fields['new_proxy'].queryset = Proxy.objects.filter(is_active=True).order_by('host')


class YouTubeCookieRobotForm(forms.ModelForm):
    """Form for creating YouTube Cookie Robot tasks"""
    account = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="YouTube Account",
        help_text="Select a YouTube account with Dolphin profile"
    )
    urls = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter URLs separated by new lines\nhttps://youtube.com\nhttps://google.com'
        }),
        label="URLs to Visit",
        help_text="Enter URLs separated by new lines"
    )
    headless = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Headless Mode",
        help_text="Run browser in headless mode (no GUI)"
    )
    imageless = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Disable Images",
        help_text="Disable image loading for faster execution"
    )

    class Meta:
        model = DolphinCookieRobotTask
        fields = ['account', 'urls', 'headless', 'imageless']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset to only YouTube accounts with Dolphin profiles
        from uploader.models import YouTubeAccount
        self.fields['account'].queryset = YouTubeAccount.objects.filter(
            dolphin_profile_id__isnull=False
        ).order_by('email')

    def clean_urls(self):
        urls = self.cleaned_data.get('urls', '')
        if not urls.strip():
            raise forms.ValidationError("Please enter at least one URL")
        
        # Split by newlines and clean up
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        if not url_list:
            raise forms.ValidationError("Please enter at least one valid URL")
        
        # Basic URL validation
        for url in url_list:
            if not (url.startswith('http://') or url.startswith('https://')):
                raise forms.ValidationError(f"Invalid URL format: {url}")
        
        return url_list

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Set YouTube account
        instance.youtube_account = instance.account
        instance.instagram_account = None
        
        if commit:
            instance.save()
        return instance

