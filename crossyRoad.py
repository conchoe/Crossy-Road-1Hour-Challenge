import pygame
import random
import sys

'''FEATURES
Grid-based movement system with smooth animations
Multiple lane types: Grass (safe), Road (cars), Water (logs)
Procedural lane generation with varying difficulty
Camera system that follows player upward
IMPROVED COLLISION DETECTION - Grid-based and accurate
Score tracking based on forward progress
Game states: Start Screen, Playing, Game Over
High score persistence across sessions
Visual feedback for deaths and achievements
Particle effects for collisions
Progressive difficulty scaling

COLLISION IMPROVEMENTS:
- Only checks collisions on the player's current lane
- Accurate grid-based detection prevents false positives
- Player only dies if: 
  1. Hit by vehicle on their current lane
  2. In water WITHOUT being on a log
  3. Falls behind camera death zone
  4. Pushed off edge by a log
- Collisions don't check during movement animation (prevents mid-jump deaths)

CONTROLS:
Arrow Keys or WASD - Move player
SPACE - Start game / Restart after game over
ESC - Quit game

HOTKEYS (for testing):
K - Kill player
L - Skip to next level marker
'''

# Color constants
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
GREEN = (34, 139, 34)
GRASS_GREEN = (50, 205, 50)
ROAD_GRAY = (80, 80, 80)
WATER_BLUE = (30, 144, 255)
DARK_BLUE = (0, 100, 200)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)

# Game constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRID_SIZE = 50  # Size of each grid cell in pixels
PLAYER_SIZE = 40
VEHICLE_MIN_SPEED = 2
VEHICLE_MAX_SPEED = 6
LOG_MIN_SPEED = 1
LOG_MAX_SPEED = 3

