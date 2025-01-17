import os
from datetime import datetime
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc
from werkzeug.utils import secure_filename
from pillow_heif import register_heif_opener
from dotenv import load_dotenv

load_dotenv()
register_heif_opener()
ADMIN_PASSWORD = "1234"
TINY_API = os.environ.get("TINY_API_KEY")
CURRENT_DATE = datetime.now().strftime('%m/%d/%Y')
app = Flask(__name__)

UPLOAD_FOLDER = 'static/images/blog_images'
C_UPLOAD_FOLDER = 'static/images/carousel'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Directory to save uploaded files
app.config['C_UPLOAD_FOLDER'] = C_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max file size: 16 MB
app.secret_key = os.urandom(24)


# Initialize Flask-Limiter
limiter = Limiter(
    get_remote_address,  # Uses the client's IP address for rate limiting
    app=app,
    default_limits=["200 per day", "50 per hour"]  # General rate limits for all routes
)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'heic'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def logged_in():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

def query_blog():
    #Get a list of the posts in backwards order so the newest ones get listed first.
    #First entry in the DB controls the headline and feature 1&2 posts
    result = db.session.execute(db.select(Post).order_by(desc(Post.id)))
    posts = result.scalars().all()
    posts_len = len(posts)
    for _ in posts:
        print(_.title)
    # Create 2 posts if there are no posts in the DB
    if posts_len < 2:
        print("!")
        first_post = Post(title="first post", author='nick', category='config', date='7/11/1981', body=1, picture=1,
                        thumb=1)
        second_post = Post(title="Delete this after you make your first post", author='nick', category='', date='7/11/1981', body=2)
        db.session.add(first_post)
        db.session.add(second_post)
        db.session.commit()
        # Populate temporary posts
        posts = (Post.query.all())[::-1]
        posts_len = len(posts)
    print(posts[-1].thumb, posts[-1].picture, posts[-1].body )
    hl = next(post for post in posts if post.id == int(posts[-1].body))
    f1 = next(post for post in posts if post.id == int(posts[-1].thumb))
    f2 = next(post for post in posts if post.id == int(posts[-1].picture))

    return posts, posts_len, hl, f1, f2

# def query_carousel():
#     all_entries = []
#     with app.app_context():
#         entries = db.session.execute(db.select(CarouselImage).order_by(CarouselImage.id)).scalars()
#         for _ in entries:
#             all_entries.append([_.id, _.link, _.body, _.picture, _.thumb, _.order, _.expire])
#     entries_len = len(all_entries)
#     return all_entries, entries_len

def get_pictures(file):
    # give secure name to file
    filename = secure_filename(file.filename)
    # save file and open it in PIL
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    image = Image.open(f"{UPLOAD_FOLDER}/{filename}")
    image = image.convert('RGB')
    #delete original file
    os.remove(f"{UPLOAD_FOLDER}/{filename}")
    # change file extension to and save as webp
    filename = f"{filename.split('.')[0]}.webp"
    image.save(f"static/images/blog_images/{filename}", 'webp')
    image = Image.open(f"static/images/blog_images/{filename}")
    # Define the thumbnail size as a tuple (width, height)
    thumbnail_size = (200, 200)
    # Create a thumbnail
    image.thumbnail(thumbnail_size, resample=Image.BOX)
    image.save(f"static/images/blog_images/thm{filename}")
    thumb = f"thm{filename}"
    return filename, thumb

def get_c_pictures(file):
    filename = secure_filename(file.filename)
    print(filename)
    file.save(os.path.join(app.config['C_UPLOAD_FOLDER'], filename))
    image = Image.open(f"static/images/carousel/{filename}")
    # Define the thumbnail size as a tuple (width, height)
    thumbnail_size = (200, 200)
    # Create a thumbnail
    image.thumbnail(thumbnail_size, resample=Image.BOX)
    image.save(f"static/images/carousel/thm{filename}")
    picture = filename
    thumb = f"thm{filename}"
    return picture, thumb


