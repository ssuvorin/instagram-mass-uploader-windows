from django import forms
from django.core.validators import FileExtensionValidator
from .models import UploadTask, InstagramAccount, Proxy, VideoFile, BulkUploadTask, BulkVideo


class ProxyForm(forms.ModelForm):
    class Meta:
        model = Proxy
        fields = ['host', 'port', 'proxy_type', 'username', 'password', 'is_active', 'notes']
        widgets = {
            'password': forms.PasswordInput(render_value=True),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'proxy_type': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'proxy_type': 'Select the type of proxy server',
            'username': 'Leave empty if proxy does not require authentication',
            'password': 'Leave empty if proxy does not require authentication',
        }


class InstagramAccountForm(forms.ModelForm):
    class Meta:
        model = InstagramAccount
        fields = ['username', 'password', 'email_username', 'email_password', 
                  'tfa_secret', 'proxy', 'status', 'notes', 'dolphin_profile_id']
        widgets = {
            'password': forms.PasswordInput(render_value=True),
            'email_password': forms.PasswordInput(render_value=True),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'dolphin_profile_id': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),
        }
        help_texts = {
            'dolphin_profile_id': 'ID профиля Dolphin Anty. Заполняется автоматически при запуске теста аккаунта.',
            'proxy': 'Прокси-сервер для использования с этим аккаунтом. Будет автоматически добавлен в профиль Dolphin.',
        }
        labels = {
            'dolphin_profile_id': 'Dolphin Anty Profile ID',
        }


class UploadTaskForm(forms.ModelForm):
    caption = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    
    start_immediately = forms.BooleanField(
        initial=True,
        required=False,
        label="Start upload immediately"
    )

    class Meta:
        model = UploadTask
        fields = ['account']
        

class VideoUploadForm(forms.Form):
    video_file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mov', 'avi'])]
    )


class BulkUploadTaskForm(forms.ModelForm):
    selected_accounts = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select Instagram accounts to use"
    )
    
    default_location = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'For example: Moscow, Russia'
        }),
        label="Default Location",
        help_text="Location template to copy to videos (not applied automatically)"
    )
    
    default_mentions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '@username1\n@username2\n@username3'
        }),
        label="Default Mentions",
        help_text="Mentions to copy to videos (not applied automatically)"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set queryset dynamically to get fresh data from database
        # Sort by creation date descending (newest first) for better UX
        self.fields['selected_accounts'].queryset = InstagramAccount.objects.all().order_by('-created_at')
    
    class Meta:
        model = BulkUploadTask
        fields = ['default_location', 'default_mentions']
    
    def save(self, commit=True):
        """Создаем задачу с автогенерированным именем"""
        instance = super().save(commit=False)
        if not instance.name:
            # Генерируем название на основе даты и количества аккаунтов
            from django.utils import timezone
            selected_accounts = self.cleaned_data.get('selected_accounts', [])
            account_count = len(selected_accounts)
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            instance.name = f"Bulk Upload - {account_count} accounts - {timestamp}"
        
        if commit:
            instance.save()
        return instance


class BulkVideoUploadForm(forms.Form):
    """
    Form for uploading videos
    Note: To handle multiple files, the template will have multiple attribute on the input
    """
    video_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mov', 'avi'])],
        required=True,
        label="Select videos to upload",
        help_text="You can select multiple video files"
    )


class BulkTitlesUploadForm(forms.Form):
    titles_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control'
        }),
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        required=True,
        help_text="Upload a text file with titles/captions - one per line"
    )


class CookieRobotForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=InstagramAccount.objects.filter(dolphin_profile_id__isnull=False).order_by('-created_at'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Instagram Account',
        required=True
    )
    
    urls = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'Enter one URL per line'}),
        label='URLs to Visit',
        required=True,
        help_text='Enter one URL per line. Example: https://www.instagram.com'
    )
    
    headless = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Run Headless',
        help_text='Run without visible browser window'
    )
    
    imageless = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Disable Images',
        help_text="Don't load images (faster)"
    )
    
    def clean_urls(self):
        urls_text = self.cleaned_data['urls']
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        
        if not urls:
            raise forms.ValidationError("Please enter at least one URL")
        
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                raise forms.ValidationError(f"Invalid URL: {url}. URLs must start with http:// or https://")
        
        return urls


class BulkVideoLocationMentionsForm(forms.ModelForm):
    """Form for editing location and mentions of individual videos"""
    
    location = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'For example: Moscow, Russia'
        }),
        label="Location",
        help_text="Leave empty to use default location"
    )
    
    mentions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '@username1\n@username2\n@username3'
        }),
        label="Mentions",
        help_text="Mentions for this video, one per line (overrides defaults)"
    )
    
    class Meta:
        model = BulkVideo
        fields = ['location', 'mentions']