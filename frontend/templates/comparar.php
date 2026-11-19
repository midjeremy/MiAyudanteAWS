<?php
// INICIAR LA SESIÓN Y CARGAR EL BFF (api.php)
session_start();
require_once 'api.php';
require_once 'catalogo.php';

if (!isset($_SESSION['comparar'])) {
    $_SESSION['comparar'] = [];
}

// LÓGICA PARA ELIMINAR UNA CARRERA AL PRESIONAR LA "✖"
if (isset($_GET['remover'])) {
    $id_a_remover = intval($_GET['remover']);
    $_SESSION['comparar'] = array_values(array_diff($_SESSION['comparar'], [$id_a_remover]));
    
    if (!empty($_SESSION['comparar'])) {
        header("Location: comparar.php?ids=" . implode(',', $_SESSION['comparar']));
    } else {
        header("Location: comparar.php");
    }
    exit;
}

// Limpiar todo el comparador
if (isset($_GET['clear_comp'])) {
    $_SESSION['comparar'] = [];
    header("Location: comparar.php");
    exit;
}

// LEER LOS IDs: SOPORTA TANTO LA URL (GET) COMO LA SESIÓN
$ids_seleccionados = [];
if (isset($_GET['ids']) && !empty($_GET['ids'])) {
    $ids_seleccionados = array_slice(array_map('intval', (array) $_GET['ids']), 0, 2);
    $_SESSION['comparar'] = $ids_seleccionados; 
} elseif (!empty($_SESSION['comparar'])) {
    $ids_seleccionados = array_slice(array_map('intval', $_SESSION['comparar']), 0, 2);
}

// PEDIR A DJANGO LAS OFERTAS SELECCIONADAS
$carreras_por_id = [];
if (!empty($ids_seleccionados)) {
    $respuesta = api_get('/api/v1/ofertas/?' . http_build_query(['ids' => implode(',', $ids_seleccionados)]));
    
    if (empty($respuesta['results'])) {
        $catalogo_raw = api_get('/api/v1/catalogo/');
        if (is_array($catalogo_raw)) {
            $respuesta = ['results' => $catalogo_raw];
        }
    }

    $resultados_api = $respuesta['results'] ?? (is_array($respuesta) ? $respuesta : []);
    
    foreach ($resultados_api as $row) {
        if (!in_array(intval($row['id']), $ids_seleccionados)) {
            continue;
        }

        // Detección robusta de la institución
        $inst_codigo = strtolower($row['institucion_codigo'] ?? '');
        $inst_nombre = strtolower($row['institucion'] ?? '');
        $es_duoc = str_contains($inst_nombre, 'duoc') || $inst_codigo === 'duoc';
        
        $arancel = arancel_de_oferta($row);

        $carreras_por_id[$row['id']] = [
            'id' => $row['id'],
            'institucion' => $row['institucion'] ?? '',
            'nombre' => $row['carrera'] ?? $row['nombre'] ?? '',
            'sede_nombre' => $row['sede'] ?? '',
            'sede_ubicacion' => $row['region'] ?? 'Región no informada',
            'logo_text' => $es_duoc ? 'DuocUC' : 'inacap',
            'logo_class' => $es_duoc ? 'duoc-logo' : 'square-logo',
            'arancel' => $arancel['monto'],
            'arancel_periodo' => $arancel['periodo'],
            'duracion_anos' => duracion_de_oferta($row),
            'duracion_publicada' => ($row['duracion_texto'] ?? '') ?: '-',
            'titulo' => $row['titulo'] ?? 'No informado',
            'tipo_titulo' => $row['nivel'] ?? 'No informado',
            'modalidad' => $row['modalidad'] ?? 'No informada',
            'jornada' => $row['jornada'] ?? 'No informada',
            'link_malla' => $row['malla_url'] ?? '#'
        ];
    }
}

// RESPETAR EL ORDEN EN QUE EL USUARIO LAS ELIGIÓ Y ASIGNAR COLORES INDEPENDIENTES
$carreras_seleccionadas = [];
$paleta_colores = [
    ['tema_color' => 'card-purple', 'badge_color' => 'badge-purple'],
    ['tema_color' => 'card-teal', 'badge_color' => 'badge-teal']
];

$index = 0;
foreach ($ids_seleccionados as $id_sel) {
    if (isset($carreras_por_id[$id_sel])) {
        $carrera_item = $carreras_por_id[$id_sel];
        $estilo = $paleta_colores[$index % count($paleta_colores)];
        $carrera_item['tema_color'] = $estilo['tema_color'];
        $carrera_item['badge_color'] = $estilo['badge_color'];
        
        $carreras_seleccionadas[] = $carrera_item;
        $index++;
    }
}

