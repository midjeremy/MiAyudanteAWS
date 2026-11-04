<?php
//INICIAR LA SESIÓN Y CARGAR LA API BFF
session_start();
require_once 'api.php';

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

//CONSUMIR EL CATÁLOGO DESDE DJANGO MEDIANTE cURL (BFF)
$catalogo = api_get('/api/v1/catalogo/');
if ($catalogo === null) {
    $error_api = 'No se pudo cargar el catálogo. Inténtalo más tarde.';
    $catalogo = [];
}

$todas_las_carreras = [];

if (is_array($catalogo)) {
    $contador = 1;
    foreach ($catalogo as $row) {
        $institucion = $row['institucion'] ?? 'INACAP';
        $inst_clave = (stripos($institucion, 'duoc') !== false) ? 'duoc' : 'inacap';
        $logo_texto = ($inst_clave === 'duoc') ? 'DuocUC' : 'inacap';
        $logo_clase = ($inst_clave === 'duoc') ? 'duoc-logo' : 'square-logo';
        
        $nombre_carrera = $row['carrera'] ?? '';
        $area_clave = (stripos($nombre_carrera, 'diseño') !== false) ? 'diseno' : 'tecnologia';
        $categoria = ($area_clave === 'diseno') ? 'Diseño' : 'Tecnología';
        $categoria_clase = ($area_clave === 'diseno') ? 'badge-pink' : 'badge-blue';

        $sede = $row['sede'] ?? 'Santiago';
        $sede_clave = strtolower(str_replace([' ', 'á', 'é', 'í', 'ó', 'ú'], ['_', 'a', 'e', 'i', 'o', 'u'], $sede));

        $modalidad = $row['modalidad'] ?? 'Presencial';
        $modalidad_clave = strtolower($modalidad);

        $semestres = intval($row['duracion_semestres'] ?? 8);
        $anos = round($semestres / 2, 1);
        $duracion = $anos . ' años';

        $arancel_val = $row['valor_anual'] ?? '0';
        $arancel_formateado = is_numeric($arancel_val) ? '$' . number_format(intval($arancel_val), 0, ',', '.') : '$' . $arancel_val;

        $todas_las_carreras[] = [
            "id" => $row['id'] ?? $contador,
            "nombre" => $nombre_carrera,
            "institucion" => $institucion,
            "inst_clave" => $inst_clave,
            "logo_texto" => $logo_texto,
            "logo_clase" => $logo_clase,
            "categoria" => $categoria,
            "area_clave" => $area_clave,
            "categoria_clase" => $categoria_clase,
            "ubicacion" => $sede,
            "sede_clave" => $sede_clave,
            "modalidad" => $modalidad,
            "modalidad_clave" => $modalidad_clave,
            "duracion" => $duracion,
            "arancel" => $arancel_formateado
        ];
        $contador++;
    }
}

//FILTROS DE BÚSQUEDA
$busqueda     = isset($_GET['q']) ? trim($_GET['q']) : '';
$area         = isset($_GET['area']) ? $_GET['area'] : '';
$institucion  = isset($_GET['institucion']) ? $_GET['institucion'] : '';
$modalidad    = isset($_GET['modalidad']) ? $_GET['modalidad'] : '';
$sede         = isset($_GET['sede']) ? $_GET['sede'] : '';

$carreras = array_filter($todas_las_carreras, function ($carrera) use ($busqueda, $area, $institucion, $modalidad, $sede) {
    if ($busqueda !== '') {
        $texto     = mb_strtolower($busqueda);
        $nombre    = mb_strtolower($carrera['nombre']);
        $instName  = mb_strtolower($carrera['institucion']);
        if (strpos($nombre, $texto) === false && strpos($instName, $texto) === false) {
            return false;
        }
    }
    if ($area !== '' && $carrera['area_clave'] !== $area) return false;
    if ($institucion !== '' && $carrera['inst_clave'] !== $institucion) return false;
    if ($modalidad !== '' && $carrera['modalidad_clave'] !== $modalidad) return false;
    if ($sede !== '' && $carrera['sede_clave'] !== $sede) return false;
    return true;
});

$total_resultados = count($carreras);
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Explorar carreras - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/carreras.css">
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
            
            <!-- MENÚ DESPLEGABLE DE USUARIO -->
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

    <!-- CONTENEDOR PRINCIPAL -->
    <main class="main-container">
        
        <!-- ENCABEZADO -->
        <header class="page-header">
            <h1>Explorar carreras</h1>
            <p>Encuentra la carrera que se adapta a ti en INACAP y Duoc UC.</p>
        </header>

        <!-- ALERTA DE ERROR SI LA API FALLA -->
        <?php if (!empty($error_api)): ?>
            <div style="background-color: #fee2e2; border: 1px solid #ef4444; color: #b91c1c; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 14px;">
                <?= htmlspecialchars($error_api) ?>
            </div>
        <?php endif; ?>

        <!-- BARRA DE BÚSQUEDA Y FILTROS -->
        <section class="search-filter-section">
            <form action="carreras.php" method="GET" class="search-form">
                
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
                        <label>Sede</label>
                        <select name="sede" onchange="this.form.submit()">
                            <option value="">Todas</option>
                            <option value="san_joaquin" <?= $sede === 'san_joaquin' ? 'selected' : '' ?>>San Joaquín</option>
                            <option value="la_granja" <?= $sede === 'la_granja' ? 'selected' : '' ?>>La Granja</option>
                            <option value="santiago_centro" <?= $sede === 'santiago_centro' ? 'selected' : '' ?>>Santiago Centro</option>
                            <option value="plaza_vespucio" <?= $sede === 'plaza_vespucio' ? 'selected' : '' ?>>Plaza Vespucio</option>
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
                    <strong><?= $total_resultados ?></strong> resultados encontrados
                </div>
                
                <?php if ($total_resultados > 0): ?>
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
                            
                            <!-- CHECKBOX DE SELECCIÓN -->
                            <div style="position: absolute; top: 15px; left: 15px; z-index: 10;">
                                <input type="checkbox" name="ids[]" value="<?= $carrera['id'] ?>" style="width: 20px; height: 20px; cursor: pointer;" title="Seleccionar para comparar">
                            </div>

                            <!-- Botón de favorito -->
                            <a href="<?= $link_corazon ?>" class="btn-heart" title="<?= $es_favorito ? 'Quitar de favoritos' : 'Guardar en favoritos' ?>" style="right: 15px; text-decoration: none;">
                                <?= $es_favorito ? '❤️' : '♡' ?>
                            </a>

                            <div class="card-left-content" style="padding-left: 30px;">
                                <div class="institution-logo <?= $carrera['logo_clase'] ?>">
                                    <?= $carrera['logo_texto'] ?>
                                </div>

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

                            <div class="card-right-content">
                                <div class="price-box">
                                    <strong><?= htmlspecialchars($carrera['arancel']) ?></strong>
                                    <span>arancel anual aprox.</span>
                                </div>
                                <a href="detalle.php?id=<?= $carrera['id'] ?>" class="btn-details">Ver detalles</a>
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

        <div class="pagination">
            <a href="#" class="page-nav">&lt;</a>
            <a href="#" class="page-num active">1</a>
            <a href="#" class="page-nav">&gt;</a>
        </div>

    </main>

    <!-- ASISTENTE DE IA FLOTANTE Y DESPLEGABLE -->
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

            <div class="ai-chat-footer">
                <input type="text" placeholder="Escribe tu duda aquí...">
                <button type="button">➤</button>
            </div>
        </div>
    </details>

</body>
</html>