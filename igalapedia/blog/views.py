from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.utils import timezone

from main.utils import get_client_ip_hash
from .models import BlogPost, BlogPostLike, BlogPostComment, BlogGuidelinesAck, BlogPostReport, BlogPostView
from .forms import BlogPostForm, BlogCommentForm


def blog_list(request):
    qs = BlogPost.objects.filter(status='published', is_hidden=False).order_by('-published_at').annotate(view_count=Count('view_records'))
    paginator = Paginator(qs, 12)
    page = request.GET.get('page', 1)
    posts = paginator.get_page(page)
    return render(request, 'blog/blog_list.html', {'posts': posts})


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost.objects.annotate(view_count=Count('view_records')), slug=slug)
    if post.is_hidden:
        raise Http404
    if post.status == 'draft' and (not request.user.is_authenticated or request.user != post.author):
        raise Http404
    ip_hash = get_client_ip_hash(request)
    if ip_hash:
        today = timezone.localdate()
        BlogPostView.objects.get_or_create(post=post, ip_hash=ip_hash, viewed_date=today)
    liked = False
    if request.user.is_authenticated:
        liked = BlogPostLike.objects.filter(user=request.user, post=post).exists()
    comments = post.comments.filter(parent=None).select_related('user').prefetch_related('replies__user')
    return render(request, 'blog/blog_detail.html', {
        'post': post,
        'liked': liked,
        'comments': comments,
        'comment_form': BlogCommentForm(),
    })


@login_required
def blog_guidelines(request):
    if request.method == 'POST':
        BlogGuidelinesAck.objects.get_or_create(user=request.user)
        next_url = request.GET.get('next', '/blog/create/')
        return redirect(next_url)
    return render(request, 'blog/blog_guidelines.html')


@login_required
def blog_create(request):
    if not BlogGuidelinesAck.objects.filter(user=request.user).exists():
        return redirect(f"/blog/guidelines/?next={request.path}")
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Post created successfully.')
            return redirect('blog:blog_detail', slug=post.slug)
    else:
        form = BlogPostForm()
    return render(request, 'blog/blog_create.html', {'form': form})


@login_required
def blog_edit(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    if post.author != request.user:
        raise Http404
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated.')
            return redirect('blog:blog_detail', slug=post.slug)
    else:
        form = BlogPostForm(instance=post)
    return render(request, 'blog/blog_edit.html', {'form': form, 'post': post})


@login_required
@require_POST
def blog_delete(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    if post.author != request.user:
        raise Http404
    post.delete()
    messages.success(request, 'Post deleted.')
    return redirect('blog:blog_list')


@login_required
@require_POST
def blog_like_toggle(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    like, created = BlogPostLike.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    count = post.likes.count()
    return JsonResponse({'liked': liked, 'count': count})


@login_required
@require_POST
def blog_comment_add(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    parent_id = request.POST.get('parent')
    parent = None
    if parent_id:
        parent = BlogPostComment.objects.filter(post=post, pk=parent_id).first()
    form = BlogCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.post = post
        comment.parent = parent
        comment.save()
        messages.success(request, 'Comment added.')
    return redirect('blog:blog_detail', slug=slug)


@login_required
@require_POST
def blog_report(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    reason = request.POST.get('reason', '')
    BlogPostReport.objects.create(post=post, reported_by=request.user, reason=reason or None)
    messages.success(request, 'Thank you. Your report has been submitted.')
    return redirect('blog:blog_detail', slug=slug)
