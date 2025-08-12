from flask import Flask, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime
from models import db, Users, Blogs, Category, Comment
from extensions import init_app, login_manager

def create_app():
    app = Flask(__name__)
    app.secret_key = 'mi_super_secreto_12345' 

    # Configuración temporal con SQLite (cambiar a MySQL cuando esté configurado)
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@127.0.0.1/db_blogs'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializar extensiones
    init_app(app)
    
    # Configuración de Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return Users.query.get(int(user_id))
    
    # Importar y registrar blueprints (si los tienes)
    # from .routes import main_bp
    # app.register_blueprint(main_bp)
    
    # Registrar rutas
    register_routes(app)
    
    with app.app_context():
        # Crear tablas si no existen
        db.create_all()
        
        # Verificar y crear categorías por defecto si no existen
        create_default_categories()
    
    return app

def register_routes(app):
    """Registrar todas las rutas de la aplicación"""
    from flask import render_template, request, redirect, url_for, flash, abort
    from flask_login import login_user, login_required, logout_user, current_user
    from models import Users, Blogs, Category
    
    @app.route('/')
    def index():
        try:
            # Obtener todos los blogs con sus autores y categorías, ordenados por fecha de creación
            blogs = db.session.query(Blogs, Users, Category).\
                join(Users, Blogs.user_id == Users.id).\
                outerjoin(Category, Blogs.category_id == Category.id).\
                order_by(Blogs.created_at.desc()).all()
            
            # Debug: Verificar si se están obteniendo blogs
            print(f"Número de blogs encontrados: {len(blogs)}")
            if blogs:
                print(f"Primer blog: {blogs[0][0].title} por {blogs[0][1].username}")
            
            # Obtener todas las categorías para el menú desplegable
            categories = Category.query.all()
            print(f"Número de categorías encontradas: {len(categories)}")
            
            # Reestructurar los datos para la plantilla
            blog_data = [{
                'id': blog.id,
                'title': blog.title,
                'description': blog.description,
                'created_at': blog.created_at,
                'author': {
                    'id': user.id,
                    'username': user.username
                },
                'blog_category': {'name': category.name, 'id': category.id} if category else None,
                'comment_count': len(blog.comments) if hasattr(blog, 'comments') else 0
            } for blog, user, category in blogs]
            
            # Debug: Verificar los datos que se enviarán a la plantilla
            print(f"Datos de blog a enviar a la plantilla: {blog_data}")
            
            return render_template('index.html', blogs=blog_data, categories=categories)
            
        except Exception as e:
            print(f"Error en la ruta index: {str(e)}")
            import traceback
            traceback.print_exc()
            return "Ocurrió un error al cargar los blogs. Por favor, revisa los logs del servidor."

    @app.route('/about')
    def about():
        return render_template('about.html')
        
    @app.route('/crear_blog', methods=['GET', 'POST'])
    @login_required
    def crear_blog():
        # Obtener todas las categorías para el formulario
        categorias = Category.query.all()
        
        if request.method == 'POST':
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            categoria_id = request.form.get('categoria')

            nuevo_blog = Blogs(
                title=titulo, 
                description=descripcion, 
                user_id=current_user.id,
                category_id=categoria_id if categoria_id else None
            )

            db.session.add(nuevo_blog)
            db.session.commit()

            flash('Blog creado con éxito', 'success')
            return redirect(url_for('index'))

        return render_template('crear_blog.html', categorias=categorias)

    @app.route('/blog/<int:blog_id>')
    def blog_detalle(blog_id):
        # Obtener el blog con su autor y categoría
        blog_data = db.session.query(Blogs, Users, Category).\
            join(Users, Blogs.user_id == Users.id).\
            outerjoin(Category, Blogs.category_id == Category.id).\
            filter(Blogs.id == blog_id).first()
        
        if not blog_data:
            abort(404)
            
        blog, author, category = blog_data
        
        # Estructurar los datos para la plantilla
        blog_info = {
            'id': blog.id,
            'title': blog.title,
            'description': blog.description,
            'created_at': blog.created_at,
            'author': {'id': author.id, 'username': author.username},
            'blog_category': {'id': category.id, 'name': category.name} if category else None,
            'comments': blog.comments  # Esto ya está disponible por la relación
        }
        
        return render_template('blog_detalle.html', blog=blog_info)
        
    @app.route('/blog/<int:blog_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_blog(blog_id):
        blog = Blogs.query.get_or_404(blog_id)
        
        # Verificar que el usuario actual es el autor del blog
        if current_user.id != blog.user_id:
            flash('No tienes permiso para editar este blog', 'danger')
            return redirect(url_for('blog_detalle', blog_id=blog_id))
            
        if request.method == 'POST':
            blog.title = request.form.get('title', blog.title)
            blog.description = request.form.get('description', blog.description)
            category_id = request.form.get('category_id')
            
            # Validar que la categoría existe si se proporciona
            if category_id:
                category = Category.query.get(category_id)
                if not category:
                    flash('La categoría seleccionada no existe', 'danger')
                    return redirect(url_for('edit_blog', blog_id=blog_id))
                blog.category_id = category_id
            else:
                blog.category_id = None
            
            try:
                db.session.commit()
                flash('El blog se ha actualizado correctamente', 'success')
                return redirect(url_for('blog_detalle', blog_id=blog_id))
            except Exception as e:
                db.session.rollback()
                flash('Ocurrió un error al actualizar el blog', 'danger')
                
        # Obtener todas las categorías para el formulario
        categories = Category.query.all()
        return render_template('edit_blog.html', blog=blog, categories=categories)
        
    # Moved delete route to a single location (see below)
        
    @app.route('/blog/<int:blog_id>/comment', methods=['POST'])
    @login_required
    def add_comment(blog_id):
        blog = Blogs.query.get_or_404(blog_id)
        content = request.form.get('content', '').strip()
        
        if not content:
            flash('El comentario no puede estar vacío', 'error')
            return redirect(url_for('blog_detalle', blog_id=blog_id))
            
        comment = Comment(
            content=content,
            user_id=current_user.id,
            blog_id=blog_id
        )
        
        db.session.add(comment)
        db.session.commit()
        
        flash('Comentario agregado correctamente', 'success')
        return redirect(url_for('blog_detalle', blog_id=blog_id))
    
    @app.route('/categoria')
    def categoria():
        # Obtener todas las categorías de la base de datos
        categorias_db = Category.query.all()
        return render_template('categoria.html', categorias=categorias_db)

    @app.route('/categoria/<string:slug>')
    def categoria_detalle(slug):
        # Obtener la categoría por su slug
        categoria = Category.query.filter_by(slug=slug).first_or_404()
        # Obtener los blogs de esta categoría, ordenados por fecha de creación
        blogs = Blogs.query.filter_by(category_id=categoria.id).order_by(Blogs.created_at.desc()).all()
        
        return render_template('categoria_detalle.html', categoria=categoria, blogs=blogs)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']

            user_exist = Users.query.filter((Users.username == username) | (Users.email == email)).first()
            if user_exist:
                flash('El usuario o email ya existe', 'danger')
                return redirect(url_for('register'))

            new_user = Users(username=username, email=email)
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()
            flash('Registro exitoso, ya puedes iniciar sesión', 'success')
            return redirect(url_for('login'))

        return render_template('auth/register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            user = Users.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('Has iniciado sesión correctamente', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('Usuario o contraseña incorrectos', 'danger')
                return redirect(url_for('login'))

        return render_template('auth/login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Has cerrado sesión correctamente', 'info')
        return redirect(url_for('login'))

    @app.route('/like/<int:blog_id>', methods=['POST'])
    @login_required
    def like(blog_id):
        blog = Blogs.query.get_or_404(blog_id)
        # Aquí iría la lógica para dar like
        flash('Like registrado', 'success')
        return redirect(url_for('index'))

    @app.route('/delete/<int:blog_id>', methods=['POST'])
    @login_required
    def delete(blog_id):
        blog = Blogs.query.get_or_404(blog_id)
        
        # Verificar que el usuario actual es el autor del blog
        if blog.user_id != current_user.id:
            flash('No tienes permiso para eliminar este blog', 'danger')
            return redirect(url_for('blog_detalle', blog_id=blog_id))
            
        try:
            # Eliminar los comentarios asociados primero (si hay una relación de cascada)
            for comment in blog.comments:
                db.session.delete(comment)
                
            # Luego eliminar el blog
            db.session.delete(blog)
            db.session.commit()
            flash('El blog se ha eliminado correctamente', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('Ocurrió un error al eliminar el blog', 'danger')
            return redirect(url_for('blog_detalle', blog_id=blog_id))

    @app.route('/edit/<int:blog_id>', methods=['GET', 'POST'])
    @login_required
    def edit(blog_id):
        blog = Blogs.query.get_or_404(blog_id)
        
        # Verificar que el usuario sea el autor del blog
        if blog.author.id != current_user.id:
            flash('No tienes permiso para editar este blog', 'danger')
            return redirect(url_for('index'))
        
        # Obtener todas las categorías para el formulario
        categorias = Category.query.all()
        
        if request.method == 'POST':
            blog.title = request.form['titulo']
            blog.description = request.form['descripcion']
            categoria_id = request.form.get('categoria')
            
            # Actualizar la categoría
            if categoria_id:
                blog.category_id = int(categoria_id)
            else:
                blog.category_id = None
            
            db.session.commit()
            flash('Blog actualizado exitosamente', 'success')
            return redirect(url_for('index'))
            
        return render_template('edit_blog.html', blog=blog, categorias=categorias)

def create_default_categories():
    # Categorías por defecto
    default_categories = [
        {'name': 'Tecnología', 'slug': 'tecnologia', 'description': 'Explora los últimos avances y noticias tecnológicas.'},
        {'name': 'Programación', 'slug': 'programacion', 'description': 'Tutoriales y consejos sobre desarrollo de software.'},
        {'name': 'Diseño', 'slug': 'diseno', 'description': 'Inspiración y tendencias en diseño web y gráfico.'},
        {'name': 'Negocios', 'slug': 'negocios', 'description': 'Estrategias y consejos para emprendedores.'},
        {'name': 'Educación', 'slug': 'educacion', 'description': 'Recursos y consejos para el aprendizaje continuo.'},
        {'name': 'Estilo de Vida', 'slug': 'estilo-de-vida', 'description': 'Consejos para mejorar tu día a día.'}
    ]
    
    for cat_data in default_categories:
        if not Category.query.filter_by(slug=cat_data['slug']).first():
            new_category = Category(
                name=cat_data['name'],
                slug=cat_data['slug'],
                description=cat_data['description']
            )
            db.session.add(new_category)
    
    db.session.commit()

# Crear la aplicación
app = create_app()

# Ruta para manejar errores 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Ruta para manejar errores 500
@app.errorhandler(500)
def internal_server_error(e):
    # Log the error for debugging
    app.logger.error(f'500 Error: {str(e)}')
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
