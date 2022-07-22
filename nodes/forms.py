from django import forms

from .models import Nodes, CropImage


class RegisterForm(forms.ModelForm):
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={'placeholder': 'Name', 'class': 'form-control'}
        )
    )
    description = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.Textarea(
            attrs={'placeholder': 'add description', 'class': 'form-control', 'rows': 5}
        )
    )
    status = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.RadioSelect(
            choices=((True, 'Active'), (False, 'Inactive')),
            attrs={'class': 'form-check-input'}
        )
    )
    latitude = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={'placeholder': 'latitude', 'class': 'form-control'}
        )
    )
    longitude = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={'placeholder': 'longitude', 'class': 'form-control'}
        )
    )

    class Meta:
        model = Nodes
        fields = ['name', 'status', 'description', 'latitude', 'longitude']


class ImageUploadForm(forms.ModelForm):
    node_id = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    image = forms.ImageField(
        required=True,
        widget=forms.FileInput(
            attrs={'placeholder': 'image', 'class': 'form-control-file'}
        )
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'add description'}),
        required=False,
    )

    class Meta:
        model = CropImage
        fields = ['node_id', 'image', 'description']
