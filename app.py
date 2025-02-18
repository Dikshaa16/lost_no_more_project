from flask import Flask, render_template, redirect, request, url_for, flash,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import os

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = 'Your secret key'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password)

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(10), nullable=False)

def save_image(image):
    filename = image.filename
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(filepath)
    return filename


with app.app_context():
    db.create_all()

    # Check if an admin user already exists
    if not User.query.filter_by(role="admin").first():
        admin_user = User(name="Diksha Sharma", email="dikshasharma162005@gmail.com",
                          mobile="9478622626", role="admin")
        admin_user.set_password("diksha123")  # Set a default password
        db.session.add(admin_user)
        db.session.commit()
        
       

from functools import wraps

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('dashboard'))
        return func(*args, **kwargs)
    return wrapper



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        user = User.query.filter_by(email=email, role=role).first()
        if user and user.check_password(password):
            login_user(user)
            if user.role == 'admin':
                flash('Welcome, Diksha!', 'success')
            else:
                flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to index.html
        else:
            flash('Invalid credentials!', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        mobile = request.form.get('mobile')
        role = request.form.get('role')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, mobile=mobile, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/report-lost', methods=['POST'])
@app.route('/report-found', methods=['POST'])
@login_required
def report_item():
    status = 'lost' if request.path == '/report-lost' else 'found'
    item = Item(
        name=request.form['item_name'],
        description=request.form['description'],
        category=request.form['category'],
        date=request.form['date'],
        location=request.form['location'],
        image=save_image(request.files['image']),
        status=status
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('gallery'))

@app.route('/gallery')
@login_required
def gallery():
    items = Item.query.all()
    return render_template('gallery.html', items=items)

@app.route('/user_gallery')
@login_required
def user_gallery():
    items = Item.query.all()
    return render_template('user_gallery.html', items=items)

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['item_name']
        item.description = request.form['description']
        item.category = request.form['category']
        item.date = request.form['date']
        item.location = request.form['location']
        if 'image' in request.files and request.files['image'].filename != '':
            item.image = save_image(request.files['image'])
        item.status = request.form['status']
        db.session.commit()
        return redirect(url_for('gallery'))
    return render_template('edit_item.html', item=item)

@app.route('/delete/<int:item_id>', methods=['POST'])
@login_required
@admin_required

def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('gallery'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        current_user.mobile = request.form.get('mobile')
        current_user.role = request.form.get('role')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', user=current_user)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'GET':
        return render_template('search.html', items=[])
    elif request.method == 'POST':
        data = request.get_json()
        search = data.get('search', '')
        category = data.get('category', '')
        date = data.get('date', '')
        location = data.get('location', '')
        sort = data.get('sort', 'date')

        # Build query
        items_query = Item.query

        if search:
            items_query = items_query.filter(Item.name.ilike(f'%{search}%') | Item.description.ilike(f'%{search}%'))
        if category:
            items_query = items_query.filter_by(category=category)
        if date:
            items_query = items_query.filter_by(date=date)
        if location:
            items_query = items_query.filter(Item.location.ilike(f'%{location}%'))

        if sort == 'date':
            items_query = items_query.order_by(Item.date)
        elif sort == 'name':
            items_query = items_query.order_by(Item.name)

        items = items_query.all()

        results = [
            {
                'name': item.name,
                'description': item.description,
                'category': item.category,
                'date': item.date,
                'location': item.location,
                'image': url_for('static', filename='uploads/' + item.image),
                'status': item.status
            }
            for item in items
        ]

        return jsonify(results)





if __name__ == '__main__':
    app.run(debug=True)
