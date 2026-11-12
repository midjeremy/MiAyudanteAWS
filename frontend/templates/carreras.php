<?php
// INICIAR LA SESIÓN Y CARGAR LA API BFF
session_start();
require_once 'api.php';
require_once 'catalogo.php';

if (!isset($_SESSION['favoritos'])) {
    $_SESSION['favoritos'] = [];
}

// Lógica de favoritos
if (isset($_GET['toggle_fav'])) {
    $id_fav = intval($_GET['toggle_fav']);
    $index = array_search($id_fav, $_SESSION['favoritos']);
    
    if ($index !== false) {
        unset($_SESSION['favoritos'][$index]);
        $_SESSION['favoritos'] = array_values($_SESSION['favoritos']);
    } else {
        $_SESSION['favoritos'][] = $id_fav;
    }
    
    $params = $_GET;
    unset($params['toggle_fav']);
    $url_limpia = 'carreras.php' . (!empty($params) ? '?' . http_build_query($params) : '');
    header("Location: " . $url_limpia);
    exit;
}

// FILTROS DE BÚSQUEDA
$busqueda     = isset($_GET['q']) ? trim($_GET['q']) : '';
$area         = isset($_GET['area']) ? $_GET['area'] : '';
$institucion  = isset($_GET['institucion']) ? $_GET['institucion'] : '';
$modalidad    = isset($_GET['modalidad']) ? $_GET['modalidad'] : '';
$region       = isset($_GET['region']) ? trim($_GET['region']) : '';
$pagina       = max(1, intval($_GET['page'] ?? 1));
$carrera_id   = max(0, intval($_GET['carrera_id'] ?? 0));

// Vista por defecto: una tarjeta por carrera. Al elegir una carrera se ven sus ofertas
$vista        = ($carrera_id > 0) ? 'ofertas' : 'carreras';
$carrera_id_val = ($carrera_id > 0) ? $carrera_id : '';

$parametros = array_filter([
    'q'           => $busqueda,
    'institucion' => $institucion,
    'modalidad'   => $modalidad,
    'region'      => $region,
    'carrera_id'  => $carrera_id_val,
    'page'        => $pagina,
    'page_size'   => TAMANO_PAGINA,
], fn($valor) => $valor !== '');

// El área aún no existe en los datos: se aproxima por el nombre de la carrera
if ($area === 'diseno') {
    $parametros['carrera'] = 'diseño';
} elseif ($area === 'tecnologia') {
    $parametros['excluir'] = 'diseño';
}

$endpoint = ($vista === 'carreras') ? '/api/v1/carreras/?' : '/api/v1/ofertas/?';
$respuesta = api_get($endpoint . http_build_query($parametros));
if ($respuesta === null && $pagina > 1) {
    $pagina = 1;
    $parametros['page'] = 1;
    $respuesta = api_get($endpoint . http_build_query($parametros));
}
if ($respuesta === null) {
    $error_api = 'No se pudo cargar el catálogo. Inténtalo más tarde.';
    $respuesta = ['count' => 0, 'results' => []];
}

$filtros = api_get('/api/v1/filtros/') ?? ['sedes' => [], 'regiones' => []];

$carreras = array_map(($vista === 'carreras') ? 'carrera_a_tarjeta' : 'oferta_a_tarjeta', $respuesta['results']);
$total_resultados = $respuesta['count'];
$total_paginas = max(1, (int) ceil($total_resultados / TAMANO_PAGINA));

