TODO - Productivity Web App
Your trusty productivity buddy.

Creator: Eleah Joy Melchor
Access online: https://todobuddy-51zz.onrender.com

TODO is a full-stack web application for managing personal and collaborative tasks. It features a Kanban board interface where users can easily drag and drop todos according to the current status — backlogs, in progress, or completed. This web application is built with Flask and vanilla Javascript.

=============
  Features
=============

Task Management
-> Kanban Board: A visual task management with three columns (Backlogs, In Progress, Completed)
-> Drag and Drop: Features an intuitive drag-and-drop interface to move tasks between status columns
-> Task Properties:
	- Title, priority (High/Medium/Low)
	- Due dates
	- Status
-> Task archiving: Features a soft delete functionality to archive completed tasks
-> Undo Delete: 5-second window to undo accident task deletions
-> Search: Search tasks by title

=======================
  Collaborative Lists
=======================
-> Collaborate with friends toi create collaborative todo lists together
-> Invite friends as members by username or email
-> Manage members (add/remove)
-> Tasks can belong to personal lists or collaborative lists

=======================
  User Authentication
=======================
-> User signup and login
-> Password reset uses via email token
-> Session-based authentication
-> User profiles

==============
  Teck Stack 
==============

-> Backend
	- Flask: Python web framework
	- SQLite: Database
	- Flask-Bcrypt: Password hashing
	- Flask-CORS: Cross-origin resource sharing
-> Frontend
	- HTML5/CSS3: Structure and styling
	- Vanilla Javascript: No framework, pure JS for drag-and-drop and API calls
	- Font Awesome: Icons

===================
Project Structure
===================
```
cmsc128-IndivProject_Melchor/
├── app.py                 # Main Flask application
├── database.py            # User database operations
├── tasks.py               # Task database operations
├── collab_lists.py        # Collaborative list database operations
├── collab_members.py      # Collaborative member database operations
├── requirements.txt       # Python dependencies
│
├── routes/
│   ├── auth_routes.py     # Authentication endpoints
│   ├── task_routes.py     # Task API endpoints
│   └── collab_routes.py   # Collaborative list endpoints
│
├── templates/
│   ├── base.html          # Base template
│   ├── login.html         # Login page
│   ├── signup.html        # Registration page
│   ├── tasks.html         # Main Kanban board page
│   ├── profile.html       # User profile page
│   ├── forgot_password.html
│   ├── reset_password.html
│   └── logout.html
│
├── static/
│   ├── js/
│   │   └── tasks.js       # Frontend JavaScript (drag-drop, API calls)
│   ├── style.css          # Stylesheet
│   └── todo.png           # Assets
│
├── database.db            # Users database
├── tasks.db               # Tasks database
├── collab_lists.db        # Collaborative lists database
└── collab_members.db      # Collaborative members database
```

=====================
Future Improvements
=====================

Potential improvements:
- Email notifications for task assignments
- Task comments and attachments
- Task due date reminders
- Export tasks to CSV/PDF
- Dark mode theme
- Mobile responsive improvements
- Real-time updates with WebSockets

========
License
========

This project is part of CMSC 128 Individual Project.
