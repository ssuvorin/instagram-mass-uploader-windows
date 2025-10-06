from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import HashtagAnalytics
from cabinet.models import Client


class ClientAnalyticsForm(forms.ModelForm):
    """Form for manually adding client analytics data"""
    
    class Meta:
        model = HashtagAnalytics
        fields = [
            'client', 'social_network', 'hashtag',
            'analyzed_medias', 'total_views', 'total_likes', 'total_comments', 
            'total_shares', 'total_followers', 'growth_rate',
            'instagram_stories_views', 'instagram_reels_views',
            'youtube_subscribers', 'youtube_watch_time',
            'tiktok_video_views', 'tiktok_profile_views',
            # Advanced account-level metrics
            'total_accounts', 'avg_videos_per_account', 'max_videos_per_account',
            'avg_views_per_video', 'max_views_per_video',
            'avg_views_per_account', 'max_views_per_account',
            'avg_likes_per_video', 'max_likes_per_video',
            'avg_likes_per_account', 'max_likes_per_account',
            'notes'
        ]
        widgets = {
            'client': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'social_network': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'onchange': 'togglePlatformFields()'
            }),
            'analyzed_medias': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'required': True
            }),
            'total_views': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'required': False
            }),
            'total_likes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'required': False
            }),
            'total_comments': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'required': False
            }),
            'total_shares': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'required': False
            }),
            'total_followers': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'required': False
            }),
            'growth_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00',
                'required': False
            }),
            'instagram_stories_views': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'instagram_reels_views': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'youtube_subscribers': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'youtube_watch_time': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': 'Minutes'
            }),
            'tiktok_video_views': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'tiktok_profile_views': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'hashtag': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Enter hashtag without #'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': 'Additional notes about this analytics data...'
            }),
            # Advanced metrics widgets
            'total_accounts': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '0'
            }),
            'avg_videos_per_account': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.1',
                'placeholder': '0.0'
            }),
            'max_videos_per_account': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '0'
            }),
            'avg_views_per_video': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.1',
                'placeholder': '0.0'
            }),
            'max_views_per_video': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '0'
            }),
            'avg_views_per_account': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.1',
                'placeholder': '0.0'
            }),
            'max_views_per_account': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '0'
            }),
            'avg_likes_per_video': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.1',
                'placeholder': '0.0'
            }),
            'max_likes_per_video': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '0'
            }),
            'avg_likes_per_account': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.1',
                'placeholder': '0.0'
            }),
            'max_likes_per_account': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '0'
            }),
        }
        labels = {
            'client': 'Client',
            'social_network': 'Social Network',
            'analyzed_medias': 'Total Posts/Videos',
            'total_views': 'Total Views',
            'total_likes': 'Total Likes',
            'total_comments': 'Total Comments',
            'total_shares': 'Total Shares/Reposts',
            'total_followers': 'Total Followers',
            'growth_rate': 'Growth Rate (%)',
            'instagram_stories_views': 'Instagram Stories Views',
            'instagram_reels_views': 'Instagram Reels Views',
            'youtube_subscribers': 'YouTube Subscribers',
            'youtube_watch_time': 'YouTube Watch Time (minutes)',
            'tiktok_video_views': 'TikTok Video Views',
            'tiktok_profile_views': 'TikTok Profile Views',
            'hashtag': 'Hashtag',
            'notes': 'Notes',
            # Advanced metrics labels
            'total_accounts': 'Total Accounts',
            'avg_videos_per_account': 'Avg Videos per Account',
            'max_videos_per_account': 'Max Videos per Account',
            'avg_views_per_video': 'Avg Views per Video',
            'max_views_per_video': 'Max Views per Video',
            'avg_views_per_account': 'Avg Views per Account',
            'max_views_per_account': 'Max Views per Account',
            'avg_likes_per_video': 'Avg Likes per Video',
            'max_likes_per_video': 'Max Likes per Video',
            'avg_likes_per_account': 'Avg Likes per Account',
            'max_likes_per_account': 'Max Likes per Account',
        }
        help_texts = {
            'growth_rate': 'Follower growth rate as percentage (e.g., 5.25 for 5.25%)',
            'youtube_watch_time': 'Total watch time in minutes',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order clients by name
        self.fields['client'].queryset = Client.objects.all().order_by('name')
        
        # Set default values
        if not self.instance.pk:
            self.fields['analyzed_medias'].initial = 0
            self.fields['total_views'].initial = 0
            self.fields['total_likes'].initial = 0
            self.fields['total_comments'].initial = 0
            self.fields['total_shares'].initial = 0
            self.fields['total_followers'].initial = 0
            self.fields['growth_rate'].initial = 0.0

    def clean(self):
        cleaned_data = super().clean()
        social_network = cleaned_data.get('social_network')
        client = cleaned_data.get('client')
        hashtag = cleaned_data.get('hashtag', '')
        
        # Validate required hashtag field
        if not hashtag or hashtag.strip() == '':
            raise ValidationError('Hashtag is required. Please select a hashtag from the dropdown.')
        
        # Set default values for platform-specific fields that are not relevant
        if social_network == 'INSTAGRAM':
            # Clear YouTube and TikTok fields
            cleaned_data['youtube_subscribers'] = 0
            cleaned_data['youtube_watch_time'] = 0
            cleaned_data['tiktok_video_views'] = 0
            cleaned_data['tiktok_profile_views'] = 0
        elif social_network == 'YOUTUBE':
            # Clear Instagram and TikTok fields
            cleaned_data['instagram_stories_views'] = 0
            cleaned_data['instagram_reels_views'] = 0
            cleaned_data['tiktok_video_views'] = 0
            cleaned_data['tiktok_profile_views'] = 0
        elif social_network == 'TIKTOK':
            # Clear Instagram and YouTube fields
            cleaned_data['instagram_stories_views'] = 0
            cleaned_data['instagram_reels_views'] = 0
            cleaned_data['youtube_subscribers'] = 0
            cleaned_data['youtube_watch_time'] = 0
        
        # Check for duplicate analytics entry (same client, network, hashtag on same day)
        if client and social_network:
            today = timezone.now().date()
            existing = HashtagAnalytics.objects.filter(
                client=client,
                social_network=social_network,
                hashtag=hashtag,
                is_manual=True,
                created_at__date=today
            )
            
            # Exclude current instance if editing
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                hashtag_text = f" for hashtag #{hashtag}" if hashtag else ""
                raise ValidationError(
                    f'Analytics for {client.name} - {dict(HashtagAnalytics.SOCIAL_NETWORK_CHOICES).get(social_network, social_network)} '
                    f'{hashtag_text} already exists for today. '
                    f'Please wait until tomorrow or edit the existing entry.'
                )
        
        return cleaned_data


class ClientAnalyticsFilterForm(forms.Form):
    """Form for filtering analytics data"""
    
    client = forms.ModelChoiceField(
        queryset=Client.objects.all().order_by('name'),
        required=False,
        empty_label="All Clients",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    social_network = forms.ChoiceField(
        choices=[('', 'All Networks')] + HashtagAnalytics.SOCIAL_NETWORK_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    period_start = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    period_end = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
