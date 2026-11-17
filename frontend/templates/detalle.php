<?php
session_start();
require_once 'api.php';
require_once 'catalogo.php';

if (!isset($_SESSION['favoritos'])) {
    $_SESSION['favoritos'] = [];
}

$oferta_id = max(0, intval($_GET['id'] ?? 0));
if ($oferta_id === 0) {
    header('Location: carreras.php');
    exit;
}

// Guardar o quitar de favoritos en sesión
if (isset($_GET['toggle_fav'])) {
    $index = array_search($oferta_id, $_SESSION['favoritos']);
    if ($index !== false) {
        unset($_SESSION['favoritos'][$index]);
        $_SESSION['favoritos'] = array_values($_SESSION['favoritos']);
    } else {
        $_SESSION['favoritos'][] = $oferta_id;
    }
    header('Location: detalle.php?id=' . $oferta_id);
    exit;
}

$respuesta = api_get('/api/v1/ofertas/' . $oferta_id . '/');
$detalle = null;
$error_api = '';

if ($respuesta === null || empty($respuesta['id'])) {
    $error_api = 'No se pudo cargar el detalle de la carrera. Verifica tu conexión o inténtalo más tarde.';
} else {
    $detalle = oferta_a_detalle($respuesta);
}

$es_favorito = in_array($oferta_id, $_SESSION['favoritos']);
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $detalle ? htmlspecialchars($detalle['nombre']) . ' - Mi Ayudante' : 'Detalle de carrera - Mi Ayudante' ?></title>
    <link rel="icon" type="image/png" href="../static/img/Birrete.ico">
    <link rel="stylesheet" href="../static/css/carreras.css">
    <link rel="stylesheet" href="../static/css/detalle.css">
    <link rel="stylesheet" href="../static/css/responsive.css">
