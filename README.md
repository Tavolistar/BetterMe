# BetterMe - Sistema de Seguimiento de Hábitos

Aplicación web para seguimiento de hábitos y productividad personal con sistema de recompensas (monedas y rachas), autenticación de usuarios y datos completamente aislados por usuario.

## Características

- ✅ **Autenticación completa**: Registro, inicio de sesión y cierre de sesión
- ✅ **Datos aislados por usuario**: Cada usuario tiene sus propias tareas, hábitos y progreso
- ✅ **Selección de hábitos al registrarse**: Elige qué hábitos diarios quieres seguir
- ✅ **Seguimiento de hábitos diarios** con recompensas en monedas
- ✅ **Tareas personalizadas** que puedes agregar y completar
- ✅ **Sistema de rachas** para mantener la consistencia
- ✅ **Recuperación de contraseña** por correo electrónico
- ✅ **Interfaz dashboard** con SB Admin 2 (Bootstrap 4)
- ✅ **Base de datos SQLite** para persistencia de datos
- ✅ **Galería de avatares** para personalizar tu perfil
- ✅ **Landing page** con información del sistema
- ✅ **Clave secreta segura** con variables de entorno

## Estructura del Proyecto

```
betterme/
├── app.py                 # Aplicación Flask (rutas y lógica de negocio)
├── models.py              # Modelos de base de datos (SQLAlchemy)
├── requirements.txt       # Dependencias de Python
├── .env                   # Variables de entorno (SECRET_KEY, DB, email)
├── .gitignore             # Archivos ignorados por Git
├── README.md              # Este archivo
├── instance/
│   └── betterme.db        # Base de datos SQLite (se crea automáticamente)
├── static/
│   ├── css/
│   │   ├── custom.css         # Estilos personalizados (flash, animaciones)
│   │   ├── sb-admin-2.css     # Template SB Admin 2
│   │   └── sb-admin-2.min.css # Template SB Admin 2 (minificado)
│   ├── js/
│   │   ├── betterme.js        # JavaScript personalizado (toggles, reset)
│   │   ├── sb-admin-2.js      # SB Admin 2 JS
│   │   ├── sb-admin-2.min.js  # SB Admin 2 JS (minificado)
│   │   └── demo/              # Demos de gráficos (chart.js)
│   ├── img/                   # Imágenes SVG (undraw illustrations)
│   └── avatars/               # Avatares de usuario
└── templates/
    ├── base.html              # Template base (layout, CDNs, flash messages)
    ├── index.html             # Página de inicio / landing page
    ├── login.html             # Inicio de sesión
    ├── register.html          # Registro con selección de hábitos
    ├── dashboard.html         # Dashboard principal (tareas, hábitos, progreso)
    ├── avatars.html           # Galería de avatares
    ├── reset_password.html    # Solicitar recuperación de contraseña
    └── reset_password_confirm.html  # Establecer nueva contraseña
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
6. **Configurar variables de entorno** (`.env`):
   - `SECRET_KEY`: Clave secreta para sesiones Flask
   - `DATABASE_URL`: URI de la base de datos (por defecto `sqlite:///betterme.db`)
   - `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`: Configuración SMTP
   - `MAIL_USERNAME`, `MAIL_PASSWORD`: Credenciales de email
   - `MAIL_DEFAULT_SENDER`: Remitente por defecto

## Ejecución

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Rutas de la API

### Rutas Públicas

| Ruta | Métodos | Descripción | Autenticación |
|------|---------|-------------|---------------|
| `/` | GET | Landing page / Inicio | No |
| `/login` | GET, POST | Inicio de sesión | No |
| `/register` | GET, POST | Registro de usuario con selección de hábitos | No |
| `/reset_password` | GET, POST | Solicitar recuperación de contraseña | No |
| `/reset_password/<token>` | GET, POST | Confirmar cambio de contraseña | No (requiere token) |
| `/avatars` | GET | Galería de avatares | No |
| `/logout` | GET | Cerrar sesión | No |

### Rutas Protegidas (requieren inicio de sesión)

| Ruta | Métodos | Descripción |
|------|---------|-------------|
| `/dashboard` | GET | Dashboard principal con tareas, hábitos y progreso |
| `/add_task` | POST | Agregar nueva tarea personalizada |
| `/delete_task/<id>` | GET | Eliminar una tarea |
| `/toggle_task/<id>` | GET | Marcar/desmarcar tarea como completada |
| `/toggle_habit/<id>` | GET | Marcar/desmarcar hábito como completado |
| `/reset_day` | GET | Reiniciar todos los hábitos del día |
| `/add_sample_tasks` | GET | Agregar tareas de ejemplo |

## Modelos de Base de Datos

