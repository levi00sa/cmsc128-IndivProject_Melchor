# Task Management System

A full-stack web application for managing personal and collaborative tasks with a Kanban board interface. Built with Flask and vanilla JavaScript.

## Features

### Task Management
- **Kanban Board**: Visual task management with three columns (Backlogs, In Progress, Completed)
- **Drag & Drop**: Intuitive drag-and-drop interface to move tasks between status columns
- **Task Properties**: 
  - Title, description, priority (High/Medium/Low)
  - Due dates
  - Status tracking
- **Task Archiving**: Soft delete functionality to archive completed tasks
- **Undo Delete**: 5-second window to undo task deletions
- **Search**: Search tasks by title or description

### Collaborative Lists
- Create collaborative task lists
- Invite members by username or email
- Manage members (add/remove)
- Tasks can belong to personal lists or collaborative lists

### User Authentication
- User registration and login
- Password reset via email token
- Session-based authentication
- User profiles

## Tech Stack

### Backend
- **Flask**: Python web framework
- **SQLite**: Database (multiple databases for separation of concerns)
- **Flask-Bcrypt**: Password hashing
- **Flask-CORS**: Cross-origin resource sharing

### Frontend
- **HTML5/CSS3**: Structure and styling
- **Vanilla JavaScript**: No frameworks, pure JS for drag-and-drop and API calls
- **Font Awesome**: Icons

## Project Structure

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

## Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository** (or navigate to the project directory)

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**:
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the application**:
   - Open your browser and navigate to `http://localhost:5002`

## Database Schema

### Users Table (`database.db`)
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email
- `password_hash`: Bcrypt hashed password
- `name`: User's display name
- `reset_token`: Password reset token
- `reset_token_expires`: Token expiration time
- `created_at`: Account creation timestamp

### Tasks Table (`tasks.db`)
- `id`: Primary key
- `user_id`: Foreign key to users table
- `title`: Task title (required)
- `description`: Task description (optional)
- `priority`: High/Medium/Low (default: Medium)
- `status`: pending/in_progress/completed (default: pending)
- `due_date`: Task due date (optional)
- `created_at`: Task creation timestamp
- `updated_at`: Last update timestamp
- `collab_list_id`: Foreign key to collab_lists (NULL for personal tasks)
- `archived`: 0 or 1 (soft delete flag)

### Collaborative Lists Table (`collab_lists.db`)
- `id`: Primary key
- `name`: List name
- `owner_id`: Foreign key to users table
- `created_at`: List creation timestamp

### Collaborative Members Table (`collab_members.db`)
- `id`: Primary key
- `collab_list_id`: Foreign key to collab_lists
- `user_id`: Foreign key to users table
- Unique constraint on (collab_list_id, user_id)

## API Endpoints

### Authentication (`/auth`)
- `POST /auth/signup` - Register new user
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/forgot_password` - Request password reset
- `POST /auth/reset_password` - Reset password with token
- `GET /auth/profile` - Get user profile

### Tasks (`/tasks`)
- `GET /tasks` - Get all tasks (supports query params: status, priority, search, collab_list_id, include_archived, archived_only)
- `POST /tasks` - Create new task
- `GET /tasks/<id>` - Get specific task
- `PUT /tasks/<id>` - Update task
- `DELETE /tasks/<id>` - Delete task
- `PUT /tasks/<id>/status` - Update task status only
- `POST /tasks/<id>/archive` - Archive task
- `POST /tasks/<id>/unarchive` - Unarchive task
- `GET /my-tasks` - Render tasks page

### Collaborative Lists (`/collab_lists`)
- `GET /collab_lists` - Get all collaborative lists for user
- `POST /collab_lists` - Create new collaborative list
- `GET /collab_lists/<id>` - Get specific list with members
- `PUT /collab_lists/<id>` - Update list
- `DELETE /collab_lists/<id>` - Delete list
- `POST /collab_lists/<id>/members` - Add member to list
- `DELETE /collab_lists/<id>/members/<member_id>` - Remove member from list

## Usage

### Creating Tasks
1. Log in to your account
2. Enter a task title in the input field
3. (Optional) Select priority and due date
4. Click "Add Task"
5. Task appears in the "BACKLOGS" column

### Managing Tasks
- **Move tasks**: Drag and drop tasks between columns to change status
- **Delete tasks**: Click the trash icon (5-second undo available)
- **Archive tasks**: Click the archive icon on completed tasks
- **View archived**: Click "Archived" button to view archived tasks

### Collaborative Lists
1. Click "New" button next to the list selector
2. Enter a list name and create
3. Select the list from the dropdown
4. Click "Members" to manage list members
5. Add members by username or email
6. Tasks created while a collaborative list is selected will belong to that list

## Architecture

The application follows a **3-layer architecture**:

1. **Frontend Layer** (`templates/` + `static/js/`)
   - HTML templates with Jinja2
   - JavaScript for interactivity and API communication
   - CSS for styling

2. **API Layer** (`routes/`)
   - Flask blueprints for route organization
   - Request validation and authentication
   - JSON responses

3. **Database Layer** (`*.py` files)
   - SQLite database operations
   - Data access functions
   - Database initialization

## Security Features

- Password hashing with Bcrypt
- Session-based authentication
- Access control for tasks (users can only access their own tasks or collaborative lists they're members of)
- SQL injection prevention (parameterized queries)
- XSS prevention (HTML escaping in templates)

## Development Notes

- The application runs on port **5002** by default
- Debug mode is enabled in `app.py` (change for production)
- Database files are created automatically on first run
- All routes except `/` and `/auth/*` require authentication

## Future Enhancements

Potential improvements:
- Email notifications for task assignments
- Task comments and attachments
- Task due date reminders
- Export tasks to CSV/PDF
- Dark mode theme
- Mobile responsive improvements
- Real-time updates with WebSockets

## License

This project is part of CMSC 128 Individual Project.

## Author

Eleah Joy Melchor

---

**Note**: This is a development project. For production use, consider:
- Changing the secret key in `app.py`
- Using environment variables for configuration
- Implementing proper email service for password resets
- Adding rate limiting and additional security measures
- Using a production-grade database (PostgreSQL, MySQL)
