from typing import Optional

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Count
from taggit.models import Tag

from .models import Post
from .forms import CommentForm, EmailPostForm, SearchForm


def post_list(request, tag_slug: Optional[str] = None):
    post_list = Post.published.select_related("author")\
        .prefetch_related("tags").all()

    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])

    # pagination with 3 posts per page
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get("page", 1)
    posts = paginator.get_page(page_number)

    return render(
        request, "base/post/list.html", {"posts": posts, "tag": tag}
        )


def post_detail(request, year, month, day, post):
    post_qs = Post.published.select_related("author")\
        .prefetch_related("tags", "comments")

    post = get_object_or_404(
        post_qs, 
        status=Post.Status.PUBLISHED,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day      
    )
    # list of active comments for this post
    comments = post.comments.filter(active=True)
    # form for users to comment
    form = CommentForm()

    # list of similar posts
    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = (
        Post.published.filter(tags__in=post_tags_ids)
        .exclude(id=post.id)
        .annotate(same_tags=Count("tags", distinct=True))
        .order_by("-same_tags", "-publish")[:4]
        .select_related("author")
        .prefetch_related("tags")
    )

    return render(
        request,
        "base/post/detail.html",
        {
            "post": post,
            "comments": comments,
            "form": form,
            "similar_posts": similar_posts
        }
    )


def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if "query" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']

            results = (
                Post.published.annotate(similarity=TrigramSimilarity("title", query))
                .filter(similarity_gte=0.1)
                .order_by("-similarity")
                .select_related("author")
                .prefetch_related("tags")
            )

    return render(
        request,
        "base/post/search.html",
        {
            "form": form,
            "query": query,
            "results": results
        }
    )


def post_share(request, post_id):
    # retrieve post by id
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED
    )
    sent = False

    if request.method == "POST":
        # form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid(): # TODO
            # form fields passed validation, 
            # retrieve a dict of the clean, validated data
            cd = form.cleaned_data
            # send email
            post_url = request.build_absolute_uri(
                post.get_absolute_url()
            )
            subject = f"{cd['name']} ({cd['email']}) recommends you read '{post.title}'"
            message = f"Read {post.title} at {post_url}\n\n{cd['name']}'s comment: {cd['comment']}"
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

            sent = send_mail(subject, message, from_email, [cd["to"]]) > 0
    else:
        form = EmailPostForm()
        
    return render(
        request,
        "base/post/share.html",
        {"post": post, "form": form, "sent": sent}
    )


# only allow post reqs for this view
@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED
    )
    comment = None

    # comment was posted
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # create a comment object without saving it to the database
        comment = form.save(commit=False)
        # assign the post to the comment
        comment.post = post
        # save the comment to the database
        comment.save()

    return render(
        request,
        "base/post/comment.html",
        {
            "post": post,
            "form": form,
            "comment": comment
        }
    )
