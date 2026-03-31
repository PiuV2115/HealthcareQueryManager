Title : Smart Healthcare Queue Management System with Real-Time Monitoring
1. Overview

The Smart Healthcare Queue Management System is a digital solution designed to streamline patient flow in hospitals and clinics. It replaces traditional manual queue systems with an automated, real-time platform that improves efficiency, reduces waiting time, and enhances patient experience.

Patients can generate tokens either manually or through QR code scanning, while administrators manage the queue using a centralized dashboard. The system provides real-time updates on the current serving patient, upcoming queue, and overall statistics.

By integrating a clean user interface with a lightweight backend, the system ensures smooth operation even in small-scale healthcare setups without requiring complex infrastructure.

⚙️ 2. Tech Stack & Tools
💻 Frontend
HTML5
CSS3 (Responsive UI, animations)
JavaScript (Fetch API, DOM manipulation)
🧠 Backend
Python (Flask Framework)
🗄️ Database
SQLite (Built-in lightweight database)
📊 Libraries & Tools
Chart.js → For analytics visualization
Fetch API → For real-time communication
QR Code Generator (optional module/page)
🛠️ Development Tools
VS Code / PyCharm
Browser (Chrome/Edge)
Python 3.x
🧰 3. Installation & Setup
✅ Step 1: Install Python

Download and install Python (3.x)
👉 https://www.python.org/downloads/

✅ Step 2: Install Required Libraries

Open terminal in your project folder:

pip install flask

(If using charts or extras, no backend install needed for Chart.js)

✅ Step 3: Project Structure

Make sure your project looks like this:

Queue_Management/
│
├── app.py
├── queue.db
├── templates/
│   ├── index.html
│   ├── admin.html
│   ├── queue_status.html
│   └── qrpage.html

✅ Step 4: Run the Application
python app.py

You will see:

Running on http://127.0.0.1:5000/

Open browser and go to:

http://127.0.0.1:5000

🔄 4. System Workflow
👤 Patient Side
User enters name or scans QR
Token is generated
User is redirected to queue status page
Sees:
Current serving patient
People ahead
Estimated waiting time
👨‍⚕️ Admin Side
Admin opens dashboard
Can perform:
✅ Call Next Patient
❌ Cancel Token
✔ Mark Completed
Dashboard updates in real-time
Analytics chart shows visitor trends

✨ 5. Key Features
Real-time queue updates
Token-based patient management
Admin control panel with full access
Cancel & complete functionality
Clean and responsive UI/UX
Lightweight SQLite database
Analytics using charts
QR-based token generation (optional)
🚀 6. Future Enhancements (Optional for Viva 💯)
SMS/WhatsApp notification for patients
Estimated waiting time using AI
Multi-doctor queue handling
Cloud database (MySQL/Firebase)
Mobile app integration

1. System Architecture Diagram
📌 Explanation (Simple)

Your system follows a 3-tier architecture:

Presentation Layer (Frontend) → HTML, CSS, JS
Application Layer (Backend) → Flask (Python)
Data Layer (Database) → SQLite


🧠 Architecture Diagram (Concept)
<img width="1400" height="931" alt="image" src="https://github.com/user-attachments/assets/3b9bb177-0950-4e87-9c07-23e2a4b92c6f" />
✍️ How to Draw (Step-by-Step for Exam)

Draw 3 blocks:

1️⃣ Client Layer (Top / Left)
Browser (User)
Pages:
Index Page
Queue Status Page
Admin Dashboard

⬇ (HTTP Requests)

2️⃣ Server Layer (Middle)
Flask Backend
APIs:
/token → Generate token
/queue → Get queue
/current → Current serving
/next → Call next
/delete/<id> → Cancel
/complete → Mark completed

⬇ (SQL Queries)

3️⃣ Database Layer (Bottom / Right)
SQLite Database
Tables:
queue / tokens

🗄️ 2. ER Diagram (Entity Relationship Diagram)

<img width="1004" height="646" alt="image" src="https://github.com/user-attachments/assets/cdeb2a61-51f5-45d7-bb24-bd3d63e6aa63" />

📌 Main Entity: Token / Patient Queue
🧠 ER Diagram Visualization
✍️ How to Draw ER Diagram
🎯 Entity: Tokens (or Queue)

Draw a rectangle:

TOKENS
📋 Attributes (Draw as ovals)

Connect these to TOKENS:

id (Primary Key) 🔑
token

name
status (pending / completed / canceled)
timestamp
✅ Primary Key
id → underline it

💡 ER Diagram Meaning
Each token represents one patient
No relationships needed (simple system)
If expanded → you can add:
Doctor entity
Appointment entity
