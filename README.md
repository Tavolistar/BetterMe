# BetterMe - Sistema de Seguimiento de Hábitos

Aplicación web para seguimiento de hábitos y productividad con sistema de recompensas (monedas y rachas).

## Características

- ✅ **Seguimiento de hábitos diarios** con recompensas en monedas
- ✅ **Tareas personalizadas** que puedes agregar y completar
- ✅ **Sistema de rachas** para mantener la consistencia
- ✅ **Interfaz dashboard** con SB Admin 2 (Bootstrap 4)
- ✅ **Base de datos SQLite** para persistencia de datos
- ✅ **Galería de avatares** para personalizar tu perfil
- ✅ **Landing page** con información del sistema
- ✅ **Clave secreta segura** con variables de entorno

## Estructura del Proyecto

```
betterme/
├── app.py                 # Aplicación Flask (rutas y lógica)
├── models.py              # Modelos de base de datos
├── requirements.txt       # Dependencias de Python
├── .env                   # Variables de entorno
├── README.md              # Este archivo
├── instance/
│   └── betterme.db        # Base de datos SQLite (se crea automáticamente)
├── static/
│   ├── css/
│   │   ├── custom.css         # Estilos personalizados
│   │   ├── sb-admin-2.css     # Template SB Admin 2
│   │   └── sb-admin-2.min.css # Template SB Admin 2 (minificado)
│   ├── js/
│   │   ├── betterme.js        # JavaScript personalizado
│   │   ├── sb-admin-2.js      # SB Admin 2 JS
│   │   ├── sb-admin-2.min.js  # SB Admin 2 JS (minificado)
│   │   └── demo/              # Demos de gráficos
│   ├── img/                   # Imágenes SVG (undraw)
│   └── avatars/               # Avatares de usuario
└── templates/
    ├── base.html          # Template base (layout principal)
    ├── index.html         # Página de inicio / landing page
    ├── login.html         # Inicio de sesión
    ├── register.html      # Registro de usuarios
    ├── dashboard.html     # Dashboard principal
    └── avatars.html       # Galería de avatares
```

## Instalación

1. **Clonar o descargar** el repositorio
2. **Navegar al directorio** del proyecto:
   ```bash
   cd betterme
   ```
3. **Crear entorno virtual** (recomendado):
   ```bash
   python -m venv .venv
   ```
4. **Activar entorno virtual**:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`
5. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
6. **Configurar variables de entorno** (opcional):
   - El archivo `.env` ya está creado con valores por defecto
   - Puedes modificar `SECRET_KEY` y `DATABASE_URL` si es necesario

## Ejecución

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Rutas Disponibles

| Ruta | Descripción |
|------|-------------|
| `/` | Landing page / Inicio |
| `/dashboard` | Dashboard principal |
| `/login` | Inicio de sesión |
| `/register` | Registro de usuarios |
| `/avatars` | Galería de avatares |
| `/add_task` | Agregar nueva tarea (POST) |
| `/delete_task/<id>` | Eliminar tarea |
| `/toggle_task/<id>` | Marcar/desmarcar tarea |
| `/toggle_habit/<id>` | Marcar/desmarcar hábito |
| `/reset_day` | Reiniciar hábitos del día |
| `/add_sample_tasks` | Agregar tareas de ejemplo |

## Modelos de Base de Datos

- **Task**: Tareas personalizadas del usuario
- **Habit**: Hábitos predefinidos (agua, ejercicio, lectura)
- **UserProgress**: Progreso del usuario (monedas, racha)

## Tecnologías

- **Backend**: Flask, Flask-SQLAlchemy, Python
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 4
- **Base de datos**: SQLite
- **Template**: SB Admin 2

## Licencia

MIT
