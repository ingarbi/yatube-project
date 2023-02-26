from django.contrib.auth import views as view
from django.urls import path

from .views import SignUp

app_name = 'users'

urlpatterns = [
    path('signup/', SignUp.as_view(), name='signup'),
    path('login/', view.LoginView.as_view(
        template_name='users/login.html'),
        name='login'),
    path('logout/', view.LogoutView.as_view(
        template_name='users/logged_out.html'),
        name='logout'),
    path('password_change/', view.PasswordChangeView.as_view(
        template_name='users/password_change_form.html'),
        name='password_change'),
    path('password_change/done/', view.PasswordChangeDoneView.as_view(
        template_name='users/password_change_done.html'),
        name='password_change_done'),
    path('password_reset/', view.PasswordResetView.as_view(
        template_name='users/password_reset_form.html'),
        name='password_reset_form'),
    path('password_reset/done/', view.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'),
        name='password_reset_done'),
    path('reset/<uidb64>/<token>/', view.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html'),
        name='password_reset_confirm'),
    path('reset/done/', view.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'),
        name='password_reset_complete'),
]
