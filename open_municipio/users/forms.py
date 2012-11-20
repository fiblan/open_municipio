from django import forms
from django.forms.models import ModelForm
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from model_utils import Choices
from registration.forms import RegistrationForm, RegistrationFormUniqueEmail
from sorl.thumbnail.admin.current import AdminImageWidget
from open_municipio.locations.models import Location

from open_municipio.users.models import UserProfile


"""
``User`` and ``UserProfile`` model forms. A few of them are used in
the ``django-social-auth`` registration process, whenever some extra
data are needed.
"""

# This is just a shortcut
attrs_dict = {'class': 'required'}


class UserRegistrationForm(RegistrationFormUniqueEmail):
    """
    ``User`` and ``UserProfile`` model form for standard (non-social)
    registration.
    """
    first_name = forms.CharField(max_length=30, label=_('First Name'))
    last_name = forms.CharField(max_length=30, label=_('Last Name'))
    uses_nickname = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                                       label=_(u'I want only my nickname to be publicly shown'),
                                       required=False)
    says_is_politician = forms.BooleanField(required=False, label=_('I am a politician'))
    wants_newsletter = forms.BooleanField(required=False, label=_('Wants newsletter'))
    location = forms.ModelChoiceField(required=False, queryset=Location.objects.all(), label=_('Location, if applicable'))
    description = forms.CharField(required=False, label=_('Description'), widget=forms.Textarea())
    image = forms.ImageField(required=False, label=_('Your image'))
    tos = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Terms of Service'),
                             error_messages={'required': _("You must agree to the terms to register")})
    pri = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Privacy conditions'),
                             error_messages={'required': _("You must agree to the conditions to register")})



class SocialIntegrationForm(forms.Form):
    """
    ``User`` model form for social registration: collecting
    some extra data not provided by social networks.
    """
    username = forms.RegexField(regex=r'^[\w.@+-]+$',
                                max_length=30,
                                widget=forms.TextInput(attrs=attrs_dict),
                                label=_("Username"),
                                error_messages={'invalid': _("This value must contain only letters, numbers and underscores.")})
    uses_nickname = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                                       label=_(u'I want only my nickname to be publicly shown'),
                                       required=False)
    says_is_politician = forms.BooleanField(required=False, label=_('I am a politician'))
    wants_newsletter = forms.BooleanField(required=False, label=_('Wants newsletter'))
    location = forms.ModelChoiceField(required=False, queryset=Location.objects.all(), label=_('Location, if applicable'))
    tos = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Terms of Service'),
                             error_messages={'required': _("You must agree to the terms to register")})
    pri = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Privacy conditions'),
                             error_messages={'required': _("You must agree to the conditions to register")})

    def clean_username(self):
        """
        Validate that the username is alphanumeric and is not already
        in use.
        """
        try:
            user = User.objects.get(username__iexact=self.cleaned_data['username'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_("A user with that username already exists."))



class SocialTwitterIntegrationForm(SocialIntegrationForm):
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,maxlength=75)),
                             label=_("E-mail"))


class ProfileSocialRegistrationForm(ModelForm):
    """
    ``UserProfile`` model form for social registration: collecting
    some extra data not provided by social networks.
    """
    class Meta:
        model = UserProfile
        exclude = ('user', 'person', 'privacy_level')


class UserProfileForm(ModelForm):
    """
    ``UserProfile`` model form: used by users to edit their own
    profiles.
    """
    image = forms.ImageField(required=False, label=_('Your image'), widget=AdminImageWidget)

    class Meta:
        model = UserProfile
        exclude = ('user', 'person', 'privacy_level')
