import datetime
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from sqlalchemy.exc import IntegrityError
import os
import smtplib

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap5(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return db.session.execute(db.select(User).where(User.id == id)).scalar()

# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "Users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)

    # Relational Database
    author_posts: Mapped["BlogPost"] = relationship(back_populates="author_post")
    author_comments: Mapped["Comment"] = relationship(back_populates="author_comment")


class BlogPost(db.Model):
    __tablename__ = "Blog"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    image: Mapped[str] = mapped_column(String(250), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    release: Mapped[str] = mapped_column(String(250), nullable=False)

    # User and Blog Posts
    author_id: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    author_post: Mapped["User"] = relationship(back_populates="author_posts")

    # Relational Database
    blog_comments: Mapped["Comment"] = relationship(back_populates="blog_comment")


class Comment(db.Model):
    __tablename__ = "Comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment: Mapped[str] = mapped_column(String, nullable=False)
    author_address: Mapped[str] = mapped_column(String, nullable=False)
    author_name: Mapped[str] = mapped_column(String, nullable=False)

    # User and Comments and Blog
    author_id: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    blog_id: Mapped[int] = mapped_column(ForeignKey("Blog.id"))
    author_comment: Mapped["User"] = relationship(back_populates="author_comments")
    blog_comment: Mapped["BlogPost"] = relationship(back_populates="blog_comments")


with app.app_context():
    db.create_all()

def secure(f):
    @wraps(f)
    def access(*args, **kwargs):
        active = [user.address for user in db.session.execute(db.select(User)).scalars().all()]
        try:
            if current_user.address not in active:
                abort(403) 
        
        except AttributeError:
            abort(403)
        
        else:
            return f(*args, **kwargs)
        
    return access

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            hash = generate_password_hash(request.form.get("password"), method="pbkdf2:sha256", salt_length=12)
            new_user = User(
                name=request.form.get("name"),
                address=request.form.get("address"),
                password=hash
                )
            
            db.session.add(new_user)
            db.session.commit()
        
        except IntegrityError:
            flash("There is already an account associated with that address. Please login!")
            return redirect(url_for("login"))
        
        else:
            login_user(new_user)
            return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, current_user=current_user)

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.address == request.form.get("address"))).scalar()
        if not user:
            flash("This address does not exist. ")
            return redirect(url_for("login"))

        elif not check_password_hash(user.password, request.form.get("password")):
            flash("Incorrect password. Please try again! ")
            return redirect(url_for("login"))
        
        else:
            login_user(user)
            return redirect(url_for("get_all_posts"))
        
    return render_template("login.html", form=form, current_user=current_user)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

@secure
@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, current_user=current_user)

@app.route("/post/<int:post_id>", methods=["GET", "POST"])
@secure
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    comment_form = CommentForm()
    comments = db.session.execute(db.select(Comment)).scalars().all()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            comment=request.form.get("content"),
            author_address=current_user.address,
            author_id=current_user.id,
            author_name=current_user.name,
            blog_id=post_id
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form, comments=comments)

@app.route("/new-post", methods=["GET", "POST"])
@secure
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new = BlogPost(
            title=request.form.get("title"),
            subtitle=request.form.get("subtitle"),
            image=request.form.get("image"),
            content=request.form.get("content"),
            author=current_user.name,
            release=datetime.datetime.now().strftime("%B %d, %Y"),
            author_id=current_user.id
        )
        db.session.add(new)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    
    return render_template("make-post.html", form=form)

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@secure
def edit_post(post_id):
    query = db.get_or_404(BlogPost, post_id)
    form = CreatePostForm(title=query.title, subtitle=query.subtitle, image=query.image, author=query.author, content=query.content)

    if form.validate_on_submit():
        query.title = form.title.data
        query.subtitle = form.subtitle.data
        query.image = form.image.data
        query.author = current_user.name
        query.content = form.content.data

        db.session.commit()
        return redirect(url_for("show_post", post_id=query.id))
    
    return render_template("make-post.html", form=form, is_edit=True)

@app.route("/delete/<int:post_id>")
@secure
def delete_post(post_id):
    deletion = db.get_or_404(BlogPost, post_id)
    db.session.delete(deletion)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/about")
def about():
    return render_template("about.html")

MAIL_ADDRESS = os.environ.get("EMAIL_KEY")
MAIL_APP_PW = os.environ.get("PASSWORD_KEY")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        send_email(request.form.get("name"), request.form.get("email"), request.form.get("phone"), request.form.get("message"))
        return render_template("contact.html", msg_sent=True)
    
    return render_template("contact.html", msg_sent=False)


def send_email(name, email, phone, message):
    email_message = f"Subject:New Message\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(MAIL_ADDRESS, MAIL_APP_PW)
        connection.sendmail(email, MAIL_ADDRESS, email_message)

if __name__ == "__main__":
    app.run(debug=False)