### User
Tabla principal de usuarios del sistema.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer (PK) | Identificador único del usuario |
| `email` | String(120), UNIQUE, NOT NULL, INDEX | Correo electrónico (usado para login) |
| `password_hash` | String(256), NOT NULL | Hash de la contraseña (werkzeug.security) |
| `name` | String(100), NOT NULL | Nombre completo del usuario |
| `avatar` | String(50), DEFAULT 'undraw_profile.svg' | Nombre del archivo de avatar |
| `created_at` | DateTime, DEFAULT utcnow | Fecha de registro |

**Relaciones:**
- `tasks` → one-to-many con `Task` (cascade delete)
- `progress` → one-to-one con `UserProgress` (cascade delete)
- `habits` → one-to-many con `UserHabit` (cascade delete)

**Métodos:**
- `set_password(password)` → Genera hash con `generate_password_hash`
- `check_password(password)` → Verifica contra el hash con `check_password_hash`

### Task
Tareas personalizadas creadas por cada usuario.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer (PK) | Identificador único |
| `text` | String(200), NOT NULL | Descripción de la tarea |
| `completed` | Boolean, DEFAULT False | Estado de completado |
| `created_at` | DateTime, DEFAULT utcnow | Fecha de creación |
| `user_id` | Integer (FK → User.id), NOT NULL, INDEX | Propietario de la tarea |

### Habit
Catálogo de hábitos predefinidos (compartido entre todos los usuarios).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer (PK) | Identificador único |
| `name` | String(100), NOT NULL | Nombre del hábito (ej: "Beber agua") |
| `description` | String(200) | Descripción del hábito |
| `coins` | Integer, DEFAULT 5 | Monedas que otorga al completarse |

**Hábitos predefinidos:**
1. Beber agua (+5 monedas) - Tomar al menos 8 vasos de agua al día
2. Ejercicio 30 min (+10 monedas) - Realizar actividad física por 30 minutos
3. Leer 20 páginas (+8 monedas) - Leer 20 páginas de un libro

### UserHabit
Tabla intermedia que registra el progreso individual de cada usuario sobre cada hábito.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer (PK) | Identificador único |
| `user_id` | Integer (FK → User.id), NOT NULL, INDEX | Usuario |
| `habit_id` | Integer (FK → Habit.id), NOT NULL, INDEX | Hábito |
| `completed` | Boolean, DEFAULT False | Completado por este usuario |
| `completed_date` | Date, NULL | Fecha en que se completó |

**Restricciones:** `UNIQUE(user_id, habit_id)` - un solo registro por par usuario-hábito.

### UserProgress
Progreso y estadísticas de cada usuario.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer (PK) | Identificador único |
| `user_id` | Integer (FK → User.id), UNIQUE, NOT NULL, INDEX | Usuario (one-to-one) |
| `coins` | Integer, DEFAULT 100 | Monedas acumuladas |
| `streak` | Integer, DEFAULT 0 | Racha actual de días consecutivos |
| `last_activity` | Date, DEFAULT today | Último día con actividad |

**Métodos:**
- `update_streak()` → Actualiza la racha:
  - Si el último día de actividad fue ayer → incrementa racha
  - Si fue antes de ayer → reinicia racha a 1
  - Si ya se actualizó hoy → no hace nada

## Diagrama de Relaciones

```
User (1) ──── (N) Task
User (1) ──── (1) UserProgress
User (1) ──── (N) UserHabit (N) ──── (1) Habit
```

## Sistema de Monedas y Rachas

### Monedas
- **100 monedas iniciales** al registrarse
- **+10 monedas** al completar una tarea personalizada
- **+5 a +10 monedas** al completar un hábito (según el hábito)
- **-5 monedas** al desmarcar una tarea
- **-50% del valor** al desmarcar un hábito

### Rachas
- La racha aumenta si hay actividad días consecutivos
- Se reinicia a 1 si se salta un día
- Se actualiza al completar tareas, hábitos o al resetear el día

## Recuperación de Contraseña

El sistema incluye recuperación de contraseña por email usando Flask-Mail.

### Configuración SMTP (Gmail)
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion
```

> **Nota**: Si usas Gmail con 2FA, debes generar una **contraseña de aplicación** en https://myaccount.google.com/apppasswords

### Modo Desarrollo
Si no hay configuración de email, el sistema muestra el enlace de recuperación directamente en la interfaz como mensaje flash.

## Tecnologías

- **Backend**: Flask 3.1, Flask-SQLAlchemy 3.1, Flask-Mail 0.9, Python 3
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 4.6
- **Base de datos**: SQLite (producción: migrar a PostgreSQL/MySQL)
- **Template**: SB Admin 2
- **Dependencias CDN**: FontAwesome 5, Google Fonts (Nunito), jQuery 3.6, jQuery Easing

## Licencia

MIT
