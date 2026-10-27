"""Auth, profile and address API views (docs/api.md §2)."""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.models import Address
from apps.accounts.serializers import (
    AddressSerializer,
    LoginSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    ProfileSerializer,
    RegisterSerializer,
)
from apps.core.audit import log_audit


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Initial CSRF token (double-submit cookie). Public."""

    permission_classes = [AllowAny]
    throttle_classes: list = []

    def get(self, request):
        token = get_token(request)
        return Response({"detail": "CSRF cookie set.", "csrfToken": token})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = services.register_user(
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=data.get("phone"),
            request=request,
        )
        login(request, user)
        return Response(MeSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {
                    "error": {
                        "code": "invalid_credentials",
                        "message": "Email ou mot de passe incorrect.",
                        "details": {},
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request, user)
        log_audit("user.login", actor=user, object_type="user", object_id=user.pk, request=request)
        return Response(MeSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        log_audit(
            "user.logout", actor=request.user, object_type="user", object_id=request.user.pk, request=request
        )
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-login"

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(request=request)
        return Response({"detail": "Si un compte existe, un email a été envoyé."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes: list = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_audit(
            "user.password_reset_completed",
            actor=user,
            object_type="user",
            object_id=user.pk,
            request=request,
        )
        return Response({"detail": "Mot de passe mis à jour."})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_audit(
            "user.password_changed", actor=user, object_type="user", object_id=user.pk, request=request
        )
        return Response({"detail": "Mot de passe mis à jour."})


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        old_phone = serializer.instance.phone
        serializer.save()
        if serializer.instance.phone != old_phone:
            log_audit(
                "user.phone_updated",
                actor=self.request.user,
                object_type="user",
                object_id=self.request.user.pk,
                request=self.request,
            )


class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        address = serializer.save(user=self.request.user)
        log_audit(
            "address.created",
            actor=self.request.user,
            object_type="address",
            object_id=address.pk,
            request=self.request,
        )


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        log_audit(
            "address.updated",
            actor=self.request.user,
            object_type="address",
            object_id=serializer.instance.pk,
            request=self.request,
        )

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.delete()
        log_audit(
            "address.deleted",
            actor=self.request.user,
            object_type="address",
            object_id=pk,
            request=self.request,
        )
