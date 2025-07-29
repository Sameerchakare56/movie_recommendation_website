from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile  # <-- This is needed to create a Profile
  # <-- If you have a separate file for states

from django.core.exceptions import ValidationError
import datetime



INDIAN_STATES = [
    ('AN', 'Andaman and Nicobar Islands'),
    ('AP', 'Andhra Pradesh'),
    ('AR', 'Arunachal Pradesh'),
    ('AS', 'Assam'),
    ('BR', 'Bihar'),
    ('CH', 'Chandigarh'),
    ('CT', 'Chhattisgarh'),
    ('DL', 'Delhi'),
    ('DN', 'Dadra and Nagar Haveli'),
    ('GA', 'Goa'),
    ('GJ', 'Gujarat'),
    ('HP', 'Himachal Pradesh'),
    ('HR', 'Haryana'),
    ('JH', 'Jharkhand'),
    ('JK', 'Jammu and Kashmir'),
    ('KA', 'Karnataka'),
    ('KL', 'Kerala'),
    ('LA', 'Ladakh'),
    ('LD', 'Lakshadweep'),
    ('MH', 'Maharashtra'),
    ('ML', 'Meghalaya'),
    ('MN', 'Manipur'),
    ('MP', 'Madhya Pradesh'),
    ('MZ', 'Mizoram'),
    ('NL', 'Nagaland'),
    ('OR', 'Odisha'),
    ('PB', 'Punjab'),
    ('PY', 'Puducherry'),
    ('RJ', 'Rajasthan'),
    ('SK', 'Sikkim'),
    ('TG', 'Telangana'),
    ('TN', 'Tamil Nadu'),
    ('TR', 'Tripura'),
    ('UP', 'Uttar Pradesh'),
    ('UT', 'Uttarakhand'),
    ('WB', 'West Bengal'),
]

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    birthday = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    state = forms.ChoiceField(choices=INDIAN_STATES)
    city = forms.CharField(max_length=100, required=False)  # Add city field here

    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'birthday', 'state', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile = Profile.objects.create(
                user=user,
                birthday=self.cleaned_data['birthday'],
                state=self.cleaned_data['state']
            )
            profile.save()
        return user

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_pic', 'birthday', 'state', 'city', 'mobile_no']
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'}),
        }
    