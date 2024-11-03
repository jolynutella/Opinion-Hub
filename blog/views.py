import openai
from django.shortcuts import render, redirect, get_object_or_404
from .models import PostModel, Comment
from .forms import PostModelForm, PostUpdateForm, CommentForm
from django.contrib.auth.decorators import login_required
from django.conf import settings


# Helper function to initialize OpenAI API
def get_openai_api_key():
    openai.api_key = settings.OPENAI_API_KEY


# Helper function to generate improvements via OpenAI API
def generate_improvements(comments_text):
    get_openai_api_key()
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-0125",
            prompt=f"Analyze the following comments and provide a list of things that must be improved:\n\n{comments_text}",
            max_tokens=5000,
            n=1,
            temperature=0.5,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Unable to generate improvements at this time."


# Helper function to calculate average score and classify it
def calculate_average_score(comments):
    if not comments.exists():
        return 0, 'No comments'

    average_score = sum(comment.score for comment in comments) / comments.count()
    if average_score > 0.25:
        return average_score, 'Positive'
    elif average_score < -0.25:
        return average_score, 'Negative'
    else:
        return average_score, 'Mixed'


# Helper function to filter comments based on score
def filter_comments(comments, filter_type):
    if filter_type == 'positive':
        return comments.filter(score__gt=0.25)
    elif filter_type == 'negative':
        return comments.filter(score__lt=-0.25)
    elif filter_type == 'mixed':
        return comments.filter(score__lte=0.25, score__gte=-0.25)
    return comments


@login_required
def index(request):
    posts = PostModel.objects.all()
    post_data = []
    total_score = 0
    total_comments_count = 0

    for post in posts:
        comments = post.comments()  # Retrieve comments for each post
        average_score, score_classification = calculate_average_score(comments)  # Use the helper function to get scores

        post_data.append({
            'post': post,
            'average_score': average_score,
            'score_classification': score_classification,
        })

        # Accumulate the total score and count comments for overall average calculation
        if comments.exists():
            total_score += average_score * comments.count()  # Sum score for all comments
            total_comments_count += comments.count()  # Total number of comments

    # Calculate overall average score
    if total_comments_count > 0:
        overall_average_score = total_score / total_comments_count
        if overall_average_score > 0.25:
            overall_classification = 'Positive'
        elif overall_average_score < -0.25:
            overall_classification = 'Negative'
        else:
            overall_classification = 'Mixed'
    else:
        overall_average_score = 0
        overall_classification = 'No comments'

    if request.method == 'POST':
        form = PostModelForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog-index')
    else:
        form = PostModelForm()

    context = {
        'post_data': post_data,  # List of post data with scores
        'form': form,
        'overall_average_score': overall_average_score,  # Overall average score for all posts
        'overall_classification': overall_classification,  # Overall classification
    }
    return render(request, 'blog/index.html', context)


@login_required
def post_detail(request, pk):
    post = get_object_or_404(PostModel, id=pk)
    comments = post.comments()
    filter_type = request.GET.get('filter', 'all')
    comments = filter_comments(comments, filter_type)

    if request.method == 'POST':
        c_form = CommentForm(request.POST)
        if c_form.is_valid():
            comment = c_form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()
            return redirect('blog-post-detail', pk=post.id)
    else:
        c_form = CommentForm()

    # Calculate average score and classify comments
    average_score, score_classification = calculate_average_score(comments)
    
    # Prepare comments text for AI analysis
    comments_text = "\n".join(comment.content for comment in comments)
    improvements = generate_improvements(comments_text)

    context = {
        'post': post,
        'average_score': average_score,
        'average_score_classification': score_classification,
        'comments': comments,
        'c_form': c_form,
        'filter_type': filter_type,
        'positive_comments': comments.filter(score__gt=0.25).count(),
        'negative_comments': comments.filter(score__lt=-0.25).count(),
        'mixed_comments': comments.filter(score__lte=0.25, score__gte=-0.25).count(),
        'improvements': improvements,
    }
    return render(request, 'blog/post_detail.html', context)


@login_required
def post_edit(request, pk):
    post = get_object_or_404(PostModel, id=pk)
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
    post = get_object_or_404(PostModel, id=pk)
    if request.method == 'POST':
        post.delete()
        return redirect('blog-index')
    
    context = {
        'post': post,
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
