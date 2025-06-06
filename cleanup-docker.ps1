param(
    [switch]$Force,
    [switch]$All
)

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

Write-Info "🧹 Docker Cleanup Utility"
Write-Info "   Deep cleaning Docker artifacts to free up space"
Write-Info ""

# Get current disk usage
$initialSize = (docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}" | Measure-Object -Line).Lines

Write-Info "📊 Current Docker disk usage:"
docker system df

Write-Info ""
Write-Warning "⚠️  This will remove:"
Write-Warning "   • All stopped containers"
Write-Warning "   • All unused networks"
Write-Warning "   • All dangling images"
Write-Warning "   • All build cache"
if ($All) {
    Write-Warning "   • All unused images (not just dangling)"
    Write-Warning "   • All unused volumes"
}

# Confirmation unless forced
if (-not $Force) {
    $confirmation = Read-Host "Continue? (y/N)"
    if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
        Write-Info "Cleanup cancelled."
        exit 0
    }
}

Write-Info ""
Write-Info "🧹 Starting cleanup..."

# Stop all running containers for RAGdoll
Write-Info "   → Stopping RAGdoll containers..."
docker-compose -f docker-compose.fast.yml down --remove-orphans 2>$null
docker-compose -f docker-compose.full.yml down --remove-orphans 2>$null
docker-compose -f docker-compose.yml down --remove-orphans 2>$null

# Remove stopped containers
Write-Info "   → Removing stopped containers..."
$stoppedContainers = docker ps -aq --filter "status=exited"
if ($stoppedContainers) {
    docker rm $stoppedContainers 2>$null
}

# Remove dangling images
Write-Info "   → Removing dangling images..."
$danglingImages = docker images -f "dangling=true" -q
if ($danglingImages) {
    docker rmi $danglingImages 2>$null
}

# Remove unused networks
Write-Info "   → Removing unused networks..."
docker network prune -f 2>$null

# Remove build cache
Write-Info "   → Removing build cache..."
docker builder prune -f 2>$null

if ($All) {
    # Remove all unused images
    Write-Info "   → Removing all unused images..."
    docker image prune -a -f 2>$null
    
    # Remove unused volumes
    Write-Info "   → Removing unused volumes..."
    docker volume prune -f 2>$null
}

# Final system cleanup
Write-Info "   → Running final system cleanup..."
docker system prune -f 2>$null

Write-Success ""
Write-Success "✅ Cleanup completed!"

# Show final disk usage
Write-Info ""
Write-Info "📊 Final Docker disk usage:"
docker system df

Write-Info ""
Write-Success "🎉 Docker cleanup complete!"
Write-Info "   💾 Space has been freed up"
Write-Info "   🚀 Ready for fast builds with: .\build-fast.ps1"
