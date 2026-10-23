<?php
// 1. INICIAR LA SESIÓN
session_start();

$todas_las_carreras = [
    [
        "id" => 1,
        "nombre" => "Ingeniería en Informática",
        "institucion" => "INACAP",
        "inst_clave" => "inacap",
        "logo_texto" => "inacap",
        "logo_clase" => "square-logo",
        "categoria" => "Tecnología",
        "area_clave" => "tecnologia",
        "categoria_clase" => "badge-blue",
        "ubicacion" => "La Granja",
        "sede_clave" => "la_granja",
        "modalidad" => "Presencial",
        "modalidad_clave" => "presencial",
        "duracion" => "4 años",
        "arancel" => "$2.350.000",
        "favorito" => false
    ],
    [
        "id" => 2,
        "nombre" => "Analista Programador",
        "institucion" => "Duoc UC",
        "inst_clave" => "duoc",
        "logo_texto" => "DuocUC",
        "logo_clase" => "duoc-logo",
        "categoria" => "Tecnología",
        "area_clave" => "tecnologia",
        "categoria_clase" => "badge-blue",
        "ubicacion" => "San Joaquín",
        "sede_clave" => "san_joaquin",
        "modalidad" => "Presencial",
        "modalidad_clave" => "presencial",
        "duracion" => "2 años",
        "arancel" => "$1.750.000",
        "favorito" => false
    ],
    [
        "id" => 3,
        "nombre" => "Ingeniería en Telecomunicaciones",
        "institucion" => "INACAP",
        "inst_clave" => "inacap",
        "logo_texto" => "inacap",
        "logo_clase" => "square-logo",
        "categoria" => "Tecnología",
        "area_clave" => "tecnologia",
        "categoria_clase" => "badge-blue",
        "ubicacion" => "Santiago Centro",
        "sede_clave" => "santiago_centro",
        "modalidad" => "Presencial",
        "modalidad_clave" => "presencial",
        "duracion" => "4 años",
        "arancel" => "$2.200.000",
        "favorito" => false
    ],
    [
        "id" => 4,
        "nombre" => "Diseño Gráfico Digital",
        "institucion" => "Duoc UC",
        "inst_clave" => "duoc",
        "logo_texto" => "DuocUC",
        "logo_clase" => "duoc-logo",
        "categoria" => "Diseño",
        "area_clave" => "diseno",
        "categoria_clase" => "badge-pink",
        "ubicacion" => "Plaza Vespucio",
        "sede_clave" => "plaza_vespucio",
        "modalidad" => "Presencial",
        "modalidad_clave" => "presencial",
        "duracion" => "4 años",
        "arancel" => "$2.100.000",
        "favorito" => false
    ]
];

$busqueda     = isset($_GET['q']) ? trim($_GET['q']) : '';
$area         = isset($_GET['area']) ? $_GET['area'] : '';
$institucion = isset($_GET['institucion']) ? $_GET['institucion'] : '';
$modalidad   = isset($_GET['modalidad']) ? $_GET['modalidad'] : '';
$sede         = isset($_GET['sede']) ? $_GET['sede'] : '';

$carreras = array_filter($todas_las_carreras, function ($carrera) use ($busqueda, $area, $institucion, $modalidad, $sede) {
    
    // Filtrar por texto ingresado (Nombre o Institución)
    if ($busqueda !== '') {
        $texto     = mb_strtolower($busqueda);
        $nombre    = mb_strtolower($carrera['nombre']);
        $instName  = mb_strtolower($carrera['institucion']);

        if (strpos($nombre, $texto) === false && strpos($instName, $texto) === false) {
            return false;
        }
    }

    // Filtrar por Área
    if ($area !== '' && $carrera['area_clave'] !== $area) {
        return false;
    }

    // Filtrar por Institución
    if ($institucion !== '' && $carrera['inst_clave'] !== $institucion) {
        return false;
    }

    // Filtrar por Modalidad
    if ($modalidad !== '' && $carrera['modalidad_clave'] !== $modalidad) {
        return false;
    }

    // Filtrar por Sede
    if ($sede !== '' && $carrera['sede_clave'] !== $sede) {
        return false;
    }

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
            <li><a href="test.php">Test vocacional</a></li>
            <li><a href="ia.php">Asistente IA</a></li>
        </ul>
        <div class="nav-actions">
            <a href="guardados.php" class="btn-action-saved" title="Guardados">
                <span>❤️</span> Guardados
            </a>
            <button class="btn-icon" title="Notificaciones">🔔</button>
            
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
        
        <!-- ENCABEZADO -->
        <header class="page-header">
            <h1>Explorar carreras</h1>
            <p>Encuentra la carrera que se adapta a ti en INACAP y Duoc UC.</p>
        </header>

        <!-- BARRA DE BÚSQUEDA Y FILTROS -->
        <section class="search-filter-section">
            <form action="carreras.php" method="GET" class="search-form">
                
                <!-- Búsqueda Principal -->
                <div class="main-search-bar">
                    <input type="text" name="q" value="<?= htmlspecialchars($busqueda) ?>" placeholder="Buscar carrera">
                    <button type="submit" class="btn-search">🔍</button>
                </div>

                <!-- Selectores de Filtro -->
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
            
            <!-- HEADER DE RESULTADOS Y BOTÓN COMPARAR -->
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
                        
                        <div class="career-card" style="position: relative;">
                            
                            <!-- CHECKBOX DE SELECCIÓN -->
                            <div style="position: absolute; top: 15px; left: 15px; z-index: 10;">
                                <input type="checkbox" name="ids[]" value="<?= $carrera['id'] ?>" style="width: 20px; height: 20px; cursor: pointer;" title="Seleccionar para comparar">
                            </div>

                            <!-- Botón de favorito -->
                            <button class="btn-heart" title="Guardar en favoritos" style="right: 15px;">♡</button>

                            <div class="card-left-content" style="padding-left: 30px;">
                                <!-- Logo institución -->
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

                            <!-- Lado derecho: Arancel y Acción -->
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

        <!-- PAGINACIÓN -->
        <div class="pagination">
            <a href="#" class="page-nav">&lt;</a>
            <a href="#" class="page-num active">1</a>
            <a href="#" class="page-nav">&gt;</a>
        </div>

    </main>

</body>
</html>