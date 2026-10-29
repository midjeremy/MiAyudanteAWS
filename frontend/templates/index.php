<?php
// ==========================================
// DATOS DE LAS FUNCIONALIDADES
// ==========================================
$funciones = [
    [
        "icono" => "🔍",
        "titulo" => "Explora carreras",
        "descripcion" => "Encuentra carreras de diferentes instituciones en un solo lugar.",
        "enlace" => "/templates/carreras.php"
    ],
    [
        "icono" => "⚖️",
        "titulo" => "Compara opciones",
        "descripcion" => "Compara carreras y revisa sus principales características.",
        "enlace" => "/templates/comparar.php"
    ],
    [
        "icono" => "🧠",
        "titulo" => "Test vocacional",
        "descripcion" => "Descubre qué carreras se relacionan con tus intereses.",
        "enlace" => "pages/test.php"
    ]
];

$busqueda = "";
if (isset($_GET["buscar"])) {
    $busqueda = trim($_GET["buscar"]);
}
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Ayudante</title>
    <!-- CSS -->
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body class="app-body">

    <!-- ==========================================
         BARRA DE NAVEGACIÓN SUPERIOR
    ========================================== -->
    <nav class="navbar">
        <div class="nav-brand">
            <span class="nav-logo-icon">🎓</span>
            <div class="nav-logo-text">
                <strong>Mi Ayudante</strong>
                <span>Tu futuro, nuestra guía</span>
            </div>
        </div>
        <ul class="nav-links">
            <li><a href="index.php" class="active">Inicio</a></li>
            <li><a href="/templates/carreras.php">Explorar carreras</a></li>
            <li><a href="/templates/comparar.php">Comparar</a></li>
            <li><a href="pages/test.php">Test vocacional</a></li>
        </ul>
        
        <!-- ACCIONES DE LA NAVBAR -->
        <div class="nav-actions">
            <a href="/templates/guardados.php" class="btn-action-saved" title="Guardados">
                <span>❤️</span> Guardados
            </a>
            <button class="btn-icon" title="Notificaciones">
                🔔
            </button>
            
            <!-- MENÚ DESPLEGABLE DE USUARIO CON AVATAR DE GATO -->
            <details class="user-menu-container">
                <summary class="user-menu-btn" title="Perfil">
                    <img src="/static/img/gato-avatar.png" alt="Perfil" class="user-avatar-img">
                    <span class="dropdown-arrow">▼</span>
                </summary>
                
                <div class="user-dropdown">
                    <a href="pages/perfil.php" class="dropdown-item">Perfil</a>
                    <div class="dropdown-divider"></div>
                    <a href="logout.php" class="dropdown-item logout-item">Cerrar sesión</a>
                </div>
            </details>
        </div>
    </nav>

    <!-- ==========================================
         CONTENIDO PRINCIPAL
    ========================================== -->
    <main class="main-container">

        <!-- PORTADA -->
        <section class="portada">
            <div class="portada-content">
                <span class="portada-tag">🎓 Orientación para estudiantes</span>
                
                <h1>Encuentra la carrera <span>ideal para ti</span></h1>
                
                <p>Compara carreras, descubre tus intereses y encuentra información para tomar la mejor decisión sobre tu futuro.</p>

                <!-- BUSCADOR -->
                <form class="search-box" method="GET" action="index.php">
                    <input type="text" name="buscar" placeholder="¿Qué carrera estás buscando?" value="<?= htmlspecialchars($busqueda) ?>">
                    <button type="submit">🔍</button>
                </form>

                <!-- BOTONES -->
                <div class="portada-buttons">
                    <a href="/templates/carreras.php" class="btn btn-primary">Explorar carreras</a>
                    <a href="pages/test.php" class="btn btn-secondary">Hacer test vocacional</a>
                </div>
            </div>

            <div class="portada-illustration">
                <img src="/static/img/portada.png" alt="Ilustración Orientación">
            </div>
        </section>

        <!-- FUNCIONALIDADES -->
        <section class="features" id="funciones">
            <?php foreach ($funciones as $funcion): ?>
                <article class="feature-card">
                    <div class="feature-icon">
                        <?= $funcion["icono"] ?>
                    </div>
                    <h2><?= $funcion["titulo"] ?></h2>
                    <p><?= $funcion["descripcion"] ?></p>
                    <a href="<?= $funcion["enlace"] ?>">Ver más →</a>
                </article>
            <?php endforeach; ?>
        </section>

        <!-- INFORMACIÓN -->
        <section class="information">
            <div class="information-icon">🛡️</div>
            <div>
                <h3>Información actualizada y confiable</h3>
                <p>Datos de instituciones de educación superior en Chile.</p>
            </div>
        </section>

    </main>

    <!-- ==========================================
         FOOTER
    ========================================== -->
    <footer class="footer">
        <p>© <?= date("Y") ?> Mi Ayudante</p>
        <p>Plataforma de orientación para estudiantes</p>
    </footer>

</body>
</html>