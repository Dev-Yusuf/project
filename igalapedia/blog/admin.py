from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import BlogPost, BlogPostLike, BlogPostComment, BlogGuidelinesAck, BlogPostReport, BlogPostView


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'published_at', 'is_hidden', 'created_at')
    list_filter = ('status', 'is_hidden', 'created_at')
    search_fields = ('title', 'author__username', 'body')
    actions = ['hide_posts', 'unhide_posts']

    @admin.action(description='Hide selected posts')
    def hide_posts(self, request, queryset):
        updated = queryset.update(is_hidden=True)
        self.message_user(request, f'{updated} post(s) hidden.')

    @admin.action(description='Unhide selected posts')
    def unhide_posts(self, request, queryset):
        updated = queryset.update(is_hidden=False)
        self.message_user(request, f'{updated} post(s) unhidden.')


@admin.register(BlogPostLike)
class BlogPostLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    list_filter = ('created_at',)


@admin.register(BlogPostComment)
class BlogPostCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'parent', 'created_at')
    list_filter = ('created_at',)


@admin.register(BlogGuidelinesAck)
class BlogGuidelinesAckAdmin(admin.ModelAdmin):
    list_display = ('user', 'acknowledged_at')


@admin.register(BlogPostView)
class BlogPostViewAdmin(admin.ModelAdmin):
    list_display = ('post', 'ip_hash', 'viewed_date')
    list_filter = ('viewed_date',)
    readonly_fields = ('post', 'ip_hash', 'viewed_date')


@admin.register(BlogPostReport)
class BlogPostReportAdmin(admin.ModelAdmin):
    list_display = ('post', 'post_link', 'reported_by', 'reason', 'created_at')
    list_filter = ('created_at',)

    def post_link(self, obj):
        url = reverse('admin:blog_blogpost_change', args=[obj.post_id])
        return format_html('<a href="{}">{}</a>', url, obj.post.title)
    post_link.short_description = 'Post'
