from app import app, db
from models import Users, Blogs, Category

if __name__ == '__main__':
    with app.app_context():
        # Crear tablas si no existen
        db.create_all()
    
    # Ejecutar la aplicación
    app.run(debug=True, port=5000)
