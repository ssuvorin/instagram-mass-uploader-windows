"""Views module: tasks (split from monolith)."""
from .common import *


def task_list(request):
    """List all tasks with filtering and pagination"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    tasks = UploadTask.objects.order_by('-created_at')
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if search_query:
        tasks = tasks.filter(
            Q(account__username__icontains=search_query) |
            Q(log__icontains=search_query)
        )
    
    context = {
        'tasks': tasks,
        'status_filter': status_filter,
        'search_query': search_query,
        'active_tab': 'tasks'
    }
    return render(request, 'uploader/task_list.html', context)


def task_detail(request, task_id):
    """View details of a specific task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    context = {
        'task': task,
        'active_tab': 'tasks'
    }
    return render(request, 'uploader/task_detail.html', context)


def create_task(request):
    """Create a new upload task"""
    if request.method == 'POST':
        form = UploadTaskForm(request.POST)
        files_form = VideoUploadForm(request.POST, request.FILES)
        
        if form.is_valid() and files_form.is_valid():
            # Create task
            task = form.save(commit=False)
            task.status = 'PENDING'
            task.save()
            
            # Handle video file
            video_file = files_form.cleaned_data['video_file']
            VideoFile.objects.create(
                task=task,
                video_file=video_file,
                caption=form.cleaned_data.get('caption', '')
            )
            
            messages.success(request, f'Task created successfully! Task ID: {task.id}')
            
            # Start task in background thread
            if form.cleaned_data.get('start_immediately', False):
                thread = threading.Thread(target=run_upload_task, args=(task.id,))
                thread.daemon = True
                thread.start()
                messages.info(request, 'Task started in background.')
            
            return redirect('task_detail', task_id=task.id)
    else:
        form = UploadTaskForm()
        files_form = VideoUploadForm()
    
    context = {
        'form': form,
        'files_form': files_form,
        'active_tab': 'create_task'
    }
    return render(request, 'uploader/create_task.html', context)


def start_task(request, task_id):
    """Start a pending task"""
    task = get_object_or_404(UploadTask, id=task_id)
    
    if task.status != 'PENDING':
        messages.error(request, 'Only pending tasks can be started.')
        return redirect('task_detail', task_id=task.id)
    
    thread = threading.Thread(target=run_upload_task, args=(task.id,))
    thread.daemon = True
    thread.start()
    
    messages.success(request, f'Task {task.id} started!')
    return redirect('task_detail', task_id=task.id)
