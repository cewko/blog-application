from django.shortcuts import get_object_or_404, render, redirect
# from django.views.generic import ListView
from django.http import Http404
from django.core.mail import send_mail
from django.views.decorators.http import require_POST

from .models import Post
# from django.contrib.postgres.search import (
#     SearchVector,
#     SearchQuery,
#     SearchRank
# )
from .forms import CommentForm, EmailPostForm, SearchForm
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.contrib.postgres.search import TrigramSimilarity
from taggit.models import Tag
from django.db.models import Count

def post_list(request, tag_slug=None):
    post_list = Post.published.all()

    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])

    # Pagination with 3 posts per page
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get("page", 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # if page_number isn't an int get the first page
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return render(
        request, 
        "base/post/list.html", 
        {"posts": posts, "tag": tag}
    )

# class PostListView(ListView):
#     queryset = Post.published.all()
#     context_object_name = "posts"
#     paginate_by = 3
#     template_name = "base/post/list.html"

#     def get(self, request, *args, **kwargs):
#         try:
#             return super().get(request, *args, **kwargs)
#         except Http404:
#             return redirect(request.path)


def post_detail(request, year, month, day, post):
    post = get_object_or_404(
        Post, 
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

    # List of similar posts
    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = Post.published.filter(
        tags__in=post_tags_ids
    ).exclude(id=post.id)
    similar_posts = similar_posts.annotate(
        same_tags=Count("tags")
    ).order_by("-same_tags", "-publish")[:4]

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

            results = Post.published.annotate(
                similarity=TrigramSimilarity("title", query)
            ).filter(similarity__gte=0.1).order_by("-similarity")

            # search_vector = SearchVector(
            #     "title", weight="A"
            # ) + SearchVector("body", weight="B")
            # search_query = SearchQuery(query)
            # results = (
            #     Post.published.annotate(
            #         search=search_vector,
            #         rank=SearchRank(search_vector, search_query)
            #     ).filter(rank__gte=0.3).order_by("-rank")
            # )

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
        if form.is_valid():
            # form fields passed validation, 
            # retrieve a dict of the clean, validated data
            cd = form.cleaned_data
            # send email
            post_url = request.build_absolute_uri(
                post.get_absolute_url()
            )
            subject = (
                f"{cd['name']} ({cd['email']}) "
                f"recommends you read {post.title}"
            )
            message = (
                f"Read {post.title} at {post_url}\n\n"
                f"{cd['name']}\'s comment: {cd['comment']}"
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[cd["to"]]
            )
            sent = True
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

    # a comment was posted
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
