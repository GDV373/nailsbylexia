import phonenumbers

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "name@example.com",
            "autocomplete": "email",
        })
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Create password",
            "autocomplete": "new-password",
            "id": "password1",
        })
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Confirm password",
            "autocomplete": "new-password",
            "id": "password2",
        })
    )

    class Meta:
        model = User
        fields = ["username", "email", "phone", "password1", "password2"]

        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Your name",
                "autocomplete": "name",
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        try:
            parsed = phonenumbers.parse(phone, None)
        except phonenumbers.NumberParseException:
            raise forms.ValidationError("Enter a valid phone number.")

        if not phonenumbers.is_valid_number(parsed):
            raise forms.ValidationError("Enter a valid phone number.")

        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    def clean_email(self):
        email = self.cleaned_data.get("email").lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")

        return email


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "name@example.com",
            "autocomplete": "email",
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "Password",
            "autocomplete": "current-password",
        })
    )


class CompleteProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["phone"]

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        try:
            parsed = phonenumbers.parse(phone, None)
        except phonenumbers.NumberParseException:
            raise forms.ValidationError("Enter a valid phone number.")

        if not phonenumbers.is_valid_number(parsed):
            raise forms.ValidationError("Enter a valid phone number.")

        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "phone"]

        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control form-control-lg",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control form-control-lg",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control form-control-lg",
                "id": "phone",
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        try:
            parsed = phonenumbers.parse(phone, None)
        except phonenumbers.NumberParseException:
            raise forms.ValidationError("Enter a valid phone number.")

        if not phonenumbers.is_valid_number(parsed):
            raise forms.ValidationError("Enter a valid phone number.")

        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)