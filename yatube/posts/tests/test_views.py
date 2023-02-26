import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post, Follow

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostPageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='test_username')
        cls.group = Group.objects.create(
            title='Заголовок для тестовой группы',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.group_2 = Group.objects.create(
            title='Заголовок для тестовой группы 777',
            slug='test_slug777',
            description='Тестовое описание 777',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
            image=cls.image,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.author = User.objects.get(username='test_username')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон, нейм и неймспейс."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': self.group.slug}): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': self.author.username}): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': self.post.pk}): 'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={
                'post_id': self.post.pk}): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def assert_post(self, first_object):
        """Код-миксин для проверки постов."""
        post_context = {
            first_object.text: self.post.text,
            first_object.author.username: self.post.author.username,
            first_object.author.pk: self.post.author.pk,
            first_object.group.title: self.group.title,
            first_object.group.pk: self.group.pk,
            first_object.pk: self.post.pk,
            first_object.image: self.post.image,
        }
        for key, value in post_context.items():
            with self.subTest(key=key):
                self.assertEqual(key, value)

    def test_index_pages_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assert_post(first_object)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        group_context = {
            'title': self.group.title,
            'description': self.group.description,
            'slug': self.group.slug,
            'pk': self.group.pk,
        }
        for key, value in group_context.items():
            with self.subTest(key=key):
                self.assertEqual(
                    getattr(response.context.get('group'), key), value
                )
        self.assertEqual(
            response.context['page_obj'][0].image, self.post.image
        )

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом"""
        response = (self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.author})))
        first_object = response.context['page_obj'][0]
        self.assert_post(first_object)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом"""
        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})))
        self.assertEqual(response.context.get('post').id, self.post.pk)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом"""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}))
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context.get('form'), PostForm)
        self.assertIs(type(response.context.get('is_edit')), bool)
        self.assertEqual(response.context.get('is_edit'), True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_another_group(self):
        """Пост не попал в другую группу"""
        response = self.guest_client.get(
            reverse("posts:group_list", kwargs={"slug": self.group_2.slug})
        )
        group_post_list_2 = response.context.get("page_obj").object_list
        self.assertNotIn(self.post, group_post_list_2)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(
            username='test_username',
            email='test@test.ru',
            password='Test1234',
        )
        cls.group = Group.objects.create(
            title=('Заголовок для тестовой группы'),
            slug='test_slug2',
            description='Тестовое описание')
        cls.posts = []
        for i in range(13):
            cls.posts.append(Post(
                text=f'Тестовый пост {i}',
                author=cls.author,
                group=cls.group
            )
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.guest_client = Client()
        self.author = User.objects.get(username='test_username')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_first_page_contains_ten_posts(self):
        """Проверка пагинации на первой странице."""
        list_urls = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author}),
        ]
        for tested_url in list_urls:
            response = self.client.get(tested_url)
            self.assertEqual(
                len(response.context.get('page_obj').object_list),
                settings.PAGINATION
            )

    def test_second_page_contains_three_posts(self):
        """Проверка пагинации на второй странице."""
        list_urls = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author}),
        ]
        for tested_url in list_urls:
            response = self.client.get(tested_url, {'page': 2})
            self.assertEqual(
                len(response.context.get('page_obj').object_list), 3
            )


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='test_username')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост.',
        )

    def setUp(self):
        self.guest_client = Client()
        self.author = User.objects.get(username='test_username')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_cache_index(self):
        """Тест кэширования страницы index.html"""
        response_first = self.authorized_client.get(reverse('posts:index'))
        post_1 = Post.objects.get(pk=1)
        post_1.text = 'Измененный текст'
        post_1.save()
        response_second = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_first.content, response_second.content)
        cache.clear()
        response_third = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_first.content, response_third.content)


class FollowTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_follower = User.objects.create(
            username='follower',
            email='test@test.ru',
            password='Test1234',
        )
        cls.user_following = User.objects.create(
            username='following',
            email='test2@test.ru',
            password='Test1234',
        )

    def setUp(self):
        self.post = Post.objects.create(
            author=self.user_following,
            text='Тестовая запись 777'
        )
        self.follower = Follow.objects.create(
            user=self.user_follower, author=self.user_following
        )
        self.guest_client = Client()
        self.client_follower = Client()
        self.client_following = Client()
        self.client_follower.force_login(self.user_follower)
        self.client_following.force_login(self.user_following)

    def test_follow_auth_user(self):
        """Тест подписка на выбранного профиля"""
        response = self.client_follower.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_following.username}
            )
        )
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(self.user_follower.follower.count(), 1)
        self.assertTrue(response.status_code, HTTPStatus.OK)

    def test_unfollow_auth_user(self):
        """Тест отподписка от выбранного профиля"""
        self.client_follower.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user_following.username}
            )
        )
        self.assertFalse(Follow.objects.filter(
            user=self.user_follower, author=self.user_following
        ).exists())
        self.assertEqual(Follow.objects.count(), 0)

    def test_appears_in_subscription_feed(self):
        """Пост появляется в ленте подписчиков"""
        response = self.client_follower.get('/follow/')
        post_text_0 = response.context['page_obj'][0].text
        self.assertEqual(post_text_0, 'Тестовая запись 777')

    def test_not_appears_in_subscription_feed(self):
        """Пост не появляется в ленте подписчиков"""
        response_new = self.client_following.get('/follow/')
        self.assertNotContains(response_new,
                               'Тестовая запись 777')

    def test_guest_user_attempt_to_follow(self):
        """Попытка гостя подписаться"""
        response = self.guest_client.get('/follow/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
