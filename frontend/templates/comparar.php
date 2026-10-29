<?php
// 1. INICIAR LA SESIÓN
session_start();

$todas_las_carreras = [
    [
        'id' => 1,
        'institucion' => 'INACAP',
        'nombre' => 'Ingeniería en Informática',
        'sede_nombre' => 'La Granja',
        'sede_ubicacion' => 'Santiago, RM',
        'tema_color' => 'card-purple',   
        'badge_color' => 'badge-purple', 
        'logo_text' => '■',
        'logo_class' => 'square-logo',
        'arancel' => 2350000,
        'duracion_anos' => 4,
        'duracion_semestres' => 8,
        'titulo' => 'Ingeniero en Informática',
        'tipo_titulo' => 'Título profesional',
        'modalidad' => 'Presencial',
        'jornada' => 'Diurno',
        'campo_laboral' => 'Desarrollo de software, gestión de proyectos TI, bases de datos y arquitectura de sistemas.',
        'link_malla' => '#'
    ],
    [
        'id' => 2,
        'institucion' => 'Duoc UC',
        'nombre' => 'Analista Programador',
        'sede_nombre' => 'San Joaquín',
        'sede_ubicacion' => 'Santiago, RM',
        'tema_color' => 'card-teal',
        'badge_color' => 'badge-teal',
        'logo_text' => 'DuocUC',
        'logo_class' => 'duoc-logo',
        'arancel' => 1750000,
        'duracion_anos' => 2,
        'duracion_semestres' => 4,
        'titulo' => 'Analista Programador',
        'tipo_titulo' => 'Título técnico',
        'modalidad' => 'Presencial',
        'jornada' => 'Diurno y Vespertino',
        'campo_laboral' => 'Desarrollo web, creación de aplicaciones móviles, soporte de software y bases de datos.',
        'link_malla' => '#'
    ],
    [
        'id' => 3,
        'institucion' => 'INACAP',
        'nombre' => 'Ingeniería en Telecomunicaciones',
        'sede_nombre' => 'Santiago Centro',
        'sede_ubicacion' => 'Santiago, RM',
        'tema_color' => 'card-blue',
        'badge_color' => 'badge-blue',
        'logo_text' => '■',
        'logo_class' => 'square-logo',
        'arancel' => 2200000,
        'duracion_anos' => 4,
        'duracion_semestres' => 8,
        'titulo' => 'Ingeniero en Telecomunicaciones',
        'tipo_titulo' => 'Título profesional',
        'modalidad' => 'Presencial',
        'jornada' => 'Diurno',
        'campo_laboral' => 'Redes empresariales, ciberseguridad, administración de servidores y fibra óptica.',
        'link_malla' => '#'
    ],
    [
        'id' => 4,
        'institucion' => 'Duoc UC',
        'nombre' => 'Diseño Gráfico Digital',
        'sede_nombre' => 'Plaza Vespucio',
        'sede_ubicacion' => 'Santiago, RM',
        'tema_color' => 'card-pink',
        'badge_color' => 'badge-pink',
        'logo_text' => 'DuocUC',
        'logo_class' => 'duoc-logo',
        'arancel' => 2100000,
        'duracion_anos' => 4,
        'duracion_semestres' => 8,
        'titulo' => 'Diseñador Gráfico',
        'tipo_titulo' => 'Título profesional',
        'modalidad' => 'Presencial',
        'jornada' => 'Diurno',
        'campo_laboral' => 'Agencias de publicidad, branding, diseño UX/UI, y producción editorial.',
        'link_malla' => '#'
    ]
];

// 2. LEER LOS IDs QUE VIENEN DE LA PÁGINA ANTERIOR
$ids_seleccionados = isset($_GET['ids']) ? $_GET['ids'] : [];

// 3. BUSCAR LAS CARRERAS QUE COINCIDAN CON LOS IDs
$carreras_seleccionadas = [];
if (!empty($ids_seleccionados)) {
    foreach ($todas_las_carreras as $carrera) {
        if (in_array($carrera['id'], $ids_seleccionados)) {
            $carreras_seleccionadas[] = $carrera;
        }
    }
}

// 4. ASIGNAR LAS COLUMNAS (Máximo 2)
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
            <li><a href="test.php">Test vocacional</a></li>
            <li><a href="ia.php">Asistente IA</a></li>
        </ul>
        <div class="nav-actions">
            <button class="btn-icon">❤️ Guardados</button>
            <button class="btn-icon">🔔</button>
            
            <!-- MENÚ DESPLEGABLE DE USUARIO (CON AVATAR DE GATO) -->
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

                    <!-- BUCLE PHP: Genera automáticamente la lista en la barra lateral -->
                    <?php 
                    $contador = 1;
                    if(count($carreras_seleccionadas) > 0):
                        foreach (array_slice($carreras_seleccionadas, 0, 2) as $carrera_sidebar): 
                    ?>
                        <div class="selected-career">
                            <div class="career-number <?= $carrera_sidebar['badge_color'] ?>"><?= $contador ?></div>
                            <div class="career-info">
                                <strong><?= htmlspecialchars($carrera_sidebar['nombre']) ?></strong>
                                <span><?= htmlspecialchars($carrera_sidebar['institucion']) ?></span>
                            </div>
                            <button class="btn-remove" title="Quitar">✖</button>
                        </div>
                    <?php 
                        $contador++;
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
                
                <?php if($carrera1 && $carrera2): // Requiere exactamente 2 carreras para comparar bien ?>
                
                <!-- Encabezados de las carreras-->
                <div class="comparison-headers">
                    <!-- Tarjeta 1-->
                    <div class="header-card <?= $carrera1['tema_color'] ?>">
                        <div class="card-top">
                            <div class="inst-logo <?= $carrera1['logo_class'] ?>"><?= $carrera1['logo_text'] ?></div>
                            <span class="heart-icon">♡</span>
                        </div>
                        <span class="inst-name"><?= $carrera1['institucion'] ?></span>
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
                        <span class="inst-name"><?= $carrera2['institucion'] ?></span>
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
                                <strong>Arancel anual</strong>
                                <span>Costo referencial</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <strong>$<?= number_format($carrera1['arancel'], 0, ',', '.') ?> CLP</strong>
                            <span>Valor anual</span>
                        </div>
                        <div class="feature-value">
                            <strong>$<?= number_format($carrera2['arancel'], 0, ',', '.') ?> CLP</strong>
                            <span>Valor anual</span>
                        </div>
                    </div>

                    <!--Duracion-->
                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">⏱</span>
                            <div>
                                <strong>Duracion</strong>
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

                    <!--titulo-->
                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">📜</span>
                            <div>
                                <strong>Titulo</strong>
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

                    <!--modalidad-->
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

                    <!--sede-->
                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">📍</span>
                            <div>
                                <strong>Sede</strong>
                                <span>Ubicacion</span>
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

                    <!--campo laboral-->
                    <div class="compare-row">
                        <div class="feature-label">
                            <span class="icon">📈</span>
                            <div>
                                <strong>Campo laboral</strong>
                                <span>Area de desempeño</span>
                            </div>
                        </div>
                        <div class="feature-value">
                            <span class="text-desc"><?= htmlspecialchars($carrera1['campo_laboral']) ?></span>
                        </div>
                        <div class="feature-value">
                            <span class="text-desc"><?= htmlspecialchars($carrera2['campo_laboral']) ?></span>
                        </div>
                    </div>

                    <!--malla-->
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

                <!--botones inferiores-->
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
</body>
</html>