function enlace_pagina(int $numero): string{
    return 'carreras.php?' . http_build_query(array_merge($_GET, ['page' => $numero]));
}
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Explorar carreras - Mi Ayudante</title>
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
        
        <header class="page-header">
            <h1>Explorar carreras</h1>
            <p>Encuentra la carrera que se adapta a ti en INACAP y Duoc UC.</p>
        </header>

        <?php if (!empty($error_api)): ?>
            <div style="background-color: #fee2e2; border: 1px solid #ef4444; color: #b91c1c; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 14px;">
                <?= htmlspecialchars($error_api) ?>
            </div>
        <?php endif; ?>

        <!-- BARRA DE BÚSQUEDA Y FILTROS -->
        <section class="search-filter-section">
            <form action="carreras.php" method="GET" class="search-form">
                <?php if ($carrera_id > 0): ?>
                    <input type="hidden" name="carrera_id" value="<?= $carrera_id ?>">
                <?php endif; ?>
                
                <div class="main-search-bar">
                    <input type="text" name="q" value="<?= htmlspecialchars($busqueda) ?>" placeholder="Buscar carrera">
                    <button type="submit" class="btn-search">🔍</button>
                </div>

                <div class="filters-row">
                    <div class="filter-group">
                        <label>Área de estudio</label>
                        <select name="area" onchange="this.form.submit()">
                            <option value="">Todas</option>
                            <option value="tecnologia" <?= $area === 'tecnologia' ? 'selected' : '' ?>>Tecnología</option>
                            <option value="diseno" <?= $area === 'diseno' ? 'selected' : '' ?>>Diseño</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Institución</label>
                        <select name="institucion" onchange="this.form.submit()">
                            <option value="">Todas</option>
                            <option value="inacap" <?= $institucion === 'inacap' ? 'selected' : '' ?>>INACAP</option>
                            <option value="duoc" <?= $institucion === 'duoc' ? 'selected' : '' ?>>Duoc UC</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Modalidad</label>
                        <select name="modalidad" onchange="this.form.submit()">
                            <option value="">Todas</option>
                            <option value="presencial" <?= $modalidad === 'presencial' ? 'selected' : '' ?>>Presencial</option>
                            <option value="online" <?= $modalidad === 'online' ? 'selected' : '' ?>>Online</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Región</label>
                        <select name="region" onchange="this.form.submit()">
                            <option value="">Todas</option>
                            <?php foreach ($filtros['regiones'] ?? [] as $opcion_region): ?>
                                <?php if ($opcion_region === 'Online') continue; ?>
                                <option value="<?= htmlspecialchars($opcion_region) ?>" <?= $region === $opcion_region ? 'selected' : '' ?>><?= htmlspecialchars($opcion_region) ?></option>
                            <?php endforeach; ?>
                        </select>
                    </div>

                    <a href="carreras.php" class="btn-reset-filters">Limpiar filtros</a>
                </div>
            </form>
        </section>

        <!-- FORMULARIO PARA ENVIAR A COMPARAR -->
        <form action="comparar.php" method="GET">
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div class="results-count">
                    <strong><?= $total_resultados ?></strong> <?= $vista === 'carreras' ? 'carreras encontradas' : 'ofertas encontradas' ?>
                    <?php if ($carrera_id > 0): ?>
                        · <a href="carreras.php">← Volver a todas las carreras</a>
                    <?php endif; ?>
                </div>
                
                <?php if ($total_resultados > 0 && $vista === 'ofertas'): ?>
                <button type="submit" style="background-color: #4f46e5; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">
                    <span>⚖️</span> Comparar seleccionadas
                </button>
                <?php endif; ?>
            </div>

            <!-- LISTA DE TARJETAS DE CARRERAS -->
            <section class="careers-list">
                <?php if ($total_resultados > 0): ?>
                    <?php foreach ($carreras as $carrera): ?>
                        <?php 
                            $es_favorito = in_array($carrera['id'], $_SESSION['favoritos']);
                            $query_params = $_GET;
                            $query_params['toggle_fav'] = $carrera['id'];
                            $link_corazon = 'carreras.php?' . http_build_query($query_params);
                        ?>
                        
                        <div class="career-card" style="position: relative;">
                            
                            <?php if (empty($carrera['es_carrera'])): ?>
                            <!-- CHECKBOX DE SELECCIÓN -->
                            <div style="position: absolute; top: 15px; left: 15px; z-index: 10;">
                                <input type="checkbox" name="ids[]" value="<?= $carrera['id'] ?>" style="width: 20px; height: 20px; cursor: pointer;" title="Seleccionar para comparar">
                            </div>

                            <!-- Botón de favorito -->
                            <a href="<?= $link_corazon ?>" class="btn-heart" title="<?= $es_favorito ? 'Quitar de favoritos' : 'Guardar en favoritos' ?>" style="right: 15px; text-decoration: none;">
                                <?= $es_favorito ? '❤️' : '♡' ?>
                            </a>
                            <?php endif; ?>

                            <div class="card-left-content" style="padding-left: 30px;">
                                <div class="institution-logo <?= $carrera['logo_clase'] ?>">
                                    <?= $carrera['logo_texto'] ?>
                                </div>

                                <div class="career-details">
                                    <h2><a href="<?= !empty($carrera['es_carrera']) ? 'carreras.php?carrera_id=' : 'detalle.php?id=' ?><?= $carrera['id'] ?>"><?= htmlspecialchars($carrera['nombre']) ?></a></h2>
                                    <p class="institution-name"><?= htmlspecialchars($carrera['institucion']) ?></p>

                                    <!-- Etiqueta eliminada para que no aparezca el badge de tecnología ni diseño -->

                                    <div class="career-meta">
                                        <span>📍 <?= htmlspecialchars($carrera['ubicacion']) ?></span>
                                        <span>📖 <?= htmlspecialchars($carrera['modalidad']) ?></span>
                                        <span>⏱ <?= htmlspecialchars($carrera['duracion']) ?></span>
                                    </div>
                                </div>
                            </div>

                            <div class="card-right-content">
                                <div class="price-box">
                                    <strong><?= htmlspecialchars($carrera['arancel']) ?></strong>
                                    <span><?= htmlspecialchars($carrera['arancel_periodo']) ?></span>
                                </div>
                                <?php if (!empty($carrera['es_carrera'])): ?>
                                    <a href="carreras.php?carrera_id=<?= $carrera['id'] ?>" class="btn-details">Ver sedes y aranceles</a>
                                <?php else: ?>
                                    <a href="detalle.php?id=<?= $carrera['id'] ?>" class="btn-details">Ver detalles</a>
                                <?php endif; ?>
                            </div>

                        </div>
                    <?php endforeach; ?>
                <?php else: ?>
                    <div style="background: white; padding: 40px; text-align: center; border-radius: 14px; border: 1px solid #e2e8f0;">
                        <p style="color: #64748b; font-size: 15px;">No se encontraron carreras que coincidan con tu búsqueda.</p>
                    </div>
                <?php endif; ?>
            </section>
        
        </form>

        <?php if ($total_paginas > 1): ?>
        <div class="pagination">
            <a href="<?= $pagina > 1 ? htmlspecialchars(enlace_pagina($pagina - 1)) : '#' ?>" class="page-nav">&lt;</a>
            <?php for ($numero = max(1, $pagina - 2); $numero <= min($total_paginas, $pagina + 2); $numero++): ?>
                <a href="<?= htmlspecialchars(enlace_pagina($numero)) ?>" class="page-num <?= $numero === $pagina ? 'active' : '' ?>"><?= $numero ?></a>
            <?php endfor; ?>
            <a href="<?= $pagina < $total_paginas ? htmlspecialchars(enlace_pagina($pagina + 1)) : '#' ?>" class="page-nav">&gt;</a>
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
                    ¡Hola! ¿Buscas alguna carrera en particular o necesitas ayuda con los filtros?
                </div>
            </div>

            <form class="ai-chat-footer">
                <input type="text" placeholder="Escribe tu duda aquí..." aria-label="Escribe tu duda" maxlength="500" autocomplete="off" required>
                <button type="submit" aria-label="Enviar mensaje">➤</button>
            </form>
        </div>
    </details>

</body>
</html