from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Relación con blogs
    blogs = db.relationship('Blogs', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    blogs = db.relationship('Blogs', backref='blog_category', lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"


class Blogs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Clave foránea que referencia a Users.id
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Clave foránea que referencia a Category.id
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    
    # Relaciones
    comments = db.relationship('Comment', backref='blog', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Blog {self.title}>"


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Clave foránea que referencia a Users.id
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Clave foránea que referencia a Blogs.id
    blog_id = db.Column(db.Integer, db.ForeignKey('blogs.id'), nullable=False)
    
    # Relación con el usuario que hizo el comentario
    user = db.relationship('Users', backref=db.backref('comments', lazy=True))

    def __repr__(self):
        return f"<Comment {self.id} on Blog {self.blog_id}>"
