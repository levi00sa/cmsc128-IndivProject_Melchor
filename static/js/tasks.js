// ======================================================
//  tasks.js — Kanban Board Engine (Drag/Drop Fixed)
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    // -----------------------------------------
    // DOM SELECTORS
    // -----------------------------------------
    const backlogList = document.getElementById("backlog-list");
    const progressList = document.getElementById("progress-list");
    const completedList = document.getElementById("completed-list");

    const inputTitle = document.getElementById("task-title-input");
    const inputPriority = document.getElementById("task-priority-input");
    const inputDate = document.getElementById("task-date-input");
    const addBtn = document.getElementById("task-add-btn");

    const undoToast = document.getElementById("undo-toast");
    const undoBtn = document.getElementById("undo-btn");
    const undoCount = document.getElementById("undo-count");

    // Collaborative list selectors
    const listSelector = document.getElementById("list-selector");
    const createCollabBtn = document.getElementById("create-collab-list-btn");
    const collabListInfo = document.getElementById("collab-list-info");
    const collabListName = document.getElementById("collab-list-name");
    const manageMembersBtn = document.getElementById("manage-members-btn");
    const createCollabModal = document.getElementById("create-collab-modal");
    const manageMembersModal = document.getElementById("manage-members-modal");
    const collabOwnerBadge = document.getElementById("collab-owner-badge");
    const collabMemberCount = document.getElementById("collab-member-count");
    
    // Archived tasks selectors
    const toggleArchivedBtn = document.getElementById("toggle-archived-btn");
    const archivedSection = document.getElementById("archived-section");
    const hideArchivedBtn = document.getElementById("hide-archived-btn");
    const archivedTasksList = document.getElementById("archived-tasks-list");
    const boardLoadingState = document.getElementById("board-loading-state");
    const boardLoadingMessage = document.getElementById("board-loading-message");

    let allTasks = [];
    let deletedTaskBackup = null;
    let undoTimer = null;
    let deleteTimeout = null;
    let dragDropInitialized = false;
    let currentListId = null; // null for personal, number for collab list
    let collabLists = [];
    let loadingCounter = 0;

    // -----------------------------------------
    // INIT
    // -----------------------------------------
    (async () => {
        setBoardLoading(true, "Loading your workspace...");
        try {
            await Promise.all([loadCollabLists(true), loadTasks()]);
        } finally {
            setBoardLoading(false);
        }
    })();

    // Modal close handlers
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.modal').style.display = 'none';
        });
    });

    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });

    // List selector change handler
    listSelector.addEventListener('change', (e) => {
        if (e.target.value === 'personal') {
            currentListId = null;
            collabListInfo.style.display = 'none';
            updateCollabContext(null);
        } else {
            currentListId = parseInt(e.target.value);
            const list = collabLists.find(l => l.id === currentListId);
            if (list) {
                updateCollabContext(list);
            }
        }
        loadTasks();
    });

    // Toggle archived tasks
    toggleArchivedBtn.addEventListener('click', () => {
        archivedSection.style.display = archivedSection.style.display === 'none' ? 'block' : 'none';
        if (archivedSection.style.display === 'block') {
            loadArchivedTasks();
        }
    });

    hideArchivedBtn.addEventListener('click', () => {
        archivedSection.style.display = 'none';
    });

    // Create collaborative list
    createCollabBtn.addEventListener('click', () => {
        createCollabModal.style.display = 'block';
    });

    document.getElementById('create-collab-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('collab-list-name-input').value.trim();
        if (!name) return;

        try {
            const res = await fetch('/collab_lists', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const result = await res.json();
            if (result.success) {
                showToast('Collaborative list created!');
                createCollabModal.style.display = 'none';
                document.getElementById('collab-list-name-input').value = '';
                loadCollabLists();
            } else {
                showToast(result.message || 'Failed to create list', 'error');
            }
        } catch (err) {
            showToast('Error creating list', 'error');
            console.error(err);
        }
    });

    // Manage members
    manageMembersBtn.addEventListener('click', () => {
        if (currentListId) {
            loadMembers();
            manageMembersModal.style.display = 'block';
        }
    });

    document.getElementById('add-member-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('member-username').value.trim();
        if (!username) return;

        try {
            const res = await fetch(`/collab_lists/${currentListId}/members`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username_or_email: username })
            });
            const result = await res.json();
            if (result.success) {
                showToast('Member added!');
                document.getElementById('member-username').value = '';
                loadMembers();
            } else {
                showToast(result.message || 'Failed to add member', 'error');
            }
        } catch (err) {
            showToast('Error adding member', 'error');
            console.error(err);
        }
    });

    function updateCollabContext(list) {
        if (!list) {
            collabListInfo.style.display = 'none';
            collabOwnerBadge.textContent = '';
            collabMemberCount.textContent = '';
            collabListName.textContent = '';
            return;
        }
        collabListName.textContent = list.name;
        collabOwnerBadge.textContent = list.is_owner ? 'You own this list' : `Owner: ${list.owner_name || 'Unknown'}`;
        const members = list.member_count || 0;
        collabMemberCount.textContent = `${members} member${members === 1 ? '' : 's'}`;
        collabListInfo.style.display = 'flex';
    }

    function setBoardLoading(active, message) {
        if (!boardLoadingState) return;
        if (active) {
            loadingCounter += 1;
            if (message) {
                boardLoadingMessage.textContent = message;
            }
            boardLoadingState.classList.remove("hidden");
            addBtn.disabled = true;
            addBtn.setAttribute("aria-busy", "true");
        } else {
            loadingCounter = Math.max(0, loadingCounter - 1);
            if (loadingCounter === 0) {
                boardLoadingState.classList.add("hidden");
                boardLoadingMessage.textContent = "Loading your tasks...";
                addBtn.disabled = false;
                addBtn.removeAttribute("aria-busy");
            }
        }
    }

    // Load collaborative lists
    async function loadCollabLists(showLoader = false) {
        if (showLoader) {
            setBoardLoading(true, "Loading collaborative lists...");
        }
        try {
            const res = await fetch('/collab_lists');
            const data = await res.json();
            if (data.success) {
                collabLists = data.lists || [];
                // Update selector
                listSelector.innerHTML = '<option value="personal">Personal Tasks</option>';
                collabLists.forEach(list => {
                    const option = document.createElement('option');
                    option.value = list.id;
                    option.textContent = list.name + (list.is_owner ? ' (Owner)' : '');
                    listSelector.appendChild(option);
                });
                const desiredValue = currentListId ? currentListId.toString() : 'personal';
                const hasOption = Array.from(listSelector.options).some(opt => opt.value === desiredValue);
                if (hasOption) {
                    listSelector.value = desiredValue;
                } else {
                    listSelector.value = 'personal';
                    currentListId = null;
                }
                const activeList = collabLists.find(l => l.id === currentListId);
                updateCollabContext(activeList || null);
            }
        } catch (err) {
            console.error('Error loading collab lists:', err);
        } finally {
            if (showLoader) {
                setBoardLoading(false);
            }
        }
    }

    // Load members for current list
    async function loadMembers() {
        if (!currentListId) return;
        try {
            const res = await fetch(`/collab_lists/${currentListId}`);
            const data = await res.json();
            if (data.success) {
                const membersList = document.getElementById('members-list');
                membersList.innerHTML = '<h3>Members:</h3>';
                data.list.members.forEach(member => {
                    const div = document.createElement('div');
                    div.style.cssText = 'padding: 0.5rem; margin: 0.25rem 0; background: #f3f4f6; border-radius: 0.5rem; display: flex; justify-content: space-between; align-items: center;';
                    const isOwner = member.is_owner || member.id === data.list.owner_id;
                    div.innerHTML = `
                        <span>${escapeHTML(member.name)} (${escapeHTML(member.username)})${isOwner ? ' <strong>[Owner]</strong>' : ''}</span>
                        ${data.list.is_owner && !isOwner ? 
                            `<button class="remove-member-btn" data-member-id="${member.id}" style="background: #e11d48; color: white; border: none; padding: 0.25rem 0.5rem; border-radius: 0.25rem; cursor: pointer;">Remove</button>` : 
                            ''}
                    `;
                    membersList.appendChild(div);
                });
                // Add remove handlers
                document.querySelectorAll('.remove-member-btn').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        const memberId = parseInt(btn.dataset.memberId);
                        try {
                            const res = await fetch(`/collab_lists/${currentListId}/members/${memberId}`, {
                                method: 'DELETE'
                            });
                            const result = await res.json();
                            if (result.success) {
                                showToast('Member removed');
                                loadMembers();
                            } else {
                                showToast(result.message || 'Failed to remove member', 'error');
                            }
                        } catch (err) {
                            showToast('Error removing member', 'error');
                        }
                    });
                });
            }
        } catch (err) {
            console.error('Error loading members:', err);
        }
    }

    // =====================================================
    // ADD NEW TASK
    // =====================================================
    addBtn.addEventListener("click", async () => {
        const title = inputTitle.value.trim();
        const priority = inputPriority.value;
        const dueDate = inputDate.value;

        if (!title) return showToast("Please enter a task title", "error");

        try {
            const taskData = {
                title,
                priority,
                due_date: dueDate || null,
                status: "pending"
            };
            if (currentListId) {
                taskData.collab_list_id = parseInt(currentListId);
            }
            const response = await fetch("/tasks", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(taskData)
            });

            const result = await response.json();
            if (result.success) {
                inputTitle.value = "";
                inputDate.value = "";
                showToast("Task added!");
                loadTasks();
            } else {
                showToast(result.message || "Failed to add task", "error");
            }
        } catch (err) {
            console.error(err);
            showToast("Error adding task", "error");
        }
    });

    // =====================================================
    // LOAD TASKS
    // =====================================================
    async function loadTasks(messageOverride) {
        setBoardLoading(true, messageOverride || (currentListId ? "Loading collaborative tasks..." : "Loading personal tasks..."));
        try {
            let url = "/tasks";
            if (currentListId) {
                url += `?collab_list_id=${currentListId}`;
            }
            const res = await fetch(url);
            const data = await res.json();

            if (!data.success) {
                showToast("Failed to load tasks", "error");
                return;
            }

            allTasks = data.tasks || [];
            renderBoard();

        } catch (err) {
            showToast("Failed to load tasks", "error");
            console.error(err);
        } finally {
            setBoardLoading(false);
        }
    }

    // =====================================================
    // RENDER THE BOARD
    // =====================================================
    function renderBoard() {
        backlogList.innerHTML = "";
        progressList.innerHTML = "";
        completedList.innerHTML = "";

        const backlogTasks = allTasks.filter(t => t.status === "pending");
        const progressTasks = allTasks.filter(t => t.status === "in_progress");
        const completedTasks = allTasks.filter(t => t.status === "completed");

        backlogTasks.forEach(task => {
            const card = createTaskCard(task);
            backlogList.appendChild(card);
        });

        progressTasks.forEach(task => {
            const card = createTaskCard(task);
            progressList.appendChild(card);
        });

        completedTasks.forEach(task => {
            const card = createTaskCard(task);
            completedList.appendChild(card);
        });

        // Add empty states
        if (backlogTasks.length === 0) {
            backlogList.appendChild(createEmptyState("No tasks in backlog", "↓"));
        }
        if (progressTasks.length === 0) {
            progressList.appendChild(createEmptyState("No tasks in progress", "→"));
        }
        if (completedTasks.length === 0) {
            completedList.appendChild(createEmptyState("No completed tasks", "↑"));
        }

        initializeDragDrop(); // enable drag-drop after rendering
    }

    // =====================================================
    // CREATE EMPTY STATE
    // =====================================================
    function createEmptyState(message, icon) {
        const emptyState = document.createElement("div");
        emptyState.className = "empty-state";
        emptyState.setAttribute("data-empty", "true");
        emptyState.innerHTML = `
            <i>${icon}</i>
            <p>${escapeHTML(message)}</p>
        `;
        return emptyState;
    }

    // =====================================================
    // CREATE TASK CARD ELEMENT
    // =====================================================
    function createTaskCard(task) {
        const card = document.createElement("div");
        card.className = `task-card ${(task.priority || 'medium').toLowerCase()}`;
        card.draggable = true;
        card.dataset.taskId = task.id;
        // set an HTML id as a fallback (helps some browsers)
        card.id = `task-${task.id}`;

        const formattedDate = task.due_date
            ? new Date(task.due_date).toLocaleDateString()
            : "No date";

        card.innerHTML = `
            <div class="task-header">
                <span class="task-date">${formattedDate}</span>
                <span class="task-priority-badge ${(task.priority || 'Medium').toLowerCase()}">${escapeHTML(task.priority || 'Medium')}</span>
            </div>

            <p class="task-title">${escapeHTML(task.title)}</p>

            <div class="task-actions">
                ${task.status === 'completed' ? 
                    `<i class="fas fa-archive archive-btn" title="Archive"></i>` : 
                    ''}
                <i class="fas fa-trash delete-btn" title="Delete"></i>
            </div>
        `;

        // DELETE HANDLER
        const delBtn = card.querySelector(".delete-btn");
        delBtn.addEventListener("click", (e) => {
            e.stopPropagation(); // Prevent triggering drag events
            deleteTask(task.id, card);
        });

        // ARCHIVE HANDLER (only for completed tasks)
        if (task.status === 'completed') {
            const archiveBtn = card.querySelector(".archive-btn");
            if (archiveBtn) {
                archiveBtn.addEventListener("click", (e) => {
                    e.stopPropagation(); // Prevent triggering drag events
                    archiveTask(task.id, card);
                });
            }
        }

        return card;
    }

    // =====================================================
    // DELETE TASK + UNDO
    // =====================================================
    async function deleteTask(id, cardElem) {
        // Convert id to string for consistent comparison
        const taskIdStr = id.toString();
        
        // Find the full task data before deleting
        const task = allTasks.find(t => t.id.toString() === taskIdStr);
        if (!task) {
            console.error("Task not found for deletion:", id, "Available tasks:", allTasks);
            showToast("Task not found", "error");
            return;
        }

        // Store full task data for undo
        deletedTaskBackup = task;

        // Immediate UI removal
        if (cardElem && cardElem.parentNode) {
            cardElem.style.transition = "opacity 0.3s ease, transform 0.3s ease";
            cardElem.style.opacity = "0";
            cardElem.style.transform = "scale(0.9)";
            setTimeout(() => {
                if (cardElem.parentNode) {
                    cardElem.parentNode.removeChild(cardElem);
                }
            }, 300);
        }

        // Show undo toast
        showUndoToast();

        // Schedule actual deletion after 5 seconds (unless undone)
        if (deleteTimeout) clearTimeout(deleteTimeout);
        deleteTimeout = setTimeout(async () => {
            if (deletedTaskBackup && deletedTaskBackup.id.toString() === taskIdStr) {
                try {
                    const res = await fetch(`/tasks/${id}`, { method: "DELETE" });
                    const data = await res.json();
                    if (!data.success) {
                        showToast("Delete failed", "error");
                    }
                    deletedTaskBackup = null;
                } catch (err) {
                    showToast("Error deleting task", "error");
                    console.error(err);
                }
            }
        }, 5000);
    }

    // =====================================================
    // ARCHIVE TASK
    // =====================================================
    async function archiveTask(id, cardElem) {
        const taskIdStr = id.toString();
        
        // Find the full task data
        const task = allTasks.find(t => t.id.toString() === taskIdStr);
        if (!task) {
            showToast("Task not found", "error");
            return;
        }

        try {
            const res = await fetch(`/tasks/${id}/archive`, { method: "POST" });
            const data = await res.json();
            
            if (data.success) {
                // Remove card from UI with animation
                if (cardElem && cardElem.parentNode) {
                    cardElem.style.transition = "opacity 0.3s ease, transform 0.3s ease";
                    cardElem.style.opacity = "0";
                    cardElem.style.transform = "scale(0.9)";
                    setTimeout(() => {
                        if (cardElem.parentNode) {
                            cardElem.parentNode.removeChild(cardElem);
                        }
                    }, 300);
                }
                showToast("Task archived!");
                // Reload tasks to update the board
                await loadTasks();
            } else {
                showToast(data.message || "Failed to archive task", "error");
            }
        } catch (err) {
            showToast("Error archiving task", "error");
            console.error(err);
        }
    }

    // =====================================================
    // LOAD ARCHIVED TASKS
    // =====================================================
    async function loadArchivedTasks() {
        try {
            let url = "/tasks?archived_only=true";
            if (currentListId) {
                url += `&collab_list_id=${currentListId}`;
            }
            const res = await fetch(url);
            const data = await res.json();

            if (!data.success) {
                showToast("Failed to load archived tasks", "error");
                return;
            }

            renderArchivedTasks(data.tasks || []);

        } catch (err) {
            showToast("Failed to load archived tasks", "error");
            console.error(err);
        }
    }

    // =====================================================
    // RENDER ARCHIVED TASKS
    // =====================================================
    function renderArchivedTasks(tasks) {
        archivedTasksList.innerHTML = "";

        if (tasks.length === 0) {
            archivedTasksList.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No archived tasks</p>';
            return;
        }

        tasks.forEach(task => {
            const taskCard = createArchivedTaskCard(task);
            archivedTasksList.appendChild(taskCard);
        });
    }

    // =====================================================
    // CREATE ARCHIVED TASK CARD
    // =====================================================
    function createArchivedTaskCard(task) {
        const card = document.createElement("div");
        card.className = "archived-task-card";
        card.dataset.taskId = task.id;

        const formattedDate = task.due_date
            ? new Date(task.due_date).toLocaleDateString()
            : "No date";

        card.innerHTML = `
            <div class="archived-task-content">
                <div class="archived-task-header">
                    <span class="archived-task-priority ${(task.priority || 'Medium').toLowerCase()}">${escapeHTML(task.priority || 'Medium')}</span>
                    <span class="archived-task-date">${formattedDate}</span>
                </div>
                <p class="archived-task-title">${escapeHTML(task.title)}</p>
                <div class="archived-task-status">Status: ${escapeHTML(task.status)}</div>
            </div>
            <div class="archived-task-actions">
                <button class="unarchive-btn" data-task-id="${task.id}" title="Unarchive">
                    <i class="fas fa-undo"></i> Unarchive
                </button>
                <button class="delete-archived-btn" data-task-id="${task.id}" title="Delete">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        `;

        // Unarchive handler
        const unarchiveBtn = card.querySelector(".unarchive-btn");
        unarchiveBtn.addEventListener("click", async () => {
            await unarchiveTask(task.id, card);
        });

        // Delete handler
        const deleteBtn = card.querySelector(".delete-archived-btn");
        try {
            deleteBtn.addEventListener("click", async () => {
            if (confirm("Are you sure you want to permanently delete this archived task?")) {
                await deleteTask(task.id, card);
            }
        });
        }
        catch (err){
            showToast("Unarchive task to delete.", "error");
            console.error(err);
        }

        return card;
    }

    // =====================================================
    // UNARCHIVE TASK
    // =====================================================
    async function unarchiveTask(id, cardElem) {
        try {
            const res = await fetch(`/tasks/${id}/unarchive`, { method: "POST" });
            const data = await res.json();
            
            if (data.success) {
                showToast("Task unarchived!");
                // Remove from archived list
                if (cardElem && cardElem.parentNode) {
                    cardElem.style.transition = "opacity 0.3s ease";
                    cardElem.style.opacity = "0";
                    setTimeout(() => {
                        if (cardElem.parentNode) {
                            cardElem.parentNode.removeChild(cardElem);
                        }
                    }, 300);
                }
                // Reload main tasks to show unarchived task
                await loadTasks();
                // Reload archived tasks
                await loadArchivedTasks();
            } else {
                showToast(data.message || "Failed to unarchive task", "error");
            }
        } catch (err) {
            showToast("Error unarchiving task", "error");
            console.error(err);
        }
    }

    function showUndoToast() {
        undoToast.classList.remove("hidden");

        let counter = 5;
        undoCount.textContent = counter;

        if (undoTimer) clearInterval(undoTimer);
        undoTimer = setInterval(() => {
            counter--;
            undoCount.textContent = counter;
            if (counter <= 0) {
                undoToast.classList.add("hidden");
                clearInterval(undoTimer);
                // Task will be deleted by deleteTimeout if not undone
            }
        }, 1000);
    }

    undoBtn.addEventListener("click", async () => {
        if (!deletedTaskBackup) return;

        // Cancel the scheduled deletion
        if (deleteTimeout) {
            clearTimeout(deleteTimeout);
            deleteTimeout = null;
        }

        clearInterval(undoTimer);
        undoToast.classList.add("hidden");

        // Restore the task in the UI by reloading
        // The task was never actually deleted from the server, so it will reappear
        await loadTasks();
        showToast("Task restored!");
        deletedTaskBackup = null;
    });

    // ============
    // DRAG & DROP
    // ============
    function initializeDragDrop() {
        // Ensure lists exist
        const lists = Array.from(document.querySelectorAll(".kanban-list"));
        if (lists.length === 0) {
            console.warn("No kanban lists found");
            return;
        }

        // Set up drop zone handlers for each list (only once)
        if (!dragDropInitialized) {
            lists.forEach(list => {
                // Prevent default and allow drop
                list.addEventListener("dragover", handleDragOver);
                list.addEventListener("dragenter", handleDragEnter);
                list.addEventListener("dragleave", handleDragLeave);
                list.addEventListener("drop", handleDrop);
            });
            dragDropInitialized = true;
        }

        // Get all task cards and set up drag handlers
        const cards = Array.from(document.querySelectorAll(".task-card"));
        
        cards.forEach(card => {
            card.draggable = true;
            
            // Remove any existing dragstart listeners by cloning
            const newCard = card.cloneNode(true);
            card.parentNode.replaceChild(newCard, card);
        });

        // Re-query cards after cloning
        const freshCards = Array.from(document.querySelectorAll(".task-card"));

        // Set up drag handlers and delete button handlers for each card
        freshCards.forEach(card => {
            card.draggable = true;
            
            // buttons dont work!!??
            // Reattach delete button event listener (lost during cloning)
            const delBtn = card.querySelector(".delete-btn");
            if (delBtn) {
                const taskId = card.dataset.taskId;
                delBtn.addEventListener("click", (e) => {
                    e.stopPropagation(); // Prevent triggering drag events
                    deleteTask(taskId, card);
                });
            }

            // Reattach archive button event listener (lost during cloning)
            const archiveBtn = card.querySelector(".archive-btn");
            if (archiveBtn) {
                const taskId = card.dataset.taskId;
                archiveBtn.addEventListener("click", (e) => {
                    e.stopPropagation(); // Prevent triggering drag events
                    archiveTask(taskId, card);
                });
            }
            
            card.addEventListener("dragstart", (e) => {
                const taskId = card.dataset.taskId;                        
                if (!taskId) {
                    console.error("Card missing task ID:", card);
                    e.preventDefault();
                    return;
                }

                // Store task ID in dataTransfer for retrieval on drop
                try {
                    e.dataTransfer.effectAllowed = "move";
                    e.dataTransfer.setData("text/plain", taskId);
                    e.dataTransfer.setData("text/html", taskId); // Fallback for some browsers
                } catch (err) {
                    console.warn("Error setting drag data:", err);
                }
                
                card.classList.add("dragging"); //draggging class for visual feedback
                
                // Store current status for later comparison
                const currentTask = allTasks.find(t => t.id.toString() === taskId);
                if (currentTask) {
                    card.dataset.currentStatus = currentTask.status;
                }
            });

            card.addEventListener("dragend", (e) => {
                card.classList.remove("dragging");
                // Clean up drag-over classes from all lists
                const allLists = Array.from(document.querySelectorAll(".kanban-list"));
                allLists.forEach(l => {
                    l.classList.remove("drag-over");
                    const placeholder = l.querySelector(".drag-placeholder");
                    if (placeholder) {
                        placeholder.remove();
                    }
                });
            });
        });
    }

    // Drop zone event handlers
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        e.dataTransfer.dropEffect = "move";
        
        const list = e.currentTarget;
        list.classList.add("drag-over");

                // Visual feedback: show where the card will be inserted
                const dragging = document.querySelector(".task-card.dragging");
                if (dragging) {
                    // Remove empty state if present
                    const emptyState = list.querySelector("[data-empty='true']");
                    if (emptyState) {
                        emptyState.style.display = "none";
                    }
                    
                    const placeholder = list.querySelector(".drag-placeholder");
                    const afterElement = getDragAfterElement(list, e.clientY);
                    
                    // Remove existing placeholder
                    if (placeholder) {
                        placeholder.remove();
                    }
                    
                    // Insert placeholder at the correct position
                    const placeholderEl = document.createElement("div");
                    placeholderEl.className = "drag-placeholder";
                    
                    if (afterElement == null) {
                        // Insert at the end (but before empty state if it exists)
                        if (emptyState && emptyState.style.display !== "none") {
                            list.insertBefore(placeholderEl, emptyState);
                        } else {
                            list.appendChild(placeholderEl);
                        }
                    } else {
                        // Insert before the afterElement
                        list.insertBefore(placeholderEl, afterElement);
                    }
                }
    }

    function handleDragEnter(e) {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.add("drag-over");
    }

    function handleDragLeave(e) {
        const list = e.currentTarget;
        const rect = list.getBoundingClientRect();
        const x = e.clientX;
        const y = e.clientY;
        
        // Check if we're leaving the list bounds
        if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
            list.classList.remove("drag-over");
            const placeholder = list.querySelector(".drag-placeholder");
            if (placeholder) {
                placeholder.remove();
            }
            // Show empty state again if list is empty
            const emptyState = list.querySelector("[data-empty='true']");
            if (emptyState && list.querySelectorAll('.task-card').length === 0) {
                emptyState.style.display = "";
            }
        }
    }

    async function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const list = e.currentTarget;
        list.classList.remove("drag-over");
        
        // Remove placeholder
        const placeholder = list.querySelector(".drag-placeholder");
        if (placeholder) {
            placeholder.remove();
        }

        // Retrieve task ID from dataTransfer
        let taskId = null;
        try {
            taskId = e.dataTransfer.getData("text/plain") || e.dataTransfer.getData("text/html");
        } catch (err) {
            console.warn("Error getting drag data:", err);
        }

        // Fallback: find the element with dragging class
        if (!taskId) {
            const draggingEl = document.querySelector(".task-card.dragging");
            if (draggingEl) {
                taskId = draggingEl.dataset.taskId;
            }
        }

        if (!taskId) {
            console.error("Could not get task ID from drop event");
            return;
        }

        // Find the card element
        const card = document.querySelector(`[data-task-id="${taskId}"]`);
        if (!card) {
            console.error("Could not find card element for task:", taskId);
            return;
        }

        // Get current status
        const currentStatus = card.dataset.currentStatus || 
            (allTasks.find(t => t.id.toString() === taskId)?.status);

        // Determine new status based on the target list
        let newStatus = "pending"; // default to backlog
        if (list.id === "progress-list") {
            newStatus = "in_progress";
        } else if (list.id === "completed-list") {
            newStatus = "completed";
        } else if (list.id === "backlog-list") {
            newStatus = "pending";
        }

        console.log(`Dropping task ${taskId} from ${currentStatus} to ${newStatus} in list ${list.id}`);

        // Check if status actually changed
        if (currentStatus === newStatus) {
            // Status didn't change, just move the card visually within the same list
            const afterElement = getDragAfterElement(list, e.clientY);
            if (card.parentNode !== list) {
                if (afterElement == null) {
                    list.appendChild(card);
                } else {
                    list.insertBefore(card, afterElement);
                }
            }
            return;
        }

        // Move card to new list immediately for better UX
        if (card.parentNode !== list) {
            const afterElement = getDragAfterElement(list, e.clientY);
            if (afterElement == null) {
                list.appendChild(card);
            } else {
                list.insertBefore(card, afterElement);
            }
        }

        // Update status on server
        try {
            const res = await fetch(`/tasks/${taskId}/status`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: newStatus })
            });

            const data = await res.json();
            if (data.success) {
                // Format status name for display
                const statusNames = {
                    "pending": "Backlogs",
                    "in_progress": "In Progress",
                    "completed": "Completed"
                };
                showToast(`Task moved to ${statusNames[newStatus] || newStatus}`);
                // Refresh tasks to sync with server
                await loadTasks();
            } else {
                showToast(data.message || "Failed to update status", "error");
                // Reload to revert visual state
                await loadTasks();
            }
        } catch (err) {
            console.error("Update status error:", err);
            showToast("Network error updating status", "error");
            // Reload to revert UI to server state
            await loadTasks();
        }
    }

    // Helper: find the card after the current pointer inside a list (for ordered insert)
    function getDragAfterElement(container, y) {
        // Get all task cards, excluding the dragging one, placeholders, and empty states
        const draggableElements = [...container.querySelectorAll('.task-card:not(.dragging):not([data-empty])')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element || null;
    }

    // =====================================================
    // SMALL UTILITIES
    // =====================================================
    function escapeHTML(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function showToast(message, type = "success") {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => toast.classList.add("show"), 15);

        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

});
