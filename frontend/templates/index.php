<?php
// ==========================================
// INICIAR SESIÓN Y DATOS DE LA PÁGINA
// ==========================================
session_start();

$funciones = [
    [
        "icono" => "🔍",
        "titulo" => "Explora carreras",
        "descripcion" => "Encuentra carreras de diferentes instituciones en un solo lugar.",
        "enlace" => "carreras.php"
    ],
    [
        "icono" => "⚖️",
        "titulo" => "Compara opciones",
        "descripcion" => "Compara carreras y revisa sus principales características.",
        "enlace" => "comparar.php"
    ],
    [
        "icono" => "🧠",
        "titulo" => "Test vocacional",
        "descripcion" => "Descubre qué carreras se relacionan con tus intereses.",
        "enlace" => "pages/test.php"
    ]
];

$busqueda = "";
if (isset($_GET["q"])) {
    $busqueda = trim($_GET["q"]);
}
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mi Ayudante - Inicio</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
</head>
<body class="app-body">

    <!-- BARRA DE NAVEGACIÓN SUPERIOR -->
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
            <li><a href="carreras.php">Explorar carreras</a></li>
            <li><a href="comparar.php">Comparar</a></li>
            <li><a href="pages/test.php">Test vocacional</a></li>
        </ul>
        
        <!-- ACCIONES DE LA NAVBAR -->
        <div class="nav-actions">
            <a href="guardados.php" class="btn-action-saved" title="Guardados">
                <span>❤️</span> Guardados
            </a>
            
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

    <!-- CONTENIDO PRINCIPAL -->
    <main class="main-container">

        <!-- PORTADA -->
        <section class="portada">
            <div class="portada-content">
                <span class="portada-tag">🎓 Orientación para estudiantes</span>
                
                <h1>Encuentra la carrera <span>ideal para ti</span></h1>
                
                <p>Compara carreras, descubre tus intereses y encuentra información para tomar la mejor decisión sobre tu futuro.</p>

                <form class="search-box" method="GET" action="carreras.php">
                    <input type="text" name="q" placeholder="¿Qué carrera estás buscando?" value="<?= htmlspecialchars($busqueda) ?>" required>
                    <button type="submit" style="background:none; border:none; cursor:pointer;">🔍</button>
                </form>

                <div class="portada-buttons">
                    <a href="carreras.php" class="btn btn-primary">Explorar carreras</a>
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
                    <div class="feature-icon"><?= $funcion["icono"] ?></div>
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

    <!-- FOOTER -->
    <footer class="footer">
        <p>© <?= date("Y") ?> Mi Ayudante</p>
        <p>Plataforma de orientación para estudiantes</p>
    </footer>

    <!-- ASISTENTE DE IA FLOTANTE LATERAL (NATIVO CON <details>) -->
    <details id="ai-assistant-wrapper">
        <summary id="ai-toggle-btn">
            <span>🤖</span> Asistente IA
        </summary>
        
        <div class="ai-chat-box">
            <div class="ai-chat-header">
                <div class="ai-header-title">
                    <span>🤖</span>
                    <div>
                        <strong>Asistente Virtual IA</strong>
                        <span>Orientación vocacional</span>
                    </div>
                </div>
            </div>

            <div class="ai-chat-body">
                <div class="ai-message bot">
                    ¡Hola! Soy tu asistente de IA. ¿Tienes dudas sobre alguna carrera, arancel o institución?
                </div>
            </div>

            <div class="ai-chat-footer">
                <input type="text" placeholder="Escribe tu duda aquí...">
                <button type="button">➤</button>
            </div>
        </div>
    </details>

</body>
</html>