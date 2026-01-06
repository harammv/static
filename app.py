from flask import Flask, render_template, request, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import timedelta
import os, json

app = Flask(__name__)
app.secret_key = "silver_admin_secret"
app.permanent_session_lifetime = timedelta(days=1)

# ===============================
# Firebase 초기화 (로컬 + 배포 겸용)
# ===============================
if not firebase_admin._apps:
    if os.environ.get("FIREBASE_KEY_JSON"):
        cred_dict = json.loads(os.environ.get("FIREBASE_KEY_JSON"))
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ===============================
# 관리자 비밀번호 (여기만 바꾸면 됨)
# ===============================
ADMIN_PASSWORD = "4357"


# ===============================
# 메인 페이지
# ===============================
@app.route("/")
def index():
    posts_ref = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING)
    posts = []

    for doc in posts_ref.stream():
        post = doc.to_dict()
        post["id"] = doc.id
        post["comments"] = []
        comments_ref = db.collection("posts").document(doc.id).collection("comments")
        for c in comments_ref.stream():
            c_data = c.to_dict()
            c_data["id"] = c.id
            post["comments"].append(c_data)
        posts.append(post)

    return render_template("index.html", posts=posts)


# ===============================
# 글 작성
# ===============================
@app.route("/submit", methods=["POST"])
def submit():
    db.collection("posts").add({
        "nickname": request.form["nickname"],
        "content": request.form["content"],
        "reported": False,
        "created": firestore.SERVER_TIMESTAMP
    })
    return redirect("/")


# ===============================
# 댓글 작성
# ===============================
@app.route("/comment/<post_id>", methods=["POST"])
def comment(post_id):
    db.collection("posts").document(post_id).collection("comments").add({
        "nickname": request.form["nickname"],
        "content": request.form["content"],
        "reported": False
    })
    return redirect("/")


# ===============================
# 글 신고
# ===============================
@app.route("/report/post/<post_id>", methods=["POST"])
def report_post(post_id):
    db.collection("posts").document(post_id).update({
        "reported": True,
        "report_reason": request.form["reason"]
    })
    return redirect("/")


# ===============================
# 댓글 신고
# ===============================
@app.route("/report/comment/<post_id>/<comment_id>", methods=["POST"])
def report_comment(post_id, comment_id):
    db.collection("posts").document(post_id).collection("comments").document(comment_id).update({
        "reported": True,
        "report_reason": request.form["reason"]
    })
    return redirect("/")


# ===============================
# 관리자 로그인
# ===============================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
    return render_template("admin_login.html")


# ===============================
# 관리자 로그아웃
# ===============================
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/")


# ===============================
# 관리자 페이지
# ===============================
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin/login")

    posts = []
    for doc in db.collection("posts").stream():
        post = doc.to_dict()
        post["id"] = doc.id
        post["comments"] = []

        for c in db.collection("posts").document(doc.id).collection("comments").stream():
            c_data = c.to_dict()
            c_data["id"] = c.id
            post["comments"].append(c_data)

        posts.append(post)

    return render_template("admin.html", posts=posts)


# ===============================
# 관리자 삭제 (글 + 댓글)
# ===============================
@app.route("/admin/delete/post/<post_id>")
def delete_post(post_id):
    if session.get("admin"):
        db.collection("posts").document(post_id).delete()
    return redirect("/admin")


@app.route("/admin/delete/comment/<post_id>/<comment_id>")
def delete_comment(post_id, comment_id):
    if session.get("admin"):
        db.collection("posts").document(post_id).collection("comments").document(comment_id).delete()
    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True)
