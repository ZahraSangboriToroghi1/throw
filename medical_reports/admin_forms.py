from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User
import logging

# تنظیم لاگر
logger = logging.getLogger('medical_reports')

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'role', 'hospital')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            logger.info(f"User {user.username} created successfully")
            # پیامک غیرفعال شده زیرا پنل SMS فعال نیست
            # در آینده می‌توانید کد ارسال پیامک را اینجا اضافه کنید
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'role', 'hospital', 'is_active', 'is_staff')

    def clean_password(self):
        return self.initial.get('password', '')