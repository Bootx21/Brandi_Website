from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

load_dotenv()
app = Flask(__name__)

def query_blog():
    #Get a list of the posts in backwards order so the newest ones get listed first.
    #First entry in the DB controls the headline and feature 1&2 posts
    result = db.session.execute(db.select(Post).order_by(desc(Post.id)))
    posts = result.scalars().all()
    posts_len = len(posts)
    # Create 2 posts if there are less than 2 posts in the DB
    if posts_len < 2:
        print("!")
        first_post = Post(title="first post", author='nick', category='config', date='7/11/1981', body=1, picture=1,
                          thumb=1)
        second_post = Post(title="Delete this after you make your first post", author='nick', category='',
                           date='7/11/1981', body=2)
        db.session.add(first_post)
        db.session.add(second_post)
        db.session.commit()
        # Populate temporary posts
        result = db.session.execute(db.select(Post).order_by(desc(Post.id)))
        posts = result.scalars().all()
        posts_len = len(posts)
    categories = []
    for _ in posts:
        if _.category == "" or _.category == 'config':
            pass
        elif _.category not in categories:
            categories.append(_.category)


    hl = next(post for post in posts if post.id == int(posts[-1].body))
    f1 = next(post for post in posts if post.id == int(posts[-1].thumb))
    f2 = next(post for post in posts if post.id == int(posts[-1].picture))

    return posts, posts_len, hl, f1, f2, categories

class Base(DeclarativeBase):
    pass

# SQLAlchemy instance


# App config
if os.environ.get("LOCAL") == "True":
    print("!")
    app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///test_blog_posts(saved).db'
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI")

db = SQLAlchemy(model_class=Base)
db.init_app(app)

class Post(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=True)
    category: Mapped[str] = mapped_column(String(250), nullable=True)
    picture: Mapped[str] = mapped_column(String(250), nullable=True)
    thumb: Mapped[str] = mapped_column(String(250), nullable=True)
    body: Mapped[str] = mapped_column(String(250), nullable=False)

with app.app_context():
    db.create_all()

    posts, posts_len, hl, f1, f2, categories = query_blog()
    post = posts[1].body
    list = post.split(" ")
    print(list[0:15],"...")
    print(" ".join(list[0:15]), "...")