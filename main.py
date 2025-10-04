from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

JSON_DIR = Path(__file__).parent / "json"
REPORTS_DIR = Path(__file__).parent / "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# -------------------- Helper Functions --------------------
def load_json(file_name: str) -> Dict | List:
    file_path = JSON_DIR / f"{file_name}.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {} if file_name == "users" else []

def save_json(file_name: str, data: Dict | List):
    file_path = JSON_DIR / f"{file_name}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# -------------------- Auth --------------------
async def get_current_user(request: Request):
    auth = request.cookies.get("auth")
    if not auth:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        username, role = auth.split(":")
        users = load_json("users")
        if username in users and users[username]["role"] == role:
            return {"username": username, "role": role}
    except:
        raise HTTPException(status_code=401, detail="Invalid auth")
    raise HTTPException(status_code=401, detail="Invalid auth")

# -------------------- Routes --------------------
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    users = load_json("users")
    if username in users and users[username]["password"] == password:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="auth", value=f"{username}:{users[username]['role']}")
        return response
    raise HTTPException(status_code=401, detail="Ном ё пароли нодуруст")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: Dict = Depends(get_current_user)):
    if current_user["role"] == "admin":
        return templates.TemplateResponse("admin_dashboard.html", {"request": request})
    elif current_user["role"] == "director":
        return templates.TemplateResponse("director_dashboard.html", {"request": request})
    raise HTTPException(status_code=403, detail="Дастрасӣ манъ аст")

