<?php
//INICIAR LA SESIÓN Y CARGAR EL BFF (api.php)
session_start();
require_once 'api.php';
require_once 'catalogo.php';

//LEER LOS IDs QUE SELECCIONÓ EL USUARIO EN CARRERAS.PHP (máximo 2)
$ids_seleccionados = isset($_GET['ids']) ? array_slice(array_map('intval', (array) $_GET['ids']), 0, 2) : [];

//PEDIR A DJANGO SOLO ESAS OFERTAS, POR SU ID REAL
$carreras_por_id = [];
if (!empty($ids_seleccionados)) {
    $respuesta = api_get('/api/v1/ofertas/?' . http_build_query(['ids' => implode(',', $ids_seleccionados)]));
    foreach ($respuesta['results'] ?? [] as $row) {
        $inst_clave = strtolower($row['institucion_codigo'] ?? '');
        $semestres = (int) ($row['duracion_semestres'] ?? 0);
        $arancel = arancel_de_oferta($row);

        $carreras_por_id[$row['id']] = [
            'id' => $row['id'],
            'institucion' => $row['institucion'] ?? '',
            'nombre' => $row['carrera'] ?? '',
            'sede_nombre' => $row['sede'] ?? '',
            'sede_ubicacion' => $row['region'] ?? 'Región no informada',
            'tema_color' => ($inst_clave === 'duoc') ? 'card-teal' : 'card-purple',
            'badge_color' => ($inst_clave === 'duoc') ? 'badge-teal' : 'badge-purple',
            'logo_text' => ($inst_clave === 'duoc') ? 'DuocUC' : '■',
            'logo_class' => ($inst_clave === 'duoc') ? 'duoc-logo' : 'square-logo',
            'arancel' => $arancel['monto'],
            'arancel_periodo' => $arancel['periodo'],
            'duracion_anos' => $semestres ? round($semestres / 2, 1) : '-',
            'duracion_semestres' => $semestres ?: '-',
            'titulo' => $row['titulo'] ?? 'No informado',
            'tipo_titulo' => $row['nivel'] ?? 'No informado',
            'modalidad' => $row['modalidad'] ?? 'No informada',
            'jornada' => $row['jornada'] ?? 'No informada',
            'link_malla' => $row['malla_url'] ?? '#'
        ];
    }
}

//RESPETAR EL ORDEN EN QUE EL USUARIO LAS ELIGIÓ
$carreras_seleccionadas = [];
foreach ($ids_seleccionados as $id_sel) {
    if (isset($carreras_por_id[$id_sel])) {
        $carreras_seleccionadas[] = $carreras_por_id[$id_sel];
    }
}