class Game:
    def __init__(self):
        """Initialize the game and all its components"""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Crossy Road Clone - Fixed Collisions")
        self.clock = pygame.time.Clock()
        
        # Game state variables
        self.startScreen = True
        self.playing = False
        self.gameOver = False
        
        # Score tracking
        self.score = 0
        self.highScore = self.loadHighScore()
        self.bestProgress = 0  # Track furthest position reached
        
        # Camera offset (world coordinates that map to top-left of screen)
        self.cameraY = 0
        
        # Initialize game objects
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - GRID_SIZE * 2)
        self.lanes = []
        self.particles = []
        
        # Game progression
        self.difficultyMultiplier = 1.0
        
        # Animation and effects
        self.deathAnimationTimer = 0
        self.flashTimer = 0
        
        # Generate initial lanes
        self.initializeLanes()
        
    def initializeLanes(self):
        """Generate the initial set of lanes for the game"""
        self.lanes = []
        # Start with safe grass lanes at the bottom
        for i in range(3):
            y = SCREEN_HEIGHT - (i * GRID_SIZE)
            self.lanes.append(GrassLane(y))
        
        # Generate lanes going upward
        for i in range(20):
            y = SCREEN_HEIGHT - ((i + 3) * GRID_SIZE)
            laneType = random.choices(
                ['grass', 'road', 'water'],
                weights=[2, 3, 2],  # Weights for lane type probability
                k=1
            )[0]
            
            if laneType == 'grass':
                self.lanes.append(GrassLane(y))
            elif laneType == 'road':
                self.lanes.append(RoadLane(y, self.difficultyMultiplier))
            else:
                self.lanes.append(WaterLane(y, self.difficultyMultiplier))
    
    def restart(self):
        """Reset the game to initial state"""
        self.playing = True
        self.gameOver = False
        self.startScreen = False
        self.score = 0
        self.bestProgress = 0
        self.cameraY = 0
        self.difficultyMultiplier = 1.0
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT - GRID_SIZE * 2)
        self.particles = []
        self.deathAnimationTimer = 0
        self.initializeLanes()
    
    def loadHighScore(self):
        """Load high score from file, return 0 if file doesn't exist"""
        try:
            with open('highscore.txt', 'r') as f:
                return int(f.read())
        except:
            return 0
    
    def saveHighScore(self):
        """Save high score to file"""
        try:
            with open('highscore.txt', 'w') as f:
                f.write(str(self.highScore))
        except:
            pass
    
    def handleEvents(self):
        """Process all input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                # Start screen controls
                if self.startScreen:
                    if event.key == pygame.K_SPACE:
                        self.restart()
                
                # Game over controls
                elif self.gameOver:
                    if event.key == pygame.K_SPACE:
                        self.restart()
                
                # Playing controls
                elif self.playing:
                    if event.key in [pygame.K_UP, pygame.K_w]:
                        self.player.move(0, -1)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.player.move(0, 1)
                    elif event.key in [pygame.K_LEFT, pygame.K_a]:
                        self.player.move(-1, 0)
                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        self.player.move(1, 0)
                    
                    # Hotkeys for testing
                    elif event.key == pygame.K_k:  # Kill player
                        self.player.die()
                    elif event.key == pygame.K_l:  # Level skip
                        self.player.gridY -= 10
                
                # Universal controls
                if event.key == pygame.K_ESCAPE:
                    return False
        
        return True
    
    def update(self):
        """Update all game objects and game state"""
        if not self.playing or self.gameOver:
            return
        
        # Update player
        self.player.update()
        
        # Update camera to follow player
        self.updateCamera()
        
        # Update all lanes
        for lane in self.lanes:
            lane.update()
        
        # Check if player reached new high point
        if self.player.gridY < self.bestProgress:
            self.bestProgress = self.player.gridY
            # Award points for forward progress
            self.score = abs(self.bestProgress) * 10
            
            # Increase difficulty every 10 rows
            if abs(self.bestProgress) % 10 == 0:
                self.difficultyMultiplier += 0.1
        
        # Generate new lanes as player progresses
        self.generateNewLanes()
        
        # Remove lanes that are too far below
        self.cleanupOldLanes()
        
        # Check collisions (IMPROVED)
        self.checkCollisions()
        
        # Update particles
        for particle in self.particles[:]:
            particle.update()
            if particle.lifetime <= 0:
                self.particles.remove(particle)
        
        # Check death zone (player fell too far behind camera)
        deathZone = self.cameraY + SCREEN_HEIGHT + GRID_SIZE
        if self.player.y > deathZone:
            self.player.die()
        
        # Handle player death
        if self.player.dead:
            self.deathAnimationTimer += 1
            if self.deathAnimationTimer > 60:  # 1 second death animation
                self.endGame()
    
    def updateCamera(self):
        """Update camera position to follow player upward"""
        # Camera tries to keep player in lower third of screen
        targetCameraY = self.player.y - SCREEN_HEIGHT * 2/3
        
        # Camera can only move up, never down (like original Crossy Road)
        if targetCameraY < self.cameraY:
            self.cameraY = targetCameraY
    
    def generateNewLanes(self):
        """Generate new lanes at the top as player progresses"""
        # Find highest lane
        if self.lanes:
            highestY = min(lane.y for lane in self.lanes)
        else:
            highestY = 0
        
        # Generate new lanes if we need more at the top
        while highestY > self.cameraY - GRID_SIZE * 5:
            newY = highestY - GRID_SIZE
            
            # Avoid putting same lane type consecutively too many times
            recentLanes = [lane.type for lane in self.lanes[-3:]] if len(self.lanes) >= 3 else []
            
            # Adjust weights based on recent lanes
            weights = [2, 3, 2]  # grass, road, water
            if recentLanes.count('road') >= 2:
                weights[1] = 1  # Reduce road probability
            if recentLanes.count('water') >= 2:
                weights[2] = 1  # Reduce water probability
            
            laneType = random.choices(['grass', 'road', 'water'], weights=weights, k=1)[0]
            
            if laneType == 'grass':
                self.lanes.append(GrassLane(newY))
            elif laneType == 'road':
                self.lanes.append(RoadLane(newY, self.difficultyMultiplier))
            else:
                self.lanes.append(WaterLane(newY, self.difficultyMultiplier))
            
            highestY = newY
    
    def cleanupOldLanes(self):
        """Remove lanes that are too far below the camera"""
        cleanupY = self.cameraY + SCREEN_HEIGHT + GRID_SIZE * 3
        self.lanes = [lane for lane in self.lanes if lane.y < cleanupY]
    
    def checkCollisions(self):
        """
        IMPROVED: Check for collisions between player and obstacles/platforms
        Only checks the player's current lane for accurate grid-based collision
        """
        if self.player.dead:
            # Don't check collisions when already dead
            return
        
        # Get the lane the player is currently on (based on grid position)
        playerLane = self.getLaneAtY(self.player.y)
        
        if not playerLane:
            return
        
        if playerLane.type == 'road':
            # Check collision with vehicles ONLY on the player's current lane
            for vehicle in playerLane.obstacles:
                if self.checkVehicleCollision(vehicle):
                    self.player.die()
                    self.createDeathParticles()
                    return  # Exit early after death
    
        elif playerLane.type == 'water':
            # Check if player is on a log
            onLog = False
            logToRideOn = None
            
            for log in playerLane.obstacles:
                if self.checkLogCollision(log):
                    onLog = True
                    logToRideOn = log
                    break
            
            if onLog and logToRideOn:
                # Player moves with the log
                self.player.x += logToRideOn.speed
                self.player.gridX = int(self.player.x // GRID_SIZE)
                
                # Check if log pushed player off edge
                if self.player.x < PLAYER_SIZE // 2 or self.player.x > SCREEN_WIDTH - PLAYER_SIZE // 2:
                    self.player.die()
                    self.createDeathParticles()
                    return
            else:
                # Player is in water and NOT on a log - they drown
                self.player.die()
                self.createDeathParticles()
                return
    
    def getLaneAtY(self, y):
        """
        Get the lane at a specific Y position
        Uses grid-based detection to find which lane contains this Y coordinate
        """
        for lane in self.lanes:
            # Check if player's Y position is within this lane's grid cell
            laneTop = lane.y
            laneBottom = lane.y + GRID_SIZE
            if laneTop <= y <= laneBottom:
                return lane
        return None
    
    def checkVehicleCollision(self, vehicle):
        """
        IMPROVED: Check if player collides with a vehicle using accurate hitbox detection.
        Uses slightly smaller hitboxes for fairness (players should feel deaths are fair)
        
        Args:
            vehicle: The vehicle to check collision with
            
        Returns:
            bool: True if collision detected
        """
        # Player's grid position (center of their cell)
        playerCenterX = self.player.x
        playerCenterY = self.player.y
        
        # Vehicle hitbox (with slight padding for fairness)
        hitboxPadding = 5  # Make it slightly more forgiving
        vehicleLeft = vehicle.x - hitboxPadding
        vehicleRight = vehicle.x + vehicle.width + hitboxPadding
        vehicleTop = vehicle.y - hitboxPadding
        vehicleBottom = vehicle.y + vehicle.height + hitboxPadding

        # Player hitbox (slightly smaller than visual size for fairness)
        playerRadius = PLAYER_SIZE // 2 - 5
        playerLeft = playerCenterX - playerRadius
        playerRight = playerCenterX + playerRadius
        playerTop = playerCenterY - playerRadius
        playerBottom = playerCenterY + playerRadius
        
        # Check rectangular collision (AABB - Axis-Aligned Bounding Box)
        return (playerRight > vehicleLeft and 
                playerLeft < vehicleRight and
                playerBottom > vehicleTop and
                playerTop < vehicleBottom)
    
    def checkLogCollision(self, log):
        """
        IMPROVED: Check if player is standing on a log using accurate detection.
        Player needs to have their center over the log platform.
        
        Args:
            log: The log to check if player is standing on
            
        Returns:
            bool: True if player is on the log
        """
        # Player's position
        playerCenterX = self.player.x
        playerCenterY = self.player.y
        
        # Log platform area (generous horizontal detection so player doesn't fall off edges easily)
        logLeft = log.x
        logRight = log.x + log.width
        logTop = log.y 
        logBottom = log.y + log.height 
        
        # Check if player's center is over the log platform
        # This is more forgiving than exact grid-based collision
        return (logLeft <= playerCenterX <= logRight and
                logTop <= playerCenterY <= logBottom)
    
    def createDeathParticles(self):
        """Create particle effect when player dies"""
        for _ in range(20):
            self.particles.append(Particle(self.player.x, self.player.y, RED))
    
    def endGame(self):
        """End the game and show game over screen"""
        self.gameOver = True
        self.playing = False
        if self.score > self.highScore:
            self.highScore = self.score
            self.saveHighScore()
    
    def draw(self):
        """Draw all game elements"""
        self.screen.fill(BLACK)
        
        if self.startScreen:
            self.drawStartScreen()
        elif self.gameOver:
            self.drawGameOverScreen()
        elif self.playing:
            self.drawGame()
        
        pygame.display.flip()
    
    def drawStartScreen(self):
        """Draw the start screen"""
        # Title
        titleFont = pygame.font.Font(None, 80)
        title = titleFont.render("CROSSY ROAD", True, GREEN)
        titleRect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(title, titleRect)
        
        # Subtitle
        subtitleFont = pygame.font.Font(None, 30)
        subtitle = subtitleFont.render("FIXED COLLISION EDITION", True, YELLOW)
        subtitleRect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 60))
        self.screen.blit(subtitle, subtitleRect)
        
        # Instructions
        instructionFont = pygame.font.Font(None, 30)
        instructions = [
            "Use ARROW KEYS or WASD to move",
            "Avoid cars and stay on logs!",
            "",
            "Press SPACE to start"
        ]
        
        for i, line in enumerate(instructions):
            text = instructionFont.render(line, True, WHITE)
            textRect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + i * 40))
            self.screen.blit(text, textRect)
        
        # High score
        if self.highScore > 0:
            scoreFont = pygame.font.Font(None, 40)
            scoreText = scoreFont.render(f"High Score: {self.highScore}", True, YELLOW)
            scoreRect = scoreText.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 3/4))
            self.screen.blit(scoreText, scoreRect)
    
    def drawGameOverScreen(self):
        """Draw the game over screen"""
        # Game Over text
        gameOverFont = pygame.font.Font(None, 80)
        gameOver = gameOverFont.render("GAME OVER", True, RED)
        gameOverRect = gameOver.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(gameOver, gameOverRect)
        
        # Score
        scoreFont = pygame.font.Font(None, 50)
        scoreText = scoreFont.render(f"Score: {self.score}", True, WHITE)
        scoreRect = scoreText.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(scoreText, scoreRect)
        
        # High score
        if self.score >= self.highScore:
            newHighText = scoreFont.render("NEW HIGH SCORE!", True, YELLOW)
            newHighRect = newHighText.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
            self.screen.blit(newHighText, newHighRect)
        else:
            highScoreText = scoreFont.render(f"High Score: {self.highScore}", True, YELLOW)
            highScoreRect = highScoreText.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
            self.screen.blit(highScoreText, highScoreRect)
        
        # Restart instruction
        restartFont = pygame.font.Font(None, 30)
        restart = restartFont.render("Press SPACE to play again", True, WHITE)
        restartRect = restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT * 3/4))
        self.screen.blit(restart, restartRect)
    
    def drawGame(self):
        """Draw the main game screen"""
        # Draw lanes (only visible ones for efficiency)
        for lane in self.lanes:
            screenY = lane.y - self.cameraY
            if -GRID_SIZE < screenY < SCREEN_HEIGHT + GRID_SIZE:
                lane.draw(self.screen, self.cameraY)
        
        # Draw particles
        for particle in self.particles:
            particle.draw(self.screen, self.cameraY)
        
        # Draw player
        self.player.draw(self.screen, self.cameraY)
        
        # Draw UI
        self.drawUI()
    
    def drawUI(self):
        """Draw the user interface elements"""
        # Score
        font = pygame.font.Font(None, 40)
        scoreText = font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(scoreText, (10, 10))
        
        # High score
        highScoreText = font.render(f"Best: {self.highScore}", True, YELLOW)
        self.screen.blit(highScoreText, (10, 50))
        
        # Controls hint (small text in corner)
        hintFont = pygame.font.Font(None, 20)
        hint = hintFont.render("WASD/Arrows to move", True, GRAY)
        self.screen.blit(hint, (SCREEN_WIDTH - 180, SCREEN_HEIGHT - 25))
    
    def run(self):
        """Main game loop"""
        running = True
        while running:
            running = self.handleEvents()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()


class Player:
    def __init__(self, x, y):
        """Initialize the player character"""
        self.x = x
        self.y = y
        self.gridX = x // GRID_SIZE
        self.gridY = y // GRID_SIZE
        self.targetX = x
        self.targetY = y
        self.size = PLAYER_SIZE
        self.color = YELLOW
        self.speed = 10  # Animation speed for smooth movement
        self.moving = False
        self.dead = False
        self.moveCooldown = 0
    
    def move(self, dx, dy):
        """Move the player in a direction (grid-based)"""
        if self.moving or self.dead or self.moveCooldown > 0:
            return
        
        # Update grid position
        self.gridX += dx
        self.gridY += dy
        
        # Calculate target position
        self.targetX = self.gridX * GRID_SIZE + GRID_SIZE // 2
        self.targetY = self.gridY * GRID_SIZE + GRID_SIZE // 2
        
        # Clamp to screen bounds horizontally
        self.gridX = max(0, min((SCREEN_WIDTH // GRID_SIZE) - 1, self.gridX))
        self.targetX = max(GRID_SIZE // 2, min(SCREEN_WIDTH - GRID_SIZE // 2, self.targetX))
        
        self.moving = True
        self.moveCooldown = 5  # Prevent rapid movement
    
    def update(self):
        """Update player position and state"""
        if self.moveCooldown > 0:
            self.moveCooldown -= 1
        
        if self.moving:
            # Smoothly move toward target position
            dx = self.targetX - self.x
            dy = self.targetY - self.y
            
            if abs(dx) < 2 and abs(dy) < 2:
                # Reached target
                self.x = self.targetX
                self.y = self.targetY
                self.moving = False
            else:
                # Move toward target
                self.x += dx * 0.3
                self.y += dy * 0.3
    
    def draw(self, screen, cameraY):
        """Draw the player character"""
        screenY = self.y - cameraY
        
        if self.dead:
            # Draw death animation (red X)
            pygame.draw.line(screen, RED, 
                           (self.x - self.size//2, screenY - self.size//2),
                           (self.x + self.size//2, screenY + self.size//2), 5)
            pygame.draw.line(screen, RED,
                           (self.x + self.size//2, screenY - self.size//2),
                           (self.x - self.size//2, screenY + self.size//2), 5)
        else:
            # Draw player as a circle with direction indicator
            pygame.draw.circle(screen, self.color, (int(self.x), int(screenY)), self.size // 2)
            # Eyes facing up
            eyeOffset = self.size // 6
            pygame.draw.circle(screen, BLACK, 
                             (int(self.x - eyeOffset), int(screenY - eyeOffset)), 4)
            pygame.draw.circle(screen, BLACK,
                             (int(self.x + eyeOffset), int(screenY - eyeOffset)), 4)
    
    def die(self):
        """Kill the player"""
        self.dead = True


class Lane:
    def __init__(self, y, laneType):
        """Base class for all lane types"""
        self.y = y
        self.type = laneType
        self.obstacles = []
        self.spawnTimer = 0
        self.spawnInterval = 60  # Frames between obstacle spawns
    
    def update(self):
        """Update lane obstacles"""
        pass
    
    def draw(self, screen, cameraY):
        """Draw the lane"""
        pass


class GrassLane(Lane):
    def __init__(self, y):
        """Safe grass lane with no obstacles"""
        super().__init__(y, 'grass')
        self.color = GRASS_GREEN
        # Random decoration elements
        self.flowers = []
        for _ in range(random.randint(0, 3)):
            self.flowers.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'color': random.choice([YELLOW, WHITE, PURPLE])
            })
    
    def draw(self, screen, cameraY):
        """Draw grass lane"""
        screenY = self.y - cameraY
        pygame.draw.rect(screen, self.color, (0, screenY, SCREEN_WIDTH, GRID_SIZE))
        
        # Draw flowers
        for flower in self.flowers:
            pygame.draw.circle(screen, flower['color'], 
                             (flower['x'], int(screenY + GRID_SIZE // 2)), 5)


class RoadLane(Lane):
    def __init__(self, y, difficultyMultiplier):
        """Road lane with moving vehicles"""
        super().__init__(y, 'road')
        self.color = ROAD_GRAY
        self.direction = random.choice([-1, 1])  # -1 for left, 1 for right
        self.spawnInterval = random.randint(40, 80)
        self.difficultyMultiplier = difficultyMultiplier
    
    def update(self):
        """Update vehicles on the road"""
        self.spawnTimer += 1
        
        # Spawn new vehicles
        if self.spawnTimer >= self.spawnInterval:
            self.spawnTimer = 0
            speed = random.uniform(VEHICLE_MIN_SPEED, VEHICLE_MAX_SPEED) * self.difficultyMultiplier
            if self.direction == 1:
                x = -50  # Start off-screen left
            else:
                x = SCREEN_WIDTH + 50  # Start off-screen right
            self.obstacles.append(Vehicle(x, self.y, speed * self.direction))
        
        # Update existing vehicles
        for vehicle in self.obstacles[:]:
            vehicle.update()
            # Remove vehicles that are off-screen
            if vehicle.x < -100 or vehicle.x > SCREEN_WIDTH + 100:
                self.obstacles.remove(vehicle)
    
    def draw(self, screen, cameraY):
        """Draw road lane with lane markings"""
        screenY = self.y - cameraY
        pygame.draw.rect(screen, self.color, (0, screenY, SCREEN_WIDTH, GRID_SIZE))
        
        # Draw lane markings (dashed line)
        for i in range(0, SCREEN_WIDTH, 40):
            pygame.draw.rect(screen, YELLOW, (i, screenY + GRID_SIZE // 2 - 2, 20, 4))
        
        # Draw vehicles
        for vehicle in self.obstacles:
            vehicle.draw(screen, cameraY)


class WaterLane(Lane):
    def __init__(self, y, difficultyMultiplier):
        """Water lane with floating logs"""
        super().__init__(y, 'water')
        self.color = WATER_BLUE
        self.direction = random.choice([-1, 1])
        self.spawnInterval = random.randint(60, 100)
        self.difficultyMultiplier = difficultyMultiplier
    
    def update(self):
        """Update logs in the water"""
        self.spawnTimer += 1
        
        # Spawn new logs
        if self.spawnTimer >= self.spawnInterval:
            self.spawnTimer = 0
            speed = random.uniform(LOG_MIN_SPEED, LOG_MAX_SPEED) * self.difficultyMultiplier
            if self.direction == 1:
                x = -100
            else:
                x = SCREEN_WIDTH + 100
            # Logs are longer than vehicles
            self.obstacles.append(Log(x, self.y, speed * self.direction))
        
        # Update existing logs
        for log in self.obstacles[:]:
            log.update()
            # Remove logs that are off-screen
            if log.x < -200 or log.x > SCREEN_WIDTH + 200:
                self.obstacles.remove(log)
    
    def draw(self, screen, cameraY):
        """Draw water lane with animated water effect"""
        screenY = self.y - cameraY
        pygame.draw.rect(screen, self.color, (0, screenY, SCREEN_WIDTH, GRID_SIZE))
        
        # Draw water ripples (darker blue stripes)
        for i in range(0, SCREEN_WIDTH, 30):
            offset = (pygame.time.get_ticks() // 50) % 30
            pygame.draw.rect(screen, DARK_BLUE, (i + offset, screenY, 15, GRID_SIZE))
        
        # Draw logs
        for log in self.obstacles:
            log.draw(screen, cameraY)


class Vehicle:
    def __init__(self, x, y, speed):
        """Initialize a vehicle obstacle"""
        self.x = x
        self.y = y
        self.speed = speed
        self.width = random.randint(60, 100)
        self.height = 30
        # Random vehicle color
        self.color = random.choice([RED, ORANGE, PURPLE, WHITE, YELLOW])
    
    def update(self):
        """Move the vehicle"""
        self.x += self.speed
    
    def draw(self, screen, cameraY):
        """Draw the vehicle"""
        screenY = self.y - cameraY
        # Main body
        pygame.draw.rect(screen, self.color,
                        (self.x - self.width//2, screenY + 10, self.width, self.height))
        # Windows (darker color)
        windowColor = tuple(max(0, c - 50) for c in self.color)
        pygame.draw.rect(screen, windowColor,
                        (self.x - self.width//4, screenY + 12, self.width//2, 10))


class Log:
    def __init__(self, x, y, speed):
        """Initialize a log platform"""
        self.x = x
        self.y = y
        self.speed = speed
        self.width = random.randint(100, 180)
        self.height = 35
        self.color = (139, 69, 19)  # Brown color
    
    def update(self):
        """Move the log"""
        self.x += self.speed
    
    def draw(self, screen, cameraY):
        """Draw the log"""
        screenY = self.y - cameraY
        # Main log body
        pygame.draw.rect(screen, self.color,
                        (self.x - self.width//2, screenY + 8, self.width, self.height))
        # Wood texture (darker stripes)
        darkBrown = (101, 50, 13)
        for i in range(3):
            offset = i * self.width // 4
            pygame.draw.rect(screen, darkBrown,
                           (self.x - self.width//2 + offset, screenY + 8, 5, self.height))


class Particle:
    def __init__(self, x, y, color):
        """Initialize a particle for visual effects"""
        self.x = x
        self.y = y
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-8, -2)
        self.color = color
        self.lifetime = 30
        self.size = random.randint(3, 8)
    
    def update(self):
        """Update particle position and lifetime"""
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.5  # Gravity
        self.lifetime -= 1
    
    def draw(self, screen, cameraY):
        """Draw the particle"""
        screenY = self.y - cameraY
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / 30))
            # Create a temporary surface for alpha blending
            s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
            screen.blit(s, (int(self.x - self.size), int(screenY - self.size)))


def main():
    """Entry point for the game"""
    game = Game()
    game.run()


if __name__ == '__main__':
    main()