class Base(DeclarativeBase):
    pass

# SQLAlchemy instance


# App config
if os.environ.get("LOCAL") == "True":
    app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///test_blog_posts.db'
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI")
# app.config["SQLALCHEMY_BINDS"] = {'carousel': os.environ.get("CAROUSEL_DB_URI", 'sqlite:///test_carousel.db')}  # Second database for carousel
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

# class CarouselImage(db.Model):
#     __bind_key__ = 'carousel'  # Specify which database this model uses
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     link: Mapped[str] = mapped_column(String(250), nullable=False)
#     body: Mapped[str] = mapped_column(String(250), nullable=True)
#     picture: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
#     thumb: Mapped[str] = mapped_column(String(250), nullable=False)
#     order: Mapped[int] = mapped_column(Integer, nullable=True)  # Order of the image in the carousel
#     expire: Mapped[str]= mapped_column(String(250), nullable=True)


with app.app_context():
    db.create_all()

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Return the URL of the uploaded image (adjust for your app's static path)
        return jsonify({'location': f'/static/static/blog_images/{filename}'}), 200
    return jsonify({'error': 'Invalid file format'}), 400

@app.route('/')
def home():
    posts, posts_len, headline, f1, f2 = query_blog()
    # entries, entries_len = query_carousel()
    # return render_template("brandi.html", posts=posts, posts_len=posts_len, headline=headline, entries=entries, entries_len=entries_len)
    return render_template("brandi.html", posts=posts, posts_len=posts_len, headline=headline, f1=f1, f2=f2)

@app.route('/post/<int:post_id>')
def get_post(post_id):
    posts, posts_len, headline, f1, f2 = query_blog()
    categories = []
    for post in posts:
        if post.category == "":
            pass
        elif post.category not in categories:
            categories.append(post.category)
    print(categories)
    post = db.get_or_404(Post, post_id)

    return render_template("post.html", post=post, posts=posts, posts_len=posts_len, categories=categories)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Allow up to 5 login attempts per minute per IP address
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            # Password is correct, redirect to admin page
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            # Password is incorrect, show an error
            error = "Invalid password. Please try again."
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/blog')
def blog():
    posts, posts_len, headline, f1, f2 = query_blog()
    # if posts_len == 0:
    #     return render_template('blog.html', posts=posts, empty=True)
    # else:
    return render_template('blog.html', posts=posts, headline=headline, f1=f1, f2=f2, empty=False, posts_len=posts_len)

@app.route('/logout')
def logout():
    # Clear the session to log the user out
    session.pop('admin_logged_in', None)
    print(session.get('admin_logged_in'))
    return redirect(url_for('blog'))


@app.route("/admin", methods=["GET", "POST"])
def admin():
    logged_in()
    print('logged in')
    print(request.method)
    posts, posts_len, headline, f1, f2 = query_blog()
    # entries, entries_len = query_carousel()
    if request.method == 'GET':
        # return render_template('admin.html', posts=posts, posts_len=posts_len, TINY_API=TINY_API, date=CURRENT_DATE, entries=entries, entries_len=entries_len)
        return render_template('admin.html', posts=posts, posts_len=posts_len, TINY_API=TINY_API, date=CURRENT_DATE)
    else:
        kind = request.args.get('kind')
        print(kind)
        if kind == 'blog':
            print('blog')
            title = request.form["title"]
            date = request.form["date"]
            author = request.form["author"]
            category = request.form["category"]
            body = request.form['body']
            file = request.files.get('picture')

            if file and allowed_file(file.filename):
                print('got file')
                picture, thumb = get_pictures(file)
                new_post = Post(title=title, author=author, category=category, date=date, body=body, picture=picture, thumb=thumb)
            else:
                print('used stock photo')
                new_post = Post(title=title, author=author, category=category, date=date, body=body, picture='stock.jpg', thumb='thmstock.jpg')
            with app.app_context():
                db.session.add(new_post)
                db.session.commit()
            # return render_template('admin.html', posts=posts, posts_len= posts_len, headline=headline, empty=False, TINY_API=TINY_API, entries=entries, entries_len=entries_len)
            return render_template('admin.html', posts=posts, posts_len=posts_len, headline=headline, empty=False,
                                   TINY_API=TINY_API)


        elif kind == 'carousel':
            print('carousel')
            link = request.form["link"]
            body = request.form['body']
            file = request.files.get('picture')
            picture, thumb = get_c_pictures(file)
            # new_carousel = CarouselImage(link=link, body=body, picture=picture, thumb=thumb)

            with app.app_context():
                # db.session.add(new_carousel)
                db.session.commit()
            return render_template('admin.html', posts=posts, posts_len= posts_len, headline=headline, empty=False, TINY_API=TINY_API)


@app.route('/delete')
def delete():
    print(session.get('admin_logged_in'))
    post_id = request.args.get('post_id')
    with app.app_context():
        post = db.get_or_404(Post, post_id)
        db.session.delete(post)
        db.session.commit()
    return redirect('/admin')

@app.route('/update', methods=['GET', 'POST'])
def update():
    kind = request.args.get('kind')
    print(kind, '1')
    if kind == 'blog':
        print(session.get('admin_logged_in'))
        logged_in()
        if request.method=='POST':
            post_id = request.form['post_id']
            print(post_id,'this should be the post id')
            print('2!')
            print('another 2')

            try:
                hl = request.form['headline']
                print("Checked hl")
                headline = db.get_or_404(Post, 1)
                headline.body = post_id
                db.session.commit()
            except:
                pass
            try:
                f1 = request.form['featured1']
                print("Checked f1")
                headline = db.get_or_404(Post, 1)
                headline.thumb = post_id
                db.session.commit()
            except:
                pass
            try:
                f2 = request.form['featured2']
                print("Checked f2")
                headline = db.get_or_404(Post, 1)
                headline.picture = post_id
                db.session.commit()
            except:
                pass
            finally:
                print('didnt work')
                with app.app_context():
                    post = db.get_or_404(Post, post_id)
                    post.title = request.form["title"]
                    post.date = request.form["date"]
                    post.author = request.form["author"]
                    post.category = request.form["category"]
                    post.body = request.form["body"]
                    file = request.files.get('picture')
                    if file and allowed_file(file.filename):
                        print('got file')
                        post.picture, post.thumb = get_pictures(file)
                        db.session.commit()
                    else:
                        print('used same photo')
                        db.session.commit()
                    return redirect(url_for('admin'))
            # try: #check to see if featured is checkmarked
            #     ues = request.form['featured']
            #     headline = db.get_or_404(Post, 1)
            #     headline.body = post_id
            #     db.session.commit()
            # except:
            #     pass
            # finally:
            #     with app.app_context():
            #         post = db.get_or_404(Post, post_id)
            #         post.title = request.form["title"]
            #         post.date = request.form["date"]
            #         post.author = request.form["author"]
            #         post.category = request.form["category"]
            #         post.body = request.form["body"]
            #         file = request.files.get('picture')
            #         if file and allowed_file(file.filename):
            #             print('got file')
            #             post.picture, post.thumb = get_pictures(file)
            #             db.session.commit()
            #         else:
            #             print('used stock photo')
            #             db.session.commit()
            #         return redirect(url_for('admin'))
        elif request.method=='GET':
            print('GET')
            posts, posts_len, headline, f1,f2 = query_blog()
            post_id = request.args.get('post_id')
            print(post_id)
            post = db.get_or_404(Post, post_id)
            return render_template('admin.html', update=True, post=post, posts=posts, posts_len= posts_len, post_id=post_id, TINY_API=TINY_API)
    elif kind == 'carousel':
        print('not blog')
        return redirect(url_for('admin'))
if __name__ == "__main__":
    app.run(debug=True)