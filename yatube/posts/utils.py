from django.conf import settings
from django.core.paginator import Paginator


def paginate(request, posts):
    paginator = Paginator(posts, settings.PAGINATION)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