# -------------------- API Endpoints --------------------
@app.get("/api/courses")
async def get_courses(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои админ ва директор дастрас аст")
    return load_json("courses")

@app.get("/api/groups")
async def get_groups(course_id: int = None, current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои админ ва директор дастрас аст")
    groups = load_json("groups")
    if course_id:
        groups = [g for g in groups if g["course_id"] == course_id]
    return groups

@app.get("/api/students")
async def get_students(group_id: int = None, current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои админ ва директор дастрас аст")
    students = load_json("students")
    if group_id:
        students = [s for s in students if s["group_id"] == group_id]
    return students

@app.get("/api/students/all")
async def get_all_students(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "director"]:
        raise HTTPException(status_code=403, detail="Дастрасӣ манъ аст")
    return load_json("students")

@app.post("/api/attendance")
async def record_attendance(
    date: str = Form(...),
    group_id: int = Form(...),
    present_students: str = Form(...),
    current_user: Dict = Depends(get_current_user)
):
    if current_user["role"] not in ["admin", "director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои админ ва директор дастрас аст")

    attendance = load_json("attendance")
    students = load_json("students")
    group_students = [s["id"] for s in students if s["group_id"] == group_id]

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=422, detail="Санаи нодуруст")

    if not group_id or not any(g["id"] == group_id for g in load_json("groups")):
        raise HTTPException(status_code=422, detail="Гурӯҳи интихобшуда вуҷуд надорад")

    present_students_list = []
    if present_students:
        try:
            present_students_list = [int(id) for id in present_students.split(",") if id and int(id) in group_students]
        except ValueError:
            raise HTTPException(status_code=422, detail="Нодурустии формати ID-ҳои донишҷӯён")

    # Update existing
    existing_attendance = [
        a for a in attendance if a.get("group_id") == group_id and a["date"] == date
    ]
    if existing_attendance:
        for record in attendance:
            if record.get("group_id") == group_id and record["date"] == date:
                record["status"] = "present" if record["student_id"] in present_students_list else "absent"
        save_json("attendance", attendance)
        return {"status": "updated", "message": f"Ҳузур барои гурӯҳ {group_id} дар сана {date} навсозӣ шуд!"}

    # Insert new
    for student_id in group_students:
        status = "present" if student_id in present_students_list else "absent"
        attendance.append({
            "student_id": student_id,
            "date": date,
            "status": status,
            "score": 0,
            "teacher_id": 1,
            "group_id": group_id
        })
    save_json("attendance", attendance)
    return {"status": "success", "message": f"Ҳузур барои гурӯҳ {group_id} дар сана {date} бо муваффақият захира шуд!"}

@app.get("/api/attendance/today")
async def get_attendance_today(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои админ ва директор дастрас аст")
    today = datetime.now().strftime("%Y-%m-%d")
    attendance = load_json("attendance")
    students = load_json("students")
    filtered_attendance = [a for a in attendance if a["date"] == today]
    for a in filtered_attendance:
        student = next((s for s in students if s["id"] == a["student_id"]), None)
        if student:
            a["name"] = student["name"]
            a["group_id"] = student["group_id"]
            a["course_id"] = student["course_id"]
    return filtered_attendance

@app.get("/api/attendance/all")
async def get_all_attendance(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои админ ва директор дастрас аст")
    attendance = load_json("attendance")
    students = load_json("students")
    for a in attendance:
        student = next((s for s in students if s["id"] == a["student_id"]), None)
        if student:
            a["name"] = student["name"]
            a["group_id"] = student["group_id"]
            a["course_id"] = student["course_id"]
    return attendance

@app.get("/api/absent_students/today")
async def get_absent_students_today(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои директор дастрас аст")

    print(current_user)  # Debug: Check user role
    attendance = load_json("attendance")
    students = load_json("students")
    groups = load_json("groups")
    courses = load_json("courses")
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Checking absent students for date: {today}")  # Debug: Verify date
    problem = []

    for student in students:
        absent_today = [a for a in attendance if a["student_id"] == student["id"] and a["date"] == today and a["status"] == "absent"]
        if absent_today:
            total_absences = len([a for a in attendance if a["student_id"] == student["id"] and a["status"] == "absent"])
            student_info = {
                "name": student["name"],
                "group_number": next((g["number"] for g in groups if g["id"] == student["group_id"]), "Unknown"),
                "course_id": student["course_id"],
                "total_absences": total_absences
            }
            problem.append(student_info)

    print(f"Found {len(problem)} absent students")  # Debug: Check result count
    return problem

@app.get("/api/absent_summary")
async def get_absent_summary(period: str = "weekly", current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои директор дастрас аст")

    attendance = load_json("attendance")
    students = load_json("students")
    groups = load_json("groups")
    courses = load_json("courses")

    if period == "weekly":
        days_back = 7
    elif period == "monthly":
        days_back = 30
    else:
        raise HTTPException(status_code=400, detail="Период нодуруст: weekly ё monthly")

    start_date = datetime.now() - timedelta(days=days_back)
    start_date_str = start_date.strftime("%Y-%m-%d")

    summary = []

    for student in students:
        absent_dates = [a["date"] for a in attendance if a["student_id"] == student["id"] and a["status"] == "absent" and a["date"] >= start_date_str]
        absent_count = len(set(absent_dates))  # Unique days absent

        if absent_count > 0:
            student_info = {
                "name": student["name"],
                "group_number": next((g["number"] for g in groups if g["id"] == student["group_id"]), "Unknown"),
                "course_id": student["course_id"],
                "absent_count": absent_count
            }
            summary.append(student_info)

    summary.sort(key=lambda x: x["absent_count"], reverse=True)
    return summary

@app.get("/api/generate_monthly_report")
async def generate_monthly_report(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["director"]:
        raise HTTPException(status_code=403, detail="Танҳо барои директор дастрас аст")

    attendance = load_json("attendance")
    students = load_json("students")
    groups = load_json("groups")
    courses = load_json("courses")

    current_year_month = datetime.now().strftime("%Y-%m")
    monthly_attendance = [a for a in attendance if a["date"].startswith(current_year_month)]

    if not monthly_attendance:
        return {"message": "Маълумот барои моҳи ҷорӣ вуҷуд надорад."}

    file_name = f"monthly_attendance_{current_year_month}.txt"
    file_path = REPORTS_DIR / file_name

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Ҳисоботи моҳона барои {current_year_month}\n\n")
        for student in students:
            student_absences = [a["date"] for a in monthly_attendance if a["student_id"] == student["id"] and a["status"] == "absent"]
            if student_absences:
                f.write(f"Донишҷӯ: {student['name']}\n")
                f.write(f"Гурӯҳ: {next((g['number'] for g in groups if g['id'] == student['group_id']), 'Unknown')}\n")
                f.write(f"Курс: {next((c['year'] for c in courses if c['id'] == student['course_id']), 'Unknown')}\n")
                f.write(f"Рӯзҳои ғоиб: {', '.join(sorted(set(student_absences)))}\n")
                f.write(f"Шумораи умумӣ: {len(set(student_absences))}\n\n")

    # Reset attendance for the month
    remaining_attendance = [a for a in attendance if not a["date"].startswith(current_year_month)]
    save_json("attendance", remaining_attendance)

    return {"message": f"Ҳисобот дар файл {file_name} захира шуд."}

# -------------------- Run --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)