$carrera1 = $carreras_seleccionadas[0] ?? null;
$carrera2 = $carreras_seleccionadas[1] ?? null;
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comparar Carreras - Mi Ayudante</title>
    <link rel="stylesheet" href="/static/css/comparar.css">
    <link rel="stylesheet" href="/static/css/responsive.css">
    <link rel="stylesheet" href="/static/css/chat.css">
    <script src="/static/js/chat.js" defer></script>
</head>
<body class="app-body">

    <!-- BARRA DE NAVEGACIÓN SUPERIOR -->
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
            <li><a href="carreras.php">Explorar carreras</a></li>
            <li><a href="comparar.php" class="active">Comparar</a></li>
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
            <div>
                <h1>Comparar carreras</h1>
                <p>Compara ofertas académicas de forma interna o cruzada entre instituciones.</p>
            </div>
        </header>

        <div class="comparison-grid">
            
            <!-- BARRA LATERAL -->
            <aside class="sidebar">
                <div class="sidebar-card">
                    <h3>Mis comparaciones</h3>
                    <p class="subtitle">Duoc UC e INACAP</p>

                    <?php 
                    $contador_sidebar = 1;
                    if(count($carreras_seleccionadas) > 0):
                        foreach ($carreras_seleccionadas as $carrera_sidebar): 
                    ?>
                        <div class="selected-career">
                            <div class="career-number <?= $carrera_sidebar['badge_color'] ?>"><?= $contador_sidebar ?></div>
                            <div class="career-info">
                                <strong><?= htmlspecialchars($carrera_sidebar['nombre']) ?></strong>
                                <span><?= htmlspecialchars($carrera_sidebar['institucion']) ?></span>
                            </div>
                            <!-- BOTÓN DE ELIMINAR (X) -->
                            <a href="comparar.php?remover=<?= $carrera_sidebar['id'] ?>" class="btn-remove" title="Quitar" style="text-decoration: none;">✖</a>
                        </div>
                    <?php 
                        $contador_sidebar++;
                        endforeach; 
                    else:
                    ?>
                        <p style="font-size: 13px; color: #64748b; margin-top: 15px;">Ninguna carrera seleccionada.</p>
                    <?php endif; ?>

                    <a href="comparar.php?clear_comp=1" class="btn-clear" style="display: block; text-align: center; text-decoration: none;">🗑 Limpiar todo</a>
                </div>

                <!-- BUSCADOR FUNCIONAL EN EL SIDEBAR -->
                <div class="sidebar-card">
                    <h3>Agregar carrera</h3>
                    <form action="carreras.php" method="GET">
                        <div class="search-box">
                            <span class="search-icon">🔍</span>
                            <input type="text" name="q" placeholder="Buscar carrera..." autocomplete="off">
                        </div>
                        <button type="submit" class="btn-primary-full" style="width: 100%; margin-top: 10px; cursor: pointer;">Explorar carreras</button>
                    </form>
                </div>

                <div class="info-box">
                    <h4>💡 Comparación flexible</h4>
                    <p>Puedes comparar dos opciones de la misma institución o combinarlas entre Duoc UC e INACAP.</p>
                </div>
            </aside>

            <!-- ÁREA DE COMPARACIÓN -->
            <section class="comparison-content">
                
                <?php if($carrera1 && $carrera2): ?>
                
                <div class="comparison-headers">
                    <!-- Tarjeta 1 -->
                    <div class="header-card <?= $carrera1['tema_color'] ?>">
                        <div class="card-top">
                            <div class="inst-logo <?= $carrera1['logo_class'] ?>"><?= $carrera1['logo_text'] ?></div>
                            <span class="heart-icon">♡</span>
                        </div>
                        <span class="inst-name"><?= htmlspecialchars($carrera1['institucion']) ?></span>
                        <h2><?= htmlspecialchars($carrera1['nombre']) ?></h2>
                        <p>Sede <?= htmlspecialchars($carrera1['sede_nombre']) ?></p>
                    </div>

                    <!-- Insignia VS -->
                    <div class="vs-badge">VS</div>

                    <!-- Tarjeta 2 -->
                    <div class="header-card <?= $carrera2['tema_color'] ?>">
                        <div class="card-top">
                            <div class="inst-logo <?= $carrera2['logo_class'] ?>"><?= $carrera2['logo_text'] ?></div>
                            <span class="heart-icon">♡</span>
                        </div>
                        <span class="inst-name"><?= htmlspecialchars($carrera2['institucion']) ?></span>
                        <h2><?= htmlspecialchars($carrera2['nombre']) ?></h2>
                        <p>Sede <?= htmlspecialchars($carrera2['sede_nombre']) ?></p>
                    </div>
                </div>

                <!-- TABLA COMPARATIVA -->
                <div class="comparison-table">
                    
                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">💰</span>
                            <div>
                                <strong>Arancel</strong>
                                <span>Costo referencial</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <strong>$<?= number_format($carrera1['arancel'], 0, ',', '.') ?> CLP</strong>
                            <span><?= htmlspecialchars($carrera1['arancel_periodo']) ?></span>
                        </div>
                        <div class="feature-value">
                            <strong>$<?= number_format($carrera2['arancel'], 0, ',', '.') ?> CLP</strong>
                            <span><?= htmlspecialchars($carrera2['arancel_periodo']) ?></span>
                        </div>
                    </div>

                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">⏱</span>
                            <div>
                                <strong>Duración</strong>
                                <span>Tiempo de estudio</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <strong><?= htmlspecialchars($carrera1['duracion_anos']) ?></strong>
                            <span><?= htmlspecialchars($carrera1['duracion_publicada']) ?></span>
                        </div>
                        <div class="feature-value">
                            <strong><?= htmlspecialchars($carrera2['duracion_anos']) ?></strong>
                            <span><?= htmlspecialchars($carrera2['duracion_publicada']) ?></span>
                        </div>
                    </div>

                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">📜</span>
                            <div>
                                <strong>Título</strong>
                                <span>Grado otorgado</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <strong><?= htmlspecialchars($carrera1['titulo']) ?></strong>
                            <span><?= htmlspecialchars($carrera1['tipo_titulo']) ?></span>
                        </div>
                        <div class="feature-value">
                            <strong><?= htmlspecialchars($carrera2['titulo']) ?></strong>
                            <span><?= htmlspecialchars($carrera2['tipo_titulo']) ?></span>
                        </div>
                    </div>

                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">📖</span>
                            <div>
                                <strong>Modalidad</strong>
                                <span>Formato de estudio</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <strong><?= htmlspecialchars($carrera1['modalidad']) ?></strong>
                            <span><?= htmlspecialchars($carrera1['jornada']) ?></span>
                        </div>
                        <div class="feature-value">
                            <strong><?= htmlspecialchars($carrera2['modalidad']) ?></strong>
                            <span><?= htmlspecialchars($carrera2['jornada']) ?></span>
                        </div>
                    </div>

                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">📍</span>
                            <div>
                                <strong>Sede</strong>
                                <span>Ubicación</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <strong><?= htmlspecialchars($carrera1['sede_nombre']) ?></strong>
                            <span><?= htmlspecialchars($carrera1['sede_ubicacion']) ?></span>
                        </div>
                        <div class="feature-value">
                            <strong><?= htmlspecialchars($carrera2['sede_nombre']) ?></strong>
                            <span><?= htmlspecialchars($carrera2['sede_ubicacion']) ?></span>
                        </div>
                    </div>

                    <div class="compare-row border-none">
                        <div class="feature-label">
                            <span class="icon">🎓</span>
                            <div>
                                <strong>Malla curricular</strong>
                                <span>Plan de estudio</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <button class="btn-outline-small" onclick="window.location.href='<?= htmlspecialchars($carrera1['link_malla']) ?>'">Ver malla curricular ↗</button>
                        </div>
                        <div class="feature-value">
                            <button class="btn-outline-small" onclick="window.location.href='<?= htmlspecialchars($carrera2['link_malla']) ?>'">Ver malla curricular ↗</button>
                        </div>
                    </div>
                </div>

                <div class="bottom-actions">
                    <button class="btn-outline" onclick="window.location.href='carreras.php'">← Volver a resultados</button>
                    <button class="btn-primary">⭐ Ver recomendaciones</button>
                </div>

                <?php else: ?>
                    <div style="padding: 60px; text-align:center; background-color: #fff; border-radius: 12px; border: 1px solid #e2e8f0;">
                        <h2 style="color: #334155; margin-bottom: 15px;">Necesitas 2 carreras para comparar</h2>
                        <p style="color: #64748b; margin-bottom: 25px;">Por favor, vuelve a la página de explorar carreras y selecciona exactamente 2 carreras marcando sus casillas.</p>
                        <a href="carreras.php" class="btn-primary" style="text-decoration: none; padding: 10px 20px;">Volver a Explorar Carreras</a>
                    </div>
                <?php endif; ?>

            </section>
        </div>
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
                    ¡Hola! Veo que estás comparando carreras. ¿Te ayudo a analizar cuál se adapta mejor a tu presupuesto o jornada?
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