from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile


class CustomUserCreationForm(UserCreationForm):
    """
    Extended user registration form with additional fields
    """
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes for styling
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'username'})
        self.fields['first_name'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'given-name'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'family-name'})
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'email'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'new-password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'new-password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            # The UserProfile will be automatically created by the signal
        return user

class UserProfileForm(forms.ModelForm):
    """
    Form for editing user profile information
    """
    class Meta:
        model = UserProfile
        fields = ('phone_number', 'address', 'date_of_birth', 'profile_picture', 'role')
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'autocomplete': 'bday'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only allow role editing for superusers or owners
        if user and not (user.is_superuser or (hasattr(user, 'profile') and getattr(user.profile, 'role', None) == 'owner')):
            self.fields['role'].widget = forms.HiddenInput()
            # Don't disable the field; just hide it so value submits as-is

class UserUpdateForm(forms.ModelForm):
    """
    Form for updating basic user information
    """
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
        }

class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'username',
            'placeholder': 'Username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'current-password',
            'placeholder': 'Password'
        })