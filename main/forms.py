from django.contrib.auth.forms import UserCreationForm

class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = (
            "Your password can't be too similar to your other personal information.\n"
            "Your password must contain at least 8 characters.\n"
            "Your password can't be a commonly used password.\n"
            "Your password can't be entirely numeric."
        )