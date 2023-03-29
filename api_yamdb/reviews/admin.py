from reviews.models import Category, Genre, GenreTitle, Title
from django.contrib import admin

admin.site.register(Title)
admin.site.register(Genre)
admin.site.register(Category)
admin.site.register(GenreTitle)
