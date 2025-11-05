document.addEventListener('DOMContentLoaded', function() {
    const addTaskBtn = document.getElementById('add-task-button');
    const taskInput = document.getElementById('task-input');
    const prioritySelect = document.getElementById('priority-select');
    const timeInput = document.getElementById('time-input');
    const taskCardContainer = document.getElementById('task-card');
    const dateInput = document.getElementById('date-input');

    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;

    document.querySelectorAll('.task-card').forEach(taskDiv => {
        attachTaskEvents(taskDiv);
        addSecondsDisplay(taskDiv);
    });

    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            addTaskBtn.click();
        }
        
        if (e.key === 'Escape' && document.activeElement === taskInput) {
            taskInput.value = '';
            taskInput.blur();
        }
    });

    taskInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            addTaskBtn.click();
        }
    });

    taskInput.addEventListener('focus', function() {
        taskInput.style.transform = 'scale(1.02)';
    });

    taskInput.addEventListener('blur', function() {
        taskInput.style.transform = 'scale(1)';
    });


    // add new task
    addTaskBtn.addEventListener('click', function() {
        const taskText = taskInput.value.trim();
        const priority = prioritySelect.value;
        const date = dateInput.value;
        const time = timeInput.value;

        if (taskText !== '') {
            // Add loading state
            addTaskBtn.classList.add('loading');
            addTaskBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Adding...';
            
            fetch('/add_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: taskText,
                    priority: priority,
                    date: date,
                    time: time
                })
            })
            .then(res => res.json())
            .then(task => {
                // Add success animation
                addTaskBtn.innerHTML = '<i class="fa-solid fa-check"></i> Added!';
                addTaskBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                
                // Create and add the new task element dynamically
                const taskElement = createTaskElement(task);
                const backlogContainer = document.querySelector('#task-card');
                backlogContainer.appendChild(taskElement);
                
                // Add animation to the new task
                taskElement.classList.add('new-task');
                
                // Clear form
                taskInput.value = '';
                timeInput.value = '';
                
                // Reset button after delay
                setTimeout(() => {
                    addTaskBtn.classList.remove('loading');
                    addTaskBtn.innerHTML = '<i class="fa-solid fa-plus"></i> Add Task';
                    addTaskBtn.style.background = '';
                }, 2000);
            })
            .catch(error => {
                console.error('Error:', error);
                addTaskBtn.innerHTML = '<i class="fa-solid fa-exclamation-triangle"></i> Error';
                addTaskBtn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                
                setTimeout(() => {
                    addTaskBtn.classList.remove('loading');
                    addTaskBtn.innerHTML = '<i class="fa-solid fa-plus"></i> Add Task';
                    addTaskBtn.style.background = '';
                }, 2000);
            });
        } else {
            // shake animation for empty input
            taskInput.style.animation = 'shake 0.5s ease-in-out';
            taskInput.focus();
            setTimeout(() => {
                taskInput.style.animation = '';
            }, 500);
        }
    });

    // Add shake animation for empty input
    const style = document.createElement('style');
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            75% { transform: translateX(5px); }
        }
    `;
    document.head.appendChild(style);

    function sortTasks() {
        const container = document.querySelector('.not-yet-started'); 
        const tasks = Array.from(container.querySelectorAll('.task-card'));

        tasks.sort((a, b) => {
            const priorityOrder = { high: 1, mid: 2, low: 3 };
            const aPriority = Object.keys(priorityOrder).find(p => a.classList.contains(p));
            const bPriority = Object.keys(priorityOrder).find(p => b.classList.contains(p));

            // compare priority
            if (priorityOrder[aPriority] !== priorityOrder[bPriority]) {
                return priorityOrder[aPriority] - priorityOrder[bPriority];
            }

            // compare date + time
            const aDate = new Date(`${a.querySelector('.date-time').textContent}`);
            const bDate = new Date(`${b.querySelector('.date-time').textContent}`);
            return aDate - bDate;
        });

        tasks.forEach(task => container.appendChild(task)); 
    }   

    function createTaskElement(task) {
        const taskDiv = document.createElement('div');
        taskDiv.className = `task-card ${task.priority}`;
        taskDiv.setAttribute('data-id', task.id);
        taskDiv.setAttribute('draggable', 'true');
        
        taskDiv.innerHTML = `
            <div class="task-header">
                <div class="task-name">${task.name}</div>
                <div class="task-priority-badge ${task.priority}">${task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}</div>
            </div>
            <div class="task-content">
                <div class="task-date">${task.date}</div>
                <div class="task-time">
                    <i class="fa-solid fa-clock"></i>
                    ${task.time}
                </div>
            </div>
            <div class="task-actions">
                <i class="fa-solid fa-pen" title="Edit task"></i>
                <i class="fa-solid fa-trash" title="Delete task"></i>
            </div>
        `;
        
        // Attach event listeners
        attachTaskEvents(taskDiv);
        addSecondsDisplay(taskDiv);
        
        return taskDiv;
    }

    function attachTaskEvents(taskDiv) {
        const deleteIcon = taskDiv.querySelector('.fa-trash');
        const editIcon = taskDiv.querySelector('.fa-pen');
        const taskId = taskDiv.dataset.id;

        // drag and drop functionality
        setupDragAndDrop(taskDiv);

        // delete
        deleteIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            
            // confirmation before deleting task
            const confirmed = confirm('Are you sure you want to delete this task?');
            if (confirmed) {
                deleteTaskWithUndo(taskDiv, taskId);
            }
        });

        // edit
        editIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            const taskNameDiv = taskDiv.querySelector('.task-name');
            const taskDateDiv = taskDiv.querySelector('.task-date');
            const taskTimeDiv = taskDiv.querySelector('.task-time');
            const oldDate = taskDateDiv.textContent.trim();
            const oldTime = taskTimeDiv.textContent.trim().replace('🕐 ', '');

            const editForm = document.createElement('form');
            editForm.className = 'edit-overlay';

            // Create form header
            const formHeader = document.createElement('div');
            formHeader.style.cssText = 'display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;';
            formHeader.innerHTML = '<i class="fa-solid fa-edit"></i><h3 style="margin: 0; color: var(--text-primary);">Edit Task</h3>';
            editForm.appendChild(formHeader);

            const editTaskInput = document.createElement('input');
            editTaskInput.type = 'text';
            editTaskInput.value = taskNameDiv.textContent;
            editTaskInput.placeholder = 'Task name';
            editTaskInput.required = true;

            const editPrioritySelect = document.createElement('select');
            editPrioritySelect.innerHTML = `
                <option value="high">High Priority</option>
                <option value="mid">Medium Priority</option>
                <option value="low">Low Priority</option>
            `;
            ['high', 'mid', 'low'].forEach(optionVal => {
                if (taskDiv.classList.contains(optionVal)) {
                    editPrioritySelect.value = optionVal;
                }
            });

            const editDateInput = document.createElement('input');
            editDateInput.type = 'date';
            editDateInput.value = oldDate;

            const editTimeInput = document.createElement('input');
            editTimeInput.type = 'time';
            editTimeInput.value = oldTime;

            const buttonContainer = document.createElement('div');
            buttonContainer.style.cssText = 'display: flex; gap: 0.75rem; margin-top: 0.5rem;';

            const saveBtn = document.createElement('button');
            saveBtn.type = 'submit';
            saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Save';

            const cancelBtn = document.createElement('button');
            cancelBtn.type = 'button';
            cancelBtn.innerHTML = '<i class="fa-solid fa-times"></i> Cancel';

            buttonContainer.appendChild(saveBtn);
            buttonContainer.appendChild(cancelBtn);

            editForm.appendChild(editTaskInput);
            editForm.appendChild(editPrioritySelect);
            editForm.appendChild(editDateInput);
            editForm.appendChild(editTimeInput);
            editForm.appendChild(buttonContainer);

            // Add backdrop for emphasis
            const backdrop = document.createElement('div');
            backdrop.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                z-index: 9998;
                backdrop-filter: blur(4px);
            `;

            document.body.appendChild(backdrop);
            document.body.appendChild(editForm);
            editForm.style.display = "flex"; 
            editTaskInput.focus();

            const closeModal = () => {
                editForm.remove();
                backdrop.remove();
            };

            cancelBtn.addEventListener('click', function(e) {
                e.preventDefault();
                closeModal();
            });

            backdrop.addEventListener('click', closeModal);

            // Keyboard shortcuts
            editForm.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    closeModal();
                }
            });

            editForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                if (!editTaskInput.value.trim()) {
                    editTaskInput.style.animation = 'shake 0.5s ease-in-out';
                    editTaskInput.focus();
                    return;
                }

                saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
                saveBtn.disabled = true;

                fetch(`/edit_task/${taskId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: editTaskInput.value.trim(),
                        date: editDateInput.value,
                        time: editTimeInput.value,
                        priority: editPrioritySelect.value
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        taskNameDiv.textContent = editTaskInput.value.trim();
                        taskDateDiv.textContent = editDateInput.value;
                        taskTimeDiv.innerHTML = `<i class="fa-solid fa-clock"></i> ${editTimeInput.value}`;
                        
                        // updating priority badges
                        const priorityBadge = taskDiv.querySelector('.task-priority-badge');
                        priorityBadge.textContent = editPrioritySelect.value.charAt(0).toUpperCase() + editPrioritySelect.value.slice(1);
                        priorityBadge.className = `task-priority-badge ${editPrioritySelect.value}`;
                        
                        taskDiv.classList.remove('high', 'mid', 'low');
                        taskDiv.classList.add(editPrioritySelect.value);
                        closeModal();
                        sortTasks(); 
                    }
                })
                .catch(error => {
                    console.error('Error updating task:', error);
                    saveBtn.innerHTML = '<i class="fa-solid fa-exclamation-triangle"></i> Error';
                    setTimeout(() => {
                        saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Save';
                        saveBtn.disabled = false;
                    }, 2000);
                });
            });
        });
    }

    function addSecondsDisplay(taskDiv) {
        const dateTimeDiv = taskDiv.querySelector('.date-time');
        if (!dateTimeDiv) return;

        // Create seconds display element
        const secondsDisplay = document.createElement('div');
        secondsDisplay.className = 'seconds-display';
        dateTimeDiv.appendChild(secondsDisplay);

        // Add hover event listeners
        dateTimeDiv.addEventListener('mouseenter', function() {
            const timeText = dateTimeDiv.textContent.trim();
            const timeMatch = timeText.match(/(\d{1,2}):(\d{2})/);
            
            if (timeMatch) {
                const hours = parseInt(timeMatch[1]);
                const minutes = parseInt(timeMatch[2]);
                const seconds = Math.floor(Math.random() * 60); // Random seconds for demo
                const formattedTime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                secondsDisplay.textContent = formattedTime;
            }
        });

        dateTimeDiv.addEventListener('mouseleave', function() {
            secondsDisplay.textContent = '';
        });
    }

    function setupDragAndDrop(taskElement) {
        // to make sure task card is able to drag
        if (!taskElement.draggable) {
            taskElement.draggable = true;
        }

        //  start drag
        taskElement.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('text/plain', taskElement.dataset.id);
            e.dataTransfer.effectAllowed = 'move';
            taskElement.classList.add('dragging');
            
            // hide the original element
            setTimeout(() => {
                taskElement.style.display = 'none';
            }, 0);
        });

        // end of drag
        taskElement.addEventListener('dragend', function(e) {
            taskElement.classList.remove('dragging');
            taskElement.style.display = '';
            
            document.querySelectorAll('.drop-zone').forEach(zone => {
                zone.classList.remove('drag-over');
            });
        });
    }

    // for drop
    function setupDropZones() {
        const dropZones = document.querySelectorAll('.drop-zone');
        
        dropZones.forEach(zone => {
            zone.addEventListener('dragover', function(e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                zone.classList.add('drag-over');
            });

            zone.addEventListener('dragleave', function(e) {
                // Only remove drag-over if we're actually leaving the zone
                if (!zone.contains(e.relatedTarget)) {
                    zone.classList.remove('drag-over');
                }
            });

            zone.addEventListener('drop', function(e) {
                e.preventDefault();
                zone.classList.remove('drag-over');
                
                const taskId = e.dataTransfer.getData('text/plain');
                const draggedTask = document.querySelector(`[data-id="${taskId}"]`);
                const newStatus = zone.closest('.column').dataset.status;
                
                if (draggedTask && newStatus) {
                    moveTaskToStatus(taskId, newStatus, draggedTask, zone);
                }
            });
        });
    }

    function moveTaskToStatus(taskId, newStatus, taskElement, targetZone) {
        // Update task status in database
        fetch(`/update_task_status/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // remove task from current 
                taskElement.remove();
                
                // update target zone
                if (targetZone.dataset.empty === 'true') {
                    // Remove empty state
                    targetZone.innerHTML = '';
                    targetZone.removeAttribute('data-empty');
                }
                
                // add task to new location
                targetZone.appendChild(taskElement);
                
                // show toasty!
                showTaskMovedFeedback(taskElement, newStatus);
            } else {
                console.error('Failed to update task status');
                // if update failed, reload back to location
                window.location.reload();
            }
        })
        .catch(error => {
            console.error('Error updating task status:', error);
            // Restore original position if error occurred
            window.location.reload();
        });
    }

    function showTaskMovedFeedback(taskElement, status) {
        // animation to show the task was moved
        taskElement.style.transform = 'scale(1.05)';
        taskElement.style.boxShadow = '0 8px 25px rgba(98, 35, 117, 0.3)';
        
        setTimeout(() => {
            taskElement.style.transform = '';
            taskElement.style.boxShadow = '';
        }, 500);

        // toast
        const toast = document.createElement('div');
        toast.className = 'status-toast';
        
        const statusText = {
            'backlog': 'moved to Backlog',
            'in-progress': 'moved to In Progress',
            'completed': 'moved to Completed'
        };
        
        toast.textContent = `Task ${statusText[status]}!`;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('slide-out');
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }

    function deleteTaskWithUndo(taskElement, taskId) {
        // store task for undoing
        const taskData = {
            id: taskId,
            name: taskElement.querySelector('.task-name').textContent,
            priority: taskElement.classList.contains('high') ? 'high' : 
                     taskElement.classList.contains('mid') ? 'mid' : 'low',
            date: taskElement.querySelector('.task-date').textContent,
            time: taskElement.querySelector('.task-time').textContent.replace(/.*?(\d{1,2}:\d{2}).*/, '$1'),
            element: taskElement.cloneNode(true),
            parent: taskElement.parentElement
        };

        // delete animation
        taskElement.style.animation = 'fadeOut 0.3s ease-out';
        
        // Delete from database
        fetch(`/delete_task/${taskId}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Remove from DOM after successful database deletion
                setTimeout(() => {
                    taskElement.remove();
                    showUndoNotification(taskData);
                }, 300);
            } else {
                console.error('Failed to delete task from database');
                // Restore animation if deletion failed
                taskElement.style.animation = '';
            }
        })
        .catch(error => {
            console.error('Error deleting task:', error);
            // Restore animation if deletion failed
            taskElement.style.animation = '';
        });
    }

    function showUndoNotification(taskData) {
        const undoNotification = document.createElement('div');
        undoNotification.className = 'undo-notification';

        const message = document.createElement('span');
        message.className = 'undo-message';
        message.textContent = 'Task deleted!';

        const countdown = document.createElement('span');
        countdown.className = 'undo-countdown';

        const undoButton = document.createElement('button');
        undoButton.className = 'undo-button';
        undoButton.textContent = 'Undo';

        undoNotification.appendChild(message);
        undoNotification.appendChild(countdown);
        undoNotification.appendChild(undoButton);
        document.body.appendChild(undoNotification);

        // countdown for undo
        let timeLeft = 5;
        countdown.textContent = timeLeft;

        const countdownInterval = setInterval(() => {
            timeLeft--;
            countdown.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
                undoNotification.style.animation = 'slideOutToBottom 0.3s ease-in';
                setTimeout(() => undoNotification.remove(), 300);
            }
        }, 1000);

        // Undo functionality!!
        undoButton.addEventListener('click', () => {
            clearInterval(countdownInterval);
            undoTask(taskData);
            undoNotification.style.animation = 'slideOutToBottom 0.3s ease-in';
            setTimeout(() => undoNotification.remove(), 300);
        });
    }

    function undoTask(taskData) {
        // Restore task in database first
        fetch('/add_task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: taskData.name,
                priority: taskData.priority,
                date: taskData.date,
                time: taskData.time
            })
        })
        .then(res => res.json())
        .then(newTask => {
    
            const restoredTask = taskData.element;
            restoredTask.setAttribute('data-id', newTask.id);
            taskData.parent.appendChild(restoredTask);
            
            // reattach event listeners when undo
            attachTaskEvents(restoredTask);
            addSecondsDisplay(restoredTask);

            // add redo animation
            restoredTask.style.animation = 'slideInFromTop 0.5s ease-out';
        })
        .catch(error => {
            console.error('Error restoring task:', error);
        });
        
        // show message for success undo
        const successToast = document.createElement('div');
        successToast.className = 'success-toast';
        
        successToast.textContent = 'Task restored!';
        document.body.appendChild(successToast);
        
        setTimeout(() => {
            successToast.style.animation = 'slideOutToRight 0.3s ease-in';
            setTimeout(() => successToast.remove(), 300);
        }, 2000);
    }

    setupDropZones();
});