</head>
<body class="portal-body">

    <!-- BARRA DE NAVEGACIÓN SUPERIOR UNIFICADA -->
    <nav class="navbar">
        <div class="nav-brand">
            <span class="nav-logo-icon">🎓</span>
            <div class="nav-logo-text">
                <a href="index.php">
                    <strong style="color: #000000;">Mi Ayudante</strong>
                </a>
                <span>Tu futuro, nuestra guía</span>
            </div>
        </div>
        <ul class="nav-links">
            <li><a href="index.php">Inicio</a></li>
            <li><a href="carreras.php" class="active">Explorar carreras</a></li>
            <li><a href="comparar.php">Comparar</a></li>
            <li><a href="pages/test.php">Test vocacional</a></li>
        </ul>
        <div class="nav-actions">
            <a href="guardados.php" class="btn-action-saved" title="Guardados">
                <span>❤️</span> Guardados
            </a>

            <details class="user-menu-container">
                <summary class="user-menu-btn" title="Perfil">
                    <img src="../static/img/gato-avatar.png" alt="Perfil" class="user-avatar-img">
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

    <!-- CONTENEDOR PRINCIPAL -->
    <main class="main-container detalle-page">

        <div class="detalle-top-nav">
            <a href="carreras.php" class="link-volver">← Volver a explorar carreras</a>
            <?php if ($detalle && $detalle['carrera_id'] > 0): ?>
                <a href="carreras.php?carrera_id=<?= $detalle['carrera_id'] ?>" class="link-sedes">
                    Ver otras sedes de esta carrera
                </a>
            <?php endif; ?>
        </div>

        <?php if (!empty($error_api)): ?>
            <div class="detalle-error-box">
                <p><?= htmlspecialchars($error_api) ?></p>
                <a href="carreras.php" class="btn-navy-primary">Volver al catálogo</a>
            </div>
        <?php else: ?>

            <!-- ESTRUCTURA PRINCIPAL EN 2 COLUMNAS (IZQUIERDA: FICHA | DERECHA: DETALLES CLAVE) -->
            <div class="detalle-layout-grid">

                <!-- TARJETA IZQUIERDA -->
                <section class="detalle-card-principal">
                    <div class="card-top-bar">
                        <div class="institucion-brand-inline">
                            <span class="inst-icon-box <?= htmlspecialchars($detalle['inst_clave']) ?>">
                                <?= $detalle['inst_clave'] === 'duoc' ? 'D' : 'I' ?>
                            </span>
                            <span class="inst-brand-name"><?= htmlspecialchars($detalle['institucion']) ?></span>
                        </div>

                        <a href="detalle.php?id=<?= $detalle['id'] ?>&toggle_fav=1"
                           class="btn-circle-fav <?= $es_favorito ? 'saved' : '' ?>"
                           title="<?= $es_favorito ? 'Quitar de guardados' : 'Guardar carrera' ?>">
                            <?= $es_favorito ? '❤️' : '♡' ?>
                        </a>
                    </div>

                    <h1 class="carrera-titulo-principal"><?= htmlspecialchars($detalle['nombre']) ?></h1>

                    <p class="carrera-descripcion">
                        <?= nl2br(htmlspecialchars($detalle['descripcion'])) ?>
                    </p>

                    <div class="carrera-cta-row">
                        <a href="#malla-curricular" class="btn-navy-primary">
                            Ver Malla Curricular
                        </a>
                    </div>

                    <hr class="detalle-separador">

                    <!-- SUB-COLUMNAS INFERIORES: OBJETIVOS Y CAMPO LABORAL -->
                    <div class="detalle-subcolumns">
                        <div class="subcol-bloque">
                            <div class="subcol-header">
                                <span class="subcol-icon" aria-hidden="true">🎯</span>
                                <h2>Objetivos de la Carrera</h2>
                                <span class="pill-navy-tag"><?= htmlspecialchars($detalle['objetivos_badge']) ?></span>
                            </div>
                            <ul class="detalle-bullet-list">
                                <?php foreach ($detalle['objetivos'] as $objetivo): ?>
                                    <li><?= htmlspecialchars($objetivo) ?></li>
                                <?php endforeach; ?>
                            </ul>
                        </div>

                        <div class="subcol-bloque">
                            <div class="subcol-header">
                                <span class="subcol-icon" aria-hidden="true">💼</span>
                                <h2>Campo Laboral</h2>
                                <span class="pill-navy-tag"><?= htmlspecialchars($detalle['campo_badge']) ?></span>
                            </div>
                            <ul class="detalle-bullet-list">
                                <?php foreach ($detalle['campo_laboral'] as $campo): ?>
                                    <li><?= htmlspecialchars($campo) ?></li>
                                <?php endforeach; ?>
                            </ul>
                        </div>
                    </div>
                </section>

                <!-- COLUMNA DERECHA (SIDEBAR) -->
                <aside class="detalle-sidebar-column">

                    <!-- TARJETA SUPERIOR: INSTITUCIÓN -->
                    <div class="sidebar-box sidebar-institucion-box">
                        <span class="inst-icon-box <?= htmlspecialchars($detalle['inst_clave']) ?>">
                            <?= $detalle['inst_clave'] === 'duoc' ? 'D' : 'I' ?>
                        </span>
                        <p>Institución: <strong><?= htmlspecialchars($detalle['institucion']) ?></strong></p>
                    </div>

                    <!-- TARJETA INFERIOR: DETALLES CLAVE Y BOTONES DE ACCIÓN -->
                    <div class="sidebar-box sidebar-claves-box">
                        <h2>Detalles Clave</h2>

                        <dl class="detalles-clave-lista">
                            <div class="clave-item">
                                <dt>Matrícula Anual:</dt>
                                <dd><?= htmlspecialchars($detalle['matricula']) ?></dd>
                            </div>
                            <div class="clave-item">
                                <dt>Arancel Anual:</dt>
                                <dd><?= htmlspecialchars($detalle['arancel']) ?></dd>
                            </div>
                            <div class="clave-item">
                                <dt>Duración:</dt>
                                <dd><?= htmlspecialchars($detalle['duracion_texto']) ?></dd>
                            </div>
                            <div class="clave-item">
                                <dt>Campus:</dt>
                                <dd><?= htmlspecialchars($detalle['campus_texto']) ?></dd>
                            </div>
                            <div class="clave-item">
                                <dt>Modalidad:</dt>
                                <dd><?= htmlspecialchars($detalle['modalidad_texto']) ?></dd>
                            </div>
                        </dl>

                        <div class="sidebar-botones-stack">
                            <a href="comparar.php?ids[]=<?= $detalle['id'] ?>" class="btn-navy-block">
                                Comparar Carrera
                            </a>

                            <?php if (!empty($detalle['malla_pdf'])): ?>
                                <a href="<?= htmlspecialchars($detalle['malla_pdf']) ?>"
                                   target="_blank"
                                   rel="noopener noreferrer"
                                   class="btn-navy-block">
                                    Descargar Malla
                                </a>
                            <?php else: ?>
                                <a href="#malla-curricular" class="btn-navy-block">
                                    Descargar Malla
                                </a>
                            <?php endif; ?>
                        </div>
                    </div>

                </aside>

            </div>

        <?php endif; ?>
    </main>

    <!-- ASISTENTE DE IA FLOTANTE -->
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
                    ¡Hola! ¿Tienes dudas sobre la malla, sede o arancel de <?= $detalle ? htmlspecialchars($detalle['nombre']) : 'esta carrera' ?>?
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