//ASIGNAR LAS COLUMNAS (Máximo 2)
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
                <strong>Mi Ayudante</strong>
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
            <!-- Botón Guardados -->
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
        
        <!-- ENCABEZADO DE LA PÁGINA -->
        <header class="page-header">
            <div>
                <h1>Comparar carreras</h1>
                <p>Selecciona hasta 2 carreras para comparar sus características.</p>
            </div>
        </header>

        <!-- CUADRÍCULA DE CONTENIDO -->
        <div class="comparison-grid">
            
            <!-- COLUMNA IZQUIERDA (BARRA LATERAL) -->
            <aside class="sidebar">
                <!-- Tarjeta: Mis comparaciones -->
                <div class="sidebar-card">
                    <h3>Mis comparaciones</h3>
                    <p class="subtitle">Puedes seleccionar hasta 2 carreras para compararlas.</p>

                    <!-- BUCLE PHP: Lista en la barra lateral -->
                    <?php 
                    $contador_sidebar = 1;
                    if(count($carreras_seleccionadas) > 0):
                        foreach (array_slice($carreras_seleccionadas, 0, 2) as $carrera_sidebar): 
                    ?>
                        <div class="selected-career">
                            <div class="career-number <?= $carrera_sidebar['badge_color'] ?>"><?= $contador_sidebar ?></div>
                            <div class="career-info">
                                <strong><?= htmlspecialchars($carrera_sidebar['nombre']) ?></strong>
                                <span><?= htmlspecialchars($carrera_sidebar['institucion']) ?></span>
                            </div>
                            <button class="btn-remove" title="Quitar">✖</button>
                        </div>
                    <?php 
                        $contador_sidebar++;
                        endforeach; 
                    else:
                    ?>
                        <p style="font-size: 13px; color: #64748b; margin-top: 15px;">Ninguna carrera seleccionada.</p>
                    <?php endif; ?>

                    <a href="carreras.php" class="btn-clear" style="display: block; text-align: center; text-decoration: none; margin-top: 15px;">🗑 Volver y limpiar</a>
                </div>

                <!-- Tarjeta: Agregar carrera -->
                <div class="sidebar-card">
                    <h3>Agregar carrera</h3>
                    <div class="search-box">
                        <input type="text" placeholder="Buscar carrera...">
                        <span class="search-icon">🔍</span>
                    </div>
                    <a href="carreras.php" style="text-decoration: none;">
                        <button class="btn-primary-full" style="width: 100%;">Buscar carreras</button>
                    </a>
                </div>

                <!-- Tarjeta: ¿Cómo funciona? -->
                <div class="info-box">
                    <h4>💡 ¿Cómo funciona?</h4>
                    <p>Compara características clave como arancel, duración, malla curricular y más para tomar la mejor decisión.</p>
                </div>
            </aside>

            <!--ÁREA DE COMPARACIÓN-->
            <section class="comparison-content">
                
                <?php if($carrera1 && $carrera2): ?>
                
                <!-- Encabezados de las carreras-->
                <div class="comparison-headers">
                    <!-- Tarjeta 1-->
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

                    <!--Tarjeta 2-->
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

                <!-- Tabla de comparativos -->
                <div class="comparison-table">
                    
                    <!-- Arancel -->
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

                    <!--Duración-->
                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">⏱</span>
                            <div>
                                <strong>Duración</strong>
                                <span>Tiempo de estudio</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <strong><?= $carrera1['duracion_anos'] ?> años</strong>
                            <span><?= $carrera1['duracion_semestres'] ?> semestres</span>
                        </div>
                        <div class="feature-value">
                            <strong><?= $carrera2['duracion_anos'] ?> años</strong>
                            <span><?= $carrera2['duracion_semestres'] ?> semestres</span>
                        </div>
                    </div>

                    <!--Título-->
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

                    <!--Modalidad-->
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

                    <!--Sede-->
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

                    <!--Malla-->
                    <div class="compre-row border-none">
                        <div class="feature-label">
                            <span class="icon">🎓</span>
                            <div>
                                <strong>Malla curricular</strong>
                                <span>Plan de estudio</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <button class="btn-outline-small" onclick="window.location.href='<?= $carrera1['link_malla'] ?>'">Ver malla curricular ↗</button>
                        </div>
                        <div class="feature-value">
                            <button class="btn-outline-small" onclick="window.location.href='<?= $carrera2['link_malla'] ?>'">Ver malla curricular ↗</button>
                        </div>
                    </div>
                </div>

                <!--Botones inferiores-->
                <div class="bottom-actions">
                    <button class="btn-outline" onclick="window.location.href='carreras.php'">← Volver a resultados</button>
                    <button class="btn-primary">⭐ Ver recomendaciones</button>
                </div>

                <?php else: ?>
                    <!-- Mensaje si seleccionaron 1 o 0 carreras -->
                    <div style="padding: 60px; text-align:center; background-color: #fff; border-radius: 12px; border: 1px solid #e2e8f0;">
                        <h2 style="color: #334155; margin-bottom: 15px;">Necesitas 2 carreras para comparar</h2>
                        <p style="color: #64748b; margin-bottom: 25px;">Por favor, vuelve a la página de explorar carreras y selecciona exactamente 2 carreras marcando sus casillas.</p>
                        <a href="carreras.php" class="btn-primary" style="text-decoration: none; padding: 10px 20px;">Volver a Explorar Carreras</a>
                    </div>
                <?php endif; ?>

            </section>
        </div>
    </main>

    <!-- ASISTENTE DE IA FLOTANTE LATERAL -->
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