// Funciones JavaScript para BetterMe App

// Toggle de hábitos
function toggleHabit(habitId) {
    // Enviar solicitud al servidor para alternar el hábito
    window.location.href = `/toggle_habit/${habitId}`;
}

// Toggle de tareas
function toggleTask(taskId) {
    // Enviar solicitud al servidor para alternar la tarea
    window.location.href = `/toggle_task/${taskId}`;
}

// Resetear día completo
function resetAll() {
    if (confirm('¿Estás seguro de que quieres reiniciar el día? Esto marcará todos los hábitos como incompletos.')) {
        window.location.href = '/reset_day';
    }
}

// Agregar tareas de ejemplo
function addSampleTasks() {
    if (confirm('¿Agregar tareas de ejemplo? Esto agregará 4 tareas predefinidas.')) {
        window.location.href = '/add_sample_tasks';
    }
}

// Actualizar checkboxes visualmente
document.addEventListener('DOMContentLoaded', function() {
    // Marcar checkboxes según estado
    const habitCheckboxes = document.querySelectorAll('input[type="checkbox"][id^="habit"]');
    habitCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('click', function(e) {
            e.stopPropagation(); // Evitar que el click se propague al card
        });
    });
    
    const taskCheckboxes = document.querySelectorAll('input[type="checkbox"][id^="task"]');
    taskCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('click', function(e) {
            e.stopPropagation(); // Evitar que el click se propague al card
            const taskId = this.id.replace('task', '');
            toggleTask(taskId);
        });
    });
    
    // Agregar efecto hover a las cards
    const cards = document.querySelectorAll('.task-card');
    cards.forEach(card => {
        card.style.cursor = 'pointer';
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
            this.style.transition = 'all 0.2s ease';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });
    
    // Actualizar progreso visualmente
    updateProgressBars();
});

// Actualizar barras de progreso
function updateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.getAttribute('aria-valuenow') || bar.style.width;
        if (width) {
            // Animar la barra
            bar.style.transition = 'width 1s ease-in-out';
        }
    });
}

// Notificación de monedas ganadas
function showCoinNotification(coins) {
    const notification = document.createElement('div');
    notification.className = 'alert alert-warning alert-dismissible fade show position-fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        <strong>¡+${coins} monedas!</strong> Has completado una tarea.
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
        </button>
    `;
    document.body.appendChild(notification);
    
    // Auto-eliminar después de 3 segundos
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Detectar si hay monedas nuevas en la URL
if (window.location.search.includes('coins=')) {
    const urlParams = new URLSearchParams(window.location.search);
    const newCoins = urlParams.get('coins');
    if (newCoins) {
        showCoinNotification(newCoins);
    }
}