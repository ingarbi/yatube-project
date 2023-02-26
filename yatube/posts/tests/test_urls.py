from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author2 = User.objects.create_user(
            username='test_username2',
            email='test2@test.ru',
            password='Test1234'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=User.objects.create_user(
                username='test_username',
                email='test@test.ru',
                password='Test1234'
            ),
        )

    def setUp(self):
        self.guest_client = Client()
        self.author = User.objects.get(username='test_username')
        self.authorized_client = Client()
        self.authorized_client_2 = Client()
        self.authorized_client.force_login(self.author)
        self.authorized_client_2.force_login(self.author2)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        post_detail_url = reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk}
        )
        post_edit_url = reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}
        )

        templates_url_names = {
            '/': 'posts/index.html',
            '/follow/': 'posts/follow.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/test_username/': 'posts/profile.html',
            post_detail_url: 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            post_edit_url: 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_status_code(self):
        """URL статусы ответа на адреса авторизованного и неавтор-го юзера."""
        urls_names = [
            [reverse('posts:index'), self.guest_client, HTTPStatus.OK],
            [reverse(
                'posts:follow_index'), self.authorized_client, HTTPStatus.OK],
            [reverse('posts:follow_index'),
             self.guest_client, HTTPStatus.FOUND],
            [reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}),
                self.guest_client, HTTPStatus.OK],
            [reverse(
                'posts:profile',
                kwargs={'username': self.author.username}),
                self.guest_client, HTTPStatus.OK],
            [reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}),
                self.guest_client, HTTPStatus.OK],
            [reverse(
                'posts:post_create'),
                self.authorized_client, HTTPStatus.OK],
            [reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.pk}),
                self.authorized_client, HTTPStatus.OK],
            [reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.pk}),
                self.authorized_client_2, HTTPStatus.FOUND],
            [reverse(
                'posts:post_create'),
                self.guest_client, HTTPStatus.FOUND],
            [reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.pk}),
                self.guest_client, HTTPStatus.FOUND],
        ]
        for url, client, status in urls_names:
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, status)

    def test_home_group_profile(self):
        """
        Доступные не авторизованному пользователю
        страницы: главная, группа, профиль.
        """
        url_names = (
            '/',
            '/group/test-slug/',
            '/profile/test_username/',
        )
        for address in url_names:
            with self.subTest():
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_post_authorized(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_authorized(self):
        """Страница /post_edit/ доступна только
           авторизованному автору поста.
        """
        post_edit_url = reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}
        )
        response = self.authorized_client.get(post_edit_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_redirect_authorized_client_page_edit(self):
        """Авторизированного пользователя(не автора поста)
           со страницы /post_edit/
           переадресовывает на страницу просмотра поста
        """
        response = self.authorized_client_2.get(reverse('posts:post_edit',
                                                        kwargs={'post_id':
                                                                self.post.id}))
        self.assertRedirects(response, reverse('posts:post_detail',
                                               kwargs={'post_id':
                                                       self.post.id}))

    def test_post_edit_unauthorized(self):
        """Страница /post_edit/ недоступна не авторизванному."""
        post_edit_url = reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}
        )
        response = self.guest_client.get(post_edit_url)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.pk}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_403_page_uses_custom_template(self):
        self.guest_client = Client(enforce_csrf_checks=True)
        template = 'core/403csrf.html'
        form_data = {
            'text': ''
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTemplateUsed(response, template)

    def test_404_page_uses_custom_template(self):
        template = 'core/404.html'
        response = self.guest_client.get('/unexisting-page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, template)
