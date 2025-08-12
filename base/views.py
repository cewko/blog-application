from django.shortcuts import get_object_or_404, render
from .models import Post


def post_list(request):
    posts = Post.published.all()
    return render(
        request, 
        "base/post/list.html", 
        {"posts": posts}
    )


def post_detail(request, year, month, day, post):
    post = get_object_or_404(
        Post, 
        status=Post.Status.PUBLISHED,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day      
    )
    
    return render(
        request,
        "base/post/detail.html",
        {"post": post}
    )