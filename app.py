import os, uuid, json
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-in-production")

def init_firebase():
    if firebase_admin._apps:
        return firestore.client()
    service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_json:
        cred = credentials.Certificate(json.loads(service_json))
    else:
        path = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE", "firebase-service-account.json")
        cred = credentials.Certificate(path)
    firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

def now():
    return datetime.now(timezone.utc).isoformat()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "uid" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email=request.form["email"].strip().lower()
        password=request.form["password"]
        name=request.form["name"].strip()
        if len(password)<6:
            flash("Password must contain at least 6 characters.")
            return redirect(url_for("register"))
        q=db.collection("users").where("email","==",email).limit(1).stream()
        if next(q, None):
            flash("Email already registered.")
            return redirect(url_for("register"))
        uid=str(uuid.uuid4())
        db.collection("users").document(uid).set({
            "name":name,"email":email,
            "password_hash":generate_password_hash(password),
            "balance":0.0,"plan":"Free","created_at":now(),"status":"active"
        })
        session["uid"]=uid
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower()
        password=request.form["password"]
        docs=db.collection("users").where("email","==",email).limit(1).stream()
        user=next(docs,None)
        if user and check_password_hash(user.to_dict().get("password_hash",""),password):
            session["uid"]=user.id
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    user=db.collection("users").document(session["uid"]).get().to_dict()
    bots=list(db.collection("bots").where("owner_uid","==",session["uid"]).stream())
    return render_template("dashboard.html",user=user,bots=[{"id":b.id,**b.to_dict()} for b in bots])

@app.route("/bots")
@login_required
def bots():
    docs=db.collection("bots").where("owner_uid","==",session["uid"]).stream()
    data=[{"id":d.id,**d.to_dict()} for d in docs]
    return render_template("bots.html",bots=data)

@app.route("/bots/create",methods=["GET","POST"])
@login_required
def create_bot():
    if request.method=="POST":
        name=request.form["name"].strip()
        entry=request.form["entry"].strip() or "main.py"
        bot_id=str(uuid.uuid4())
        db.collection("bots").document(bot_id).set({
            "owner_uid":session["uid"],"name":name,"entrypoint":entry,
            "status":"stopped","plan":"Free","created_at":now()
        })
        flash("Bot created. Upload/deploy integration can be connected next.")
        return redirect(url_for("bots"))
    return render_template("create_bot.html")

@app.route("/billing")
@login_required
def billing():
    u=db.collection("users").document(session["uid"]).get().to_dict()
    tx=list(db.collection("transactions").where("uid","==",session["uid"]).stream())
    return render_template("billing.html",user=u,transactions=[{"id":x.id,**x.to_dict()} for x in tx])

@app.route("/api/deposit",methods=["POST"])
@login_required
def deposit():
    amount=float(request.json.get("amount",0))
    if amount<=0: return jsonify({"error":"Invalid amount"}),400
    tid=str(uuid.uuid4())
    db.collection("transactions").document(tid).set({
        "uid":session["uid"],"amount":amount,"type":"deposit",
        "status":"pending","created_at":now()
    })
    return jsonify({"message":"Deposit request created","transaction_id":tid})

@app.route("/admin")
@login_required
def admin():
    user=db.collection("users").document(session["uid"]).get().to_dict()
    if user.get("role")!="admin":
        return "Forbidden",403
    users=list(db.collection("users").stream())
    return render_template("admin.html",users=[{"id":u.id,**u.to_dict()} for u in users])

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
