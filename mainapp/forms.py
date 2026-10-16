from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, strip=True)
    email = forms.EmailField(max_length=254)
    subject = forms.CharField(max_length=200, strip=True)
    message = forms.CharField(max_length=10000, strip=True, widget=forms.Textarea)
