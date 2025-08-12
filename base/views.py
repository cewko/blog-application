from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView
from django.http import Http404
from django.core.mail import send_mail
from django.views.decorators.http import require_POST

from .models import Post
from .forms import CommentForm, EmailPostForm
# from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = "posts"
    paginate_by = 3
    template_name = "base/post/list.html"

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            return redirect(request.path)


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

    
    return render(
        request,
        "base/post/detail.html",
        {
            "post": post,
            "comments": comments,
            "form": form
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



# def post_list(request):
#     post_list = Post.published.all()
#     # Pagination with 3 posts per page
#     paginator = Paginator(post_list, 3)
#     page_number = request.GET.get("page", 1)
#     try:
#         posts = paginator.page(page_number)
#     except PageNotAnInteger:
#         # if page_number isn't an int get the first page
#         posts = paginator.page(1)
#     except EmptyPage:
#         posts = paginator.page(paginator.num_pages)

#     return render(
#         request, 
#         "base/post/list.html", 
#         {"posts": posts}
#     )