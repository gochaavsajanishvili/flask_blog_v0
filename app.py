from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config['SECRET_KEY'] = 'random string'

db = SQLAlchemy(app)


class Users(db.Model):
    # @TODO Check if autoincrement parameter does anything
    id = db.Column('user_id', db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    username = db.Column(db.String(30))
    password = db.Column(db.String(100))
    # @TODO Fix/calibrate timezone hours to my local hours (it's now -4)
    register_date = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def __init__(self, name, email, username, password):
        self.name = name
        self.email = email
        self.username = username
        self.password = password


class Articles(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    title = db.Column(db.String(255))
    author = db.Column(db.String(100))
    body = db.Column(db.TEXT)
    create_date = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def __init__(self, title, body):
        self.title = title
        self.body = body
        self.author = session['username']


# Index
@app.route('/')
def home():
    return render_template('home.html')


# About
@app.route('/about')
def about():
    return render_template('about.html')


# Articles
@app.route('/articles')
def article_list():
    articles = Articles.query.all()
    return render_template('articles.html', articles=articles)


# Single Article
@app.route('/articles/<pk>/')
def article_detail(pk):

    article = Articles.query.filter_by(id=pk).first()
    return render_template('article.html', article=article)


# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        user = Users(request.form['name'],
                     request.form['email'],
                     request.form['username'],
                     sha256_crypt.encrypt(request.form['password']))

        db.session.add(user)
        db.session.commit()

        flash('You are now registered and can log in!', 'success')

        return redirect(url_for('home'))

    return render_template('register.html', form=form)


# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form.get('username')
        password_candidate = request.form.get('password')

        # Get User by username
        user = Users.query.filter_by(username=username).first()

        if user:
            # Compare Passwords
            if sha256_crypt.verify(password_candidate, user.password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Incorrect Password'
                return render_template('login.html', error=error)
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'warning')
    return redirect(url_for('login'))


# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    result = Articles.query.all()
    return render_template('dashboard.html', result=result)


# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        post = Articles(request.form['title'], request.form['body'])

        db.session.add(post)
        db.session.commit()

        flash('Article Created', 'success')

        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


# Edit Article
@app.route('/edit_article/<pk>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(pk):

    # Get article by id
    article = Articles.query.filter_by(id=pk).first()

    form = ArticleForm(request.form)

    # Populate Article Form Fields
    form.title.data = article.title
    form.body.data = article.body

    if request.method == 'POST' and form.validate():
        post = Articles(request.form['title'], request.form['body'])

        article.title = request.form['title']
        article.body = request.form['body']

        db.session.commit()

        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)


# Delete Article
@app.route('/delete_article/<pk>', methods=['POST'])
@is_logged_in
def delete_article(pk):
    Articles.query.filter_by(id=pk).delete()

    db.session.commit()

    flash('Article Deleted', 'warning')

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
