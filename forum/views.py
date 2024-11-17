# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Post,Subject,Collect,Comment,Reply
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection, transaction
from django.core.paginator import Paginator

from django.utils import timezone
#import pytz

def home(request):
    return render(request, 'home.html')

def post_list(request):
    subjects = Subject.objects.all()  
    selected_subject = request.GET.get('subject')  
    collected_filter = request.GET.get('collected', '') 

    if selected_subject:
        posts = Post.objects.filter(subject__name=selected_subject)
    else:
        posts = Post.objects.all()

    if collected_filter == "yes":
        posts = posts.filter(id__in=Collect.objects.filter(user=request.user).values('post_id'))
    if collected_filter == "no":
        posts = Post.objects.all()

    paginator = Paginator(posts, 8)  # 每页显示8个帖子
    page_number = request.GET.get('page')  
    page_obj = paginator.get_page(page_number)  

    return render(request, 'post_list.html', {
        'posts': posts,
        'page_obj': page_obj,
        'subjects': subjects,
        'selected_subject': selected_subject,
        'collected_filter': collected_filter,
    })

@login_required(login_url='/login/')
def new_post(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        subject_name = request.POST.get('subject')
        user = request.user
        print(f"Title: '{title}', Content: '{content}', subject_name: '{subject_name}'")  # 调试输出


        if title and content: 
            subject, created = Subject.objects.get_or_create(name=subject_name)

            post = Post(title=title, content=content, user=user, subject=subject)
            post.save()

            messages.success(request, "帖子已成功发布。")
            return redirect('post_list') 
        else:
            messages.error(request, "标题和内容不能为空。")

    subjects = Subject.objects.all() 
    return render(request, 'new_post.html', {
        'user_id': request.user.id,
        'username': request.user.username,
        'subjects': subjects,
    })

"""""
@login_required(login_url='/login/')
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.user != request.user:
        messages.error(request, "你没有权限删除这篇帖子。")
        return redirect('post_list')

    post.delete()
    return redirect('post_list')  
"""""

@login_required(login_url='/login/')
def delete_post(request, post_id):
    current_user_id = request.user.id

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id FROM forum_post
            WHERE id = %s
        """, [post_id])
        row = cursor.fetchone()

    if not row or row[0] != current_user_id:
        messages.error(request, "你没有权限删除这篇帖子。")
        return redirect('post_list')

    with transaction.atomic():
        Collect.objects.filter(post_id=post_id).delete()

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM forum_post WHERE id = %s", [post_id])

    return redirect('post_list')
"""
@login_required(login_url='/login/')
def edit_post(request, post_id):
    #print("GET data:", request.GET)
    #print("POST data:", request.POST)

    post = get_object_or_404(Post, id=post_id)

    if post.user != request.user:
        messages.error(request, "你没有权限编辑这篇帖子。")
        return redirect('post_list')

    if request.method == 'POST':

        title = request.POST.get("title","").strip()
        content = request.POST.get("content","").strip()
        subject_name = request.POST.get('subject',"").strip()
        print(f"Title: '{title}', Content: '{content}', subject_name: '{subject_name}'")  # 调试输出

        if title and content and subject_name:
            post.title = title
            post.content = content

            subject, created = Subject.objects.get_or_create(name=subject_name)
            post.subject = subject

            post.updated_at = timezone.now()  
            post.save()

            messages.success(request, "帖子已成功更新。")
            return redirect('post_list')  
        else:
            messages.error(request, "主题不能为空")


    subjects = Subject.objects.all()
    return render(request, 'edit_post.html', {
        'post': post,
        'subjects': subjects,
    })
"""
@login_required(login_url='/login/')
def edit_post(request, post_id):
    current_user_id = request.user.id

    post = get_object_or_404(Post, id=post_id)

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id FROM forum_post
            WHERE id = %s
        """, [post_id])
        row = cursor.fetchone()

    if not row or row[0] != current_user_id:
        messages.error(request, "你没有权限编辑这篇帖子。")
        return redirect('post_list')

    if request.method == 'POST':
        title = request.POST.get('title')  
        content = request.POST.get('content')  

        if not title or not content:
            messages.error(request, "标题和内容不能为空。")
            return render(request, 'edit_post.html', {'post': post})

        title = title.strip() if title else ''
        content = content.strip() if content else ''

        with transaction.atomic():
            # 代码中所有与数据库交互的SQL查询都使用了参数化查询，如%s，
            # 将变量绑定到查询参数，而不是直接插入SQL字符串中，可以有效防止SQL注入攻击。
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE forum_post 
                    SET title = %s, content = %s, updated_at = NOW()
                    WHERE id = %s
                """, [title, content, post_id])

            post.title = title
            post.content = content
            post.save()

        messages.success(request, "帖子更新成功！")
        return redirect('post_detail', post_id=post_id)

    return render(request, 'edit_post.html', {'post': post})



def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_collected = Collect.objects.filter(user=request.user, post=post).exists() if request.user.is_authenticated else False
    return render(request, 'post_detail.html', {
        'post': post,
        'is_collected': is_collected,
    })

@login_required(login_url='/login/')
def collect_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    collect, created = Collect.objects.get_or_create(user=request.user, post=post)
    if created:
        messages.success(request, '成功收藏该帖子！')
    else:
        messages.info(request, '你已经收藏过这个帖子。')
    return redirect('post_detail', post_id=post_id)

@login_required(login_url='/login/')
def remove_collect(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    collect = Collect.objects.filter(user=request.user, post=post).first()
    if collect:
        collect.delete()
        messages.success(request, '成功移除收藏！')
    return redirect('post_detail', post_id=post_id)

@login_required(login_url='/login/')
def collected_posts(request, post_id):
    collected_posts = Collect.objects.filter(user=request.user).values_list('post', flat=True)
    posts = Post.objects.filter(id__in=collected_posts)
    return render(request, 'collected_posts.html', {'posts'})

@login_required(login_url='/login/')
def new_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        username = request.POST.get('username')
        content = request.POST.get('content')
        print(f"user:,'{username}',content:, '{content}'")

        if content:  
            comment = Comment(content=content, user=request.user, post=post)
            comment.save()
            messages.success(request, "评论已成功发布。")
            return redirect('post_detail', post_id=post_id)  
        else:
            messages.error(request, "请补全评论内容。")

    return render(request, 'new_comment.html', {
        'post': post,
        'post_id': post_id,
    })


@login_required(login_url='/login/')
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if comment.user != request.user:
        messages.error(request, "你没有权限删除这条评论。")
        return redirect('post_list')

    comment.delete()
    messages.success(request, "评论已成功删除。")
    return redirect('post_list') 


@login_required(login_url='/login/')
def new_reply(request, post_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if request.method == 'POST':
        username = request.POST.get('username')
        content = request.POST.get('content')
        print(f"user:,'{username}',content:, '{content}'")

        if content: 
            reply = Reply(content=content, user=request.user, comment=comment)
            reply.save()
            messages.success(request, "回复已成功发布。")
            return redirect('post_detail', post_id=post_id) 
        else:
            messages.error(request, "请补全回复内容。")

    return render(request, 'new_reply.html', {
        'comment': comment,
    })


@login_required(login_url='/login/')
def delete_reply(request, post_id, reply_id):
    reply = get_object_or_404(Reply, id=reply_id)

    if reply.user != request.user:
        messages.error(request, "你没有权限删除这条回复。")
        return redirect('post_detail', post_id=post_id)

    reply.delete()
    messages.success(request, "回复已成功删除。")
    return redirect('post_detail', post_id=post_id) 
