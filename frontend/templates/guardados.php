<?php
//INICIAR LA SESIÓN
require_once __DIR__ . '/sesion.php';
requerir_sesion();

require_once 'api.php';
require_once 'catalogo.php';

// Lógica para quitar una carrera de guardados mediante PHP al presionar el corazón rojo
if (isset($_GET['remover'])) {
    $id_remover = intval($_GET['remover']);
    if (isset($_SESSION['favoritos'])) {
        $key = array_search($id_remover, $_SESSION['favoritos']);
        if ($key !== false) {
            unset($_SESSION['favoritos'][$key]);
            $_SESSION['favoritos'] = array_values($_SESSION['favoritos']);
        }
    }
    header("Location: guardados.php");
    exit;
}

// Obtener IDs guardados en la sesión
$ids_guardados = $_SESSION['favoritos'] ?? [];
$carreras_guardadas = [];

// Se piden a Django solo las ofertas guardadas, por su ID real
if (!empty($ids_guardados)) {
    $ids = implode(',', array_map('intval', $ids_guardados));
    $respuesta = api_get('/api/v1/ofertas/?' . http_build_query(['ids' => $ids, 'page_size' => 100]));
    foreach ($respuesta['results'] ?? [] as $row) {
        $carreras_guardadas[] = oferta_a_tarjeta($row);
    }
}
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mis Carreras Guardadas - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/carreras.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
    <link rel="stylesheet" href="/static/css/chat.css">
    <script src="/static/js/chat.js" defer></script>
</head>
<body class="portal-body">

    <!-- BARRA DE NAVEGACIÓN SUPERIOR UNIFICADA -->
    <nav class="navbar">
        <div class="nav-brand">
            <span class="nav-logo-icon">🎓</span>
            <div class="nav-logo-text">
                <strong>Mi Ayudante</strong>
                <span>Tu futuro, nuestra guía</span>
            </div>
        </div>
        <ul class="nav-links">
            <li><a href="index.php">Inicio</a></li>
            <li><a href="carreras.php">Explorar carreras</a></li>
            <li><a href="comparar.php">Comparar</a></li>
            <li><a href="pages/test.php">Test vocacional</a></li>
        </ul>
        <div class="nav-actions">
            <!-- Botón de Guardados Activo -->
            <a href="guardados.php" class="btn-action-saved" title="Guardados" style="border-color: var(--brand-purple); background-color: var(--brand-purple-light); color: var(--brand-purple);">
                <span>❤️</span> Guardados
            </a>
            
            <!-- MENÚ DESPLEGABLE DE USUARIO (CON AVATAR DE GATO) -->
            <details class="user-menu-container">
                <summary class="user-menu-btn" title="Perfil">
                    <img src="/static/img/gato-avatar.png" alt="Perfil" class="user-avatar-img">
                    <span class="dropdown-arrow">▼</span>
                </summary>
                
                <div class="user-dropdown">
                    <a href="perfil.php" class="dropdown-item">Perfil</a>
                    <div class="dropdown-divider"></div>
                    <a href="logout.php" class="dropdown-item logout-item">Cerrar sesión</a>
                </div>
            </details>
        </div>
    </nav>

    <!-- CONTENEDOR PRINCIPAL -->
    <main class="main-container">
        
        <!-- ENCABEZADO DE LA PÁGINA -->
        <header class="page-header">
            <h1>Mis Carreras Guardadas</h1>
            <p>Aquí tienes el listado de las opciones que has marcado como favoritas.</p>
        </header>

        <!-- LISTADO DE CARRERAS FAVORITAS -->
        <section class="careers-list">
            <?php if (count($carreras_guardadas) > 0): ?>
                <?php foreach ($carreras_guardadas as $carrera): ?>
                    
                    <div class="career-card" style="position: relative;">
                        
                        <!-- BOTÓN PARA DESMARCAR/QUITAR DE GUARDADOS -->
                        <a href="guardados.php?remover=<?= $carrera['id'] ?>" class="btn-heart" title="Quitar de favoritos" style="right: 15px; text-decoration: none;">❤️</a>

                        <div class="card-left-content" style="padding-right: 30px;">
                            <!-- Logo Institución -->
                            <div class="institution-logo <?= $carrera['logo_clase'] ?>">
                                <?= $carrera['logo_texto'] ?>
                            </div>

                            <!-- Detalles principales -->
                            <div class="career-details">
                                <h2><a href="detalle.php?id=<?= $carrera['id'] ?>"><?= htmlspecialchars($carrera['nombre']) ?></a></h2>
                                <p class="institution-name"><?= htmlspecialchars($carrera['institucion']) ?></p>

                                <span class="category-badge <?= $carrera['categoria_clase'] ?>">
                                    <?= htmlspecialchars($carrera['categoria']) ?>
                                </span>

                                <div class="career-meta">
                                    <span>📍 <?= htmlspecialchars($carrera['ubicacion']) ?></span>
                                    <span>📖 <?= htmlspecialchars($carrera['modalidad']) ?></span>
                                    <span>⏱ <?= htmlspecialchars($carrera['duracion']) ?></span>
                                </div>
                            </div>
                        </div>

                        <!-- Lado derecho: Arancel y Detalles -->
                        <div class="card-right-content">
                            <div class="price-box">
                                <strong><?= htmlspecialchars($carrera['arancel']) ?></strong>
                                <span><?= htmlspecialchars($carrera['arancel_periodo']) ?></span>
                            </div>
                            <a href="detalle.php?id=<?= $carrera['id'] ?>" class="btn-details">Ver detalles</a>
                        </div>

                    </div>

                <?php endforeach; ?>
            <?php else: ?>
                <!-- Estado vacío si no hay guardados -->
                <div style="background: white; padding: 50px; text-align: center; border-radius: 14px; border: 1px solid var(--border-color, #eaeaea);">
                    <p style="color: var(--text-gray, #666); font-size: 15px; margin-bottom: 15px;">Aún no tienes ninguna carrera guardada en tus favoritos.</p>
                    <a href="carreras.php" class="btn-primary" style="display: inline-block; padding: 10px 20px; background: var(--brand-purple, #6a0dad); color: white; border-radius: 8px; text-decoration: none; font-weight: 600;">Explorar carreras</a>
                </div>
            <?php endif; ?>
        </section>

    </main>

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
                    ¡Hola! Aquí puedes revisar las carreras que guardaste. ¿Quieres que comparemos sus aranceles o duraciones?
                </div>
            </div>

            <form class="ai-chat-footer">
                <input type="text" placeholder="Escribe tu duda aquí..." aria-label="Escribe tu duda" maxlength="500" autocomplete="off" required>
                <button type="submit" aria-label="Enviar mensaje">➤</button>
            </form>
        </div>
    </details>

</body>
</html>