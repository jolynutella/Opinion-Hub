import openai

from django.shortcuts import render, redirect, get_object_or_404
from .models import PostModel, Comment
from .forms import PostModelForm, PostUpdateForm, CommentForm
from django.contrib.auth.decorators import login_required
from django.conf import settings


# Create your views here.

# Initialize the OpenAI API
openai.api_key = settings.OPENAI_API_KEY

@login_required
def index(request):
    posts = PostModel.objects.all()
    if request.method == 'POST':
        form = PostModelForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.author = request.user
            instance.save()
            return redirect('blog-index')
    else:
        form = PostModelForm()
    context = {
        'posts': posts,
        'form': form
    }

    return render(request, 'blog/index.html', context)


@login_required
def post_detail(request, pk):
    post = get_object_or_404(PostModel, id=pk)
    comments = post.comments()

    if request.method == 'POST':
        c_form = CommentForm(request.POST)
        if c_form.is_valid():
            instance = c_form.save(commit=False)
            instance.user = request.user
            instance.post = post
            instance.save()
            return redirect('blog-post-detail', pk=post.id)
    else:
        c_form = CommentForm()

    # Filter comments based on query parameter
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'positive':
        comments = comments.filter(score__gt=0.25)
    elif filter_type == 'negative':
        comments = comments.filter(score__lt=-0.25)
    elif filter_type == 'mixed':
        comments = comments.filter(score__lte=0.25, score__gte=-0.25)

    # Calculate average score and determine its classification
    if comments.exists():
        average_score = sum(comment.score for comment in comments) / comments.count()
        if average_score > 0.25:
            average_score_classification = 'Positive'
        elif average_score < -0.25:
            average_score_classification = 'Negative'
        else:
            average_score_classification = 'Mixed'
    else:
        average_score = 0
        average_score_classification = 'No comments'

    # Prepare comments text for AI analysis
    comments_text = "\n".join(comment.content for comment in comments)

    # Call the OpenAI API to generate the list of improvements
    improvements = generate_improvements(comments_text)

    context = {
        'post': post,
        'average_score': average_score,
        'average_score_classification': average_score_classification,
        'comments': comments,
        'c_form': c_form,
        'filter_type': filter_type,
        'positive_comments': comments.filter(score__gt=0.25).count(),
        'negative_comments': comments.filter(score__lt=-0.25).count(),
        'mixed_comments': comments.filter(score__lte=0.25, score__gte=-0.25).count(),
        'improvements': improvements,
    }
    return render(request, 'blog/post_detail.html', context)

def generate_improvements(comments_text):
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-0125",
            prompt=f"Analyze the following comments and provide a list of things that must be improved:\n\n{comments_text}",
            max_tokens=5000,
            n=1,
            stop=None,
            temperature=0.5,
        )
        improvements = response.choices[0].text.strip()
    except Exception as e:
        print(e)
        improvements = "Unable to generate improvements at this time."
    
    return improvements


@login_required
def post_edit(request, pk):
    post = PostModel.objects.get(id=pk)
    if request.method == 'POST':
        form = PostUpdateForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog-post-detail', pk=post.id)
    else:
        form = PostUpdateForm(instance=post)
    context = {
        'post': post,
        'form': form,
    }
    return render(request, 'blog/post_edit.html', context)


@login_required
def post_delete(request, pk):
    post = PostModel.objects.get(id=pk)
    if request.method == 'POST':
        post.delete()
        return redirect('blog-index')
    context = {
        'post': post
    }
    return render(request, 'blog/post_delete.html', context)

@login_required
def comment_edit(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user != comment.user:
        return redirect('blog-post-detail', pk=comment.post.pk)
    
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog-post-detail', pk=comment.post.pk)
    else:
        form = CommentForm(instance=comment)
    
    context = {
        'form': form,
        'comment': comment,
    }
    return render(request, 'blog/comment_edit.html', context)


@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    post_id = comment.post.pk
    if request.user != comment.user:
        return redirect('blog-post-detail', pk=post_id)
    
    if request.method == 'POST':
        comment.delete()
        return redirect('blog-post-detail', pk=post_id)
    
    context = {
        'comment': comment,
    }
    return render(request, 'blog/comment_delete.html', context)