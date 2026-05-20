from flask import Flask, request, redirect, render_template_string
import sqlite3
import pandas as pd
import os
import PyPDF2

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("hr.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT,
            dept TEXT,
            salary TEXT,
            status TEXT
        )
        ''')

        conn.execute('''
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate TEXT,
            role TEXT,
            date TEXT,
            status TEXT
        )
        ''')
        conn.commit()

init_db()

# ---------------- AI RESUME SCORING ----------------
def analyze_resume(filepath):
    text = ""
    with open(filepath, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for p in reader.pages:
            if p.extract_text():
                text += p.extract_text()

    text = text.lower()

    skills = {
        'python': 15,
        'machine learning': 20,
        'ai': 15,
        'sql': 10,
        'flask': 10,
        'data science': 15,
        'communication': 10,
        'leadership': 5
    }

    score = 0
    matched = []

    for k, v in skills.items():
        if k in text:
            matched.append(k)
            score += v

    score = min(score, 100)

    if score >= 75:
        result = "Strong Candidate"
    elif score >= 50:
        result = "Good Candidate"
    else:
        result = "Needs Improvement"

    return result, matched, score

# ---------------- EXCEL IMPORT ----------------
def import_excel(file_path):
    df = pd.read_excel(file_path)
    conn = get_db()
    count = 0

    for _, row in df.iterrows():
        conn.execute('''
        INSERT INTO employees VALUES (?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
        name=excluded.name,
        dept=excluded.dept,
        salary=excluded.salary,
        status=excluded.status
        ''', (
            str(row['id']),
            str(row['name']),
            str(row['dept']),
            str(row['salary']),
            str(row['status'])
        ))
        count += 1

    conn.commit()
    return count

# ---------------- UI TEMPLATE ----------------
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
<title>HR Analytics Platform</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body { background:#f5f7ff; font-family: Arial; }

.sidebar {
    width:250px;
    height:100vh;
    position:fixed;
    background:#0f172a;
    padding:20px;
    color:white;
}

.sidebar h3 { color:#60a5fa; font-weight:700; }

.sidebar a {
    display:block;
    padding:10px;
    margin:6px 0;
    color:#cbd5e1;
    text-decoration:none;
    border-radius:8px;
}

.sidebar a:hover { background:#1e293b; color:white; }

.main {
    margin-left:270px;
    padding:25px;
}

.kpi-card {
    background:white;
    padding:18px;
    border-radius:16px;
    box-shadow:0 8px 25px rgba(0,0,0,0.06);
}

.section-title {
    font-size:24px;
    font-weight:700;
    margin-bottom:15px;
}
</style>
</head>

<body>

<div class="sidebar">
<h3>HR PRO AI</h3>

<a href="/">📊 Dashboard</a>
<a href="/employees">👨‍💼 Employees</a>
<a href="/interviews">📅 Interviews</a>
<a href="/screening">🤖 AI Screening</a>
<a href="/import">📂 Excel Import</a>

</div>

<div class="main">
{{content|safe}}
</div>

</body>
</html>
'''

# ---------------- DASHBOARD ----------------
@app.route('/')
def dashboard():
    conn = get_db()
    emp = conn.execute("SELECT * FROM employees").fetchall()
    ints = conn.execute("SELECT * FROM interviews").fetchall()

    active = len([e for e in emp if e['status'] == "Active"])
    inactive = len(emp) - active

    scheduled = len([i for i in ints if i['status'] == "Scheduled"])
    completed = len([i for i in ints if i['status'] == "Completed"])

    content = f'''
    <div class="section-title">📊 Dashboard</div>

    <div class="row g-3 mb-4">
        <div class="col-md-3"><div class="kpi-card">Employees <h3>{len(emp)}</h3></div></div>
        <div class="col-md-3"><div class="kpi-card">Active <h3>{active}</h3></div></div>
        <div class="col-md-3"><div class="kpi-card">Scheduled <h3>{scheduled}</h3></div></div>
        <div class="col-md-3"><div class="kpi-card">Completed <h3>{completed}</h3></div></div>
    </div>

    <div class="row">
        <div class="col-md-6"><div class="kpi-card"><canvas id="empChart"></canvas></div></div>
        <div class="col-md-6"><div class="kpi-card"><canvas id="intChart"></canvas></div></div>
    </div>

    <script>
    new Chart(document.getElementById('empChart'), {{
        type:'doughnut',
        data:{{
            labels:['Active','Inactive'],
            datasets:[{{data:[{active},{inactive}], backgroundColor:['green','red']}}]
        }}
    }});

    new Chart(document.getElementById('intChart'), {{
        type:'bar',
        data:{{
            labels:['Scheduled','Completed'],
            datasets:[{{data:[{scheduled},{completed}], backgroundColor:'blue'}}]
        }}
    }});
    </script>
    '''

    return render_template_string(BASE_TEMPLATE, content=content)

# ---------------- EMPLOYEES ----------------
@app.route('/employees', methods=['GET','POST'])
def employees():
    conn = get_db()

    if request.method == 'POST':
        conn.execute('''
        INSERT INTO employees VALUES (?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
        name=excluded.name,
        dept=excluded.dept,
        salary=excluded.salary,
        status=excluded.status
        ''', (
            request.form['id'],
            request.form['name'],
            request.form['dept'],
            request.form['salary'],
            request.form['status']
        ))
        conn.commit()

    data = conn.execute("SELECT * FROM employees").fetchall()

    content = '''
    <div class="section-title">Employees</div>

    <form method="POST" class="row g-2 mb-3">
        <input class="form-control col" name="id" placeholder="ID">
        <input class="form-control col" name="name" placeholder="Name">
        <input class="form-control col" name="dept" placeholder="Dept">
        <input class="form-control col" name="salary" placeholder="Salary">
        <select class="form-control col" name="status">
            <option>Active</option>
            <option>Inactive</option>
        </select>
        <button class="btn btn-primary col">Add</button>
    </form>

    <table class="table table-hover">
    <tr><th>ID</th><th>Name</th><th>Dept</th><th>Status</th><th>Action</th></tr>
    '''

    for e in data:
        content += f'''
        <tr>
        <td>{e['id']}</td>
        <td>{e['name']}</td>
        <td>{e['dept']}</td>
        <td>{e['status']}</td>
        <td><a href="/delete_emp/{e['id']}" class="btn btn-danger btn-sm">Delete</a></td>
        </tr>
        '''

    content += "</table>"
    return render_template_string(BASE_TEMPLATE, content=content)

# ---------------- INTERVIEWS ----------------
@app.route('/interviews', methods=['GET','POST'])
def interviews():
    conn = get_db()

    if request.method == 'POST':
        conn.execute("INSERT INTO interviews (candidate, role, date, status) VALUES (?,?,?,?)",
                     (request.form['candidate'], request.form['role'],
                      request.form['date'], request.form['status']))
        conn.commit()

    data = conn.execute("SELECT * FROM interviews").fetchall()

    content = '''
    <div class="section-title">Interviews</div>

    <form method="POST" class="row g-2 mb-3">
        <input class="form-control col" name="candidate" placeholder="Candidate">
        <input class="form-control col" name="role" placeholder="Role">
        <input class="form-control col" type="date" name="date">
        <select class="form-control col" name="status">
            <option>Scheduled</option>
            <option>Completed</option>
        </select>
        <button class="btn btn-success col">Add</button>
    </form>

    <table class="table table-bordered">
    <tr><th>Name</th><th>Role</th><th>Date</th><th>Status</th></tr>
    '''

    for i in data:
        content += f'''
        <tr>
        <td>{i['candidate']}</td>
        <td>{i['role']}</td>
        <td>{i['date']}</td>
        <td>{i['status']}</td>
        </tr>
        '''

    content += "</table>"
    return render_template_string(BASE_TEMPLATE, content=content)

# ---------------- SCREENING ----------------
@app.route('/screening', methods=['GET','POST'])
def screening():
    result, matched, score = "", [], 0

    if request.method == 'POST':
        file = request.files['resume']
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        result, matched, score = analyze_resume(path)

    content = f'''
    <div class="section-title">AI Resume Screening</div>

    <div class="kpi-card">
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="resume" class="form-control mb-2">
            <button class="btn btn-primary">Analyze</button>
        </form>

        <hr>
        <h4>{result}</h4>
        <p>Score: {score}/100</p>
        <p>Skills: {", ".join(matched)}</p>

        <canvas id="scoreChart"></canvas>
    </div>

    <script>
    new Chart(document.getElementById('scoreChart'), {{
        type:'bar',
        data:{{
            labels:['Score'],
            datasets:[{{data:[{score}], backgroundColor:'blue'}}]
        }},
        options:{{scales:{{y:{{beginAtZero:true, max:100}}}}}}
    }});
    </script>
    '''

    return render_template_string(BASE_TEMPLATE, content=content)

# ---------------- DELETE ----------------
@app.route('/delete_emp/<id>')
def delete_emp(id):
    conn = get_db()
    conn.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    return redirect('/employees')

# ---------------- EXCEL IMPORT ----------------
@app.route('/import', methods=['GET','POST'])
def import_page():
    msg = ""

    if request.method == 'POST':
        file = request.files['file']
        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)
        count = import_excel(path)
        msg = f"{count} employees imported"

    content = f'''
    <div class="section-title">Excel Import</div>

    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" class="form-control mb-2">
        <button class="btn btn-success">Upload</button>
    </form>

    <h5>{msg}</h5>
    '''

    return render_template_string(BASE_TEMPLATE, content=content)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)