import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_username')
        cls.group = Group.objects.create(
            title=('Заголовок для тестовой группы'),
            slug='test_slug',
            description='Тестовое описание'
        )
        small_jpg_file = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image = SimpleUploadedFile(
            name='picture.jpg',
            content=small_jpg_file,
            content_type='image/jpg',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
            image=cls.image
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': self.image
        }

    def test_authorized_user_create_post(self):
        """Создание поста автор-ным пользователем"""
        count_posts = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=self.form_data, follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        self.assertEqual(
            Post.objects.count(),
            count_posts + 1,
            msg='Поcт не добавлен в БД'
        )
        self.assertTrue(Post.objects.filter(
                        text=self.post.text,
                        group=self.group.id,
                        author=self.author,
                        image=self.post.image
                        ).exists(), msg='Данные поста не совпадают')

    def test_unauthorized_user_create_post(self):
        """Попытка создания поста неавтор-ным пользователем"""
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data={'text': 'Текст, который не должен пройти'},
            follow=True,
        )
        self.assertFalse(Post.objects.filter(
            text='Текст, который не должен пройти').exists()
        )
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse('posts:post_create')
        )

    def test_authorized_user_edit_post(self):
        """Авторизованный пользователь может редактировать пост"""
        count_posts = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data={'text': 'Отредактированный текст'},
            follow=True,
        )
        self.assertEqual(
            Post.objects.get(id=self.post.id).text,
            'Отредактированный текст',
            msg='Редактирование не работает',
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), count_posts)
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk})
        )

    def test_authorized_user_can_comment_post(self):
        """Только авторизованный пользователь может комментировать пост"""
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.author
        )
        form_data = {
            'post': post,
            'author': post.author,
            'text': 'Тестовый комментарий'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data,
            follow=True
        )
        comment = Comment.objects.first()
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(
            response.context['comments'][0].text,
            'Тестовый комментарий'
        )

    def test_unauthorized_user_cannot_comment_post(self):
        form_data = {
            'text': 'Тестовый комментарий'
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        comments_count = Comment.objects.count()
        self.assertEqual(comments_count, 0)
