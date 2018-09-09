from django import http
from django.views import View
from django.urls import reverse, reverse_lazy
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.generic.edit import FormView
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect

import json

from studygroups.models import TeamMembership
from uxhelpers.utils import json_response
from api import schema
from .models import create_user
from .models import check_user_token
from .models import confirm_user_email
from .models import send_email_confirm_email
from .forms import SignupForm
from .decorators import user_is_not_logged_in

# TODO make sure user is not signed in!!
@method_decorator(user_is_not_logged_in, name='dispatch')
class SignupView(FormView):
    form_class = SignupForm
    template_name = 'custom_registration/signup.html'

    def get_success_url(self):
        # if there is a next URL defined, use that
        if 'next' in self.request.GET:
            return self.request.GET['next']
        return reverse('studygroups_facilitator')


    def form_valid(self, form):
        user = form.save(commit=False)
        user = create_user(user.email, user.first_name, user.last_name, form.cleaned_data['password1'], form.cleaned_data['communication_opt_in'], form.cleaned_data['interested_in_learning'], )
        login(self.request, user)
        return http.HttpResponseRedirect(self.get_success_url())


@method_decorator(user_is_not_logged_in, name='dispatch')
class AjaxSignupView(View):
    def post(self, request):
        def _user_check():
            def _validate(value):
                error = _('A user with that email address already exists.')
                if User.objects.filter(username__iexact=value).exists():
                    return None, error
                return value, None
            return _validate
        post_schema = {
            "email": schema.chain([
                schema.email(required=True),
                _user_check(),
            ]),
            "first_name": schema.text(required=True),
            "last_name": schema.text(required=True),
            "password": schema.text(required=True),
            "communication_opt_in": schema.boolean(required=True),
        }
        data = json.loads(request.body)
        data, errors = schema.validate(post_schema, data)
        if errors != {}:
            return json_response(request, {"status": "error", "errors": errors})

        user = create_user(data['email'], data['first_name'], data['last_name'], data['password'], data.get('communication_opt_in', False))
        login(request, user)
        return json_response(request, { "status": "created", "user": user.username });


class AjaxLoginView(View):
    def post(self, request):
        post_schema = {
            "email": schema.email(required=True),
            "password": schema.text(required=True),
        }
        data = json.loads(request.body)
        data, errors = schema.validate(post_schema, data)
        if errors != {}:
            return json_response(request, {"status": "error", "errors": errors})

        username = data.get('email').lower()
        password = data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return json_response(request, {
                "status": "error",
                "errors": AuthenticationForm.error_messages.get('invalid_login') % { "username" : "email" }
            })

        if not user.is_active:
            return json_response(request, {
                "status": "error",
                "errors": AuthenticationForm.error_messages.get('inactive')
            })

        login(request, user)
        return json_response(request, { "status": "success", "user": user.username });


class WhoAmIView(View):
    def get(self, request):
        user_data = {
            "user": "anonymous",
        }
        if request.user.is_authenticated():
            user_data["user"] = request.user.first_name
            user_data["links"] = [
                {"text": "My learning circles", "url": reverse('studygroups_facilitator')},
                {"text": "Log out", "url": reverse('logout')},
            ]
            if request.user.is_staff or TeamMembership.objects.filter(user=request.user, role=TeamMembership.ORGANIZER):
                user_data["links"][:0] = [
                    {"text": "My Team", "url": reverse('studygroups_organize')},
                ]

            if request.user.is_staff:
                user_data["links"][:0] = [
                    {"text": "Staff dash", "url": reverse('studygroups_staff_dash')},
                ]
        return json_response(request, user_data);


@method_decorator(login_required, name='dispatch')
class EmailConfirmRequestView(View):

    def post(self, request, *args, **kwargs):
        send_email_confirm_email(request.user)
        messages.success(self.request, _('Verification email sent. Please check your inbox and follow instructions.'))
        url = reverse('studygroups_facilitator')
        return HttpResponseRedirect(url)


class EmailConfirmView(View):
    """ View mostly copied from Django password reset confirm view """

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def get(self, *args, **kwargs):
        assert 'uidb64' in kwargs and 'token' in kwargs
        user = self.get_user(kwargs['uidb64'])
        if user is not None:
            token = kwargs['token']
            if self.request.user.is_authenticated() and user.pk != self.request.user.pk:
                # make sure logged in user and user confirming emails are the same people
                messages.warning(self.request, _('There is a problem with your password confirmation URL. Please try logging out and then click the link in the email we sent you.'))
                url = reverse('studygroups_login_redirect')
                return HttpResponseRedirect(url)


            if check_user_token(user, token):
                # Set email address to confirmed in profile
                if user.profile.email_confirmed_at != None:
                    # redirect user to login page
                    # NB! Don't log user in, since link could have leaked and hash isn't gauranteed to change after the user confirms their email address
                    messages.success(self.request, _('Your email address has been already been confirmed.'))
                    url = reverse('studygroups_login_redirect')
                    return HttpResponseRedirect(url)
                else:
                    confirm_user_email(user)
                    login(self.request, user)
                    messages.success(self.request, _('Your email address has been confirmed!'))
                    # redirect them to dashboard
                    url = reverse('studygroups_facilitator')
                    return HttpResponseRedirect(url)

        messages.warning(self.request, _('Invalid email confirmation URL.'))
        url = reverse('login')
        return HttpResponseRedirect(url)


    def get_user(self, uidb64):
        try:
            # urlsafe_base64_decode() decodes to bytestring on Python 3
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        return user
