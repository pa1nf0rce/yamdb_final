from django.shortcuts import get_object_or_404
from django.db import IntegrityError

from rest_framework import filters, permissions, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from reviews.models import Category, Comment, Genre, Review, Title, User
from api.permission import (
    AdminOrReadOnly,
    AdminOrStaffPermission,
    AuthorOrModerPermission,
)
from api.serializers import (
    AuthSignUpSerializer,
    AuthTokenSerializer,
    CategorySerializer,
    CommentSerializer,
    GenreSerializer,
    ReadTitleSerializer,
    ReviewSerializer,
    TitleSerializer,
    UserSerializer
)
from api.utils import send_confirmation_code_to_email


@api_view(['POST'])
def signup_new_user(request):
    """Регистрируем нового пользователя."""
    username = request.data.get('username')
    email = request.data.get('email')
    serializer = AuthSignUpSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        User.objects.get_or_create(
            username=username,
            email=email
        )
        send_confirmation_code_to_email(username)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except IntegrityError:
        return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def get_token(request):
    """Получаем JWT токен."""
    serializer = AuthTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = serializer.validated_data['username']
    confirmation_code = serializer.validated_data['confirmation_code']
    user = get_object_or_404(User, username=username)
    if user.confirmation_code == confirmation_code:
        refresh = RefreshToken.for_user(user)
        token_data = {'token': str(refresh.access_token)}
        return Response(token_data, status=status.HTTP_200_OK)
    return Response(
        'Неверный код подтверждения', status=status.HTTP_400_BAD_REQUEST
    )


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.all()
    serializer_class = TitleSerializer
    permission_classes = (AdminOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'POST',):
            return TitleSerializer
        return ReadTitleSerializer

    def get_queryset(self):
        queryset = Title.objects.all()
        genre = self.request.query_params.get('genre')
        year = self.request.query_params.get('year')
        name = self.request.query_params.get('name')
        category = self.request.query_params.get('category')
        if genre is not None:
            related = Genre.objects.get(slug=genre)
            queryset = Title.objects.filter(genre=related.id)
        if year is not None:
            queryset = Title.objects.filter(year=year)
        if name is not None:
            queryset = Title.objects.filter(name__icontains=name)
        if category is not None:
            queryset = Title.objects.filter(category__slug=category)
        return queryset


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    permission_classes = (AdminOrReadOnly,)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def slug_gen_destroy(request, slug):
    """Удаление жанров."""
    if request.user.role == 'admin':
        cat = get_object_or_404(Genre, slug=slug)
        cat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(status=status.HTTP_403_FORBIDDEN)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    permission_classes = (AdminOrReadOnly,)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def slug_cat_destroy(request, slug):
    """Удаление категорий."""
    if request.user.role == 'admin':
        cat = get_object_or_404(Category, slug=slug)
        cat.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(status=status.HTTP_403_FORBIDDEN)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        AuthorOrModerPermission]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        title_id = self.kwargs['title_id']
        title = Title.objects.get(id=title_id)
        return title.score.all()

    def create(self, request, title_id):
        queryset = Review.objects.filter(
            author=self.request.user,
            title=title_id
        )
        if queryset.exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            author=self.request.user,
            title=get_object_or_404(Title, id=self.kwargs['title_id'])
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [
        AuthorOrModerPermission, permissions.IsAuthenticatedOrReadOnly]
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        review_id = self.kwargs['review_id']
        review = get_object_or_404(Review, id=review_id)
        return review.comments.all()

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
            review_id=get_object_or_404(Review, id=self.kwargs['review_id'])
        )


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_me(request):
    """Редактирование личного профиля."""
    user = request.user
    if request.method == 'PATCH':
        serializer = UserSerializer(user, data=request.data, partial=True)
        if not user.is_admin:
            role = user.role
            serializer.is_valid(raise_exception=True)
            serializer.validated_data['role'] = role
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post']
    permission_classes = (AdminOrStaffPermission,)


@api_view(['GET', 'PATCH', 'DELETE', 'PUT'])
@permission_classes([IsAuthenticated])
def username_update(request, slug):
    """Редактирование и создание пользователя администратором."""
    req_user = request.user
    if req_user.is_admin or req_user.is_superuser:
        user = get_object_or_404(User, username=slug)
        if request.method == 'DELETE':
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        if request.method == 'PATCH':
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'GET':
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(status=status.HTTP_403_FORBIDDEN)
