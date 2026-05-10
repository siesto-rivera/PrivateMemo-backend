from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import SignupSerializer, UserSerializer


class SignupView(generics.CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth_signup"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """로그인. 브루트포스 방지를 위해 IP당 분당 10회 제한."""
    throttle_scope = "auth_login"


class ThrottledTokenRefreshView(TokenRefreshView):
    """토큰 갱신. 인증된 클라이언트만 사용하므로 user 기본 제한 사용."""
    pass


class MeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        password = request.data.get("password")
        user = self.get_object()
        if not password or not user.check_password(password):
            return Response(
                {"password": ["비밀번호가 일치하지 않습니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
