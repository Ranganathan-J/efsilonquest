from rest_framework import viewsets, permissions, generics
from .models import User
from .serializers import UserSerializer, SignupUserSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
# Create your views here.



# signup endpoint
class SignupUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = SignupUserSerializer


# login endpoint
class loginUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    # permission_classes = [permissions.AllowAny]

    def get_object(self):
        return self.request.user