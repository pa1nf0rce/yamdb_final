from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class BaseTypeCategory(models.Model):

    name = models.CharField(max_length=256)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Category(BaseTypeCategory):
    """Модель категорий."""

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Genre(BaseTypeCategory):
    """Модель жанров."""

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'


class Title(models.Model):
    """Модель произведений."""

    name = models.CharField(max_length=256)
    year = models.IntegerField()
    description = models.TextField(null=True)
    genre = models.ManyToManyField(
        Genre,
        through='GenreTitle',
        related_name='genres'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True
    )

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = 'Произведение'
        verbose_name_plural = 'Произвдения'
        ordering = ('name',)


class GenreTitle(models.Model):
    """Модель произведний и жанров."""

    genre = models.ForeignKey(
        Genre,
        on_delete=models.CASCADE,
        related_name='genre'
    )
    title = models.ForeignKey(
        Title,
        on_delete=models.CASCADE,
        related_name='title'
    )

    def __str__(self) -> str:
        return f'Жанр {self.title}: {self.genre}'

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('genre', 'title'),
                name='unique_genr_title'
            ),
        )
        verbose_name = 'Жанр и произведение'
        verbose_name_plural = 'Жанры и произведения'


class CustomUser(AbstractUser):

    ROLE_USER = 'user'
    ROLE_MODERATOR = 'moderator'
    ROLE_ADMIN = 'admin'

    USER_ROLE_CHOICES = (
        (ROLE_USER, 'Пользователь'),
        (ROLE_MODERATOR, 'Модератор'),
        (ROLE_ADMIN, 'Администратор'),
    )

    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='Электронная почта'
    )
    role = models.CharField(
        max_length=16,
        choices=USER_ROLE_CHOICES,
        default=ROLE_USER,
        verbose_name='Роль'
    )
    bio = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Фамилия'
    )
    confirmation_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Код для авторизации'
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('username', 'email'),
                name='unique_username_email'
            ),
        )

    @property
    def is_user(self):
        return self.role == self.ROLE_USER

    @property
    def is_moderator(self):
        return self.role == self.ROLE_MODERATOR

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser


User = get_user_model()


class BaseComment(models.Model):
    text = models.TextField()
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='%(class)s')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        abstract = True


class Review(BaseComment):
    title = models.ForeignKey(
        Title, on_delete=models.CASCADE, related_name='score')
    score = models.IntegerField(
        validators=(
            MaxValueValidator(10),
            MinValueValidator(1)
        )
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('author', 'title'),
                name='unique_author_title'
            ),
        )


class Comment(BaseComment):
    review_id = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name='comments')
