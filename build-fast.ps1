param(
    [switch]$NoCache,
    [switch]$DevMode,
    [switch]$SkipIngestion,
    [switch]$Parallel,
    [switch]$Production,
    [switch]$CleanOnly
)

# Color functions for better output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Success { Write-ColorOutput Green $args }
function Write-Info { Write-ColorOutput Cyan $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }

# Banner
Write-Info "🚀 RAGdoll Fast Build & Deploy System"
Write-Info "   Build time target: <5 minutes (vs 45 minutes)"
Write-Info "   Features: Auto-cleanup, Build caching, Parallel builds"
Write-Info ""

# Enable Docker BuildKit for faster builds
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
$env:BUILDKIT_PROGRESS = "plain"

# Cleanup function
function Invoke-DockerCleanup {
    Write-Warning "🧹 Cleaning up old Docker artifacts..."
    
    # Stop and remove old containers
    Write-Info "   → Stopping old containers..."
    docker-compose -f docker-compose.fast.yml down --remove-orphans 2>$null
    docker-compose -f docker-compose.full.yml down --remove-orphans 2>$null
    
    # Remove dangling images
    Write-Info "   → Removing dangling images..."
    $danglingImages = docker images -f "dangling=true" -q
    if ($danglingImages) {
        docker rmi $danglingImages 2>$null
    }
    
    # Remove old RAGdoll images (keep latest 2)
    Write-Info "   → Cleaning old RAGdoll images..."
    $ragdollImages = docker images --format "table {{.Repository}}:{{.Tag}}" | Where-Object { $_ -match "ragdoll|tparty" } | Select-Object -Skip 4
    if ($ragdollImages) {
        $ragdollImages | ForEach-Object {
            docker rmi $_ 2>$null
        }
    }
    
    # Remove unused volumes (be careful with this)
    Write-Info "   → Removing unused volumes..."
    docker volume prune -f 2>$null
    
    # Remove build cache (if requested)
    if ($NoCache) {
        Write-Info "   → Removing build cache..."
        docker builder prune -f 2>$null
    }
    
    # System cleanup
    Write-Info "   → Running system cleanup..."
    docker system prune -f 2>$null
    
    Write-Success "✅ Cleanup completed!"
}

# If only cleanup requested
if ($CleanOnly) {
    Invoke-DockerCleanup
    Write-Success "🏁 Cleanup complete. Exiting."
    exit 0
}

# Start timing
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

# Cleanup before build
Invoke-DockerCleanup

# Build arguments
$buildArgs = @()
if ($NoCache) { 
    $buildArgs += "--no-cache" 
    Write-Warning "   🔄 Force rebuild (no cache)"
}
if ($Parallel) { 
    $buildArgs += "--parallel" 
    Write-Info "   ⚡ Parallel build enabled"
}

# Determine build target
$target = if ($Production) { "production" } else { "development" }
Write-Info "   🎯 Build target: $target"

# Build services
Write-Success "⚡ Building optimized services..."

try {
    # Build with progress and error handling
    $buildCommand = "docker-compose -f docker-compose.fast.yml build"
    if ($buildArgs) {
        $buildCommand += " " + ($buildArgs -join " ")
    }
    
    Write-Info "   📦 Executing: $buildCommand"
    Invoke-Expression $buildCommand
    
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed with exit code $LASTEXITCODE"
    }
    
    Write-Success "✅ Build completed successfully!"
    
} catch {
    Write-Error "❌ Build failed: $_"
    exit 1
}

# Start services
Write-Success "🚀 Starting services..."

try {
    if ($DevMode) {
        Write-Info "   🔧 Starting in development mode (hot reload enabled)"
        docker-compose -f docker-compose.fast.yml up -d
    } else {
        docker-compose -f docker-compose.fast.yml up -d
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Service startup failed"
    }
    
} catch {
    Write-Error "❌ Service startup failed: $_"
    exit 1
}

# Wait for services to be healthy
Write-Info "⏳ Waiting for services to be ready..."

$maxWait = 60
$waited = 0

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 2
    $waited += 2
    
    # Check Redis
    $redisStatus = docker exec ragdoll-redis redis-cli ping 2>$null
    if ($redisStatus -ne "PONG") {
        Write-Host "." -NoNewline
        continue
    }
    
    # Check API
    try {
        $apiResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($apiResponse.StatusCode -eq 200) {
            break
        }
    } catch {
        Write-Host "." -NoNewline
        continue
    }
}

Write-Host ""

if ($waited -ge $maxWait) {
    Write-Warning "⚠️  Services taking longer than expected to start"
    Write-Info "   You can check status with: docker-compose -f docker-compose.fast.yml ps"
} else {
    Write-Success "✅ All services are ready!"
}

# Run one-time ingestion if needed
if (-not $SkipIngestion) {
    Write-Info "📚 Running one-time data ingestion..."
    
    try {
        docker run --rm --network ragdoll_ragdoll-network `
            -v "${PWD}/data:/app/data:ro" `
            -v "ragdoll_ragdoll-indexes:/app/app/indexes" `
            -v "${PWD}/bge-m3_repo:/app/bge-m3_repo:ro" `
            ragdoll-ragdoll-api:latest python -m app.ingest_namespaced --auto
            
        Write-Success "✅ Data ingestion completed!"
    } catch {
        Write-Warning "⚠️  Ingestion failed, but services are running"
    }
}

# Final timing and URLs
$stopwatch.Stop()
$buildTime = $stopwatch.Elapsed.TotalMinutes

Write-Success ""
Write-Success "🎉 RAGdoll Fast Deploy Complete!"
Write-Success "   ⏱️  Total time: $($buildTime.ToString('F1')) minutes"
Write-Success "   🎯 Target achieved: $(if ($buildTime -lt 10) { '✅ Success' } else { '⚠️  Needs optimization' })"
Write-Success ""
Write-Info "🌐 Access URLs:"
Write-Info "   📊 TParty Frontend: http://localhost:3000"
Write-Info "   🔧 RAGdoll API:     http://localhost:8000"
Write-Info "   📖 API Docs:        http://localhost:8000/docs"
Write-Info "   🔍 Redis:           localhost:6379"
Write-Success ""
Write-Info "🛠️  Management Commands:"
Write-Info "   📊 Status:    docker-compose -f docker-compose.fast.yml ps"
Write-Info "   📋 Logs:      docker-compose -f docker-compose.fast.yml logs -f"
Write-Info "   🛑 Stop:      docker-compose -f docker-compose.fast.yml down"
Write-Info "   🧹 Cleanup:   .\build-fast.ps1 -CleanOnly"

# Show current container status
Write-Info ""
Write-Info "📊 Current Container Status:"
docker-compose -f docker-compose.fast.yml ps
